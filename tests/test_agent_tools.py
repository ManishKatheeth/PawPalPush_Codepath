"""
Unit tests for agent/tools.py — all tool wrappers are tested directly
without making any Anthropic API calls.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from pawpal_system import Owner, Pet, Task
from agent.tools import ToolExecutor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_owner() -> Owner:
    owner = Owner(owner_id=str(uuid.uuid4()), name="Tester")
    rex = Pet(pet_id=str(uuid.uuid4()), name="Rex", species="Dog")
    mochi = Pet(pet_id=str(uuid.uuid4()), name="Mochi", species="Cat")
    owner.add_pet(rex)
    owner.add_pet(mochi)
    return owner


def _make_executor(owner: Owner) -> ToolExecutor:
    """Return a ToolExecutor with persist=False (no disk writes in tests)."""
    return ToolExecutor(owner=owner, persist=False)


def _add_task_to_pet(owner: Owner, pet_name: str, **kwargs) -> Task:
    """Helper to add a task directly to a pet and return it."""
    pet = next(p for p in owner.get_pets() if p.name == pet_name)
    task = Task(
        task_id=str(uuid.uuid4()),
        description=kwargs.get("description", "Test task"),
        time=kwargs.get("time", "09:00"),
        frequency=kwargs.get("frequency", "once"),
        due_date=kwargs.get("due_date", date.today()),
        completed=kwargs.get("completed", False),
    )
    pet.add_task(task)
    return task


# ---------------------------------------------------------------------------
# list_pets
# ---------------------------------------------------------------------------

class TestListPets:
    def test_returns_all_pets(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("list_pets", {})
        assert result["success"] is True
        assert result["count"] == 2
        names = {p["name"] for p in result["pets"]}
        assert names == {"Rex", "Mochi"}

    def test_empty_owner(self) -> None:
        owner = Owner(owner_id=str(uuid.uuid4()), name="Empty")
        ex = _make_executor(owner)
        result = ex.execute("list_pets", {})
        assert result["success"] is True
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# add_pet
# ---------------------------------------------------------------------------

class TestAddPet:
    def test_add_new_pet(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("add_pet", {"name": "Biscuit", "species": "Rabbit"})
        assert result["success"] is True
        assert result["name"] == "Biscuit"
        assert len(owner.get_pets()) == 3

    def test_duplicate_name_rejected(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("add_pet", {"name": "Rex", "species": "Dog"})
        assert result["success"] is False
        assert "already exists" in result["error"].lower()

    def test_empty_name_rejected(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("add_pet", {"name": "   ", "species": "Cat"})
        assert result["success"] is False

    def test_idempotent_two_distinct_adds(self) -> None:
        """Adding the same species with different names creates distinct pets."""
        owner = _make_owner()
        ex = _make_executor(owner)
        ex.execute("add_pet", {"name": "Dog1", "species": "Dog"})
        ex.execute("add_pet", {"name": "Dog2", "species": "Dog"})
        assert len(owner.get_pets()) == 4


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------

class TestListTasks:
    def test_list_all_tasks(self) -> None:
        owner = _make_owner()
        _add_task_to_pet(owner, "Rex", description="Walk")
        _add_task_to_pet(owner, "Mochi", description="Feed")
        ex = _make_executor(owner)
        result = ex.execute("list_tasks", {})
        assert result["success"] is True
        assert result["count"] == 2

    def test_filter_by_pet(self) -> None:
        owner = _make_owner()
        _add_task_to_pet(owner, "Rex", description="Walk")
        _add_task_to_pet(owner, "Mochi", description="Feed")
        ex = _make_executor(owner)
        result = ex.execute("list_tasks", {"pet_name": "Rex"})
        assert result["count"] == 1
        assert result["tasks"][0]["pet_name"] == "Rex"

    def test_filter_by_completed(self) -> None:
        owner = _make_owner()
        _add_task_to_pet(owner, "Rex", description="Walk", completed=True)
        _add_task_to_pet(owner, "Rex", description="Feed", completed=False)
        ex = _make_executor(owner)
        result = ex.execute("list_tasks", {"completed": True})
        assert result["count"] == 1
        assert result["tasks"][0]["description"] == "Walk"

    def test_filter_by_due_date(self) -> None:
        owner = _make_owner()
        today = date.today()
        tomorrow = today + timedelta(days=1)
        _add_task_to_pet(owner, "Rex", description="Today task", due_date=today)
        _add_task_to_pet(owner, "Rex", description="Tomorrow task", due_date=tomorrow)
        ex = _make_executor(owner)
        result = ex.execute("list_tasks", {"due_date": today.isoformat()})
        assert result["count"] == 1
        assert result["tasks"][0]["description"] == "Today task"

    def test_invalid_due_date_returns_error(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("list_tasks", {"due_date": "not-a-date"})
        assert result["success"] is False


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------

class TestAddTask:
    def test_add_valid_task(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("add_task", {
            "pet_name": "Rex",
            "description": "Morning walk",
            "time": "07:30",
            "frequency": "daily",
            "due_date": date.today().isoformat(),
        })
        assert result["success"] is True
        assert result["pet_name"] == "Rex"
        assert "task_id" in result

    def test_unknown_pet_returns_error(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("add_task", {
            "pet_name": "Ghost",
            "description": "Walk",
            "time": "08:00",
            "frequency": "once",
        })
        assert result["success"] is False
        assert "Ghost" in result["error"]

    def test_invalid_time_format(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("add_task", {
            "pet_name": "Rex",
            "description": "Walk",
            "time": "8am",
            "frequency": "once",
        })
        assert result["success"] is False

    def test_invalid_frequency(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("add_task", {
            "pet_name": "Rex",
            "description": "Walk",
            "time": "08:00",
            "frequency": "monthly",
        })
        assert result["success"] is False

    def test_conflict_warning_included(self) -> None:
        owner = _make_owner()
        _add_task_to_pet(owner, "Rex", time="08:00", description="Feed")
        ex = _make_executor(owner)
        result = ex.execute("add_task", {
            "pet_name": "Rex",
            "description": "Walk",
            "time": "08:00",
            "frequency": "once",
        })
        assert result["success"] is True
        assert len(result["conflict_warnings"]) > 0

    def test_adding_twice_creates_two_tasks(self) -> None:
        """add_task is idempotent in structure — two calls = two distinct tasks."""
        owner = _make_owner()
        ex = _make_executor(owner)
        for _ in range(2):
            ex.execute("add_task", {
                "pet_name": "Rex",
                "description": "Morning walk",
                "time": "07:30",
                "frequency": "daily",
            })
        rex = next(p for p in owner.get_pets() if p.name == "Rex")
        assert len(rex.tasks) == 2


# ---------------------------------------------------------------------------
# complete_task
# ---------------------------------------------------------------------------

class TestCompleteTask:
    def test_complete_once_task(self) -> None:
        owner = _make_owner()
        task = _add_task_to_pet(owner, "Rex", frequency="once")
        ex = _make_executor(owner)
        result = ex.execute("complete_task", {"task_id": task.task_id})
        assert result["success"] is True
        assert task.completed is True
        assert "next_occurrence" not in result

    def test_complete_daily_task_creates_next(self) -> None:
        owner = _make_owner()
        task = _add_task_to_pet(owner, "Rex", frequency="daily", due_date=date.today())
        ex = _make_executor(owner)
        result = ex.execute("complete_task", {"task_id": task.task_id})
        assert result["success"] is True
        assert "next_occurrence" in result
        expected = (date.today() + timedelta(days=1)).isoformat()
        assert result["next_occurrence"]["due_date"] == expected

    def test_already_completed_returns_error(self) -> None:
        owner = _make_owner()
        task = _add_task_to_pet(owner, "Rex", completed=True)
        ex = _make_executor(owner)
        result = ex.execute("complete_task", {"task_id": task.task_id})
        assert result["success"] is False
        assert "already completed" in result["error"].lower()

    def test_nonexistent_task_id(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("complete_task", {"task_id": "does-not-exist"})
        assert result["success"] is False


# ---------------------------------------------------------------------------
# check_conflicts
# ---------------------------------------------------------------------------

class TestCheckConflicts:
    def test_no_conflicts(self) -> None:
        owner = _make_owner()
        _add_task_to_pet(owner, "Rex", time="07:00")
        _add_task_to_pet(owner, "Rex", time="08:00")
        ex = _make_executor(owner)
        result = ex.execute("check_conflicts", {})
        assert result["success"] is True
        assert result["count"] == 0

    def test_detects_conflict(self) -> None:
        owner = _make_owner()
        _add_task_to_pet(owner, "Rex", time="08:00", description="Walk")
        _add_task_to_pet(owner, "Rex", time="08:00", description="Feed")
        ex = _make_executor(owner)
        result = ex.execute("check_conflicts", {})
        assert result["count"] > 0

    def test_scoped_to_pet(self) -> None:
        owner = _make_owner()
        _add_task_to_pet(owner, "Rex", time="08:00", description="Walk")
        _add_task_to_pet(owner, "Rex", time="08:00", description="Feed")
        ex = _make_executor(owner)
        result = ex.execute("check_conflicts", {"pet_name": "Mochi"})
        assert result["success"] is True
        assert result["count"] == 0

    def test_unknown_pet_returns_error(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("check_conflicts", {"pet_name": "Nobody"})
        assert result["success"] is False


# ---------------------------------------------------------------------------
# reschedule_task
# ---------------------------------------------------------------------------

class TestRescheduleTask:
    def test_reschedule_to_new_time(self) -> None:
        owner = _make_owner()
        task = _add_task_to_pet(owner, "Rex", time="08:00")
        ex = _make_executor(owner)
        result = ex.execute("reschedule_task", {"task_id": task.task_id, "new_time": "10:00"})
        assert result["success"] is True
        assert result["new_time"] == "10:00"
        assert result["old_time"] == "08:00"
        assert task.time == "10:00"

    def test_reschedule_updates_due_date(self) -> None:
        owner = _make_owner()
        task = _add_task_to_pet(owner, "Rex", time="08:00")
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        ex = _make_executor(owner)
        result = ex.execute("reschedule_task", {
            "task_id": task.task_id,
            "new_time": "09:00",
            "new_due_date": tomorrow,
        })
        assert result["success"] is True
        assert result["due_date"] == tomorrow

    def test_invalid_time_format_rejected(self) -> None:
        owner = _make_owner()
        task = _add_task_to_pet(owner, "Rex", time="08:00")
        ex = _make_executor(owner)
        result = ex.execute("reschedule_task", {"task_id": task.task_id, "new_time": "8pm"})
        assert result["success"] is False
        assert task.time == "08:00"  # unchanged

    def test_nonexistent_task_id(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("reschedule_task", {"task_id": "ghost-id", "new_time": "09:00"})
        assert result["success"] is False


# ---------------------------------------------------------------------------
# delete_pet
# ---------------------------------------------------------------------------

class TestDeletePet:
    def test_deletes_pet(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("delete_pet", {"pet_name": "Rex"})
        assert result["success"] is True
        assert result["deleted_pet"] == "Rex"
        assert len(owner.get_pets()) == 1
        assert owner.get_pets()[0].name == "Mochi"

    def test_reports_tasks_removed(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("delete_pet", {"pet_name": "Rex"})
        assert "tasks_removed" in result

    def test_unknown_pet_returns_error(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("delete_pet", {"pet_name": "Ghost"})
        assert result["success"] is False

    def test_unknown_tool_name(self) -> None:
        owner = _make_owner()
        ex = _make_executor(owner)
        result = ex.execute("nonexistent_tool", {})
        assert result["success"] is False
        assert "Unknown tool" in result["error"]
