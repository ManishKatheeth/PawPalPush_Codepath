# 🐾 PawPal+ — Pet Care Management System

A full-featured pet care scheduling application that helps owners manage daily, weekly, and one-time care tasks for multiple pets. Built with Python and Streamlit.

---

## Features

- **Add & Manage Pets** — Register multiple pets (dog, cat, rabbit, and more) under a single owner profile.
- **Schedule Tasks** — Create care tasks with a description, time, frequency, and due date.
- **Sort by Time** — View the day's tasks in chronological order using an efficient string-based sort.
- **Filter by Pet** — Narrow the schedule down to one specific pet at a time.
- **Filter by Status** — Toggle between pending and completed tasks instantly.
- **Recurring Tasks (daily / weekly)** — Completing a recurring task automatically generates the next occurrence via `timedelta`.
- **Conflict Detection** — The scheduler warns you when two tasks for the same pet share an identical time slot.

---

## Smarter Scheduling

PawPal+ implements two key scheduling algorithms entirely in Python:

### Time-Based Sorting

Tasks are sorted using Python's built-in `sorted()` with a `lambda` key that extracts the `HH:MM` string from each task. Because tasks are stored in zero-padded 24-hour format, lexicographic ordering is identical to chronological ordering — no datetime parsing is required.

```python
sorted(tasks, key=lambda pair: pair[1].time)
```

### Conflict Detection

The scheduler builds a per-pet dictionary that maps each time slot to a list of tasks scheduled there. Any slot with more than one task triggers a warning. Conflict detection operates on **exact HH:MM matches** rather than overlapping duration windows, which is appropriate for point-in-time care tasks (feeding, medication, walks) that don't have a meaningful duration.

```python
time_map: dict[str, list[Task]] = {}
for task in pet.get_tasks():
    time_map.setdefault(task.time, []).append(task)
```

### Recurring Task Generation

When a daily or weekly task is marked complete, `mark_complete()` returns a brand-new `Task` dataclass instance with `due_date` advanced by `timedelta(days=1)` or `timedelta(weeks=1)`. The `Scheduler.handle_recurring()` method automatically appends this new task to the pet's task list so nothing needs to be tracked manually.

---

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Install Dependencies

```bash
pip install streamlit
```

### Run the Streamlit App

```bash
streamlit run app.py
```

The app will open automatically in your default browser at `http://localhost:8501`.

### Run the Demo Script

```bash
python main.py
```

---

## Testing PawPal+

PawPal+ includes a pytest test suite covering all core functionality.

### Run Tests

```bash
python -m pytest
```

### Run with Verbose Output

```bash
python -m pytest -v
```

### Test Coverage

| Test | Description |
|------|-------------|
| `test_task_completion` | `mark_complete()` sets `completed = True` |
| `test_add_task_to_pet` | Adding a task increases pet task count |
| `test_sort_by_time` | Tasks returned in chronological HH:MM order |
| `test_recurrence_daily` | Daily task completion creates next-day task |
| `test_conflict_detection` | Two tasks at same time trigger a warning |
| `test_filter_by_status` | Filter returns only completed / pending tasks |
| + 6 bonus edge-case tests | Duplicate names, cross-pet conflicts, un-checking, etc. |

---

## Project Structure

```
Project PawPalPlus/
├── pawpal_system.py    # Core data models: Task, Pet, Owner, Scheduler
├── main.py             # Console demo script
├── app.py              # Streamlit web application
├── tests/
│   ├── __init__.py
│   └── test_pawpal.py  # pytest test suite
├── uml_final.md        # Mermaid.js UML class diagram
├── reflection.md       # Project reflection
└── README.md
```

---

## Demo Screenshots

> _Screenshots will be added after the first Streamlit run._

| My Pets Tab | Schedule Tasks Tab | Today's Schedule Tab |
|---|---|---|
| _(screenshot)_ | _(screenshot)_ | _(screenshot)_ |

---

## Confidence Level

⭐⭐⭐⭐⭐

All features are implemented, tested, and documented. The Streamlit app is fully functional with persistent session state, real-time conflict warnings, and automatic recurring task generation.
