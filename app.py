"""
PawPal+ Streamlit Web Application
Interactive pet care management dashboard.
"""

import uuid
from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PawPal+",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Session-state bootstrap
# ---------------------------------------------------------------------------
def init_session_state() -> None:
    """Initialise persistent app state on first load."""
    if "owner" not in st.session_state:
        st.session_state.owner = Owner(
            owner_id=str(uuid.uuid4()),
            name="Sarah",
        )


init_session_state()
owner: Owner = st.session_state.owner


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://img.icons8.com/color/96/dog-heart.png",
        width=80,
    )
    st.title("PawPal+")
    st.markdown("---")
    st.subheader("Owner Profile")
    st.write(f"**Name:** {owner.name}")
    st.write(f"**Pets:** {len(owner.get_pets())}")
    total_tasks = sum(len(p.get_tasks()) for p in owner.get_pets())
    st.write(f"**Total Tasks:** {total_tasks}")
    st.markdown("---")
    st.caption("PawPal+ v1.0 — Pet Care Made Easy")


# ---------------------------------------------------------------------------
# Main header
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+ Pet Care Manager")
st.markdown(
    "Manage your pets' daily care tasks, detect scheduling conflicts, "
    "and keep everything on track — all in one place."
)
st.markdown("---")


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_pets, tab_schedule, tab_today = st.tabs(
    ["🐶 My Pets", "📋 Schedule Tasks", "📅 Today's Schedule"]
)


# ===========================================================================
# TAB 1 — My Pets
# ===========================================================================
with tab_pets:
    st.header("My Pets")

    # --- Add new pet form ---
    with st.expander("➕ Add a New Pet", expanded=len(owner.get_pets()) == 0):
        with st.form("add_pet_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_pet_name = st.text_input("Pet Name", placeholder="e.g. Buddy")
            with col2:
                new_pet_species = st.selectbox(
                    "Species",
                    ["Dog", "Cat", "Rabbit", "Bird", "Fish", "Hamster", "Other"],
                )
            submitted = st.form_submit_button("Add Pet", use_container_width=True)
            if submitted:
                if not new_pet_name.strip():
                    st.error("Please enter a pet name.")
                else:
                    # Check for duplicate names
                    existing_names = [p.name.lower() for p in owner.get_pets()]
                    if new_pet_name.strip().lower() in existing_names:
                        st.warning(f"A pet named '{new_pet_name.strip()}' already exists.")
                    else:
                        pet = Pet(
                            pet_id=str(uuid.uuid4()),
                            name=new_pet_name.strip(),
                            species=new_pet_species,
                        )
                        owner.add_pet(pet)
                        st.success(f"Added {new_pet_name.strip()} the {new_pet_species}!")
                        st.rerun()

    # --- Pet list ---
    pets = owner.get_pets()
    if not pets:
        st.info("No pets yet. Add your first pet above!")
    else:
        st.subheader(f"Your Pets ({len(pets)})")
        cols = st.columns(min(len(pets), 3))
        for idx, pet in enumerate(pets):
            with cols[idx % 3]:
                pending = sum(1 for t in pet.get_tasks() if not t.completed)
                done = sum(1 for t in pet.get_tasks() if t.completed)
                st.markdown(
                    f"""
                    <div style="
                        border:1px solid #e0e0e0;
                        border-radius:10px;
                        padding:16px;
                        margin-bottom:12px;
                        background:#f9f9f9;
                    ">
                        <h3 style="margin:0">🐾 {pet.name}</h3>
                        <p style="margin:4px 0;color:#666">{pet.species}</p>
                        <p style="margin:4px 0">
                            <strong>{len(pet.get_tasks())}</strong> tasks
                            &nbsp;|&nbsp;
                            <span style="color:green">{done} done</span>
                            &nbsp;|&nbsp;
                            <span style="color:orange">{pending} pending</span>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ===========================================================================
# TAB 2 — Schedule Tasks
# ===========================================================================
with tab_schedule:
    st.header("Schedule Tasks")

    pets = owner.get_pets()
    if not pets:
        st.warning("Add at least one pet before scheduling tasks.")
    else:
        pet_names = [p.name for p in pets]

        # --- Add task form ---
        with st.expander("➕ Add a New Task", expanded=True):
            with st.form("add_task_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    selected_pet_name = st.selectbox("Select Pet", pet_names)
                    description = st.text_input(
                        "Task Description", placeholder="e.g. Morning walk"
                    )
                    frequency = st.selectbox(
                        "Frequency", ["once", "daily", "weekly"]
                    )
                with col2:
                    task_time = st.time_input(
                        "Scheduled Time", value=time(8, 0)
                    )
                    due_date = st.date_input("Due Date", value=date.today())

                submitted = st.form_submit_button("Add Task", use_container_width=True)
                if submitted:
                    if not description.strip():
                        st.error("Please enter a task description.")
                    else:
                        target_pet = next(
                            (p for p in pets if p.name == selected_pet_name), None
                        )
                        if target_pet:
                            new_task = Task(
                                task_id=str(uuid.uuid4()),
                                description=description.strip(),
                                time=task_time.strftime("%H:%M"),
                                frequency=frequency,
                                due_date=due_date,
                            )
                            target_pet.add_task(new_task)
                            st.success(
                                f"Task '{description.strip()}' added to {selected_pet_name}!"
                            )
                            st.rerun()

        # --- Display all tasks sorted by time ---
        st.subheader("All Scheduled Tasks (sorted by time)")
        scheduler = Scheduler(owner=owner)
        all_pairs = scheduler.sort_by_time(scheduler.get_todays_schedule())

        if not all_pairs:
            st.info("No tasks scheduled yet.")
        else:
            for pet, task in all_pairs:
                status_icon = "✅" if task.completed else "🕐"
                status_color = "#cce5cc" if task.completed else "#fff3cd"
                st.markdown(
                    f"""
                    <div style="
                        border-left:4px solid {'#28a745' if task.completed else '#ffc107'};
                        background:{status_color};
                        border-radius:6px;
                        padding:10px 14px;
                        margin-bottom:8px;
                    ">
                        {status_icon} &nbsp;
                        <strong>{task.time}</strong> &nbsp;|&nbsp;
                        <strong>{pet.name}</strong> ({pet.species}) &nbsp;|&nbsp;
                        {task.description} &nbsp;
                        <em style="color:#555">({task.frequency}, due {task.due_date})</em>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ===========================================================================
# TAB 3 — Today's Schedule
# ===========================================================================
with tab_today:
    st.header("Today's Schedule")

    scheduler = Scheduler(owner=owner)
    pets = owner.get_pets()

    # --- Conflict warnings ---
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        st.subheader("⚠️ Scheduling Conflicts Detected")
        for warning in conflicts:
            st.warning(warning)

    # --- Filter controls ---
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        pet_filter_options = ["All Pets"] + [p.name for p in pets]
        pet_filter = st.selectbox("Filter by Pet", pet_filter_options)
    with col_f2:
        status_filter = st.selectbox(
            "Filter by Status", ["All", "Pending", "Completed"]
        )

    # --- Build filtered task list ---
    if pet_filter == "All Pets":
        filtered_pairs = scheduler.get_todays_schedule()
    else:
        filtered_pairs = scheduler.filter_by_pet(pet_filter)

    if status_filter == "Pending":
        filtered_pairs = [(p, t) for p, t in filtered_pairs if not t.completed]
    elif status_filter == "Completed":
        filtered_pairs = [(p, t) for p, t in filtered_pairs if t.completed]

    filtered_pairs = scheduler.sort_by_time(filtered_pairs)

    # --- Task count summary ---
    st.markdown("---")
    total = len(filtered_pairs)
    done_count = sum(1 for _, t in filtered_pairs if t.completed)
    pending_count = total - done_count

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Tasks", total)
    m2.metric("Completed", done_count)
    m3.metric("Pending", pending_count)
    st.markdown("---")

    # --- Task checkboxes ---
    if not filtered_pairs:
        st.info("No tasks match the current filters.")
    else:
        st.subheader("Tasks")
        for pet, task in filtered_pairs:
            col_check, col_info = st.columns([1, 9])
            with col_check:
                checked = st.checkbox(
                    label="",
                    value=task.completed,
                    key=f"chk_{task.task_id}",
                )
            with col_info:
                freq_badge = {
                    "once": "🔵 Once",
                    "daily": "🟢 Daily",
                    "weekly": "🟡 Weekly",
                }.get(task.frequency, task.frequency)

                st.markdown(
                    f"**{task.time}** &nbsp;|&nbsp; "
                    f"**{pet.name}** ({pet.species}) &nbsp;|&nbsp; "
                    f"{task.description} &nbsp;|&nbsp; {freq_badge} &nbsp;|&nbsp; "
                    f"Due: {task.due_date}"
                )

            # Handle checkbox state change
            if checked and not task.completed:
                next_task = scheduler.handle_recurring(task, pet)
                if next_task:
                    st.success(
                        f"'{task.description}' marked complete! "
                        f"Next {task.frequency} occurrence scheduled for {next_task.due_date}."
                    )
                else:
                    task.mark_complete()
                    st.success(f"'{task.description}' marked complete!")
                st.rerun()
            elif not checked and task.completed:
                # Allow un-checking (reset to pending)
                task.completed = False
                st.rerun()
