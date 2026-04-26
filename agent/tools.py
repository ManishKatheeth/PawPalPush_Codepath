"""
Tool definitions and executor for the PawPal+ agent.

Each tool wraps existing Scheduler / Pet / Owner methods and exposes a
JSON schema that Claude's tool-use API can consume.  The executor validates
inputs, calls the underlying domain logic, and returns JSON-serialisable
dicts.  Exceptions are caught and returned as structured errors so the
agent loop never crashes.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import date, datetime
from typing import Any

import storage
from pawpal_system import Owner, Pet, Scheduler, Task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool schema definitions (fed directly to the Anthropic API)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "list_pets",
        "description": "Return all pets registered under the current owner.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "add_pet",
        "description": "Register a new pet for the owner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The pet's name (must be unique).",
                },
                "species": {
                    "type": "string",
                    "description": "Species of the pet, e.g. Dog, Cat, Rabbit, Bird, Fish, Hamster, Other.",
                },
            },
            "required": ["name", "species"],
        },
    },
    {
        "name": "list_tasks",
        "description": (
            "List tasks for the owner, with optional filters. "
            "Pass pet_name to filter by pet, completed to filter by status, "
            "and due_date (YYYY-MM-DD) to filter by date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {
                    "type": "string",
                    "description": "Filter tasks to this pet only (case-insensitive).",
                },
                "completed": {
                    "type": "boolean",
                    "description": "If true, return only completed tasks; if false, only pending.",
                },
                "due_date": {
                    "type": "string",
                    "description": "Filter tasks due on this date (YYYY-MM-DD).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "add_task",
        "description": (
            "Schedule a new care task for a pet. "
            "Returns the created task details and any conflict warnings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {
                    "type": "string",
                    "description": "Name of the pet to add the task for.",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of the task.",
                },
                "time": {
                    "type": "string",
                    "description": "Scheduled time in HH:MM 24-hour format.",
                },
                "frequency": {
                    "type": "string",
                    "enum": ["once", "daily", "weekly"],
                    "description": "How often the task recurs.",
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format. Defaults to today.",
                },
            },
            "required": ["pet_name", "description", "time", "frequency"],
        },
    },
    {
        "name": "complete_task",
        "description": (
            "Mark a task as completed. For recurring tasks (daily/weekly) "
            "this automatically schedules the next occurrence."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The unique ID of the task to complete.",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "check_conflicts",
        "description": (
            "Check for scheduling conflicts (two tasks at the same time) "
            "across all pets, or optionally for a specific pet."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {
                    "type": "string",
                    "description": "If provided, check conflicts only for this pet.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "reschedule_task",
        "description": "Move a task to a new time and/or date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The unique ID of the task to reschedule.",
                },
                "new_time": {
                    "type": "string",
                    "description": "New scheduled time in HH:MM 24-hour format.",
                },
                "new_due_date": {
                    "type": "string",
                    "description": "New due date in YYYY-MM-DD format (optional).",
                },
            },
            "required": ["task_id", "new_time"],
        },
    },
    {
        "name": "delete_pet",
        "description": (
            "Delete a pet and all its tasks. "
            "DESTRUCTIVE — requires confirmed=true to execute."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {
                    "type": "string",
                    "description": "Name of the pet to delete.",
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Must be true to proceed. If false or missing, returns a confirmation prompt.",
                },
            },
            "required": ["pet_name"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """Wraps domain objects and executes tool calls by name.

    Args:
        owner: The Owner instance whose data the tools operate on.
        persist: If True, call storage.save() after every mutating tool call.
    """

    def __init__(self, owner: Owner, persist: bool = True) -> None:
        self.owner = owner
        self.persist = persist
        self._scheduler = Scheduler(owner)

    # ------------------------------------------------------------------
    # Public dispatch
    # ------------------------------------------------------------------

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call by name and return a JSON-serialisable result.

        Args:
            tool_name: One of the names defined in TOOL_SCHEMAS.
            tool_input: The validated input dict from Claude's tool-use block.

        Returns:
            A dict with at minimum a "success" key.  On error, "error" key
            contains the problem description.
        """
        start = time.monotonic()
        result: dict[str, Any] = {"success": False, "error": "not executed"}
        try:
            handler = getattr(self, f"_tool_{tool_name}", None)
            if handler is None:
                result = {"success": False, "error": f"Unknown tool: {tool_name}"}
            else:
                result = handler(tool_input)
        except Exception as exc:
            logger.exception("Tool %s raised an unexpected error", tool_name)
            result = {"success": False, "error": str(exc)}
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            logger.info(
                "tool=%s input=%s result=%s duration_ms=%.1f",
                tool_name,
                tool_input,
                result,
                duration_ms,
            )
        return result

    # ------------------------------------------------------------------
    # Individual tool implementations
    # ------------------------------------------------------------------

    def _tool_list_pets(self, _: dict[str, Any]) -> dict[str, Any]:
        """Return all pets as a list of dicts."""
        pets = [
            {
                "pet_id": p.pet_id,
                "name": p.name,
                "species": p.species,
                "task_count": len(p.tasks),
            }
            for p in self.owner.get_pets()
        ]
        return {"success": True, "pets": pets, "count": len(pets)}

    def _tool_add_pet(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Add a new pet if the name is not already taken."""
        name: str = inp["name"].strip()
        species: str = inp["species"].strip()
        if not name:
            return {"success": False, "error": "Pet name cannot be empty."}
        if any(p.name.lower() == name.lower() for p in self.owner.get_pets()):
            return {"success": False, "error": f"A pet named '{name}' already exists."}
        pet = Pet(pet_id=str(uuid.uuid4()), name=name, species=species)
        self.owner.add_pet(pet)
        if self.persist:
            storage.save(self.owner)
        return {"success": True, "pet_id": pet.pet_id, "name": pet.name, "species": pet.species}

    def _tool_list_tasks(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Return tasks, optionally filtered by pet, status, or due date."""
        pairs = self.owner.get_all_tasks()

        if pet_name := inp.get("pet_name"):
            pairs = [(p, t) for p, t in pairs if p.name.lower() == pet_name.lower()]

        if (completed := inp.get("completed")) is not None:
            pairs = [(p, t) for p, t in pairs if t.completed == completed]

        if due_str := inp.get("due_date"):
            try:
                due = date.fromisoformat(due_str)
                pairs = [(p, t) for p, t in pairs if t.due_date == due]
            except ValueError:
                return {"success": False, "error": f"Invalid due_date: '{due_str}'. Use YYYY-MM-DD."}

        tasks = [
            {
                "task_id": t.task_id,
                "pet_name": p.name,
                "description": t.description,
                "time": t.time,
                "frequency": t.frequency,
                "due_date": t.due_date.isoformat(),
                "completed": t.completed,
            }
            for p, t in self._scheduler.sort_by_time(pairs)
        ]
        return {"success": True, "tasks": tasks, "count": len(tasks)}

    def _tool_add_task(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Add a task to a pet; return the new task and any conflict warnings."""
        pet_name: str = inp["pet_name"].strip()
        description: str = inp["description"].strip()
        time_str: str = inp["time"].strip()
        frequency: str = inp["frequency"].strip()
        due_str: str = inp.get("due_date", date.today().isoformat())

        # Validate inputs
        if not description:
            return {"success": False, "error": "Task description cannot be empty."}
        if frequency not in ("once", "daily", "weekly"):
            return {"success": False, "error": f"frequency must be once/daily/weekly, got '{frequency}'."}
        try:
            _validate_time(time_str)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        try:
            due = date.fromisoformat(due_str)
        except ValueError:
            return {"success": False, "error": f"Invalid due_date '{due_str}'. Use YYYY-MM-DD."}

        pet = _find_pet(self.owner, pet_name)
        if pet is None:
            return {"success": False, "error": f"No pet named '{pet_name}' found."}

        task = Task(
            task_id=str(uuid.uuid4()),
            description=description,
            time=time_str,
            frequency=frequency,
            due_date=due,
        )
        pet.add_task(task)

        conflicts = self._scheduler.detect_conflicts()
        conflict_for_pet = [w for w in conflicts if pet.name in w]

        if self.persist:
            storage.save(self.owner)

        return {
            "success": True,
            "task_id": task.task_id,
            "pet_name": pet.name,
            "description": task.description,
            "time": task.time,
            "frequency": task.frequency,
            "due_date": task.due_date.isoformat(),
            "conflict_warnings": conflict_for_pet,
        }

    def _tool_complete_task(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Mark a task complete; schedule next occurrence for recurring tasks."""
        task_id: str = inp["task_id"]
        pet, task = _find_task(self.owner, task_id)
        if task is None:
            return {"success": False, "error": f"No task with ID '{task_id}' found."}
        if task.completed:
            return {"success": False, "error": f"Task '{task.description}' is already completed."}

        assert pet is not None
        next_task = self._scheduler.handle_recurring(task, pet)

        if self.persist:
            storage.save(self.owner)

        result: dict[str, Any] = {
            "success": True,
            "completed_task_id": task.task_id,
            "description": task.description,
        }
        if next_task:
            result["next_occurrence"] = {
                "task_id": next_task.task_id,
                "due_date": next_task.due_date.isoformat(),
                "time": next_task.time,
                "frequency": next_task.frequency,
            }
        return result

    def _tool_check_conflicts(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Run conflict detection, optionally scoped to one pet."""
        all_conflicts = self._scheduler.detect_conflicts()

        if pet_name := inp.get("pet_name"):
            pet = _find_pet(self.owner, pet_name)
            if pet is None:
                return {"success": False, "error": f"No pet named '{pet_name}' found."}
            filtered = [w for w in all_conflicts if pet.name in w]
            return {"success": True, "conflicts": filtered, "count": len(filtered), "scoped_to": pet.name}

        return {"success": True, "conflicts": all_conflicts, "count": len(all_conflicts)}

    def _tool_reschedule_task(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Move a task to a new time and/or due date."""
        task_id: str = inp["task_id"]
        new_time: str = inp["new_time"].strip()

        try:
            _validate_time(new_time)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}

        pet, task = _find_task(self.owner, task_id)
        if task is None:
            return {"success": False, "error": f"No task with ID '{task_id}' found."}

        old_time = task.time
        task.time = new_time

        if new_due_str := inp.get("new_due_date"):
            try:
                task.due_date = date.fromisoformat(new_due_str)
            except ValueError:
                # Roll back the time change before returning error
                task.time = old_time
                return {"success": False, "error": f"Invalid new_due_date '{new_due_str}'. Use YYYY-MM-DD."}

        conflicts = self._scheduler.detect_conflicts()
        assert pet is not None
        conflict_for_pet = [w for w in conflicts if pet.name in w]

        if self.persist:
            storage.save(self.owner)

        return {
            "success": True,
            "task_id": task.task_id,
            "description": task.description,
            "old_time": old_time,
            "new_time": task.time,
            "due_date": task.due_date.isoformat(),
            "conflict_warnings": conflict_for_pet,
        }

    def _tool_delete_pet(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Delete a pet (destructive — requires confirmed=True)."""
        pet_name: str = inp["pet_name"].strip()
        confirmed: bool = inp.get("confirmed", False)

        pet = _find_pet(self.owner, pet_name)
        if pet is None:
            return {"success": False, "error": f"No pet named '{pet_name}' found."}

        if not confirmed:
            return {
                "success": False,
                "requires_confirmation": True,
                "message": (
                    f"Deleting '{pet_name}' will permanently remove the pet and all "
                    f"{len(pet.tasks)} task(s). Please confirm by calling this tool again "
                    "with confirmed=true."
                ),
            }

        self.owner.pets = [p for p in self.owner.pets if p.pet_id != pet.pet_id]
        if self.persist:
            storage.save(self.owner)

        return {"success": True, "deleted_pet": pet_name}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _find_pet(owner: Owner, name: str) -> Pet | None:
    """Case-insensitive pet lookup."""
    return next((p for p in owner.get_pets() if p.name.lower() == name.lower()), None)


def _find_task(owner: Owner, task_id: str) -> tuple[Pet | None, Task | None]:
    """Find a task by ID across all pets; return (pet, task) or (None, None)."""
    for pet in owner.get_pets():
        for task in pet.get_tasks():
            if task.task_id == task_id:
                return pet, task
    return None, None


def _validate_time(time_str: str) -> None:
    """Validate HH:MM format and raise ValueError with a clear message if invalid."""
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        raise ValueError(f"time must be in HH:MM 24-hour format, got '{time_str}'.")
