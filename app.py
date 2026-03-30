import streamlit as st
import pandas as pd
import urllib.parse
from typing import List
from pawpal_system import (
    ENERGY_LEVELS, TASK_TYPES, FREQUENCY,
    Task, Pet, Owner, Scheduler,
)


# ─── Default tasks ──────────────────────────────────────────────────────────────

DEFAULT_TASKS = [
    {"active": True, "name": "Morning Feeding",        "description": "Fill bowl with daily food portion",          "duration": 10, "priority": 1, "energy": "Low",    "type": "survival", "frequency": "daily",      "tags": "food,feeding,meal,morning"},
    {"active": True, "name": "Evening Feeding",        "description": "Second meal of the day",                     "duration": 10, "priority": 1, "energy": "Low",    "type": "survival", "frequency": "daily",      "tags": "food,feeding,meal,evening"},
    {"active": True, "name": "Medication",             "description": "Administer prescribed daily medication",      "duration": 5,  "priority": 1, "energy": "Low",    "type": "survival", "frequency": "daily",      "tags": "medication,meds,health"},
    {"active": True, "name": "Morning Walk",           "description": "Outdoor walk for exercise and bathroom needs","duration": 30, "priority": 2, "energy": "High",   "type": "hobby",    "frequency": "daily",      "tags": "outdoor,walk,exercise,morning"},
    {"active": True, "name": "Fetch with Tennis Ball", "description": "High-energy fetch session in the yard",       "duration": 20, "priority": 3, "energy": "High",   "type": "hobby",    "frequency": "daily",      "tags": "fetch,tennis ball,play,outdoor,exercise"},
    {"active": True, "name": "Grooming & Brush",       "description": "Brush coat and check for tangles",            "duration": 15, "priority": 2, "energy": "Medium", "type": "care",     "frequency": "weekly",     "tags": "grooming,brush,hygiene,coat"},
    {"active": True, "name": "Laser Pointer Play",     "description": "Low-effort indoor play with laser toy",       "duration": 10, "priority": 3, "energy": "Low",    "type": "hobby",    "frequency": "daily",      "tags": "play,indoor,laser,light"},
    {"active": True, "name": "Training Session",       "description": "Practice commands and tricks for mental stimulation","duration": 20, "priority": 3, "energy": "Medium", "type": "hobby", "frequency": "daily",  "tags": "training,mental,tricks,focus"},
    {"active": True, "name": "Sniff & Explore Walk",   "description": "Slow-paced walk focused on sniffing and exploring","duration": 25, "priority": 3, "energy": "Medium", "type": "hobby", "frequency": "daily",  "tags": "outdoor,sniff,explore,walk,enrichment"},
    {"active": True, "name": "Cuddle & Calm Time",     "description": "Quiet bonding time on the couch",             "duration": 15, "priority": 4, "energy": "Low",    "type": "hobby",    "frequency": "as-needed",  "tags": "cuddle,indoor,calm,relax,cozy"},
]

# ─── App setup ──────────────────────────────────────────────────────────────────

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ─── Cute white paw / pink toe-bean watermark background ───────────────────────

_paw_svg = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 280 140'>"
    # left paw — tilted slightly left
    "<g transform='rotate(-12,66,76)' opacity='0.6'>"
    # main pad: near-white blush fill, soft pink stroke
    "<ellipse cx='66' cy='96' rx='32' ry='26' fill='#FFE4EE' stroke='#FFB3C6' stroke-width='3'/>"
    # toe beans: cute pink
    "<ellipse cx='32' cy='61' rx='14' ry='16' fill='#FF8FAB'/>"
    "<ellipse cx='53' cy='47' rx='14' ry='16' fill='#FF8FAB'/>"
    "<ellipse cx='77' cy='47' rx='14' ry='16' fill='#FF8FAB'/>"
    "<ellipse cx='98' cy='61' rx='14' ry='16' fill='#FF8FAB'/>"
    # tiny shine dots on toe beans for extra cuteness
    "<ellipse cx='36' cy='57' rx='4' ry='4' fill='white' opacity='0.5'/>"
    "<ellipse cx='57' cy='43' rx='4' ry='4' fill='white' opacity='0.5'/>"
    "<ellipse cx='81' cy='43' rx='4' ry='4' fill='white' opacity='0.5'/>"
    "<ellipse cx='102' cy='57' rx='4' ry='4' fill='white' opacity='0.5'/>"
    "</g>"
    # right paw — tilted slightly right
    "<g transform='rotate(12,214,76)' opacity='0.6'>"
    "<ellipse cx='214' cy='96' rx='32' ry='26' fill='#FFE4EE' stroke='#FFB3C6' stroke-width='3'/>"
    "<ellipse cx='180' cy='61' rx='14' ry='16' fill='#FF8FAB'/>"
    "<ellipse cx='201' cy='47' rx='14' ry='16' fill='#FF8FAB'/>"
    "<ellipse cx='225' cy='47' rx='14' ry='16' fill='#FF8FAB'/>"
    "<ellipse cx='246' cy='61' rx='14' ry='16' fill='#FF8FAB'/>"
    "<ellipse cx='184' cy='57' rx='4' ry='4' fill='white' opacity='0.5'/>"
    "<ellipse cx='205' cy='43' rx='4' ry='4' fill='white' opacity='0.5'/>"
    "<ellipse cx='229' cy='43' rx='4' ry='4' fill='white' opacity='0.5'/>"
    "<ellipse cx='250' cy='57' rx='4' ry='4' fill='white' opacity='0.5'/>"
    "</g>"
    "</svg>"
)

st.markdown(
    f"""<style>
    .stApp {{
        background-image: url("data:image/svg+xml,{urllib.parse.quote(_paw_svg, safe="")}");
        background-repeat: no-repeat;
        background-position: center center;
        background-size: 55vw auto;
        background-attachment: fixed;
    }}
    </style>""",
    unsafe_allow_html=True,
)

# ─── Session state ──────────────────────────────────────────────────────────────

if "tasks"    not in st.session_state:
    st.session_state.tasks    = [t.copy() for t in DEFAULT_TASKS]
if "schedule" not in st.session_state:
    st.session_state.schedule = None

# ─── Sidebar: Profiles ──────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🐾 PawPal+")
    st.caption("Your Personal Pet Concierge")
    st.divider()

    st.subheader("👤 Owner Profile")
    owner_name     = st.text_input("Your name", value="Jordan")
    available_time = st.slider(
        "Available time today", 30, 480, 120, step=15, format="%d min"
    )
    energy_raw = st.radio(
        "Your energy battery 🔋",
        ["High ⚡", "Medium 🔋", "Low 🌿"],
        index=1,
        help="This shapes which activities get prioritised for you.",
    )
    energy_battery = energy_raw.split()[0]

    st.divider()

    st.subheader("🐾 Pet Profile")
    pet_name      = st.text_input("Pet's name", value="Mochi")
    species       = st.selectbox("Species", ["Dog", "Cat", "Rabbit", "Bird", "Other"])
    favorites_raw = st.text_input(
        "Loves (comma-separated)",
        value="tennis balls, fetch, cuddles",
        help="Activities or items your pet adores — used to boost matching tasks.",
    )
    fears_raw = st.text_input(
        "Fears (comma-separated)",
        value="rain, loud noises",
        help="Things your pet dislikes — conflicting tasks will be skipped.",
    )

    st.divider()
    if st.button("↺  Reset to default tasks", width="stretch"):
        st.session_state.tasks    = [t.copy() for t in DEFAULT_TASKS]
        st.session_state.schedule = None
        st.session_state.pop("task_editor", None)
        st.rerun()

# ─── Main: Header ───────────────────────────────────────────────────────────────

st.title("🐾 PawPal+ Pet Concierge")
st.caption(
    "Balancing your pet's needs with your real-world constraints — one tail-wag at a time."
)

# ─── Task Manager ───────────────────────────────────────────────────────────────

st.subheader("📋 Care Task Manager")
st.caption(
    "Edit tasks directly in the table. Toggle **Include** to add or remove from today's plan. "
    "Use the **＋** icon at the bottom to add new rows."
)

task_df = pd.DataFrame(st.session_state.tasks)

edited = st.data_editor(
    task_df,
    column_config={
        "active":      st.column_config.CheckboxColumn("Include",          default=True,                       width="small"),
        "name":        st.column_config.TextColumn    ("Task Name",                                             width="medium"),
        "description": st.column_config.TextColumn    ("Description",                                          width="large"),
        "duration":    st.column_config.NumberColumn  ("Duration (min)",   min_value=1,  max_value=480,        width="small"),
        "priority":    st.column_config.NumberColumn  ("Priority (1–5)",   min_value=1,  max_value=5,          width="small",
                                                       help="1 = critical / survival, 5 = optional bonus"),
        "energy":      st.column_config.SelectboxColumn("Energy",          options=ENERGY_LEVELS,              width="small"),
        "type":        st.column_config.SelectboxColumn("Type",            options=TASK_TYPES,                 width="small"),
        "frequency":   st.column_config.SelectboxColumn("Frequency",       options=FREQUENCY,                  width="small"),
        "tags":        st.column_config.TextColumn    ("Tags (comma-separated)",                               width="large"),
    },
    hide_index=True,
    width="stretch",
    num_rows="dynamic",
    key="task_editor",
)

st.session_state.tasks = edited.to_dict("records")

# Profile summary strip
st.divider()
col_a, col_b = st.columns(2)
col_a.markdown(
    f"**Planning for:** {owner_name} &nbsp;·&nbsp; "
    f"{available_time} min available &nbsp;·&nbsp; "
    f"Energy: **{energy_battery}**"
)
col_b.markdown(
    f"**Pet:** {pet_name} ({species}) &nbsp;·&nbsp; "
    f"Loves: _{favorites_raw}_ &nbsp;·&nbsp; "
    f"Fears: _{fears_raw}_"
)

if st.button("🐾  Generate Tail-Wagging Timeline", type="primary", width="stretch"):
    favorites = [f.strip() for f in favorites_raw.split(",") if f.strip()]
    fears     = [f.strip() for f in fears_raw.split(",")     if f.strip()]

    # ── Pre-flight validation ────────────────────────────────────────────────────
    REQUIRED = {
        "name":      "Task Name",
        "duration":  "Duration (min)",
        "priority":  "Priority (1–5)",
        "energy":    "Energy",
        "type":      "Type",
        "frequency": "Frequency",
    }

    def _is_blank(val):
        try:
            return pd.isna(val)
        except TypeError:
            return val is None or str(val).strip() == ""

    validation_errors = []
    for row_idx, t in enumerate(st.session_state.tasks, start=1):
        active_val = t.get("active", True)
        if active_val is False or active_val == 0:
            continue                          # unchecked rows are intentionally skipped

        task_label = t.get("name") or f"Row {row_idx}"
        missing    = [label for field, label in REQUIRED.items() if _is_blank(t.get(field))]

        if missing:
            missing_str = ", ".join(f"**{m}**" for m in missing)
            validation_errors.append(
                f"⚠️ **{task_label}** (row {row_idx}) is missing: {missing_str}"
            )

    if validation_errors:
        st.error(
            "**Please fix the following before generating your plan:**\n\n"
            + "\n\n".join(validation_errors)
        )
        st.stop()
    # ── End validation ───────────────────────────────────────────────────────────

    def _cell(val, default):
        try:
            if pd.isna(val):
                return default
        except TypeError:
            pass
        return val if val is not None else default

    # Build Task objects
    task_objects: List[Task] = []
    for t in st.session_state.tasks:
        active_val = t.get("active", True)
        if active_val is False or active_val == 0:
            continue
        energy_val = str(_cell(t.get("energy"),    "Medium"))
        type_val   = str(_cell(t.get("type"),       "hobby"))
        freq_val   = str(_cell(t.get("frequency"),  "daily"))
        if energy_val not in ENERGY_LEVELS:
            energy_val = "Medium"
        if type_val not in TASK_TYPES:
            type_val = "hobby"
        if freq_val not in FREQUENCY:
            freq_val = "daily"
        task_objects.append(Task(
            name             = str(_cell(t.get("name"),        "Unnamed Task")),
            description      = str(_cell(t.get("description"), "")),
            duration_minutes = int(_cell(t.get("duration"),    15)),
            priority         = min(5, max(1, int(_cell(t.get("priority"), 3)))),
            energy_level     = energy_val,
            task_type        = type_val,
            frequency        = freq_val,
            tags             = [
                x.strip()
                for x in str(_cell(t.get("tags"), "")).split(",")
                if x.strip()
            ],
        ))

    # Build Pet → Owner → Scheduler hierarchy
    pet   = Pet(name=pet_name, species=species, favorites=favorites, fears=fears,
                tasks=task_objects)
    owner = Owner(name=owner_name, available_time_minutes=int(available_time),
                  energy_battery=energy_battery, pets=[pet])

    scheduler                = Scheduler(owner=owner)
    scheduled, skipped, note = scheduler.build_schedule()

    st.session_state.schedule = dict(
        scheduled      = scheduled,
        skipped        = skipped,
        note           = note,
        pet_name       = pet_name,
        owner_name     = owner_name,
        available_time = int(available_time),
    )

# ─── Schedule Display ───────────────────────────────────────────────────────────

if st.session_state.schedule:
    sch       = st.session_state.schedule
    scheduled = sch["scheduled"]
    skipped   = sch["skipped"]

    st.divider()
    st.subheader("🗓️ Tail-Wagging Timeline")
    st.info(sch["note"])

    total_time = sum(i.task.duration_minutes for i in scheduled)
    free_time  = sch["available_time"] - total_time

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tasks Scheduled", len(scheduled))
    m2.metric("Total Activity",  f"{total_time} min")
    m3.metric("Free Time Left",  f"{max(0, free_time)} min")
    m4.metric("Tasks Skipped",   len(skipped))

    st.caption(
        "🔴 Survival &nbsp;·&nbsp; 🟡 Care &nbsp;·&nbsp; 🟢 Hobby &nbsp;·&nbsp; "
        "⚡ High energy &nbsp;·&nbsp; 🔋 Medium &nbsp;·&nbsp; 🌿 Low"
    )
    st.divider()

    TYPE_ICON   = {"survival": "🔴", "care": "🟡", "hobby": "🟢"}
    ENERGY_ICON = {"High": "⚡", "Medium": "🔋", "Low": "🌿"}
    PRI_COLOR   = {1: "#ff4b4b", 2: "#ff8c00", 3: "#e6b800", 4: "#5a9e00", 5: "#4a90d9"}

    for item in scheduled:
        task      = item.task
        t_icon    = TYPE_ICON.get(task.task_type, "⚪")
        e_icon    = ENERGY_ICON.get(task.energy_level, "")
        pri_color = PRI_COLOR.get(task.priority, "#aaa")

        col_info, col_badge = st.columns([0.78, 0.22])

        with col_info:
            lock = " 🔒" if item.locked else ""
            st.markdown(f"### {t_icon} {task.name}{lock}")
            st.caption(
                f"{e_icon} **{task.energy_level} Energy** &nbsp;|&nbsp; "
                f"⏱️ **{task.duration_minutes} min** &nbsp;|&nbsp; "
                f"Priority **{task.priority}/5**"
                + (" &nbsp;|&nbsp; 🔒 **Locked In**" if item.locked else "")
            )

        with col_badge:
            bg    = "#fff3f3" if item.locked else "#f9f9f9"
            label = "Survival — Always First" if item.locked else f"Priority {task.priority} / 5"
            st.markdown(
                f"<div style='background:{bg};padding:10px 12px;border-radius:8px;"
                f"border:2px solid {pri_color};text-align:center;font-weight:700;"
                f"color:{pri_color};margin-top:10px'>{label}</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"<div style='background:#eef5ff;padding:12px 16px;border-radius:8px;"
            f"border-left:4px solid #4a90d9;margin:4px 0 24px 0;font-size:0.94em'>"
            f"<b>🐾 {sch['pet_name']}'s Perspective:</b>&nbsp; {item.reason}"
            f"</div>",
            unsafe_allow_html=True,
        )

    if skipped:
        with st.expander(f"⏭️ Skipped Tasks ({len(skipped)})", expanded=False):
            st.caption("These tasks didn't make today's schedule.")
            for s in skipped:
                st.markdown(
                    f"- **{s.task.name}** "
                    f"({s.task.duration_minutes} min · Priority {s.task.priority}/5) — "
                    f"_{s.reason}_"
                )
