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
            "Permanently delete a pet and all its tasks. "
            "Only call this AFTER you have asked the user to confirm in the conversation "
            "and they have said yes. Do not call this speculatively."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {
                    "type": "string",
                    "description": "Name of the pet to delete (case-insensitive).",
                },
            },
            "required": ["pet_name"],
        },
    },
    {
        "name": "get_health_tip",
        "description": (
            "Get species-specific health guidance and triage advice for a pet concern or symptom. "
            "Use when the owner mentions a symptom ('limping', 'not eating', 'lethargic'), "
            "asks about preventive care ('flea prevention', 'dental care'), or wants general "
            "health advice for their pet. Returns urgency level, actionable guidance, and "
            "when to call a vet."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {
                    "type": "string",
                    "description": "Name of the pet (used to look up species automatically).",
                },
                "concern": {
                    "type": "string",
                    "description": "The symptom, health concern, or question (e.g., 'limping', 'not eating', 'flea prevention', 'dental care').",
                },
            },
            "required": ["pet_name", "concern"],
        },
    },
    {
        "name": "get_care_summary",
        "description": (
            "Generate a care performance summary showing task completion stats, overdue tasks, "
            "upcoming tasks, and a care streak. Use when the owner asks 'how are we doing?', "
            "'give me a weekly summary', or 'what's overdue?'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {
                    "type": "string",
                    "description": "Scope summary to one pet. Omit for all pets.",
                },
                "days": {
                    "type": "integer",
                    "description": "Lookback window in days (default 7).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "suggest_schedule",
        "description": (
            "Suggest a standard care routine for a pet based on species and life stage. "
            "Use when the owner asks 'what tasks should I set up?', 'what's a good routine "
            "for my puppy?', or 'give me a starter schedule for my cat'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {
                    "type": "string",
                    "description": "Name of the pet (species looked up automatically).",
                },
                "life_stage": {
                    "type": "string",
                    "enum": ["puppy_kitten", "adult", "senior"],
                    "description": "Life stage of the pet. Defaults to 'adult' if not specified.",
                },
            },
            "required": ["pet_name"],
        },
    },
    {
        "name": "analyze_workload",
        "description": (
            "Analyze the care schedule workload across all pets. Shows task counts by pet, "
            "busiest days of the week, and time-of-day distribution. Use when the owner asks "
            "'are my pets' schedules too crowded?', 'when are my busiest care days?', or "
            "'help me balance the schedule'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "update_pet",
        "description": (
            "Rename a pet or change its species. "
            "Use when the owner says 'rename Ozil to Max', 'Mochi is actually a cat', "
            "or 'correct my pet's species'. At least one of new_name or new_species must be provided."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {
                    "type": "string",
                    "description": "Current name of the pet to update (case-insensitive).",
                },
                "new_name": {
                    "type": "string",
                    "description": "New name for the pet. Omit to keep existing name.",
                },
                "new_species": {
                    "type": "string",
                    "description": "New species (Dog, Cat, Rabbit, Bird, Fish, Hamster, Other). Omit to keep existing.",
                },
            },
            "required": ["pet_name"],
        },
    },
    {
        "name": "update_task",
        "description": (
            "Edit any field of an existing task — description, scheduled time, "
            "due date, or recurrence frequency. "
            "Use when the owner says 'change the grooming appointment to 3pm', "
            "'make the walk weekly instead of daily', or 'rename that task'. "
            "Provide only the fields that should change; omit the rest."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Unique ID of the task to update.",
                },
                "new_description": {
                    "type": "string",
                    "description": "New description/name for the task.",
                },
                "new_time": {
                    "type": "string",
                    "description": "New scheduled time in HH:MM 24-hour format.",
                },
                "new_due_date": {
                    "type": "string",
                    "description": "New due date in YYYY-MM-DD format.",
                },
                "new_frequency": {
                    "type": "string",
                    "enum": ["once", "daily", "weekly"],
                    "description": "New recurrence frequency.",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "delete_task",
        "description": (
            "Permanently remove a task from a pet's schedule. "
            "Use when the owner says 'cancel the grooming appointment', "
            "'remove that task', or 'delete the vet visit'. "
            "Only call this AFTER you have confirmed with the user in the conversation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Unique ID of the task to delete. Use list_tasks to find it.",
                },
            },
            "required": ["task_id"],
        },
    },
]

# ---------------------------------------------------------------------------
# Role-based tool subsets
# ---------------------------------------------------------------------------

_CUSTOMER_TOOLS: set[str] = {
    "list_pets",
    "list_tasks",
    "check_conflicts",
    "get_health_tip",
    "get_care_summary",
    "suggest_schedule",
    "analyze_workload",
}

_ADMIN_TOOLS: set[str] = {
    "list_pets",
    "add_pet",
    "update_pet",
    "delete_pet",
    "list_tasks",
    "add_task",
    "update_task",
    "delete_task",
    "complete_task",
    "check_conflicts",
    "reschedule_task",
    "get_health_tip",
    "get_care_summary",
    "suggest_schedule",
    "analyze_workload",
}


def get_tool_schemas(role: str) -> list[dict[str, Any]]:
    """Return the Claude tool schemas permitted for the given role.

    Args:
        role: ``"owner"`` for the Pet Owner (wellness) agent,
              ``"admin"`` for the Admin/Vet (operations) agent.
    """
    allowed = _CUSTOMER_TOOLS if role == "owner" else _ADMIN_TOOLS
    return [s for s in TOOL_SCHEMAS if s["name"] in allowed]


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
        """Delete a pet and all its tasks. Only call after conversational confirmation."""
        pet_name: str = inp["pet_name"].strip()

        pet = _find_pet(self.owner, pet_name)
        if pet is None:
            return {"success": False, "error": f"No pet named '{pet_name}' found."}

        task_count = len(pet.tasks)
        self.owner.remove_pet(pet.pet_id)
        if self.persist:
            storage.save(self.owner)

        return {"success": True, "deleted_pet": pet_name, "tasks_removed": task_count}

    def _tool_update_pet(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Rename a pet or change its species."""
        pet_name: str = inp["pet_name"].strip()
        new_name: str | None = inp.get("new_name", "").strip() or None
        new_species: str | None = inp.get("new_species", "").strip() or None

        if not new_name and not new_species:
            return {"success": False, "error": "Provide at least new_name or new_species."}

        pet = _find_pet(self.owner, pet_name)
        if pet is None:
            return {"success": False, "error": f"No pet named '{pet_name}' found."}

        # Guard: new name must not clash with an existing pet
        if new_name and new_name.lower() != pet.name.lower():
            if any(p.name.lower() == new_name.lower() for p in self.owner.get_pets()):
                return {"success": False, "error": f"A pet named '{new_name}' already exists."}

        old_name    = pet.name
        old_species = pet.species
        if new_name:
            pet.name = new_name
        if new_species:
            pet.species = new_species

        if self.persist:
            storage.save(self.owner)

        return {
            "success": True,
            "pet_id": pet.pet_id,
            "old_name": old_name,
            "new_name": pet.name,
            "old_species": old_species,
            "new_species": pet.species,
        }

    def _tool_update_task(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Edit any combination of description, time, due_date, or frequency on a task."""
        task_id: str = inp["task_id"]
        pet, task = _find_task(self.owner, task_id)
        if task is None:
            return {"success": False, "error": f"No task with ID '{task_id}' found."}

        changes: dict[str, Any] = {}

        if new_desc := inp.get("new_description", "").strip():
            changes["description"] = (task.description, new_desc)
            task.description = new_desc

        if new_time := inp.get("new_time", "").strip():
            try:
                _validate_time(new_time)
            except ValueError as exc:
                return {"success": False, "error": str(exc)}
            changes["time"] = (task.time, new_time)
            task.time = new_time

        if new_date_str := inp.get("new_due_date", "").strip():
            try:
                new_due = date.fromisoformat(new_date_str)
            except ValueError:
                return {"success": False, "error": f"Invalid new_due_date '{new_date_str}'. Use YYYY-MM-DD."}
            changes["due_date"] = (task.due_date.isoformat(), new_due.isoformat())
            task.due_date = new_due

        if new_freq := inp.get("new_frequency", "").strip():
            if new_freq not in ("once", "daily", "weekly"):
                return {"success": False, "error": f"frequency must be once/daily/weekly, got '{new_freq}'."}
            changes["frequency"] = (task.frequency, new_freq)
            task.frequency = new_freq

        if not changes:
            return {"success": False, "error": "No fields to update were provided."}

        assert pet is not None
        conflicts = self._scheduler.detect_conflicts()
        conflict_for_pet = [w for w in conflicts if pet.name in w]

        if self.persist:
            storage.save(self.owner)

        return {
            "success": True,
            "task_id": task.task_id,
            "pet_name": pet.name,
            "description": task.description,
            "changes": {k: {"from": v[0], "to": v[1]} for k, v in changes.items()},
            "conflict_warnings": conflict_for_pet,
        }

    def _tool_delete_task(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Permanently remove a task. Only call after conversational confirmation."""
        task_id: str = inp["task_id"]

        pet, task = _find_task(self.owner, task_id)
        if task is None:
            return {"success": False, "error": f"No task with ID '{task_id}' found."}

        assert pet is not None
        description = task.description
        pet.remove_task(task_id)
        if self.persist:
            storage.save(self.owner)

        return {"success": True, "deleted_task": description, "pet_name": pet.name}

    def _tool_get_health_tip(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Return species-appropriate health guidance for a concern or symptom."""
        pet_name: str = inp["pet_name"].strip()
        concern: str = inp["concern"].strip().lower()

        pet = _find_pet(self.owner, pet_name)
        if pet is None:
            return {"success": False, "error": f"No pet named '{pet_name}' found."}

        species = pet.species.lower()
        concern_lower = concern

        # Keyword → urgency + guidance map (species-aware where relevant)
        emergency_keywords = {"seizure", "collapse", "unconscious", "breathing", "choking", "poison", "toxic", "blood", "paralysis", "pale gums"}
        vet_soon_keywords = {"limping", "lame", "vomiting", "diarrhea", "not eating", "lethargy", "lethargic", "eye", "wound", "swelling", "discharge", "loss of appetite", "weight loss", "coughing", "sneezing"}
        monitor_keywords = {"scratching", "itching", "mild", "occasional", "slight", "soft stool"}

        urgency = "routine"
        for kw in emergency_keywords:
            if kw in concern_lower:
                urgency = "emergency"
                break
        if urgency == "routine":
            for kw in vet_soon_keywords:
                if kw in concern_lower:
                    urgency = "vet_soon"
                    break
        if urgency == "routine":
            for kw in monitor_keywords:
                if kw in concern_lower:
                    urgency = "monitor"
                    break

        # Build species-specific base guidance
        species_tips: dict[str, list[str]] = {
            "dog": [
                "Ensure fresh water is always available.",
                "Check for signs of pain: whimpering, reluctance to move, or changes in posture.",
                "Monitor eating and bathroom habits — changes often signal health issues.",
                "Maintain regular vet checkups (annually for adults, twice yearly for seniors).",
            ],
            "cat": [
                "Cats hide illness well — watch for subtle changes in behavior or grooming habits.",
                "Ensure the litter box is clean; avoiding it can indicate UTI or stress.",
                "Monitor water intake — increased thirst can signal kidney issues or diabetes.",
                "Annual vet visits are essential; twice yearly for cats over 7.",
            ],
            "rabbit": [
                "Rabbits must eat constantly — a rabbit not eating for 12+ hours needs emergency care.",
                "GI stasis (gut slowdown) is life-threatening; symptoms include bloating and no droppings.",
                "Ensure unlimited hay (80% of diet) and fresh leafy greens daily.",
                "Handle gently — stress and rough handling can cause fatal cardiac events.",
            ],
            "bird": [
                "Birds hide illness instinctively — fluffed feathers, lethargy, or tail-bobbing are red flags.",
                "Ensure a balanced diet: pellets + fresh vegetables; seeds alone cause nutritional deficiency.",
                "Keep away from drafts, Teflon/PTFE cookware fumes (toxic to birds), and scented candles.",
                "Annual avian vet checkups are strongly recommended.",
            ],
            "fish": [
                "Test water parameters (ammonia, nitrite, nitrate, pH) first when fish seem unwell.",
                "Quarantine new fish for 2–4 weeks before adding to a main tank.",
                "Overfeeding is a common cause of illness — only feed what fish consume in 2 minutes.",
                "Signs of illness: clamped fins, unusual spots, erratic swimming, loss of color.",
            ],
            "hamster": [
                "Hamsters are prone to wet tail (diarrhea) — fatal within 24–48 hours; see a vet immediately.",
                "Ensure a clean cage and fresh food daily; spoiled food causes digestive issues.",
                "Handle gently and avoid waking during the day — stress weakens immunity.",
                "Check teeth regularly; overgrown teeth prevent eating.",
            ],
        }

        guidance = species_tips.get(species, [
            "Monitor your pet's behavior, appetite, and energy levels closely.",
            "Keep fresh water available at all times.",
            "Contact your vet if symptoms persist or worsen.",
        ])

        when_to_call_vet = {
            "emergency": "Call an emergency vet NOW — do not wait.",
            "vet_soon": "Schedule a vet appointment within 24–48 hours. If symptoms worsen, seek emergency care.",
            "monitor": "Monitor closely for 24 hours. If no improvement, call your vet.",
            "routine": "No immediate concern, but mention this at your next routine checkup.",
        }[urgency]

        return {
            "success": True,
            "pet_name": pet.name,
            "species": pet.species,
            "concern": inp["concern"],
            "urgency_level": urgency,
            "guidance": guidance,
            "when_to_call_vet": when_to_call_vet,
        }

    def _tool_get_care_summary(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Return task completion stats, overdue tasks, upcoming tasks, and care streak."""
        pet_name: str | None = inp.get("pet_name")
        days: int = int(inp.get("days", 7))
        today = date.today()

        all_pairs = self.owner.get_all_tasks()
        if pet_name:
            pet = _find_pet(self.owner, pet_name)
            if pet is None:
                return {"success": False, "error": f"No pet named '{pet_name}' found."}
            all_pairs = [(p, t) for p, t in all_pairs if p.name.lower() == pet_name.lower()]

        # Lookback window
        from datetime import timedelta
        window_start = today - timedelta(days=days - 1)
        window_pairs = [(p, t) for p, t in all_pairs if window_start <= t.due_date <= today]

        total = len(window_pairs)
        completed_count = sum(1 for _, t in window_pairs if t.completed)
        pending_count = total - completed_count
        completion_rate = round(completed_count / total * 100, 1) if total > 0 else 0.0

        # Overdue: due_date < today, not completed
        overdue = [
            {"pet": p.name, "description": t.description, "due": t.due_date.isoformat(), "time": t.time}
            for p, t in all_pairs
            if t.due_date < today and not t.completed
        ]

        # Upcoming: due_date in next 7 days (not completed)
        upcoming_end = today + timedelta(days=7)
        upcoming = [
            {"pet": p.name, "description": t.description, "due": t.due_date.isoformat(), "time": t.time, "frequency": t.frequency}
            for p, t in all_pairs
            if today <= t.due_date <= upcoming_end and not t.completed
        ]
        upcoming.sort(key=lambda x: x["due"])

        # Care streak: consecutive days (going back from today) with ≥1 completed task
        streak = 0
        check_day = today
        completed_dates = {t.due_date for _, t in all_pairs if t.completed}
        while check_day in completed_dates:
            streak += 1
            check_day -= timedelta(days=1)

        return {
            "success": True,
            "scope": pet_name or "all pets",
            "period_days": days,
            "total_tasks": total,
            "completed": completed_count,
            "pending": pending_count,
            "completion_rate_pct": completion_rate,
            "overdue_tasks": overdue,
            "upcoming_tasks": upcoming[:10],
            "care_streak_days": streak,
        }

    def _tool_suggest_schedule(self, inp: dict[str, Any]) -> dict[str, Any]:
        """Return a suggested care routine for a pet based on species and life stage."""
        pet_name: str = inp["pet_name"].strip()
        life_stage: str = inp.get("life_stage", "adult")

        pet = _find_pet(self.owner, pet_name)
        if pet is None:
            return {"success": False, "error": f"No pet named '{pet_name}' found."}

        species = pet.species.lower()

        # Templates: (description, recommended_time, frequency, notes)
        _T = lambda d, t, f, n: {"description": d, "recommended_time": t, "frequency": f, "notes": n}

        templates: dict[str, dict[str, list[dict]]] = {
            "dog": {
                "puppy_kitten": [
                    _T("Morning feeding", "07:00", "daily", "Puppies need 3–4 small meals per day"),
                    _T("Midday feeding", "12:00", "daily", "High-quality puppy food; follow vet's portion guide"),
                    _T("Evening feeding", "18:00", "daily", "Last meal 2–3 hours before bedtime"),
                    _T("Morning walk", "08:00", "daily", "5 minutes per month of age; avoid over-exercise"),
                    _T("Socialization & training", "16:00", "daily", "Critical window: expose to people, sounds, environments"),
                    _T("Grooming brush", "19:00", "weekly", "Builds grooming tolerance early"),
                    _T("Vet checkup & vaccinations", "09:00", "once", "Core vaccines at 8, 12, 16 weeks"),
                ],
                "adult": [
                    _T("Morning feeding", "07:00", "daily", "Split daily ration into 2 meals"),
                    _T("Evening feeding", "18:00", "daily", "Consistent meal times support digestion"),
                    _T("Morning walk", "07:30", "daily", "At least 30 min; varies by breed"),
                    _T("Evening walk", "18:30", "daily", "Mental stimulation as important as exercise"),
                    _T("Teeth brushing", "20:00", "weekly", "Reduces dental disease risk significantly"),
                    _T("Grooming & coat check", "10:00", "weekly", "Check for fleas, ticks, skin issues"),
                    _T("Annual vet wellness exam", "09:00", "once", "Heartworm test, flea/tick prevention renewal"),
                ],
                "senior": [
                    _T("Morning feeding", "07:00", "daily", "Senior formula food; may need smaller, more frequent meals"),
                    _T("Evening feeding", "18:00", "daily", "Monitor weight — seniors prone to obesity or weight loss"),
                    _T("Gentle morning walk", "08:00", "daily", "Shorter, slower walks; watch for joint stiffness"),
                    _T("Joint supplement", "07:30", "daily", "Glucosamine/chondroitin — ask vet for dosage"),
                    _T("Teeth brushing", "20:00", "weekly", "Senior dogs highly prone to dental disease"),
                    _T("Bi-annual vet wellness exam", "09:00", "once", "Every 6 months for seniors (7+ years)"),
                ],
            },
            "cat": {
                "puppy_kitten": [
                    _T("Morning feeding", "07:00", "daily", "Kitten food (high protein/fat); 3–4 meals daily"),
                    _T("Midday feeding", "12:00", "daily", "Free-feed dry or scheduled wet food"),
                    _T("Evening feeding", "18:00", "daily", "Wet food supports hydration"),
                    _T("Interactive play session", "19:00", "daily", "Critical for socialization and energy burn"),
                    _T("Litter box cleaning", "08:00", "daily", "Kittens need spotless litter; dirty box causes avoidance"),
                    _T("Grooming brush", "20:00", "weekly", "Builds tolerance; reduces hairballs"),
                    _T("Vet checkup & vaccinations", "09:00", "once", "Core vaccines at 8, 12, 16 weeks; spay/neuter discussion"),
                ],
                "adult": [
                    _T("Morning feeding", "07:00", "daily", "Measured portions; free-feeding causes obesity"),
                    _T("Evening feeding", "18:00", "daily", "Mix wet + dry for hydration and dental health"),
                    _T("Litter box cleaning", "08:00", "daily", "Minimum once daily; twice is ideal"),
                    _T("Interactive play session", "19:30", "daily", "15–20 min; prevents boredom and weight gain"),
                    _T("Grooming brush", "20:00", "weekly", "Reduces shedding and hairballs"),
                    _T("Annual vet wellness exam", "09:00", "once", "Dental check, parasite prevention, bloodwork for cats 7+"),
                ],
                "senior": [
                    _T("Morning feeding", "07:00", "daily", "Senior formula; monitor for weight changes"),
                    _T("Evening feeding", "18:00", "daily", "Wet food strongly recommended — supports kidney health"),
                    _T("Litter box cleaning", "08:00", "daily", "Arthritis can make entry difficult; use low-sided box"),
                    _T("Gentle play session", "19:00", "daily", "Low-impact: wand toys, puzzle feeders"),
                    _T("Grooming brush", "20:00", "weekly", "Senior cats groom less; check for mats and skin issues"),
                    _T("Bi-annual vet exam", "09:00", "once", "Kidney, thyroid, and dental disease common in seniors"),
                ],
            },
            "rabbit": {
                "adult": [
                    _T("Morning feeding (pellets)", "07:00", "daily", "1/4 cup per 5 lbs body weight; timothy pellets"),
                    _T("Fresh hay refill", "08:00", "daily", "Unlimited timothy hay — 80% of diet"),
                    _T("Fresh greens", "18:00", "daily", "2 cups per 5 lbs: romaine, parsley, cilantro"),
                    _T("Exercise & free-roam time", "17:00", "daily", "Minimum 3 hours out of enclosure"),
                    _T("Cage cleaning", "09:00", "weekly", "Full clean weekly; spot-clean daily"),
                    _T("Nail trim", "10:00", "once", "Every 6–8 weeks; have vet show you first"),
                ],
            },
            "bird": {
                "adult": [
                    _T("Morning feeding (pellets + fresh food)", "07:30", "daily", "60–70% pellets, 30–40% fresh vegetables"),
                    _T("Fresh water change", "07:30", "daily", "Daily is mandatory; bacteria grow quickly in water bowls"),
                    _T("Out-of-cage interaction", "17:00", "daily", "Social birds need 2+ hours daily interaction"),
                    _T("Cage spot-clean", "08:00", "daily", "Remove droppings and uneaten fresh food"),
                    _T("Full cage cleaning", "09:00", "weekly", "Disinfect thoroughly; rinse well before returning bird"),
                    _T("Nail and beak check", "10:00", "once", "Trim as needed; overgrown beak needs avian vet"),
                ],
            },
            "fish": {
                "adult": [
                    _T("Morning feeding", "08:00", "daily", "Feed only what fish consume in 2 minutes"),
                    _T("Evening feeding", "18:00", "daily", "Overfeeding is the #1 cause of poor water quality"),
                    _T("Visual health check", "08:05", "daily", "Check for unusual behavior, spots, or fin damage"),
                    _T("Water parameter test", "09:00", "weekly", "Test ammonia, nitrite, nitrate, pH"),
                    _T("Partial water change (25%)", "10:00", "weekly", "Removes nitrates; use dechlorinated water at correct temp"),
                    _T("Filter maintenance", "10:00", "once", "Rinse filter media in tank water monthly; never tap water"),
                ],
            },
            "hamster": {
                "adult": [
                    _T("Evening feeding", "19:00", "daily", "Hamsters are nocturnal; feed at dusk"),
                    _T("Fresh water check", "19:05", "daily", "Clean bottle nozzle and refill daily"),
                    _T("Wheel & toy check", "19:10", "daily", "Ensure wheel spins freely; hamsters need 8+ km/night"),
                    _T("Spot-clean cage", "09:00", "weekly", "Remove soiled bedding and uneaten fresh food"),
                    _T("Full cage cleaning", "09:00", "once", "Deep clean monthly; keep a handful of old bedding for scent"),
                    _T("Nail check", "10:00", "once", "Every 4–6 weeks; trim or provide rough surfaces to wear naturally"),
                ],
            },
        }

        species_templates = templates.get(species, {})
        stage_templates = species_templates.get(life_stage, species_templates.get("adult", []))

        if not stage_templates:
            return {
                "success": True,
                "pet_name": pet.name,
                "species": pet.species,
                "life_stage": life_stage,
                "suggestions": [],
                "note": f"No template available for {pet.species} — ask your vet for a tailored routine.",
            }

        return {
            "success": True,
            "pet_name": pet.name,
            "species": pet.species,
            "life_stage": life_stage,
            "suggestions": stage_templates,
            "note": "These are general guidelines. Adjust based on your vet's specific advice.",
        }

    def _tool_analyze_workload(self, _: dict[str, Any]) -> dict[str, Any]:
        """Analyze schedule workload across all pets."""
        all_pairs = self.owner.get_all_tasks()
        today = date.today()

        # Per-pet breakdown
        per_pet: dict[str, dict[str, int]] = {}
        for pet in self.owner.get_pets():
            tasks = pet.get_tasks()
            per_pet[pet.name] = {
                "total": len(tasks),
                "pending": sum(1 for t in tasks if not t.completed),
                "completed": sum(1 for t in tasks if t.completed),
            }

        # Day-of-week breakdown (0=Monday … 6=Sunday)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_counts: dict[str, int] = {d: 0 for d in day_names}
        for _, task in all_pairs:
            day_counts[day_names[task.due_date.weekday()]] += 1

        busiest_day = max(day_counts, key=lambda d: day_counts[d]) if day_counts else None

        # Time-of-day bucket breakdown
        buckets: dict[str, int] = {"morning (6–12)": 0, "afternoon (12–17)": 0, "evening (17–22)": 0, "night (22–6)": 0}
        for _, task in all_pairs:
            try:
                hour = int(task.time.split(":")[0])
            except (ValueError, IndexError):
                continue
            if 6 <= hour < 12:
                buckets["morning (6–12)"] += 1
            elif 12 <= hour < 17:
                buckets["afternoon (12–17)"] += 1
            elif 17 <= hour < 22:
                buckets["evening (17–22)"] += 1
            else:
                buckets["night (22–6)"] += 1

        busiest_bucket = max(buckets, key=lambda b: buckets[b]) if buckets else None

        # Simple suggestion
        suggestions: list[str] = []
        if busiest_day and day_counts[busiest_day] >= 3:
            suggestions.append(
                f"{busiest_day} is your busiest day with {day_counts[busiest_day]} tasks — "
                "consider spreading some to lighter days."
            )
        if busiest_bucket and buckets[busiest_bucket] >= 3:
            suggestions.append(
                f"Most tasks are clustered in the {busiest_bucket} — "
                "distributing across the day can reduce care fatigue."
            )
        if not suggestions:
            suggestions.append("Your schedule looks well-balanced — great job!")

        total_tasks = len(all_pairs)
        return {
            "success": True,
            "total_tasks": total_tasks,
            "per_pet": per_pet,
            "by_day_of_week": day_counts,
            "by_time_of_day": buckets,
            "busiest_day": busiest_day,
            "busiest_time_bucket": busiest_bucket,
            "suggestions": suggestions,
        }


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
