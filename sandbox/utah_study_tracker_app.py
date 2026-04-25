from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(page_title="Utah Study Hours Tracker", page_icon="⏱️", layout="wide")

UTAH_TZ = ZoneInfo("America/Denver")
STATE_FILE = Path(__file__).with_name(".utah_study_tracker_state.json")
CORE_STUDY_DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"}
WEEKDAY_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
POMODORO_MINUTES = 60
POMODORO_HOURS = POMODORO_MINUTES / 60.0
# AUTO_REFRESH_SECONDS = 1
# AUTO_REFRESH_SECONDS

@dataclass(frozen=True)
class Course:
    name: str
    weekly_goal_hours: float


COURSES = [
    Course(name="Old Testament", weekly_goal_hours=6.0),
    Course(name="Algorithms", weekly_goal_hours=8.0),
    Course(name="Calculus", weekly_goal_hours=14.0),
    Course(name="Massively Parallel Computation", weekly_goal_hours=8.0),
]


def apply_dusty_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #ffffff;
            color: #2f3a4a;
        }
        [data-testid="stMetric"] {
            background-color: #f8fafe;
            border: 1px solid #c8d3e2;
            border-radius: 12px;
            padding: 0.55rem 0.75rem;
        }
        [data-testid="stInfo"] {
            background-color: #e9eef7;
            border: 1px solid #bccbe0;
            color: #2f3d52;
        }
        [data-testid="stButton"] button {
            background-color: #5f718d;
            color: #ffffff;
            border: 1px solid #4e607a;
            border-radius: 10px;
        }
        [data-testid="stButton"] button:hover {
            background-color: #536580;
            border-color: #44566f;
            color: #ffffff;
        }
        [data-testid="stProgressBar"] > div > div > div > div {
            background-color: #617695;
        }
        [data-testid="stExpander"] details {
            background-color: #f7f9fd;
            border: 1px solid #cad5e4;
            border-radius: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def now_utah() -> datetime:
    return datetime.now(UTAH_TZ)


def today_utah_str() -> str:
    return now_utah().date().isoformat()


def week_start_sunday_iso(now_local: datetime) -> str:
    day_offset = (now_local.weekday() + 1) % 7
    week_start = now_local.date().fromordinal(now_local.date().toordinal() - day_offset)
    return week_start.isoformat()


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        loaded = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def save_state(state: dict[str, Any]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def build_default_state() -> dict[str, Any]:
    return {
        "last_seen_date": today_utah_str(),
        "week_start": week_start_sunday_iso(now_utah()),
        "courses": {
            course.name: {
                "daily_hours": {},
                "running": False,
                "running_start_iso": None,
                "daily_target_sessions": {},
                "daily_completed_sessions": {},
            }
            for course in COURSES
        },
    }


def ensure_state_shape(state: dict[str, Any]) -> dict[str, Any]:
    if not state:
        state = build_default_state()
    state.setdefault("last_seen_date", today_utah_str())
    state.setdefault("week_start", week_start_sunday_iso(now_utah()))
    courses = state.setdefault("courses", {})

    for course in COURSES:
        course_state = courses.setdefault(course.name, {})
        course_state.setdefault("daily_hours", {})
        course_state.setdefault("running", False)
        course_state.setdefault("running_start_iso", None)
        course_state.setdefault("daily_target_sessions", {})
        course_state.setdefault("daily_completed_sessions", {})
    return state


def reset_for_new_week_if_needed(state: dict[str, Any], now_local: datetime) -> None:
    expected_week_start = week_start_sunday_iso(now_local)
    if state.get("week_start") != expected_week_start:
        state["week_start"] = expected_week_start
        for course_state in state["courses"].values():
            course_state["daily_hours"] = {}
            course_state["running"] = False
            course_state["running_start_iso"] = None


def rollover_daily_runtime_if_needed(state: dict[str, Any], now_local: datetime) -> None:
    today = now_local.date().isoformat()
    if state.get("last_seen_date") == today:
        return
    state["last_seen_date"] = today
    for course_state in state["courses"].values():
        course_state["running"] = False
        course_state["running_start_iso"] = None


def accumulate_runtime_into_today(course_state: dict[str, Any], now_local: datetime) -> None:
    if not course_state.get("running") or not course_state.get("running_start_iso"):
        return
    try:
        started = datetime.fromisoformat(str(course_state["running_start_iso"]))
    except ValueError:
        course_state["running"] = False
        course_state["running_start_iso"] = None
        return
    elapsed_hours = max((now_local - started).total_seconds(), 0.0) / 3600.0
    today = now_local.date().isoformat()
    daily_hours = course_state.setdefault("daily_hours", {})
    daily_hours[today] = float(daily_hours.get(today, 0.0)) + elapsed_hours
    course_state["running"] = False
    course_state["running_start_iso"] = None


def clear_running_timer(course_state: dict[str, Any]) -> None:
    course_state["running"] = False
    course_state["running_start_iso"] = None


def current_running_elapsed_hours(course_state: dict[str, Any], now_local: datetime) -> float:
    if not course_state.get("running") or not course_state.get("running_start_iso"):
        return 0.0
    try:
        started = datetime.fromisoformat(str(course_state["running_start_iso"]))
    except ValueError:
        return 0.0
    return max((now_local - started).total_seconds(), 0.0) / 3600.0


def weekly_total_hours(course_state: dict[str, Any], now_local: datetime) -> float:
    _ = now_local
    return sum(float(v) for v in course_state.get("daily_hours", {}).values())


def day_name_from_iso(date_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(date_iso)
    except ValueError:
        return "Unknown"
    return dt.strftime("%A")


def core_days_remaining_including_today(now_local: datetime) -> int:
    today_name = now_local.strftime("%A")
    if today_name == "Sunday":
        return 6
    ordered_core = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    if today_name in ordered_core:
        return len(ordered_core[ordered_core.index(today_name) :])
    return 0


def recommended_today_hours(course: Course, course_state: dict[str, Any], now_local: datetime) -> float:
    total_done = weekly_total_hours(course_state, now_local)
    remaining = max(course.weekly_goal_hours - total_done, 0.0)
    remaining_core_days = core_days_remaining_including_today(now_local)
    if now_local.strftime("%A") == "Sunday":
        return max(remaining / 6.0, 0.0)
    if remaining_core_days <= 0:
        return remaining
    return remaining / remaining_core_days


def recommended_today_sessions(course: Course, course_state: dict[str, Any], now_local: datetime) -> int:
    rec_hours = recommended_today_hours(course, course_state, now_local)
    if rec_hours <= 0:
        return 0
    return math.ceil(rec_hours / POMODORO_HOURS)


def target_sessions_for_course(course_state: dict[str, Any], today_iso: str, now_local: datetime, course: Course) -> int:
    daily_targets = course_state.setdefault("daily_target_sessions", {})
    if today_iso not in daily_targets:
        daily_targets[today_iso] = recommended_today_sessions(course, course_state, now_local)
    try:
        target = int(daily_targets.get(today_iso, 0))
    except (TypeError, ValueError):
        target = 0
    return max(target, 0)


def completed_sessions_for_course(course_state: dict[str, Any], today_iso: str) -> int:
    daily_completed = course_state.setdefault("daily_completed_sessions", {})
    try:
        count = int(daily_completed.get(today_iso, 0))
    except (TypeError, ValueError):
        count = 0
    return max(count, 0)


def set_completed_sessions_for_course(course_state: dict[str, Any], today_iso: str, count: int) -> None:
    daily_completed = course_state.setdefault("daily_completed_sessions", {})
    daily_completed[today_iso] = max(int(count), 0)


def _elapsed_seconds_since(iso_timestamp: str | None, now_local: datetime) -> float:
    if not iso_timestamp:
        return 0.0
    try:
        started = datetime.fromisoformat(str(iso_timestamp))
    except ValueError:
        return 0.0
    return max((now_local - started).total_seconds(), 0.0)


def render_session_circles(completed_sessions: int, target_sessions: int) -> str:
    if target_sessions <= 0:
        return '<span style="color:#5b6f8c;">No sessions targeted for today.</span>'
    done = min(completed_sessions, target_sessions)
    remaining = max(target_sessions - done, 0)
    filled = ''.join(
        '<span style="font-size:1.2rem; color:#8ea27e; margin-right:0.12rem;">●</span>'
        for _ in range(done)
    )
    empty = ''.join(
        '<span style="font-size:1.2rem; color:#d8dbe3; margin-right:0.12rem;">○</span>'
        for _ in range(remaining)
    )
    return f'<span style="display:inline-flex; align-items:center; gap:0.08rem;">{filled}{empty}</span>'


state = ensure_state_shape(load_state())
current_time = now_utah()
reset_for_new_week_if_needed(state, current_time)
rollover_daily_runtime_if_needed(state, current_time)
save_state(state)
apply_dusty_theme()

st.title("Weekly Study Tracker")
st.caption(
    "Tracks course hours in Utah time. Data persists across refresh. Week resets every Sunday."
)

col_a, col_b = st.columns([2, 1])
with col_a:
    st.subheader("Current Utah Time")
    st.info(current_time.strftime("%A, %Y-%m-%d %I:%M:%S %p %Z"))
with col_b:
    st.metric("Today", current_time.strftime("%A"))
    st.metric("Week Start (Sunday)", state["week_start"])

if st.button("Refresh time now"):
    st.rerun()

today_iso = current_time.date().isoformat()
today_name = current_time.strftime("%A")
st.markdown(
    "Target: finish recommended hours by **Friday evening**, with **Saturday** for carry-over. "
    "Sunday is a bonus catch-up day at the start of each week."
)
for course in COURSES:
    course_state = state["courses"][course.name]
    with st.container(border=True):
        st.subheader(course.name)
        total_done = weekly_total_hours(course_state, current_time)
        goal = course.weekly_goal_hours
        remaining = max(goal - total_done, 0.0)
        rec_today = recommended_today_hours(course, course_state, current_time)
        pct = min(total_done / goal if goal else 0.0, 1.0)

        stat1, stat2, stat3, stat4 = st.columns(4)
        stat1.metric("Weekly Goal", f"{goal:.1f}h")
        stat2.metric("Completed", f"{total_done:.2f}h")
        stat3.metric("Remaining", f"{remaining:.2f}h")
        stat4.metric(f"Recommended for {today_name}", f"{rec_today:.2f}h ({recommended_today_sessions(course, course_state, current_time)} sessions)")
        today_hours = float(course_state.get("daily_hours", {}).get(today_iso, 0.0))
        completed_sessions = completed_sessions_for_course(course_state, today_iso)
        target_sessions = target_sessions_for_course(course_state, today_iso, current_time, course)

        session_target = st.number_input(
            f"Today's session target for {course.name}",
            min_value=0,
            step=1,
            value=target_sessions,
            key=f"session_target_{course.name}_{today_iso}",
            help="Set how many study sessions you want to finish today.",
        )
        if session_target != target_sessions:
            course_state.setdefault("daily_target_sessions", {})[today_iso] = int(session_target)
            save_state(state)
            target_sessions = int(session_target)

        st.caption("Session circles (green = completed, blank = remaining)")
        st.markdown(render_session_circles(completed_sessions, target_sessions), unsafe_allow_html=True)
        st.write(f"**Completed sessions:** {completed_sessions} / {target_sessions}")

        session_update_col, session_hours_col = st.columns([2, 2])
        with session_update_col:
            if st.button(f"+ Add completed session for {course.name}", key=f"add_session_{course.name}_{today_iso}"):
                set_completed_sessions_for_course(course_state, today_iso, completed_sessions + 1)
                save_state(state)
                st.rerun()
            if st.button(f"- Remove completed session for {course.name}", key=f"remove_session_{course.name}_{today_iso}", disabled=completed_sessions <= 0):
                set_completed_sessions_for_course(course_state, today_iso, completed_sessions - 1)
                save_state(state)
                st.rerun()

        session_hours_col.metric("Today logged", f"{today_hours:.2f}h")

        st.progress(pct)

        controls_left, controls_right = st.columns([2, 3])
        with controls_left:
            is_running = bool(course_state.get("running"))
            if st.button(f"Refresh timer: {course.name}", key=f"refresh_{course.name}"):
                st.rerun()
            start_pressed = st.button(
                f"Start timer: {course.name}", key=f"start_{course.name}", disabled=is_running
            )
            stop_pressed = st.button(
                f"Stop timer (save progress): {course.name}", key=f"stop_{course.name}", disabled=not is_running
            )
            if start_pressed:
                course_state["running"] = True
                course_state["running_start_iso"] = now_utah().isoformat()
                save_state(state)
                st.rerun()
            if stop_pressed:
                accumulate_runtime_into_today(course_state, now_utah())
                save_state(state)
                st.rerun()

            live_elapsed = current_running_elapsed_hours(course_state, current_time) if is_running else 0.0
            timer_progress = min(max((live_elapsed * 60) / POMODORO_MINUTES, 0.0), 1.0)
            remaining_minutes = max(POMODORO_MINUTES - int(live_elapsed * 60), 0)
            st.progress(timer_progress)
            if is_running:
                st.caption(
                    f"Timer running: {live_elapsed*60:.0f}/{POMODORO_MINUTES} min "
                    f"(~{remaining_minutes} min remaining)"
                )
            else:
                st.caption("Timer not running")

        with controls_right:
            current_today_logged = float(course_state.get("daily_hours", {}).get(today_iso, 0.0))
            current_logged_hours = int(current_today_logged)
            current_logged_minutes = int(round((current_today_logged - current_logged_hours) * 60))
            edited_today_hours = st.number_input(
                f"Edit {today_name} hours for {course.name}",
                min_value=0,
                step=1,
                value=current_logged_hours,
                key=f"edit_hours_{course.name}_{today_iso}",
                help="Enter whole hours for today's log.",
            )
            edited_today_minutes = st.number_input(
                f"Edit {today_name} minutes for {course.name}",
                min_value=0,
                max_value=59,
                step=1,
                value=current_logged_minutes,
                key=f"edit_minutes_{course.name}_{today_iso}",
                help="Enter minutes for today's log (0-59).",
            )
            if st.button(f"Save edited time: {course.name}", key=f"save_edit_{course.name}"):
                total_hours = float(edited_today_hours) + float(edited_today_minutes) / 60.0
                course_state.setdefault("daily_hours", {})[today_iso] = total_hours
                save_state(state)
                st.success("Updated today's hours.")
                st.rerun()

        with st.expander("Daily breakdown (this week)"):
            day_rows: list[tuple[str, float]] = []
            for date_iso, hours in course_state.get("daily_hours", {}).items():
                day_name = day_name_from_iso(date_iso)
                day_rows.append((f"{day_name} ({date_iso})", float(hours)))
            day_rows.sort(key=lambda row: WEEKDAY_ORDER.index(row[0].split(" ")[0]) if row[0].split(" ")[0] in WEEKDAY_ORDER else 99)

            if day_rows:
                for label, hours in day_rows:
                    st.write(f"- {label}: {hours:.2f}h")
            else:
                st.write("No logged hours yet.")

st.divider()
if st.button("Reset this week now (all courses)"):
    state = build_default_state()
    save_state(state)
    st.rerun()
