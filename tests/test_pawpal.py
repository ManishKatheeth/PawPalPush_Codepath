"""
PawPal+ Test Suite
Covers task completion, pet management, sorting, recurring tasks,
conflict detection, and status filtering.
"""

import uuid
from datetime import date, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_task(
    description: str = "Test task",
    time: str = "09:00",
    frequency: str = "once",
    due_date: date | None = None,
    completed: bool = False,
) -> Task:
    """Create a Task with sensible defaults for testing."""
    return Task(
        task_id=str(uuid.uuid4()),
        description=description,
        time=time,
        frequency=frequency,
        due_date=due_date or date.today(),
        completed=completed,
    )


def make_pet(name: str = "Buddy", species: str = "dog") -> Pet:
    """Create a Pet with a unique ID for testing."""
    return Pet(pet_id=str(uuid.uuid4()), name=name, species=species)


def make_owner(name: str = "Sarah") -> Owner:
    """Create an Owner with a unique ID for testing."""
    return Owner(owner_id=str(uuid.uuid4()), name=name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTaskCompletion:
    """Tests related to the Task.mark_complete() method."""

    def test_task_completion(self) -> None:
        """mark_complete() should set completed to True."""
        task = make_task(frequency="once")
        assert task.completed is False
        task.mark_complete()
        assert task.completed is True

    def test_once_task_returns_none_on_complete(self) -> None:
        """A one-off task should not produce a next occurrence."""
        task = make_task(frequency="once")
        result = task.mark_complete()
        assert result is None


class TestPetTaskManagement:
    """Tests for adding, retrieving, and removing tasks on a Pet."""

    def test_add_task_to_pet(self) -> None:
        """Adding a task should increase the pet's task count by 1."""
        pet = make_pet()
        initial_count = len(pet.get_tasks())
        pet.add_task(make_task())
        assert len(pet.get_tasks()) == initial_count + 1

    def test_remove_task_from_pet(self) -> None:
        """Removing a task by ID should decrease the pet's task count."""
        pet = make_pet()
        task = make_task()
        pet.add_task(task)
        assert len(pet.get_tasks()) == 1
        removed = pet.remove_task(task.task_id)
        assert removed is True
        assert len(pet.get_tasks()) == 0

    def test_remove_nonexistent_task_returns_false(self) -> None:
        """Attempting to remove a task that doesn't exist should return False."""
        pet = make_pet()
        result = pet.remove_task("nonexistent-id")
        assert result is False


class TestSortByTime:
    """Tests for Scheduler.sort_by_time()."""

    def test_sort_by_time(self) -> None:
        """Tasks should be sorted in ascending chronological HH:MM order."""
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)

        t1 = make_task(time="14:00")
        t2 = make_task(time="07:30")
        t3 = make_task(time="09:15")

        pet.add_task(t1)
        pet.add_task(t2)
        pet.add_task(t3)

        scheduler = Scheduler(owner=owner)
        sorted_pairs = scheduler.sort_by_time(scheduler.get_todays_schedule())
        times = [task.time for _, task in sorted_pairs]
        assert times == sorted(times), f"Expected sorted times, got {times}"

    def test_sort_preserves_all_tasks(self) -> None:
        """Sorting should not drop any tasks."""
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)

        for hour in ["22:00", "06:00", "13:00", "08:30"]:
            pet.add_task(make_task(time=hour))

        scheduler = Scheduler(owner=owner)
        all_tasks = scheduler.get_todays_schedule()
        sorted_tasks = scheduler.sort_by_time(all_tasks)
        assert len(sorted_tasks) == len(all_tasks)


class TestRecurringTasks:
    """Tests for daily and weekly task recurrence."""

    def test_recurrence_daily(self) -> None:
        """Completing a daily task should create a new task for the next day."""
        today = date.today()
        task = make_task(frequency="daily", due_date=today)
        next_task = task.mark_complete()

        assert task.completed is True
        assert next_task is not None
        assert next_task.due_date == today + timedelta(days=1)
        assert next_task.frequency == "daily"
        assert next_task.completed is False

    def test_recurrence_weekly(self) -> None:
        """Completing a weekly task should create a new task 7 days later."""
        today = date.today()
        task = make_task(frequency="weekly", due_date=today)
        next_task = task.mark_complete()

        assert next_task is not None
        assert next_task.due_date == today + timedelta(weeks=1)

    def test_handle_recurring_adds_to_pet(self) -> None:
        """handle_recurring() should automatically add the next task to the pet."""
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)

        task = make_task(frequency="daily")
        pet.add_task(task)
        assert len(pet.get_tasks()) == 1

        scheduler = Scheduler(owner=owner)
        scheduler.handle_recurring(task, pet)

        # Original task stays; new task is appended
        assert len(pet.get_tasks()) == 2
        new_task = pet.get_tasks()[-1]
        assert new_task.completed is False


class TestConflictDetection:
    """Tests for Scheduler.detect_conflicts()."""

    def test_conflict_detection(self) -> None:
        """Two tasks at the same time for the same pet should produce a warning."""
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)

        pet.add_task(make_task(description="Walk", time="08:00"))
        pet.add_task(make_task(description="Feed", time="08:00"))

        scheduler = Scheduler(owner=owner)
        conflicts = scheduler.detect_conflicts()

        assert len(conflicts) > 0
        assert any("08:00" in warning for warning in conflicts)

    def test_no_conflict_when_different_times(self) -> None:
        """Tasks at different times should not produce any conflict warnings."""
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)

        pet.add_task(make_task(description="Walk", time="07:00"))
        pet.add_task(make_task(description="Feed", time="08:00"))

        scheduler = Scheduler(owner=owner)
        conflicts = scheduler.detect_conflicts()
        assert conflicts == []

    def test_conflict_across_different_pets_ignored(self) -> None:
        """Same time for different pets should NOT be flagged as a conflict."""
        owner = make_owner()
        buddy = make_pet(name="Buddy")
        whiskers = make_pet(name="Whiskers")
        owner.add_pet(buddy)
        owner.add_pet(whiskers)

        buddy.add_task(make_task(time="09:00"))
        whiskers.add_task(make_task(time="09:00"))

        scheduler = Scheduler(owner=owner)
        conflicts = scheduler.detect_conflicts()
        assert conflicts == []


class TestFilterByStatus:
    """Tests for Scheduler.filter_by_status()."""

    def test_filter_by_status_incomplete(self) -> None:
        """filter_by_status(False) should return only incomplete tasks."""
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)

        done_task = make_task(description="Done", completed=True)
        pending_task = make_task(description="Pending", completed=False)
        pet.add_task(done_task)
        pet.add_task(pending_task)

        scheduler = Scheduler(owner=owner)
        pending = scheduler.filter_by_status(completed=False)

        assert all(not task.completed for _, task in pending)
        assert len(pending) == 1
        assert pending[0][1].description == "Pending"

    def test_filter_by_status_completed(self) -> None:
        """filter_by_status(True) should return only completed tasks."""
        owner = make_owner()
        pet = make_pet()
        owner.add_pet(pet)

        done_task = make_task(description="Done", completed=True)
        pending_task = make_task(description="Pending", completed=False)
        pet.add_task(done_task)
        pet.add_task(pending_task)

        scheduler = Scheduler(owner=owner)
        completed = scheduler.filter_by_status(completed=True)

        assert all(task.completed for _, task in completed)
        assert len(completed) == 1
        assert completed[0][1].description == "Done"

    def test_filter_by_pet_name(self) -> None:
        """filter_by_pet() should return tasks only for the named pet."""
        owner = make_owner()
        buddy = make_pet(name="Buddy")
        whiskers = make_pet(name="Whiskers")
        owner.add_pet(buddy)
        owner.add_pet(whiskers)

        buddy.add_task(make_task(description="Buddy task"))
        whiskers.add_task(make_task(description="Whiskers task"))

        scheduler = Scheduler(owner=owner)
        buddy_tasks = scheduler.filter_by_pet("Buddy")

        assert len(buddy_tasks) == 1
        assert buddy_tasks[0][0].name == "Buddy"
