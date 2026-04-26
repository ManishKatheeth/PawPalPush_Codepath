"""
PawPal+ Streamlit Web Application
Interactive pet care management dashboard.
"""

import uuid
from datetime import date, time

import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY from .env if present

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
# Design tokens — warm amber / terracotta palette
# ---------------------------------------------------------------------------
C_BG        = "#FBF8F3"   # warm cream canvas
C_SURFACE   = "#FFFFFF"   # card surface
C_BORDER    = "#E8DDD0"   # warm border
C_ACCENT    = "#E07B39"   # burnt orange accent
C_ACCENT2   = "#C4612A"   # deeper accent
C_DARK      = "#1C1C1C"   # near-black text
C_MID       = "#6B5B4E"   # warm mid-tone
C_MUTED     = "#9C8A7B"   # muted label
C_GREEN     = "#3D7A4A"   # done / success
C_GREEN_BG  = "#EBF5EE"
C_YELLOW    = "#8A6B00"   # pending
C_YELLOW_BG = "#FDF6DC"
C_RED       = "#9B2C2C"   # conflict
C_RED_BG    = "#FDECEA"
C_BLUE      = "#1D5FA3"   # once
C_BLUE_BG   = "#E3EEF9"


# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Lora:wght@600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', 'SF Pro Display', sans-serif !important;
    background-color: {C_BG} !important;
    color: {C_DARK} !important;
}}

#MainMenu, footer {{ visibility: hidden; }}

.block-container {{
    padding-top: 1.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1120px !important;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #2D1F14 0%, #1C1208 100%) !important;
    border-right: none !important;
}}
[data-testid="stSidebar"] * {{ color: #F5EDE4 !important; }}
[data-testid="stSidebar"] .stMarkdown p {{ color: #C4A882 !important; font-size: 0.78rem; }}

/* ── Tabs ── */
[data-testid="stTabs"] button {{
    font-size: 0.85rem;
    font-weight: 500;
    color: {C_MUTED};
    padding: 0.6rem 1.4rem;
    border-radius: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    transition: color 0.2s, border-color 0.2s;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {C_ACCENT} !important;
    border-bottom: 2px solid {C_ACCENT} !important;
    font-weight: 600;
}}
[data-testid="stTabs"] button:hover {{ color: {C_ACCENT} !important; }}
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    border-bottom: 1px solid {C_BORDER};
    gap: 0;
}}

/* ── Buttons ── */
.stButton > button {{
    background: {C_ACCENT} !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    padding: 0.55rem 1.4rem !important;
    transition: background 0.2s, transform 0.1s !important;
    box-shadow: 0 2px 8px rgba(224,123,57,0.25) !important;
}}
.stButton > button:hover {{
    background: {C_ACCENT2} !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(224,123,57,0.35) !important;
}}
.stButton > button:active {{ transform: translateY(0) !important; }}

/* ── Inputs ── */
[data-testid="stTextInput"] input {{
    border: 1.5px solid {C_BORDER} !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
    color: {C_DARK} !important;
    font-size: 0.875rem !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: {C_ACCENT} !important;
    box-shadow: 0 0 0 3px rgba(224,123,57,0.15) !important;
    outline: none !important;
}}
[data-baseweb="select"] {{
    border: 1.5px solid {C_BORDER} !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
}}
[data-testid="stTimeInput"] input,
[data-testid="stDateInput"] input {{
    border: 1.5px solid {C_BORDER} !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
}}
*:focus {{ outline: none !important; }}
input:focus, select:focus {{
    border-color: {C_ACCENT} !important;
    box-shadow: 0 0 0 3px rgba(224,123,57,0.15) !important;
    outline: none !important;
}}

/* ── Metrics ── */
[data-testid="stMetric"] {{
    background: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 14px;
    padding: 1.1rem 1.25rem;
    position: relative;
    overflow: hidden;
}}
[data-testid="stMetric"]::before {{
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    background: {C_ACCENT};
    border-radius: 14px 0 0 14px;
}}
[data-testid="stMetricValue"] {{
    font-size: 2rem !important;
    font-weight: 700 !important;
    color: {C_DARK} !important;
}}
[data-testid="stMetricLabel"] {{
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    color: {C_MUTED} !important;
}}

/* ── Expander ── */
[data-testid="stExpander"] {{
    border: 1px solid {C_BORDER} !important;
    border-radius: 12px !important;
    background: {C_SURFACE} !important;
}}
[data-testid="stExpander"] summary {{
    font-weight: 600;
    font-size: 0.9rem;
    color: {C_DARK};
}}

/* ── Alerts ── */
[data-testid="stAlert"] {{
    border-radius: 10px !important;
    font-size: 0.875rem !important;
}}

/* ── Checkbox ── */
[data-testid="stCheckbox"] label span {{
    color: {C_MID} !important;
}}

/* ── Progress ── */
.stProgress > div > div {{
    background: {C_ACCENT} !important;
    border-radius: 99px !important;
}}
.stProgress > div {{
    background: {C_BORDER} !important;
    border-radius: 99px !important;
}}

/* ── Custom components ── */
.pp-hero {{
    background: linear-gradient(135deg, #2D1F14 0%, #3D2B1A 60%, #4A3420 100%);
    border-radius: 18px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.75rem;
    position: relative;
    overflow: hidden;
}}
.pp-hero::after {{
    content: "🐾";
    position: absolute;
    right: 2rem; top: 50%;
    transform: translateY(-50%);
    font-size: 5rem;
    opacity: 0.08;
}}
.pp-hero-title {{
    font-family: 'Lora', Georgia, serif;
    font-size: 2rem;
    font-weight: 600;
    color: #FFFFFF;
    margin: 0 0 0.25rem;
    letter-spacing: -0.02em;
}}
.pp-hero-sub {{
    font-size: 0.9rem;
    color: #C4A882;
    margin: 0;
}}
.pp-hero-stat {{
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 0.75rem 1.1rem;
    text-align: center;
}}
.pp-hero-stat-val {{
    font-size: 1.6rem;
    font-weight: 700;
    color: {C_ACCENT};
    line-height: 1;
}}
.pp-hero-stat-lbl {{
    font-size: 0.68rem;
    color: #C4A882;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-top: 0.2rem;
}}

.pp-section-title {{
    font-family: 'Lora', Georgia, serif;
    font-size: 1.4rem;
    font-weight: 600;
    color: {C_DARK};
    margin: 0 0 1rem;
    letter-spacing: -0.01em;
}}

.pp-label {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: {C_MUTED};
    margin-bottom: 0.5rem;
}}

.pp-divider {{ border: none; border-top: 1px solid {C_BORDER}; margin: 1.25rem 0; }}

.pp-pet-card {{
    background: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 14px;
    padding: 1.4rem 1.5rem;
    margin-bottom: 0.75rem;
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.2s, transform 0.2s;
}}
.pp-pet-card:hover {{
    box-shadow: 0 6px 24px rgba(224,123,57,0.12);
    transform: translateY(-2px);
}}
.pp-pet-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 3px;
    background: linear-gradient(90deg, {C_ACCENT}, {C_ACCENT2});
}}
.pp-pet-emoji {{ font-size: 2.2rem; line-height: 1; margin-bottom: 0.5rem; }}
.pp-pet-name {{ font-size: 1.05rem; font-weight: 700; color: {C_DARK}; }}
.pp-pet-species {{ font-size: 0.73rem; color: {C_MUTED}; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.85rem; }}

.pill {{
    display: inline-block;
    border-radius: 9999px;
    font-size: 0.71rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    padding: 0.2rem 0.7rem;
    margin-right: 0.3rem;
}}
.pill-orange  {{ background: #FEF0E6; color: {C_ACCENT}; }}
.pill-green   {{ background: {C_GREEN_BG}; color: {C_GREEN}; }}
.pill-yellow  {{ background: {C_YELLOW_BG}; color: {C_YELLOW}; }}
.pill-blue    {{ background: {C_BLUE_BG}; color: {C_BLUE}; }}
.pill-red     {{ background: {C_RED_BG}; color: {C_RED}; }}

.pp-task {{
    background: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.45rem;
    display: flex;
    align-items: center;
    gap: 0.85rem;
    flex-wrap: wrap;
    font-size: 0.875rem;
    transition: box-shadow 0.15s;
}}
.pp-task:hover {{ box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
.pp-task-done    {{ border-left: 3px solid {C_GREEN}; background: {C_GREEN_BG}; }}
.pp-task-pending {{ border-left: 3px solid {C_ACCENT}; }}
.pp-task-time {{ font-weight: 700; color: {C_DARK}; min-width: 3.2rem; font-variant-numeric: tabular-nums; }}
.pp-task-pet  {{ font-weight: 600; color: {C_MID}; min-width: 5rem; }}
.pp-task-desc {{ color: {C_DARK}; flex: 1; min-width: 8rem; }}
.pp-task-meta {{ font-size: 0.72rem; color: {C_MUTED}; white-space: nowrap; }}

.pp-conflict {{
    background: {C_RED_BG};
    border: 1px solid #F5C6C6;
    border-left: 3px solid {C_RED};
    border-radius: 10px;
    padding: 0.8rem 1.1rem;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: {C_RED};
    font-weight: 500;
}}

.pp-empty {{
    text-align: center;
    padding: 3rem 1rem;
    color: {C_MUTED};
    font-size: 0.9rem;
    background: {C_SURFACE};
    border: 1px dashed {C_BORDER};
    border-radius: 14px;
}}
.pp-empty-icon {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}

/* Sidebar custom */
.pp-sidebar-logo {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1.5rem;
}}
.pp-sidebar-logo-text {{
    font-family: 'Lora', Georgia, serif;
    font-size: 1.25rem;
    font-weight: 600;
    color: #FFFFFF;
    letter-spacing: -0.01em;
}}
.pp-sidebar-logo-text span {{ color: {C_ACCENT}; }}
.pp-sidebar-stat {{
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.5rem;
}}
.pp-sidebar-stat-lbl {{ font-size: 0.65rem; color: #C4A882; text-transform: uppercase; letter-spacing: 0.08em; }}
.pp-sidebar-stat-val {{ font-size: 1.1rem; font-weight: 700; color: #FFFFFF; margin-top: 0.1rem; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PAW_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 100 100">'
    '<ellipse cx="28" cy="20" rx="9" ry="11" fill="#E07B39"/>'
    '<ellipse cx="50" cy="14" rx="9" ry="11" fill="#E07B39"/>'
    '<ellipse cx="72" cy="20" rx="9" ry="11" fill="#E07B39"/>'
    '<ellipse cx="16" cy="42" rx="8" ry="10" fill="#E07B39"/>'
    '<ellipse cx="50" cy="64" rx="28" ry="26" fill="#E07B39"/>'
    '</svg>'
)

SPECIES_EMOJI = {
    "Dog": "🐕", "Cat": "🐈", "Rabbit": "🐇",
    "Bird": "🦜", "Fish": "🐟", "Hamster": "🐹", "Other": "🐾",
}

FREQ_PILL = {
    "once":   '<span class="pill pill-blue">once</span>',
    "daily":  '<span class="pill pill-green">daily</span>',
    "weekly": '<span class="pill pill-yellow">weekly</span>',
}


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = storage.load()

owner: Owner = st.session_state.owner


# ---------------------------------------------------------------------------
# Derived stats
# ---------------------------------------------------------------------------
all_pets   = owner.get_pets()
all_tasks  = [(p, t) for p in all_pets for t in p.get_tasks()]
done_tasks = [(p, t) for p, t in all_tasks if t.completed]
pct_done   = int(len(done_tasks) / len(all_tasks) * 100) if all_tasks else 0


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f'<div class="pp-sidebar-logo">'
        f'{PAW_SVG}'
        f'<div class="pp-sidebar-logo-text">PawPal<span>+</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="pp-sidebar-stat">'
        f'<div class="pp-sidebar-stat-lbl">Owner</div>'
        f'<div class="pp-sidebar-stat-val">{owner.name}</div>'
        f'</div>'
        f'<div class="pp-sidebar-stat">'
        f'<div class="pp-sidebar-stat-lbl">Pets Registered</div>'
        f'<div class="pp-sidebar-stat-val">{len(all_pets)}</div>'
        f'</div>'
        f'<div class="pp-sidebar-stat">'
        f'<div class="pp-sidebar-stat-lbl">Tasks Today</div>'
        f'<div class="pp-sidebar-stat-val">{len(all_tasks)}</div>'
        f'</div>'
        f'<div class="pp-sidebar-stat">'
        f'<div class="pp-sidebar-stat-lbl">Completion Rate</div>'
        f'<div class="pp-sidebar-stat-val">{pct_done}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:1.25rem 0;">', unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.72rem;color:#7A6355;text-align:center;">PawPal+ v1.0 — Pet Care Made Easy</p>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Hero banner
# ---------------------------------------------------------------------------
hero_cols = st.columns([3, 1, 1, 1])
with hero_cols[0]:
    st.markdown(
        f'<div class="pp-hero">'
        f'<div class="pp-hero-title">Good day, {owner.name}!</div>'
        f'<div class="pp-hero-sub">Here\'s your pet care overview for today.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# Stats beside hero
for col, val, lbl in zip(
    hero_cols[1:],
    [len(all_pets), len(all_tasks), f"{pct_done}%"],
    ["Pets", "Tasks", "Done"],
):
    with col:
        st.metric(lbl, val)


# ---------------------------------------------------------------------------
# Helper — must be defined before the tab blocks that call it
# ---------------------------------------------------------------------------

def _render_trace(trace) -> None:
    """Render a ReasoningTrace as a collapsible timeline inside an expander."""
    if not trace or not trace.steps:
        return

    import json as _json

    conf = trace.verifier_result.get("confidence", 0)
    success = trace.verifier_result.get("success", False)
    summary = (
        f"Reasoning trace — {trace.total_tool_calls} tool call(s), "
        f"{trace.iterations} iteration(s), "
        f"{'✅ verified' if success else '⚠️ issues flagged'}"
    )

    with st.expander(summary, expanded=False):
        for step in trace.steps:
            icon = trace.phase_icon(step.phase)
            phase_label = step.phase.replace("_", " ").title()
            st.markdown(
                f"**{icon} Step {step.step_num} — {phase_label}** "
                f"<span style='font-size:0.75rem;color:#9C8A7B;'>({step.duration_ms:.0f} ms)</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='margin-left:1.5rem;font-size:0.875rem;color:#1C1C1C;"
                f"background:#F8F5F0;border-radius:6px;padding:0.5rem 0.75rem;"
                f"border-left:3px solid #E07B39;margin-bottom:0.5rem;'>"
                f"{step.content}</div>",
                unsafe_allow_html=True,
            )
            # Streamlit forbids nested expanders — use a checkbox toggle instead
            if step.raw:
                if st.checkbox(f"Show raw — step {step.step_num}", key=f"raw_{id(trace)}_{step.step_num}"):
                    st.code(_json.dumps(step.raw, indent=2, default=str), language="json")

        st.markdown(
            f"<div style='font-size:0.75rem;color:#9C8A7B;margin-top:0.5rem;'>"
            f"Total: {trace.total_duration_ms:.0f} ms end-to-end</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_pets, tab_schedule, tab_today, tab_agent = st.tabs(
    ["My Pets", "Schedule Tasks", "Today's Schedule", "🤖 PawPal Agent"]
)


# ===========================================================================
# TAB 1 — My Pets
# ===========================================================================
with tab_pets:
    st.markdown('<div class="pp-section-title">My Pets</div>', unsafe_allow_html=True)

    with st.expander("+ Add a New Pet", expanded=len(all_pets) == 0):
        with st.form("add_pet_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("Pet Name", placeholder="e.g. Buddy")
            with c2:
                new_species = st.selectbox("Species", list(SPECIES_EMOJI.keys()))
            if st.form_submit_button("Add Pet", use_container_width=True):
                if not new_name.strip():
                    st.error("Please enter a pet name.")
                elif new_name.strip().lower() in [p.name.lower() for p in all_pets]:
                    st.warning(f"'{new_name.strip()}' already exists.")
                else:
                    owner.add_pet(Pet(pet_id=str(uuid.uuid4()), name=new_name.strip(), species=new_species))
                    storage.save(owner)
                    st.success(f"Added {new_name.strip()} {SPECIES_EMOJI.get(new_species,'🐾')}")
                    st.rerun()

    pets = owner.get_pets()
    if not pets:
        st.markdown(
            '<div class="pp-empty"><div class="pp-empty-icon">🐾</div>'
            'No pets yet. Add your first furry friend above!</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f'<div class="pp-label">Your Pets — {len(pets)}</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(pets), 3))
        for idx, pet in enumerate(pets):
            pending = sum(1 for t in pet.get_tasks() if not t.completed)
            done    = sum(1 for t in pet.get_tasks() if t.completed)
            total   = len(pet.get_tasks())
            pct     = int(done / total * 100) if total else 0
            emoji   = SPECIES_EMOJI.get(pet.species, "🐾")
            with cols[idx % 3]:
                st.markdown(
                    f'<div class="pp-pet-card">'
                    f'<div class="pp-pet-emoji">{emoji}</div>'
                    f'<div class="pp-pet-name">{pet.name}</div>'
                    f'<div class="pp-pet-species">{pet.species}</div>'
                    f'<span class="pill pill-orange">{total} tasks</span>'
                    f'<span class="pill pill-green">{done} done</span>'
                    f'<span class="pill pill-yellow">{pending} pending</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if total > 0:
                    st.progress(pct / 100, text=f"{pct}% complete")


# ===========================================================================
# TAB 2 — Schedule Tasks
# ===========================================================================
with tab_schedule:
    st.markdown('<div class="pp-section-title">Schedule Tasks</div>', unsafe_allow_html=True)

    pets = owner.get_pets()
    if not pets:
        st.warning("Add at least one pet first.")
    else:
        with st.expander("+ Add a New Task", expanded=True):
            with st.form("add_task_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    sel_pet  = st.selectbox("Pet", [p.name for p in pets])
                    desc     = st.text_input("Description", placeholder="e.g. Morning walk")
                    freq     = st.selectbox("Frequency", ["once", "daily", "weekly"])
                with c2:
                    t_time   = st.time_input("Scheduled Time", value=time(8, 0))
                    due      = st.date_input("Due Date", value=date.today())

                if st.form_submit_button("Schedule Task", use_container_width=True):
                    if not desc.strip():
                        st.error("Please enter a description.")
                    else:
                        target = next((p for p in pets if p.name == sel_pet), None)
                        if target:
                            target.add_task(Task(
                                task_id=str(uuid.uuid4()),
                                description=desc.strip(),
                                time=t_time.strftime("%H:%M"),
                                frequency=freq,
                                due_date=due,
                            ))
                            storage.save(owner)
                            st.success(f"Scheduled '{desc.strip()}' for {sel_pet}.")
                            st.rerun()

        scheduler = Scheduler(owner=owner)
        sorted_pairs = scheduler.sort_by_time(scheduler.get_todays_schedule())

        st.markdown('<hr class="pp-divider">', unsafe_allow_html=True)
        st.markdown('<div class="pp-label">All Tasks — Chronological Order</div>', unsafe_allow_html=True)

        if not sorted_pairs:
            st.markdown(
                '<div class="pp-empty"><div class="pp-empty-icon">📋</div>'
                'No tasks yet. Schedule something above.</div>',
                unsafe_allow_html=True,
            )
        else:
            for pet, task in sorted_pairs:
                cls = "pp-task-done" if task.completed else "pp-task-pending"
                fp  = FREQ_PILL.get(task.frequency, task.frequency)
                st.markdown(
                    f'<div class="pp-task {cls}">'
                    f'<span class="pp-task-time">{task.time}</span>'
                    f'<span class="pp-task-pet">{SPECIES_EMOJI.get(pet.species,"🐾")} {pet.name}</span>'
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
    st.markdown('<div class="pp-section-title">Today\'s Schedule</div>', unsafe_allow_html=True)

    scheduler = Scheduler(owner=owner)
    pets      = owner.get_pets()

    # Conflict warnings
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        st.markdown('<div class="pp-label" style="margin-bottom:0.5rem;">⚠ Scheduling Conflicts</div>', unsafe_allow_html=True)
        for w in conflicts:
            st.markdown(f'<div class="pp-conflict">&#9888; {w}</div>', unsafe_allow_html=True)
        st.markdown("", unsafe_allow_html=True)

    # Filters
    c1, c2 = st.columns(2)
    with c1:
        pet_filter = st.selectbox("Filter by Pet", ["All Pets"] + [p.name for p in pets])
    with c2:
        status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Completed"])

    filtered = (scheduler.filter_by_pet(pet_filter)
                if pet_filter != "All Pets"
                else scheduler.get_todays_schedule())
    if status_filter == "Pending":
        filtered = [(p, t) for p, t in filtered if not t.completed]
    elif status_filter == "Completed":
        filtered = [(p, t) for p, t in filtered if t.completed]
    filtered = scheduler.sort_by_time(filtered)

    # Summary row
    total      = len(filtered)
    done_count = sum(1 for _, t in filtered if t.completed)
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Showing", total)
    m2.metric("Completed", done_count)
    m3.metric("Pending", total - done_count)

    # Overall progress bar
    if total > 0:
        st.progress(done_count / total, text=f"{int(done_count/total*100)}% of filtered tasks complete")

    st.markdown('<hr class="pp-divider">', unsafe_allow_html=True)

    if not filtered:
        st.markdown(
            '<div class="pp-empty"><div class="pp-empty-icon">✅</div>'
            'No tasks match the current filters.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="pp-label" style="margin-bottom:0.75rem;">Tasks — Tap checkbox to mark complete</div>', unsafe_allow_html=True)

        for pet, task in filtered:
            col_chk, col_row = st.columns([1, 11])
            with col_chk:
                checked = st.checkbox("", value=task.completed, key=f"chk_{task.task_id}")
            with col_row:
                cls = "pp-task-done" if task.completed else "pp-task-pending"
                fp  = FREQ_PILL.get(task.frequency, task.frequency)
                st.markdown(
                    f'<div class="pp-task {cls}" style="margin-bottom:0;">'
                    f'<span class="pp-task-time">{task.time}</span>'
                    f'<span class="pp-task-pet">{SPECIES_EMOJI.get(pet.species,"🐾")} {pet.name}</span>'
                    f'<span class="pp-task-desc">{task.description}</span>'
                    f'{fp}'
                    f'<span class="pp-task-meta">Due {task.due_date}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            if checked and not task.completed:
                nxt = scheduler.handle_recurring(task, pet)
                msg = (f"'{task.description}' done! Next {task.frequency} occurrence: **{nxt.due_date}**."
                       if nxt else f"'{task.description}' marked complete.")
                st.success(msg)
                storage.save(owner)
                st.rerun()
            elif not checked and task.completed:
                task.completed = False
                storage.save(owner)
                st.rerun()


# ===========================================================================
# TAB 4 — PawPal Agent
# ===========================================================================
with tab_agent:
    st.markdown('<div class="pp-section-title">🤖 PawPal Agent</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#6B5B4E;font-size:0.9rem;margin-bottom:1rem;">'
        "Chat with your AI pet care assistant. Ask me to add pets, schedule tasks, "
        "check conflicts, or manage your care calendar in plain English."
        "</p>",
        unsafe_allow_html=True,
    )

    # --- Session state for chat history and metrics ---
    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []
    if "agent_total_tool_calls" not in st.session_state:
        st.session_state.agent_total_tool_calls = 0
    if "agent_confidence_scores" not in st.session_state:
        st.session_state.agent_confidence_scores = []

    # --- Sidebar metrics (agent section) ---
    with st.sidebar:
        st.markdown(
            '<hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:0.75rem 0;">',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="pp-sidebar-stat">'
            f'<div class="pp-sidebar-stat-lbl">Agent Tool Calls</div>'
            f'<div class="pp-sidebar-stat-val">{st.session_state.agent_total_tool_calls}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        scores = st.session_state.agent_confidence_scores
        avg_conf = f"{sum(scores)/len(scores):.2f}" if scores else "—"
        st.markdown(
            f'<div class="pp-sidebar-stat">'
            f'<div class="pp-sidebar-stat-lbl">Avg Confidence</div>'
            f'<div class="pp-sidebar-stat-val">{avg_conf}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # --- Clear conversation button ---
    col_clear, _ = st.columns([1, 5])
    with col_clear:
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state.agent_messages = []
            st.session_state.agent_total_tool_calls = 0
            st.session_state.agent_confidence_scores = []
            st.rerun()

    # --- Render chat history ---
    for msg in st.session_state.agent_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "trace" in msg:
                try:
                    _render_trace(msg["trace"])
                except Exception:
                    pass  # silently skip trace render on history re-display

    # --- Chat input ---
    user_input = st.chat_input("Ask PawPal+ anything about your pets…")

    if user_input:
        # Append and render user message
        st.session_state.agent_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Build conversation history for multi-turn context (text only, no trace objects)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.agent_messages
            if m["role"] in ("user", "assistant") and m.get("content")
        ]

        # Run agent
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    from agent.core import run_agent
                    trace = run_agent(user_input, owner, conversation_history=history)
                    storage.save(owner)
                except Exception as exc:
                    trace = None
                    error_msg = f"Agent error: {exc}"
                    st.error(error_msg)
                    st.session_state.agent_messages.append(
                        {"role": "assistant", "content": error_msg}
                    )

            if trace is not None:
                try:
                    st.markdown(trace.final_response)
                    _render_trace(trace)
                except Exception as render_exc:
                    st.warning(f"Could not render reasoning trace: {render_exc}")

                # Update metrics
                st.session_state.agent_total_tool_calls += trace.total_tool_calls
                conf = trace.verifier_result.get("confidence")
                if conf is not None:
                    st.session_state.agent_confidence_scores.append(float(conf))

                # Persist message with trace for re-render on rerun
                st.session_state.agent_messages.append(
                    {"role": "assistant", "content": trace.final_response, "trace": trace}
                )
                # Refresh owner ref so sidebar stats update
                st.session_state.owner = owner
                st.rerun()
