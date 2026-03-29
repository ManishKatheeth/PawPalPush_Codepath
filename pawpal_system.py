"""
PawPal+ Pet Care Management System
Core data models and scheduling logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
import uuid


@dataclass
class Task:
    """Represents a single care task for a pet.

    Attributes:
        task_id: Unique identifier for this task.
        description: Human-readable description of the task.
        time: Scheduled time in HH:MM 24-hour format.
        frequency: How often the task recurs — "once", "daily", or "weekly".
        completed: Whether the task has been marked done.
        due_date: The calendar date on which this task is due.
    """

    task_id: str
    description: str
    time: str          # HH:MM format
    frequency: str     # "once" | "daily" | "weekly"
    due_date: date
    completed: bool = False

    def mark_complete(self) -> "Task | None":
        """Mark this task as completed.

        If the task is recurring (daily or weekly), generates and returns a
        new Task instance for the next occurrence using timedelta.  The
        original task is mutated in-place (completed = True).

        Returns:
            A new Task for the next occurrence when frequency is "daily" or
            "weekly", otherwise None.
        """
        self.completed = True

        if self.frequency == "daily":
            next_due = self.due_date + timedelta(days=1)
        elif self.frequency == "weekly":
            next_due = self.due_date + timedelta(weeks=1)
        else:
            return None

        return Task(
            task_id=str(uuid.uuid4()),
            description=self.description,
            time=self.time,
            frequency=self.frequency,
            due_date=next_due,
            completed=False,
        )


@dataclass
class Pet:
    """Represents a pet belonging to an owner.

    Attributes:
        pet_id: Unique identifier for this pet.
        name: The pet's name.
        species: The species of the pet (e.g. "dog", "cat").
        tasks: List of Task objects associated with this pet.
    """

    pet_id: str
    name: str
    species: str
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list.

        Args:
            task: The Task instance to add.
        """
        self.tasks.append(task)

    def get_tasks(self) -> list[Task]:
        """Return all tasks associated with this pet.

        Returns:
            A list of Task objects.
        """
        return self.tasks

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from this pet's list by its ID.

        Args:
            task_id: The unique identifier of the task to remove.

        Returns:
            True if a task was removed, False if no matching task was found.
        """
        original_count = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        return len(self.tasks) < original_count


class Owner:
    """Represents the pet owner who manages one or more pets.

    Attributes:
        owner_id: Unique identifier for the owner.
        name: The owner's name.
        pets: List of Pet objects belonging to this owner.
    """

    def __init__(self, owner_id: str, name: str) -> None:
        """Initialise an Owner instance.

        Args:
            owner_id: Unique identifier string for the owner.
            name: Display name for the owner.
        """
        self.owner_id = owner_id
        self.name = name
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner.

        Args:
            pet: The Pet instance to add.
        """
        self.pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner.

        Returns:
            A list of Pet objects.
        """
        return self.pets

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Aggregate every task across all pets.

        Returns:
            A list of (Pet, Task) tuples so callers can identify which pet
            each task belongs to.
        """
        result: list[tuple[Pet, Task]] = []
        for pet in self.pets:
            for task in pet.get_tasks():
                result.append((pet, task))
        return result


class Scheduler:
    """Provides scheduling, filtering, and conflict-detection utilities.

    Attributes:
        owner: The Owner whose pets and tasks are being managed.
    """

    def __init__(self, owner: Owner) -> None:
        """Initialise the Scheduler for a given owner.

        Args:
            owner: The Owner instance to manage.
        """
        self.owner = owner

    def get_todays_schedule(self) -> list[tuple[Pet, Task]]:
        """Return all (Pet, Task) pairs across the owner's pets.

        Returns:
            A flat list of (Pet, Task) tuples representing today's workload.
        """
        return self.owner.get_all_tasks()

    def sort_by_time(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Sort a list of (Pet, Task) pairs chronologically by task time.

        Sorting uses the HH:MM string directly as the sort key; lexicographic
        ordering is equivalent to chronological ordering for zero-padded
        HH:MM strings.

        Args:
            tasks: A list of (Pet, Task) tuples to sort.

        Returns:
            A new list sorted in ascending time order.
        """
        return sorted(tasks, key=lambda pair: pair[1].time)

    def filter_by_pet(self, pet_name: str) -> list[tuple[Pet, Task]]:
        """Return only the tasks belonging to a specific pet.

        Args:
            pet_name: The name of the pet to filter by (case-insensitive).

        Returns:
            A list of (Pet, Task) tuples for the named pet.
        """
        return [
            (pet, task)
            for pet, task in self.get_todays_schedule()
            if pet.name.lower() == pet_name.lower()
        ]

    def filter_by_status(self, completed: bool) -> list[tuple[Pet, Task]]:
        """Return tasks filtered by their completion status.

        Args:
            completed: If True, return completed tasks; if False, return
                       pending tasks.

        Returns:
            A list of (Pet, Task) tuples matching the requested status.
        """
        return [
            (pet, task)
            for pet, task in self.get_todays_schedule()
            if task.completed == completed
        ]

    def detect_conflicts(self) -> list[str]:
        """Identify scheduling conflicts within each pet's task list.

        A conflict occurs when two or more tasks for the same pet share an
        identical HH:MM time string.  Only exact time matches are detected;
        overlapping durations are not considered.

        Returns:
            A list of human-readable warning strings describing each conflict
            found.  An empty list means no conflicts were detected.
        """
        warnings: list[str] = []

        for pet in self.owner.get_pets():
            # Map each time slot to the tasks scheduled at that time
            time_map: dict[str, list[Task]] = {}
            for task in pet.get_tasks():
                time_map.setdefault(task.time, []).append(task)

            for time_slot, conflicting_tasks in time_map.items():
                if len(conflicting_tasks) > 1:
                    descriptions = " | ".join(t.description for t in conflicting_tasks)
                    warnings.append(
                        f"Conflict for {pet.name} at {time_slot}: [{descriptions}]"
                    )

        return warnings

    def handle_recurring(self, task: Task, pet: Pet) -> Task | None:
        """Mark a recurring task complete and register its next occurrence.

        When a daily or weekly task is completed, this method calls
        mark_complete() to get the next-occurrence Task, then automatically
        adds it to the pet's task list.

        Args:
            task: The Task to mark as complete.
            pet: The Pet that owns this task.

        Returns:
            The newly created next-occurrence Task, or None for one-off tasks.
        """
        next_task = task.mark_complete()
        if next_task is not None:
            pet.add_task(next_task)
        return next_task
