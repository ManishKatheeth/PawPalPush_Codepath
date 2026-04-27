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
# Design tokens — role-aware palettes
# ---------------------------------------------------------------------------
_role_css = st.session_state.get("user_role", "owner")

if _role_css == "admin":
    # ── Cool navy / blue palette ──────────────────────────────────────────
    C_BG        = "#F0F4FF"   # cool blue-tinted canvas
    C_SURFACE   = "#FFFFFF"
    C_BORDER    = "#C7D7F5"   # blue-grey border
    C_ACCENT    = "#2563EB"   # strong blue
    C_ACCENT2   = "#1D4ED8"   # deeper blue
    C_DARK      = "#0F172A"   # near-black navy
    C_MID       = "#374151"   # slate grey
    C_MUTED     = "#6B7280"
    C_GREEN     = "#166534"
    C_GREEN_BG  = "#DCFCE7"
    C_YELLOW    = "#92400E"
    C_YELLOW_BG = "#FEF3C7"
    C_RED       = "#991B1B"
    C_RED_BG    = "#FEE2E2"
    C_BLUE      = "#1D4ED8"
    C_BLUE_BG   = "#DBEAFE"
    _SIDEBAR_BG   = "linear-gradient(180deg, #0F172A 0%, #1E293B 100%)"
    _SIDEBAR_TEXT = "#E2E8F0"
    _SIDEBAR_MID  = "#94A3B8"
    _SIDEBAR_FOOT = "#475569"
    _HERO_BG      = "linear-gradient(135deg, #0F172A 0%, #1E293B 55%, #1E3A5F 100%)"
    _HERO_ICON    = "🔧"
    _HERO_SUB_C   = "#93C5FD"
    _HERO_STAT_C  = "#60A5FA"
    _BTN_SHADOW   = "rgba(37,99,235,0.28)"
    _BTN_SHADOW2  = "rgba(37,99,235,0.40)"
    _CARD_HOVER   = "rgba(37,99,235,0.10)"
    _FOCUS_RING   = "rgba(37,99,235,0.15)"
    _PILL_ACC_BG  = "#DBEAFE"
    _PROG_TRACK   = "#C7D7F5"
    _PROG_FILL    = "linear-gradient(90deg,#2563EB,#60A5FA)"
    _PROG_DOT_OFF = "#9BB5E8"
    _TRACE_BG     = "#F0F4FF"
    _TRACE_BORDER = "#2563EB"
    _TRACE_MUTED  = "#6B7280"
    _PROGRESS_EMOJI = "📋"
else:
    # ── Warm amber / terracotta palette (default) ─────────────────────────
    C_BG        = "#FBF8F3"
    C_SURFACE   = "#FFFFFF"
    C_BORDER    = "#E8DDD0"
    C_ACCENT    = "#E07B39"
    C_ACCENT2   = "#C4612A"
    C_DARK      = "#1C1C1C"
    C_MID       = "#6B5B4E"
    C_MUTED     = "#9C8A7B"
    C_GREEN     = "#3D7A4A"
    C_GREEN_BG  = "#EBF5EE"
    C_YELLOW    = "#8A6B00"
    C_YELLOW_BG = "#FDF6DC"
    C_RED       = "#9B2C2C"
    C_RED_BG    = "#FDECEA"
    C_BLUE      = "#1D5FA3"
    C_BLUE_BG   = "#E3EEF9"
    _SIDEBAR_BG   = "linear-gradient(180deg, #2D1F14 0%, #1C1208 100%)"
    _SIDEBAR_TEXT = "#F5EDE4"
    _SIDEBAR_MID  = "#C4A882"
    _SIDEBAR_FOOT = "#7A6355"
    _HERO_BG      = "linear-gradient(135deg, #2D1F14 0%, #3D2B1A 60%, #4A3420 100%)"
    _HERO_ICON    = "🐾"
    _HERO_SUB_C   = "#C4A882"
    _HERO_STAT_C  = "#E07B39"
    _BTN_SHADOW   = "rgba(224,123,57,0.25)"
    _BTN_SHADOW2  = "rgba(224,123,57,0.35)"
    _CARD_HOVER   = "rgba(224,123,57,0.12)"
    _FOCUS_RING   = "rgba(224,123,57,0.15)"
    _PILL_ACC_BG  = "#FEF0E6"
    _PROG_TRACK   = "#E8DDD0"
    _PROG_FILL    = "linear-gradient(90deg,#E07B39,#F09050)"
    _PROG_DOT_OFF = "#C9B9A8"
    _TRACE_BG     = "#F8F5F0"
    _TRACE_BORDER = "#E07B39"
    _TRACE_MUTED  = "#9C8A7B"
    _PROGRESS_EMOJI = "🐾"


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
    background: {_SIDEBAR_BG} !important;
    border-right: none !important;
}}
[data-testid="stSidebar"] * {{ color: {_SIDEBAR_TEXT} !important; }}
[data-testid="stSidebar"] .stMarkdown p {{ color: {_SIDEBAR_MID} !important; font-size: 0.78rem; }}

/* ── Ghost / secondary action buttons ── */
button[kind="secondary"] {{
    background: transparent !important;
    color: {C_MID} !important;
    border: 1.5px solid {C_BORDER} !important;
    box-shadow: none !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 0.3rem 0.6rem !important;
    letter-spacing: 0 !important;
}}
button[kind="secondary"]:hover {{
    background: {C_BORDER} !important;
    color: {C_DARK} !important;
    transform: none !important;
    box-shadow: none !important;
}}
button[kind="secondary"]:active {{ transform: none !important; }}

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
/* Override Streamlit's default BaseWeb tab-highlight (causes double underline) */
[data-baseweb="tab-highlight"] {{
    background-color: {C_ACCENT} !important;
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
    box-shadow: 0 2px 8px {_BTN_SHADOW} !important;
}}
.stButton > button:hover {{
    background: {C_ACCENT2} !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px {_BTN_SHADOW2} !important;
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
    box-shadow: 0 0 0 3px {_FOCUS_RING} !important;
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
    box-shadow: 0 0 0 3px {_FOCUS_RING} !important;
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
    background: {_HERO_BG};
    border-radius: 18px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.75rem;
    position: relative;
    overflow: hidden;
}}
.pp-hero::after {{
    content: "{_HERO_ICON}";
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
    color: {_HERO_SUB_C};
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
    color: {_HERO_STAT_C};
    line-height: 1;
}}
.pp-hero-stat-lbl {{
    font-size: 0.68rem;
    color: {_HERO_SUB_C};
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
    box-shadow: 0 6px 24px {_CARD_HOVER};
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
.pill-orange  {{ background: {_PILL_ACC_BG}; color: {C_ACCENT}; }}
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
.pp-sidebar-stat-lbl {{ font-size: 0.65rem; color: {_SIDEBAR_MID}; text-transform: uppercase; letter-spacing: 0.08em; }}
.pp-sidebar-stat-val {{ font-size: 1.1rem; font-weight: 700; color: #FFFFFF; margin-top: 0.1rem; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PAW_SVG = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 100 100">'
    f'<ellipse cx="28" cy="20" rx="9" ry="11" fill="{C_ACCENT}"/>'
    f'<ellipse cx="50" cy="14" rx="9" ry="11" fill="{C_ACCENT}"/>'
    f'<ellipse cx="72" cy="20" rx="9" ry="11" fill="{C_ACCENT}"/>'
    f'<ellipse cx="16" cy="42" rx="8" ry="10" fill="{C_ACCENT}"/>'
    f'<ellipse cx="50" cy="64" rx="28" ry="26" fill="{C_ACCENT}"/>'
    f'</svg>'
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
# Login / Role selection — shown before any app content
# ---------------------------------------------------------------------------
if "user_role" not in st.session_state:
    st.markdown(
        """
        <style>
        .pp-login-wrap {
            max-width: 560px;
            margin: 4rem auto 0;
            text-align: center;
        }
        .pp-login-logo {
            font-family: 'Lora', Georgia, serif;
            font-size: 2.4rem;
            font-weight: 700;
            color: #2D1F14;
            margin-bottom: 0.15rem;
        }
        .pp-login-logo span { color: #E07B39; }
        .pp-login-sub {
            font-size: 0.95rem;
            color: #9B8B7E;
            margin-bottom: 2rem;
        }
        .pp-role-card {
            border: 2px solid #E8DDD0;
            border-radius: 14px;
            padding: 1.25rem 1rem;
            cursor: pointer;
            transition: border-color 0.2s, box-shadow 0.2s;
            background: #fff;
            text-align: left;
        }
        .pp-role-card:hover { border-color: #E07B39; box-shadow: 0 2px 12px rgba(224,123,57,0.15); }
        .pp-role-icon { font-size: 2rem; margin-bottom: 0.4rem; }
        .pp-role-title { font-weight: 700; font-size: 1rem; color: #2D1F14; margin-bottom: 0.2rem; }
        .pp-role-desc  { font-size: 0.8rem; color: #6B5B4E; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pp-login-wrap">'
        '<div class="pp-login-logo">PawPal<span>+</span></div>'
        '<div class="pp-login-sub">Your intelligent pet care companion</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        with st.form("login_form"):
            login_name = st.text_input("Your name", placeholder="e.g. Alice, Dr. Kim…", label_visibility="visible")
            st.markdown("<div style='margin:0.75rem 0 0.4rem;font-size:0.82rem;font-weight:600;color:#6B5B4E;'>I am a…</div>", unsafe_allow_html=True)
            role_choice = st.radio(
                "Role",
                options=["🐾  Pet Owner", "🔧  Admin / Vet"],
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Get Started →", use_container_width=True)

        if submitted:
            name = login_name.strip() or "Friend"
            role = "owner" if "Pet Owner" in role_choice else "admin"
            st.session_state.user_role = role
            st.session_state.user_name = name
            # Clear any stale agent history from a previous session
            for _k in ("agent_messages", "agent_total_tool_calls", "agent_confidence_scores", "owner"):
                st.session_state.pop(_k, None)
            st.rerun()

    st.stop()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = storage.load()

owner: Owner = st.session_state.owner
# Reflect the logged-in name in the owner object (in-memory only)
owner.name = st.session_state.get("user_name", owner.name)


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

    # Role badge + switch button
    _role_label = "🐾 Pet Owner" if st.session_state.user_role == "owner" else "🔧 Admin / Vet"
    st.markdown(
        f'<div class="pp-sidebar-stat">'
        f'<div class="pp-sidebar-stat-lbl">Logged in as</div>'
        f'<div class="pp-sidebar-stat-val" style="font-size:0.85rem;">{_role_label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Switch Role", key="switch_role", use_container_width=True):
        for _k in ("user_role", "user_name", "agent_messages", "agent_total_tool_calls",
                   "agent_confidence_scores", "owner"):
            st.session_state.pop(_k, None)
        st.rerun()

    st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:1.25rem 0;">', unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:0.72rem;color:{_SIDEBAR_FOOT};text-align:center;">PawPal+ v1.0 — Pet Care Made Easy</p>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Hero banner
# ---------------------------------------------------------------------------
hero_cols = st.columns([3, 1, 1, 1])
with hero_cols[0]:
    _hero_greeting = (
        f"Good day, {owner.name}!"
        if st.session_state.user_role == "owner"
        else f"Welcome back, {owner.name}."
    )
    _hero_sub = (
        "Here's your pet care overview for today."
        if st.session_state.user_role == "owner"
        else "Admin dashboard — full care operations at a glance."
    )
    st.markdown(
        f'<div class="pp-hero">'
        f'<div class="pp-hero-title">{_hero_greeting}</div>'
        f'<div class="pp-hero-sub">{_hero_sub}</div>'
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
                f"<span style='font-size:0.75rem;color:{_TRACE_MUTED};'>({step.duration_ms:.0f} ms)</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='margin-left:1.5rem;font-size:0.875rem;color:{C_DARK};"
                f"background:{_TRACE_BG};border-radius:6px;padding:0.5rem 0.75rem;"
                f"border-left:3px solid {_TRACE_BORDER};margin-bottom:0.5rem;'>"
                f"{step.content}</div>",
                unsafe_allow_html=True,
            )
            # Streamlit forbids nested expanders — use a checkbox toggle instead
            if step.raw:
                if st.checkbox(f"Show raw — step {step.step_num}", key=f"raw_{id(trace)}_{step.step_num}"):
                    st.code(_json.dumps(step.raw, indent=2, default=str), language="json")

        st.markdown(
            f"<div style='font-size:0.75rem;color:{_TRACE_MUTED};margin-top:0.5rem;'>"
            f"Total: {trace.total_duration_ms:.0f} ms end-to-end</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Pet CRUD dialogs  (defined here so they can access owner, C_* tokens, etc.)
# ---------------------------------------------------------------------------

@st.dialog("✏️ Edit Pet")
def _pet_edit_dialog(pet):
    sp_list = list(SPECIES_EMOJI.keys())
    sp_idx  = sp_list.index(pet.species) if pet.species in sp_list else 0
    emoji   = SPECIES_EMOJI.get(pet.species, "🐾")

    st.markdown(
        f'<div style="text-align:center;padding:0.25rem 0 1rem;">'
        f'<div style="font-size:2.5rem;line-height:1;">{emoji}</div>'
        f'<div style="font-size:1rem;font-weight:700;color:{C_DARK};margin-top:0.3rem;">{pet.name}</div>'
        f'<div style="font-size:0.72rem;color:{C_MUTED};text-transform:uppercase;'
        f'letter-spacing:0.06em;">{pet.species}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    new_name    = st.text_input("Name", value=pet.name)
    new_species = st.selectbox("Species", sp_list, index=sp_idx)

    st.markdown("<div style='margin-top:0.25rem'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save changes", use_container_width=True):
            n = new_name.strip()
            if not n:
                st.error("Name cannot be empty.")
            elif (n.lower() != pet.name.lower() and
                  n.lower() in [p.name.lower() for p in owner.get_pets()]):
                st.error(f"'{n}' already exists.")
            else:
                pet.name    = n
                pet.species = new_species
                storage.save(owner)
                st.rerun()
    with c2:
        if st.button("Cancel", type="secondary", use_container_width=True):
            st.rerun()


@st.dialog("Delete Pet")
def _pet_delete_dialog(pet):
    n_tasks = len(pet.get_tasks())
    emoji   = SPECIES_EMOJI.get(pet.species, "🐾")

    st.markdown(
        f'<div style="text-align:center;padding:0.25rem 0 0.75rem;">'
        f'<div style="font-size:2.8rem;line-height:1;">{emoji}</div>'
        f'<div style="font-size:1.05rem;font-weight:700;color:{C_DARK};margin-top:0.3rem;">'
        f'{pet.name}</div>'
        f'<div style="font-size:0.72rem;color:{C_MUTED};text-transform:uppercase;'
        f'letter-spacing:0.06em;">{pet.species}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="background:{C_RED_BG};border:1px solid #F5C6C6;border-radius:10px;'
        f'padding:0.9rem 1rem;margin-bottom:1rem;">'
        f'<p style="margin:0;font-size:0.85rem;color:{C_RED};font-weight:600;">'
        f'⚠ This cannot be undone.</p>'
        f'<p style="margin:0.35rem 0 0;font-size:0.82rem;color:{C_RED};">'
        + (f"Deleting <strong>{pet.name}</strong> will permanently remove "
           f"<strong>{n_tasks} task(s)</strong> as well."
           if n_tasks else
           f"<strong>{pet.name}</strong> has no tasks — safe to remove.")
        + f'</p></div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Yes, delete", use_container_width=True):
            owner.remove_pet(pet.pet_id)
            storage.save(owner)
            st.rerun()
    with c2:
        if st.button("Keep pet", type="secondary", use_container_width=True):
            st.rerun()


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
_agent_tab_label = "🐾 PawPal Companion" if st.session_state.user_role == "owner" else "🔧 PawPal Manager"
tab_agent, tab_pets, tab_schedule, tab_today, tab_calendar = st.tabs(
    [_agent_tab_label, "My Pets", "Schedule Tasks", "Today's Schedule", "📅 Calendar"]
)


# ===========================================================================
# TAB 1 — My Pets  (full CRUD)
# ===========================================================================
with tab_pets:
    st.markdown('<div class="pp-section-title">My Pets</div>', unsafe_allow_html=True)

    # ── Add a new pet ─────────────────────────────────────────────────────
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
                _card_msg = "All done! 🏆" if pct == 100 else f"{pct}% complete"
                _prog_bar = (
                    f'<div style="margin-top:0.75rem;">'
                    f'<div style="font-size:0.72rem;color:{C_MID};font-weight:600;margin-bottom:0.3rem;">{_card_msg}</div>'
                    f'<div style="background:{_PROG_TRACK};border-radius:99px;height:8px;">'
                    f'<div style="background:{_PROG_FILL};width:{pct}%;height:100%;border-radius:99px;'
                    f'min-width:{"0" if pct == 0 else "8px"};"></div>'
                    f'</div></div>'
                ) if total > 0 else ""

                st.markdown(
                    f'<div class="pp-pet-card">'
                    f'<div class="pp-pet-emoji">{emoji}</div>'
                    f'<div class="pp-pet-name">{pet.name}</div>'
                    f'<div class="pp-pet-species">{pet.species}</div>'
                    f'<span class="pill pill-orange">{total} tasks</span>'
                    f'<span class="pill pill-green">{done} done</span>'
                    f'<span class="pill pill-yellow">{pending} pending</span>'
                    f'{_prog_bar}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                b1, b2 = st.columns(2)
                with b1:
                    if st.button("✏️ Edit", key=f"btn_edit_{pet.pet_id}",
                                 type="secondary", use_container_width=True):
                        _pet_edit_dialog(pet)
                with b2:
                    if st.button("🗑 Delete", key=f"btn_del_{pet.pet_id}",
                                 type="secondary", use_container_width=True):
                        _pet_delete_dialog(pet)


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
    pct = int(done_count / total * 100) if total > 0 else 0
    if pct == 0:
        _prog_msg = f"Let's get started! {_PROGRESS_EMOJI}"
    elif pct < 50:
        _prog_msg = f"Good progress! {done_count} of {total} done {_PROGRESS_EMOJI}"
    elif pct < 100:
        _prog_msg = f"More than halfway there! {done_count} of {total} done ⭐"
    else:
        _prog_msg = "All done! Amazing care today 🏆"
    _milestone_dots = " ".join(
        f'<div style="position:absolute;left:{m}%;top:50%;transform:translate(-50%,-50%);'
        f'width:20px;height:20px;border-radius:50%;'
        f'background:{C_ACCENT if pct >= m else _PROG_DOT_OFF};'
        f'border:2px solid #fff;font-size:9px;display:flex;align-items:center;'
        f'justify-content:center;z-index:2;">{_PROGRESS_EMOJI}</div>'
        for m in [25, 50, 75, 100]
    )
    st.markdown(
        f'<div style="margin:1rem 0 0.25rem;">'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:0.5rem;">'
        f'<span style="font-size:0.82rem;color:{C_MID};font-weight:600;">{_prog_msg}</span>'
        f'<span style="font-size:0.82rem;color:{C_MUTED};font-weight:500;">{pct}%</span>'
        f'</div>'
        f'<div style="position:relative;background:{_PROG_TRACK};border-radius:99px;height:14px;">'
        f'<div style="background:{_PROG_FILL};'
        f'width:{pct}%;height:100%;border-radius:99px;'
        f'transition:width 0.4s ease;min-width:{"0" if pct == 0 else "14px"};"></div>'
        f'{_milestone_dots}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

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
    _is_owner = st.session_state.user_role == "owner"
    _agent_title = "🐾 PawPal Companion" if _is_owner else "🔧 PawPal Manager"
    _agent_desc = (
        "Ask me about your pets' health, habits, and how your care routine is going. "
        "I'll give you wellness tips, flag what's overdue, and suggest routines. "
        "Use the tabs above to add or change pets and tasks."
        if _is_owner else
        "Manage your full care operation in plain English — add pets, schedule tasks, "
        "detect conflicts, complete care items, and get performance reports."
    )
    _chat_placeholder = (
        "Ask about your pets' health, care summary, or routine suggestions…"
        if _is_owner else
        "Add pets, schedule tasks, check conflicts, or request a care report…"
    )
    st.markdown(f'<div class="pp-section-title">{_agent_title}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<p style="color:{C_MID};font-size:0.9rem;margin-bottom:1rem;">{_agent_desc}</p>',
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

    # --- Chat input ---
    user_input = st.chat_input(_chat_placeholder)

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
                    trace = run_agent(
                        user_input, owner,
                        conversation_history=history,
                        user_role=st.session_state.user_role,
                    )
                    storage.save(owner)
                except Exception as exc:
                    trace = None
                    error_msg = f"Agent error: {exc}"
                    st.error(error_msg)
                    st.session_state.agent_messages.append(
                        {"role": "assistant", "content": error_msg}
                    )

            if trace is not None:
                st.markdown(trace.final_response)

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


# ===========================================================================
# TAB 5 — Calendar
# ===========================================================================
with tab_calendar:
    from datetime import timedelta

    _is_owner_cal = st.session_state.user_role == "owner"
    st.markdown('<div class="pp-section-title">📅 Calendar</div>', unsafe_allow_html=True)
    st.markdown(
        f'<p style="color:{C_MID};font-size:0.9rem;margin-bottom:1.25rem;">'
        + ("View your pets' appointments, recurring care, and past schedule at a glance."
           if _is_owner_cal else
           "Full schedule overview — past, present, and projected future appointments across all pets.")
        + "</p>",
        unsafe_allow_html=True,
    )

    # ── Week navigator ────────────────────────────────────────────────────
    today_cal = date.today()
    if "cal_week_offset" not in st.session_state:
        st.session_state.cal_week_offset = 0

    nav_l, nav_mid, nav_r = st.columns([1, 3, 1])
    with nav_l:
        if st.button("← Prev week", key="cal_prev"):
            st.session_state.cal_week_offset -= 1
            st.rerun()
    with nav_r:
        if st.button("Next week →", key="cal_next"):
            st.session_state.cal_week_offset += 1
            st.rerun()

    # Compute Monday of the displayed week
    week_monday = today_cal - timedelta(days=today_cal.weekday()) + timedelta(weeks=st.session_state.cal_week_offset)
    week_days   = [week_monday + timedelta(days=i) for i in range(7)]
    week_label  = f"{week_monday.strftime('%b %d')} – {week_days[-1].strftime('%b %d, %Y')}"

    with nav_mid:
        st.markdown(
            f'<div style="text-align:center;font-weight:700;font-size:1rem;'
            f'color:{C_DARK};padding-top:0.45rem;">{week_label}</div>',
            unsafe_allow_html=True,
        )

    if st.session_state.cal_week_offset != 0:
        if st.button("Jump to today", key="cal_today"):
            st.session_state.cal_week_offset = 0
            st.rerun()

    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)

    # ── Pet filter (admin sees all; owner always sees their own) ──────────
    cal_pets = owner.get_pets()
    if not _is_owner_cal:
        cal_pet_options = ["All Pets"] + [p.name for p in cal_pets]
        cal_pet_filter  = st.selectbox("Filter by Pet", cal_pet_options, key="cal_pet_filter")
    else:
        cal_pet_filter = "All Pets"

    # ── Build task map: date → list of (Pet, Task) ────────────────────────
    # For each task, project recurring occurrences into the displayed week.
    def _project_tasks(pets, week_days):
        """Return {date: [(pet, task_or_projected)]} for the given week."""
        from collections import defaultdict
        day_map = defaultdict(list)
        week_set = set(week_days)
        week_start, week_end = week_days[0], week_days[-1]

        for pet in pets:
            for task in pet.get_tasks():
                base_date = task.due_date

                if task.frequency == "once":
                    if week_start <= base_date <= week_end:
                        day_map[base_date].append((pet, task, False))

                elif task.frequency == "daily":
                    for day in week_days:
                        # Show on this day if base_date <= day (task started on or before)
                        if base_date <= day:
                            # Check if a real task exists for this exact date already
                            day_map[day].append((pet, task, day != base_date))

                elif task.frequency == "weekly":
                    # Project weekly: show on the same weekday if base_date <= week day
                    for day in week_days:
                        if base_date <= day and (day - base_date).days % 7 == 0:
                            day_map[day].append((pet, task, day != base_date))

        return day_map

    # Apply pet filter
    pets_for_cal = (
        [p for p in cal_pets if p.name == cal_pet_filter]
        if cal_pet_filter != "All Pets"
        else cal_pets
    )

    day_map = _project_tasks(pets_for_cal, week_days)

    # ── Render week grid ──────────────────────────────────────────────────
    DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    cols = st.columns(7)

    for col_idx, (col, day) in enumerate(zip(cols, week_days)):
        is_today   = day == today_cal
        is_past    = day < today_cal
        is_weekend = col_idx >= 5

        # Day header
        header_bg  = C_ACCENT if is_today else (C_BORDER if is_past else C_SURFACE)
        header_col = "#FFFFFF" if is_today else (C_MUTED if is_past else C_DARK)
        border_col = C_ACCENT if is_today else C_BORDER

        with col:
            st.markdown(
                f'<div style="border:1.5px solid {border_col};border-radius:12px;'
                f'min-height:160px;overflow:hidden;margin-bottom:0.25rem;">'

                # Header strip
                f'<div style="background:{header_bg};padding:0.4rem 0.5rem;text-align:center;">'
                f'<div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:0.06em;color:{header_col};">{DAY_NAMES[col_idx]}</div>'
                f'<div style="font-size:1.1rem;font-weight:800;color:{header_col};">{day.day}</div>'
                f'</div>'

                # Task pills
                f'<div style="padding:0.4rem 0.35rem;">',
                unsafe_allow_html=True,
            )

            tasks_this_day = day_map.get(day, [])

            if not tasks_this_day:
                st.markdown(
                    f'<p style="font-size:0.65rem;color:{C_MUTED};text-align:center;'
                    f'margin:0.5rem 0;">—</p>',
                    unsafe_allow_html=True,
                )
            else:
                for pet, task, is_projected in tasks_this_day:
                    emoji = SPECIES_EMOJI.get(pet.species, "🐾")

                    if is_projected:
                        # Future projected occurrence of a recurring task
                        pill_bg  = C_BLUE_BG
                        pill_col = C_BLUE
                        dot      = "↻"
                    elif task.completed and day <= today_cal:
                        pill_bg  = C_GREEN_BG
                        pill_col = C_GREEN
                        dot      = "✓"
                    elif not task.completed and day < today_cal:
                        # Overdue
                        pill_bg  = C_RED_BG
                        pill_col = C_RED
                        dot      = "!"
                    else:
                        # Upcoming or today pending
                        pill_bg  = _PILL_ACC_BG
                        pill_col = C_ACCENT
                        dot      = "•"

                    freq_badge = (
                        "↻d" if task.frequency == "daily" else
                        "↻w" if task.frequency == "weekly" else ""
                    )

                    st.markdown(
                        f'<div style="background:{pill_bg};border-radius:6px;'
                        f'padding:0.25rem 0.35rem;margin-bottom:0.2rem;">'
                        f'<div style="font-size:0.6rem;font-weight:700;color:{pill_col};">'
                        f'{dot} {task.time} {emoji}</div>'
                        f'<div style="font-size:0.6rem;color:{pill_col};'
                        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'
                        f'max-width:100%;">'
                        f'{task.description[:18]}{"…" if len(task.description)>18 else ""}'
                        f'{" " + freq_badge if freq_badge else ""}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown('</div></div>', unsafe_allow_html=True)

    # ── Legend ────────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:center;'
        f'font-size:0.75rem;color:{C_MID};">'
        f'<span style="display:flex;align-items:center;gap:0.3rem;">'
        f'<span style="background:{C_GREEN_BG};color:{C_GREEN};border-radius:4px;'
        f'padding:0.1rem 0.5rem;font-weight:600;">✓ Done</span></span>'
        f'<span style="display:flex;align-items:center;gap:0.3rem;">'
        f'<span style="background:{_PILL_ACC_BG};color:{C_ACCENT};border-radius:4px;'
        f'padding:0.1rem 0.5rem;font-weight:600;">• Pending</span></span>'
        f'<span style="display:flex;align-items:center;gap:0.3rem;">'
        f'<span style="background:{C_RED_BG};color:{C_RED};border-radius:4px;'
        f'padding:0.1rem 0.5rem;font-weight:600;">! Overdue</span></span>'
        f'<span style="display:flex;align-items:center;gap:0.3rem;">'
        f'<span style="background:{C_BLUE_BG};color:{C_BLUE};border-radius:4px;'
        f'padding:0.1rem 0.5rem;font-weight:600;">↻ Recurring (projected)</span></span>'
        f'<span style="color:{C_MUTED};">↻d = daily · ↻w = weekly</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Month summary strip ───────────────────────────────────────────────
    st.markdown('<hr class="pp-divider">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="pp-label" style="margin-bottom:0.75rem;">This week at a glance</div>',
        unsafe_allow_html=True,
    )

    total_week  = sum(len(v) for v in day_map.values())
    done_week   = sum(1 for tasks in day_map.values()
                      for (_, t, proj) in tasks if t.completed and not proj)
    overdue_week = sum(1 for tasks in day_map.values()
                       for (_, t, proj) in tasks
                       if not t.completed and not proj and t.due_date < today_cal)
    projected_week = sum(1 for tasks in day_map.values() for (_, _, proj) in tasks if proj)

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total events", total_week)
    s2.metric("Completed", done_week)
    s3.metric("Overdue", overdue_week)
    s4.metric("Recurring (projected)", projected_week)
