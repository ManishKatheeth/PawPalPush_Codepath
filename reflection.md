# PawPal+ Project Reflection

---

## System Design

### Core User Actions

The three most important things a user needs to do in PawPal+ are:

1. **Register their pets** — Users need a way to add named pets with a species so the system knows whose tasks belong to whom.
2. **Schedule and manage care tasks** — Users need to create tasks with a time, frequency, and due date, then mark them complete when done.
3. **Review and organize the schedule** — Users need to see all tasks sorted by time, filter by pet or status, and be warned of conflicts so they can plan their day efficiently.

---

## 1a. Initial Design — The Four Classes

Before writing any code, the system was designed around four classes with clearly separated responsibilities:

| Class | Responsibility |
|---|---|
| **Task** | Represent a single care event. Holds all data about what needs to happen, when, and how often. Knows how to mark itself complete and generate its next occurrence. |
| **Pet** | Group tasks under a named animal. Provides add/get/remove operations so each pet's workload can be managed independently. |
| **Owner** | Act as the top-level container. Holds all pets and can aggregate every task across the household into a flat list for the Scheduler to work with. |
| **Scheduler** | Provide all derived/computed views over the raw data: sorting, filtering, conflict detection, and recurring task handling. Deliberately kept separate from Owner so data and behavior stay decoupled. |

The use of Python `dataclass` for `Task` and `Pet` was an early decision — it eliminates boilerplate `__init__` and `__repr__` code while keeping the data structure explicit and readable.

---

## 1b. Design Changes During Development

The most significant change from the initial sketch was **adding `due_date` as a first-class attribute on `Task`**.

In the first design, tasks only had a `time` (HH:MM) and `frequency`. This was sufficient for a simple daily schedule display, but as soon as recurring logic was implemented it became clear that "when is this task next due?" requires a calendar date, not just a clock time. Without `due_date`:

- `mark_complete()` could not calculate the next occurrence using `timedelta`.
- The Streamlit UI could not display meaningful due-date information.
- Filtering tasks by date would be impossible in future iterations.

Adding `due_date: date` to the `Task` dataclass resolved all of these issues cleanly. The change cascaded into `main.py` (all task instantiations needed a `due_date`) and `tests/test_pawpal.py` (test helpers set `due_date=date.today()` by default), but the core logic in `Scheduler` was unaffected.

---

## 2b. Tradeoffs

### Conflict Detection — Exact Time Matches Only

The current `detect_conflicts()` implementation checks for **exact HH:MM string equality**. It does not model task duration, so two tasks at `09:00` and `09:15` would not be flagged even if the first one takes 30 minutes.

**Why this tradeoff was made:** Care tasks for pets (feeding, medication, a short walk) are typically point-in-time events rather than meetings with explicit start and end times. Adding duration would significantly complicate the data model and the UI without providing much real-world benefit for the primary use case. The exact-match approach is simple, fast (O(n) per pet), and easy to understand.

**Known limitation:** If tasks do have meaningful durations in the future (e.g., a 1-hour grooming appointment), the conflict detector would need to be upgraded to compare time intervals rather than string equality.

### Sorting — String Comparison Instead of datetime Parsing

`sort_by_time()` sorts tasks using the raw `HH:MM` string as the sort key via a `lambda`. This works correctly because:

1. Times are zero-padded to exactly two digits for both hours and minutes.
2. Lexicographic ordering of zero-padded HH:MM strings is identical to chronological ordering.

**Why this tradeoff was made:** Converting every time string to a `datetime.time` object for comparison would be more "correct" in a type-safety sense, but it adds parsing overhead and requires error handling for malformed strings. Since PawPal+ controls all task creation (via UI forms with a `st.time_input` widget), the format is always guaranteed to be valid HH:MM, making string comparison a safe and efficient choice.

**Known limitation:** If times were ever stored in 12-hour AM/PM format, string comparison would break and datetime parsing would become necessary.

---

## AI Strategy

### How AI Assistance Was Used

GitHub Copilot's autocomplete was used throughout development, primarily for:

- Generating boilerplate dataclass field definitions and `__repr__`-style methods.
- Suggesting loop bodies when iterating over `(Pet, Task)` tuple pairs.
- Completing repetitive test helper functions once the pattern was established.

Copilot's chat feature was used to ask targeted questions about specific Python patterns (e.g., "what is the correct way to use `setdefault` to build a grouping dict?") rather than asking it to generate entire functions.

### Example of a Rejected Suggestion

When implementing `detect_conflicts()`, Copilot suggested using a nested double-loop to compare every pair of tasks (O(n²)). That approach was rejected because:

1. It produces duplicate warnings (task A conflicts with B, and separately B conflicts with A).
2. A dictionary-based grouping approach (O(n)) is both faster and produces cleaner output grouped by time slot.

The manually written dictionary approach was kept instead.

### How Separate Chat Sessions Helped

Keeping the design conversation in a separate chat session from the implementation session was valuable for two reasons. First, it prevented the AI from anchoring on implementation details too early — the design discussion stayed at the class-and-responsibility level. Second, when implementation questions arose, the clean design document could be pasted into the new session as context, giving the AI a precise specification to work from rather than having to infer intent from incomplete code.

### Lead Architect Lessons

Acting as the lead architect — deciding which suggestions to accept, reject, or modify — reinforced that AI tools are most useful as accelerators for well-understood patterns (boilerplate, repetition) and least useful as decision-makers for architectural choices (data model design, algorithmic tradeoffs). The developer still needs to understand exactly what is being built and why, because the AI cannot evaluate whether a suggestion fits the project's long-term goals.
