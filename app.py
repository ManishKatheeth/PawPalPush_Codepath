"""
PawPal+ Streamlit Web Application
Interactive pet care management dashboard.
"""

import uuid
from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task
import storage


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
# Global CSS — Minimalist-Skill aesthetic
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', 'SF Pro Display', 'Helvetica Neue', sans-serif !important;
}

#MainMenu, footer { visibility: hidden; }

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1100px !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #EAEAEA !important;
}

/* Tabs */
[data-testid="stTabs"] button {
    font-size: 0.85rem;
    font-weight: 500;
    color: #787774;
    letter-spacing: 0.02em;
    padding: 0.5rem 1.25rem;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #111111 !important;
    border-bottom: 2px solid #111111 !important;
}

/* Inputs */
[data-testid="stTextInput"] input {
    border: 1.5px solid #CACACA !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #111111 !important;
    box-shadow: 0 0 0 2px rgba(17,17,17,0.1) !important;
}
[data-baseweb="select"] {
    border: 1.5px solid #CACACA !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
}
[data-testid="stTimeInput"] input,
[data-testid="stDateInput"] input {
    border: 1.5px solid #CACACA !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
}
[data-testid="stTimeInput"] input:focus,
[data-testid="stDateInput"] input:focus {
    border-color: #111111 !important;
    box-shadow: 0 0 0 2px rgba(17,17,17,0.1) !important;
    outline: none !important;
}
/* Kill Streamlit's global red focus ring */
*:focus {
    outline: none !important;
}
input:focus, select:focus, textarea:focus {
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(17,17,17,0.1) !important;
    border-color: #111111 !important;
}

/* Buttons */
.stButton > button {
    background: #111111 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    transition: background 0.2s;
}
.stButton > button:hover {
    background: #333333 !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #EAEAEA;
    border-radius: 12px;
    padding: 1rem 1.25rem;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid #EAEAEA !important;
    border-radius: 12px !important;
    background: #FFFFFF !important;
}

/* Cards */
.pp-card {
    background: #FFFFFF;
    border: 1px solid #EAEAEA;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
}

/* Pet card */
.pp-pet-card {
    background: #FFFFFF;
    border: 1px solid #EAEAEA;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
}
.pp-pet-name { font-size: 1rem; font-weight: 600; color: #111111; margin-bottom: 0.2rem; }
.pp-pet-species { font-size: 0.75rem; color: #787774; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem; }

/* Pills */
.pill {
    display: inline-block;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.03em;
    padding: 0.2rem 0.65rem;
    margin-right: 0.3rem;
}
.pill-blue   { background: #E1F3FE; color: #1F6C9F; }
.pill-green  { background: #EDF3EC; color: #346538; }
.pill-yellow { background: #FBF3DB; color: #956400; }
.pill-red    { background: #FDEBEC; color: #9F2F2D; }

/* Task row */
.pp-task {
    background: #FFFFFF;
    border: 1px solid #EAEAEA;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.45rem;
    font-size: 0.875rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}
.pp-task-done    { border-left: 3px solid #346538; background: #f6fbf6; }
.pp-task-pending { border-left: 3px solid #956400; background: #fffdf5; }
.pp-task-time    { font-weight: 600; color: #111111; min-width: 3.2rem; }
.pp-task-pet     { font-weight: 500; color: #2F3437; min-width: 5rem; }
.pp-task-desc    { color: #2F3437; flex: 1; min-width: 8rem; }
.pp-task-meta    { font-size: 0.73rem; color: #787774; }

/* Conflict */
.pp-conflict {
    background: #FDEBEC;
    border: 1px solid #F5C6CB;
    border-left: 3px solid #9F2F2D;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: #9F2F2D;
}

/* Labels */
.pp-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #787774;
    margin-bottom: 0.4rem;
}

/* Divider */
.pp-divider { border: none; border-top: 1px solid #EAEAEA; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Inline SVG paw logo
# ---------------------------------------------------------------------------
PAW_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 100 100">'
    '<ellipse cx="28" cy="20" rx="9" ry="11" fill="#111"/>'
    '<ellipse cx="50" cy="14" rx="9" ry="11" fill="#111"/>'
    '<ellipse cx="72" cy="20" rx="9" ry="11" fill="#111"/>'
    '<ellipse cx="16" cy="42" rx="8" ry="10" fill="#111"/>'
    '<ellipse cx="50" cy="64" rx="28" ry="26" fill="#111"/>'
    '</svg>'
)


# ---------------------------------------------------------------------------
# Session-state bootstrap
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = storage.load()

owner: Owner = st.session_state.owner


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:1rem;">'
        f'{PAW_SVG}'
        f'<span style="font-size:1.2rem;font-weight:600;letter-spacing:-0.02em;color:#111111;">PawPal<span style="color:#787774;font-weight:400;">+</span></span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr style="border:none;border-top:1px solid #EAEAEA;margin:0 0 1rem;">', unsafe_allow_html=True)

    st.markdown('<div class="pp-label">Owner</div>', unsafe_allow_html=True)
    st.write(f"**{owner.name}**")

    st.markdown('<div class="pp-label" style="margin-top:0.75rem;">Pets</div>', unsafe_allow_html=True)
    st.write(f"**{len(owner.get_pets())}** registered")

    total_tasks = sum(len(p.get_tasks()) for p in owner.get_pets())
    st.markdown('<div class="pp-label" style="margin-top:0.75rem;">Total Tasks</div>', unsafe_allow_html=True)
    st.write(f"**{total_tasks}** scheduled")

    st.markdown('<hr style="border:none;border-top:1px solid #EAEAEA;margin:1rem 0;">', unsafe_allow_html=True)
    st.caption("PawPal+ v1.0 — Pet Care Made Easy")


# ---------------------------------------------------------------------------
# Main header — native Streamlit components (no raw HTML)
# ---------------------------------------------------------------------------
col_logo, col_title = st.columns([1, 12])
with col_logo:
    st.markdown(PAW_SVG, unsafe_allow_html=True)
with col_title:
    st.markdown("## PawPal+")

st.caption("Smart pet care — feeding, walks, meds, and appointments in one place.")
st.markdown('<hr class="pp-divider">', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_pets, tab_schedule, tab_today = st.tabs(["My Pets", "Schedule Tasks", "Today's Schedule"])


# ===========================================================================
# TAB 1 — My Pets
# ===========================================================================
with tab_pets:
    st.markdown("### My Pets")

    with st.expander("Add a New Pet", expanded=len(owner.get_pets()) == 0):
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
                    existing = [p.name.lower() for p in owner.get_pets()]
                    if new_pet_name.strip().lower() in existing:
                        st.warning(f"A pet named '{new_pet_name.strip()}' already exists.")
                    else:
                        owner.add_pet(Pet(
                            pet_id=str(uuid.uuid4()),
                            name=new_pet_name.strip(),
                            species=new_pet_species,
                        ))
                        st.success(f"Added {new_pet_name.strip()} the {new_pet_species}.")
                        storage.save(owner)
                        st.rerun()

    pets = owner.get_pets()
    if not pets:
        st.info("No pets yet. Add your first pet above.")
    else:
        st.markdown(f'<div class="pp-label" style="margin-bottom:0.75rem;">Your Pets — {len(pets)}</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(pets), 3))
        for idx, pet in enumerate(pets):
            pending = sum(1 for t in pet.get_tasks() if not t.completed)
            done = sum(1 for t in pet.get_tasks() if t.completed)
            with cols[idx % 3]:
                st.markdown(
                    f'<div class="pp-pet-card">'
                    f'<div class="pp-pet-name">{pet.name}</div>'
                    f'<div class="pp-pet-species">{pet.species}</div>'
                    f'<span class="pill pill-blue">{len(pet.get_tasks())} tasks</span>'
                    f'<span class="pill pill-green">{done} done</span>'
                    f'<span class="pill pill-yellow">{pending} pending</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ===========================================================================
# TAB 2 — Schedule Tasks
# ===========================================================================
with tab_schedule:
    st.markdown("### Schedule Tasks")

    pets = owner.get_pets()
    if not pets:
        st.warning("Add at least one pet before scheduling tasks.")
    else:
        with st.expander("Add a New Task", expanded=True):
            with st.form("add_task_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    selected_pet_name = st.selectbox("Pet", [p.name for p in pets])
                    description = st.text_input("Task Description", placeholder="e.g. Morning walk")
                    frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
                with col2:
                    task_time = st.time_input("Scheduled Time", value=time(8, 0))
                    due_date = st.date_input("Due Date", value=date.today())

                submitted = st.form_submit_button("Add Task", use_container_width=True)
                if submitted:
                    if not description.strip():
                        st.error("Please enter a task description.")
                    else:
                        target = next((p for p in pets if p.name == selected_pet_name), None)
                        if target:
                            target.add_task(Task(
                                task_id=str(uuid.uuid4()),
                                description=description.strip(),
                                time=task_time.strftime("%H:%M"),
                                frequency=frequency,
                                due_date=due_date,
                            ))
                            st.success(f"'{description.strip()}' added to {selected_pet_name}.")
                            storage.save(owner)
                            st.rerun()

        scheduler = Scheduler(owner=owner)
        all_pairs = scheduler.sort_by_time(scheduler.get_todays_schedule())

        st.markdown('<div class="pp-label" style="margin:1.25rem 0 0.5rem;">All Tasks — Sorted by Time</div>', unsafe_allow_html=True)

        if not all_pairs:
            st.info("No tasks scheduled yet.")
        else:
            freq_pill = {
                "once":   '<span class="pill pill-blue">once</span>',
                "daily":  '<span class="pill pill-green">daily</span>',
                "weekly": '<span class="pill pill-yellow">weekly</span>',
            }
            for pet, task in all_pairs:
                cls = "pp-task-done" if task.completed else "pp-task-pending"
                fp = freq_pill.get(task.frequency, task.frequency)
                st.markdown(
                    f'<div class="pp-task {cls}">'
                    f'<span class="pp-task-time">{task.time}</span>'
                    f'<span class="pp-task-pet">{pet.name}</span>'
                    f'<span class="pp-task-desc">{task.description}</span>'
                    f'{fp}'
                    f'<span class="pp-task-meta">Due {task.due_date}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ===========================================================================
# TAB 3 — Today's Schedule
# ===========================================================================
with tab_today:
    st.markdown("### Today's Schedule")

    scheduler = Scheduler(owner=owner)
    pets = owner.get_pets()

    # Conflict warnings
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        st.markdown('<div class="pp-label" style="margin-bottom:0.4rem;">Conflicts Detected</div>', unsafe_allow_html=True)
        for warning in conflicts:
            st.markdown(f'<div class="pp-conflict">&#9888; {warning}</div>', unsafe_allow_html=True)

    # Filters
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        pet_filter = st.selectbox("Filter by Pet", ["All Pets"] + [p.name for p in pets])
    with col_f2:
        status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Completed"])

    # Build filtered list
    filtered = scheduler.filter_by_pet(pet_filter) if pet_filter != "All Pets" else scheduler.get_todays_schedule()
    if status_filter == "Pending":
        filtered = [(p, t) for p, t in filtered if not t.completed]
    elif status_filter == "Completed":
        filtered = [(p, t) for p, t in filtered if t.completed]
    filtered = scheduler.sort_by_time(filtered)

    # Metrics
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    total = len(filtered)
    done_count = sum(1 for _, t in filtered if t.completed)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total", total)
    m2.metric("Done", done_count)
    m3.metric("Pending", total - done_count)

    st.markdown('<hr class="pp-divider">', unsafe_allow_html=True)

    if not filtered:
        st.info("No tasks match the current filters.")
    else:
        st.markdown('<div class="pp-label" style="margin-bottom:0.75rem;">Tasks</div>', unsafe_allow_html=True)
        freq_pill = {
            "once":   '<span class="pill pill-blue">once</span>',
            "daily":  '<span class="pill pill-green">daily</span>',
            "weekly": '<span class="pill pill-yellow">weekly</span>',
        }

        for pet, task in filtered:
            col_chk, col_row = st.columns([1, 11])
            with col_chk:
                checked = st.checkbox("", value=task.completed, key=f"chk_{task.task_id}")
            with col_row:
                cls = "pp-task-done" if task.completed else "pp-task-pending"
                fp = freq_pill.get(task.frequency, task.frequency)
                st.markdown(
                    f'<div class="pp-task {cls}" style="margin-bottom:0;">'
                    f'<span class="pp-task-time">{task.time}</span>'
                    f'<span class="pp-task-pet">{pet.name}</span>'
                    f'<span class="pp-task-desc">{task.description}</span>'
                    f'{fp}'
                    f'<span class="pp-task-meta">Due {task.due_date}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            if checked and not task.completed:
                next_task = scheduler.handle_recurring(task, pet)
                if next_task:
                    st.success(f"'{task.description}' done. Next {task.frequency} occurrence: {next_task.due_date}.")
                else:
                    task.mark_complete()
                    st.success(f"'{task.description}' marked complete.")
                storage.save(owner)
                st.rerun()
            elif not checked and task.completed:
                task.completed = False
                storage.save(owner)
                st.rerun()
