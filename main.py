"""
PawPal+ Demo Script
Demonstrates core functionality: task management, scheduling, filtering,
conflict detection, and recurring task handling.
"""

import uuid
from datetime import date, timedelta

from pawpal_system import Owner, Pet, Scheduler, Task


def make_id() -> str:
    """Return a short unique identifier."""
    return str(uuid.uuid4())


def print_section(title: str) -> None:
    """Print a formatted section header."""
    width = 60
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_task_row(pet: Pet, task: Task) -> None:
    """Print a single task entry in a readable format."""
    status = "DONE" if task.completed else "pending"
    print(
        f"  [{status:>7}]  {task.time}  |  {pet.name:<10}  |  {task.description}"
        f"  ({task.frequency}, due {task.due_date})"
    )


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def main() -> None:
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # --- Owner ---
    sarah = Owner(owner_id=make_id(), name="Sarah")

    # --- Pets ---
    buddy = Pet(pet_id=make_id(), name="Buddy", species="dog")
    whiskers = Pet(pet_id=make_id(), name="Whiskers", species="cat")

    sarah.add_pet(buddy)
    sarah.add_pet(whiskers)

    # --- Tasks for Buddy (dog) ---
    morning_walk = Task(
        task_id=make_id(),
        description="Morning walk",
        time="07:00",
        frequency="daily",
        due_date=today,
    )
    breakfast_buddy = Task(
        task_id=make_id(),
        description="Feed Buddy breakfast",
        time="07:30",
        frequency="daily",
        due_date=today,
    )
    vet_appointment = Task(
        task_id=make_id(),
        description="Vet check-up",
        time="10:00",
        frequency="once",
        due_date=today,
    )
    weekly_bath = Task(
        task_id=make_id(),
        description="Bath time",
        time="15:00",
        frequency="weekly",
        due_date=today,
    )
    # Conflict: same time as morning_walk (07:00) for Buddy
    conflict_task = Task(
        task_id=make_id(),
        description="Flea treatment",
        time="07:00",
        frequency="once",
        due_date=today,
    )

    buddy.add_task(morning_walk)
    buddy.add_task(breakfast_buddy)
    buddy.add_task(vet_appointment)
    buddy.add_task(weekly_bath)
    buddy.add_task(conflict_task)   # intentional conflict at 07:00

    # --- Tasks for Whiskers (cat) ---
    breakfast_whiskers = Task(
        task_id=make_id(),
        description="Feed Whiskers breakfast",
        time="08:00",
        frequency="daily",
        due_date=today,
    )
    playtime = Task(
        task_id=make_id(),
        description="Interactive play session",
        time="18:00",
        frequency="daily",
        due_date=today,
    )

    whiskers.add_task(breakfast_whiskers)
    whiskers.add_task(playtime)

    # --- Scheduler ---
    scheduler = Scheduler(owner=sarah)

    # -----------------------------------------------------------------------
    # 1. Today's full schedule (unsorted)
    # -----------------------------------------------------------------------
    print_section("TODAY'S SCHEDULE  (all pets, unsorted)")
    for pet, task in scheduler.get_todays_schedule():
        print_task_row(pet, task)

    # -----------------------------------------------------------------------
    # 2. Sorted by time
    # -----------------------------------------------------------------------
    print_section("TODAY'S SCHEDULE  (sorted by time)")
    sorted_schedule = scheduler.sort_by_time(scheduler.get_todays_schedule())
    for pet, task in sorted_schedule:
        print_task_row(pet, task)

    # -----------------------------------------------------------------------
    # 3. Filter by pet
    # -----------------------------------------------------------------------
    print_section("FILTER: Buddy's tasks only")
    for pet, task in scheduler.filter_by_pet("Buddy"):
        print_task_row(pet, task)

    print_section("FILTER: Whiskers's tasks only")
    for pet, task in scheduler.filter_by_pet("Whiskers"):
        print_task_row(pet, task)

    # -----------------------------------------------------------------------
    # 4. Filter by status (all pending at start)
    # -----------------------------------------------------------------------
    print_section("FILTER: Pending tasks")
    pending = scheduler.filter_by_status(completed=False)
    print(f"  {len(pending)} pending task(s) found.")
    for pet, task in pending:
        print_task_row(pet, task)

    # -----------------------------------------------------------------------
    # 5. Conflict detection
    # -----------------------------------------------------------------------
    print_section("CONFLICT DETECTION")
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for warning in conflicts:
            print(f"  WARNING: {warning}")
    else:
        print("  No conflicts detected.")

    # -----------------------------------------------------------------------
    # 6. Mark a recurring task complete → next occurrence created automatically
    # -----------------------------------------------------------------------
    print_section("RECURRING TASK: completing morning_walk (daily)")
    print(f"  Before: Buddy has {len(buddy.get_tasks())} tasks")
    print(f"  Marking '{morning_walk.description}' complete ...")
    next_task = scheduler.handle_recurring(morning_walk, buddy)
    print(f"  After : Buddy has {len(buddy.get_tasks())} tasks")
    if next_task:
        print(
            f"  Next occurrence created: '{next_task.description}' "
            f"due {next_task.due_date} at {next_task.time}"
        )

    # -----------------------------------------------------------------------
    # 7. Filter by status after marking one complete
    # -----------------------------------------------------------------------
    print_section("FILTER: Completed tasks (after marking morning_walk done)")
    completed_tasks = scheduler.filter_by_status(completed=True)
    for pet, task in completed_tasks:
        print_task_row(pet, task)

    print("\n")


if __name__ == "__main__":
    main()
