from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


st.set_page_config(
    page_title="Week 2 Study Plan Dashboard",
    page_icon="✅",
    layout="wide",
)


HOUR_BLOCKS = [
    {
        "title": "Hour 1 (0:00-1:00) - Learn + Setup",
        "goal": "Restate each problem in 1-2 sentences.",
        "tasks": [
            "Read all prompts in `algorithments_tasks_and_tests/week02.tex` once.",
            "Open `learning/week02_study_checklist.md` and use it as your rubric.",
            "Create notes for: hashing/chaining, infinite-room search, two-sum = h, closest pair <= h.",
        ],
    },
    {
        "title": "Hour 2 (1:00-2:00) - Hash Table Task",
        "goal": "Build the final chained table correctly.",
        "tasks": [
            "Compute each hash index for C = [3, 18, 42, 31, 40, 56, 71].",
            "Use h(k) = (8k + 2) mod 7 with table size 7.",
            "Resolve collisions by chaining and appending to the end.",
            "Explain why collisions happen and how chaining impacts operations.",
        ],
    },
    {
        "title": "Hour 3 (2:00-3:00) - Infinite Rooms Search O(log k)",
        "goal": "Write algorithm and runtime argument clearly.",
        "tasks": [
            "Bracket with rooms 1, 2, 4, 8, ... until target room k is enclosed.",
            "Run binary search in the bracketed range.",
            "State why doubling is O(log k), binary search is O(log k), total is O(log k).",
        ],
    },
    {
        "title": "Hour 4 (3:00-4:00) - Two-Sum Exact = h (Expected O(n))",
        "goal": "Provide expected-linear hash-based solution.",
        "tasks": [
            "Iterate each x in S and check if h - x has been seen.",
            "If found, report pair exists; otherwise insert x.",
            "Explain correctness: second pair element discovers first.",
            "Explain complexity: hash lookup/insert expected O(1), total expected O(n).",
        ],
    },
    {
        "title": "Hour 5 (4:00-5:00) - Closest Sum <= h (Worst-Case O(n))",
        "goal": "Deliver worst-case linear argument under bounded assumptions.",
        "tasks": [
            "Use bounded-integer setting h = 800n^8 from prompt assumptions.",
            "Sort in linear time under integer-key model assumptions.",
            "Use two pointers from both ends to track best valid sum <= h.",
            "Justify total worst-case O(n): linear sort + linear two-pointer scan.",
        ],
    },
    {
        "title": "Hour 6 (5:00-6:00) - Explain + Review + Final Check",
        "goal": "Finish cleanly and verify all deliverables.",
        "tasks": [
            "Do a Feynman pass: explain all 4 tasks out loud in simple language.",
            "Check every item in `learning/week02_study_checklist.md`.",
            "Polish `.tex` responses: clear steps, explicit runtime, expected vs worst-case wording.",
            "Create 10 flashcards from mistakes for spaced review.",
        ],
    },
]

FINAL_SUBMISSION_CHECKLIST = [
    "Hash indices and final chained table are correct.",
    "Infinite-room algorithm and O(log k) proof are included.",
    "Two-sum expected O(n) algorithm and explanation are included.",
    "Closest <= h worst-case O(n) algorithm and proof are included.",
    "Expected vs worst-case distinctions are explicit.",
    "No answer exceeds h in closest-sum part.",
]

AGENT_MODES = [
    "IntakeMode - parse request and scope impacted files",
    "PlanningMode - decide minimal edits and dependencies",
    "ImplementationMode - apply direct in-repo Streamlit edits",
    "ValidationMode - run checks, retry fixes up to 5 times",
]

AGENT_ACTORS = [
    "IntakeActor",
    "PlanningActor",
    "ImplementationActor",
    "DependencyActor",
    "ValidationActor",
    "SafetyActor",
    "RetryStateActor",
    "ChangeLogStateActor",
    "SecretsApprovalStateActor",
]


def checkbox_key(prefix: str, left: int, right: int) -> str:
    return f"{prefix}_{left}_{right}"


STATE_FILE = Path(__file__).with_name(".week02_checklist_state.json")


def load_persisted_state() -> dict[str, bool]:
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): bool(v) for k, v in data.items()}


def save_persisted_state(state: dict[str, bool]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        # Non-fatal: app should still work even if write fails.
        pass


def persist_checkboxes() -> None:
    persisted: dict[str, bool] = {}
    for key, value in st.session_state.items():
        if key.startswith("task_") or key.startswith("final_"):
            persisted[key] = bool(value)
    save_persisted_state(persisted)


def initialize_checkbox_state() -> None:
    persisted = load_persisted_state()
    for hour_index, hour_block in enumerate(HOUR_BLOCKS):
        tasks = hour_block["tasks"]
        assert isinstance(tasks, list)
        for task_index, _ in enumerate(tasks):
            key = checkbox_key("task", hour_index, task_index)
            st.session_state.setdefault(key, persisted.get(key, False))
    for checklist_index, _ in enumerate(FINAL_SUBMISSION_CHECKLIST):
        key = checkbox_key("final", 0, checklist_index)
        st.session_state.setdefault(key, persisted.get(key, False))


initialize_checkbox_state()


def render_hour_block(index: int, block: dict[str, object]) -> tuple[int, int]:
    st.subheader(block["title"])
    tasks = block["tasks"]
    assert isinstance(tasks, list)
    completed = 0

    for task_index, task in enumerate(tasks):
        checked = st.checkbox(
            task,
            key=checkbox_key("task", index, task_index),
            on_change=persist_checkboxes,
        )
        if checked:
            completed += 1

    st.caption(f"End goal: {block['goal']}")
    st.progress(completed / len(tasks))
    st.divider()
    return completed, len(tasks)


st.title("Week 2 Study Plan + Builder Clarity Dashboard")
st.caption(
    "Interactive checklist view of `learning/week02_6hour_plan.md` with a clean "
    "summary of `agents copy/streamlit-builder.jsonld`."
)

tab_plan, tab_builder = st.tabs(["Study Plan Checklist", "Streamlit Builder Summary"])

with tab_plan:
    st.markdown("### Weekly Focus")
    st.write("- Deliberate Practice")
    st.write("- Learn -> Apply -> Explain -> Review")

    total_done = 0
    total_items = 0
    for hour_index, hour_block in enumerate(HOUR_BLOCKS):
        done, item_count = render_hour_block(hour_index, hour_block)
        total_done += done
        total_items += item_count

    st.markdown("### Final Submission Checklist")
    final_done = 0
    for checklist_index, item in enumerate(FINAL_SUBMISSION_CHECKLIST):
        checked = st.checkbox(
            item,
            key=checkbox_key("final", 0, checklist_index),
            on_change=persist_checkboxes,
        )
        if checked:
            final_done += 1

    grand_done = total_done + final_done
    grand_total = total_items + len(FINAL_SUBMISSION_CHECKLIST)
    st.markdown(f"### Progress: {grand_done}/{grand_total} complete")
    st.progress(grand_done / grand_total if grand_total else 0.0)

    if st.button("Reset all checkboxes"):
        for key in list(st.session_state.keys()):
            if key.startswith("task_") or key.startswith("final_"):
                st.session_state[key] = False
        save_persisted_state({})
        st.rerun()

with tab_builder:
    st.markdown("### Builder Agent Pattern")
    st.code("Pattern: 4-mode-9-actor", language="text")
    st.write(
        "Purpose: Build/edit Streamlit apps directly in-repo with validation and "
        "safety checks."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Modes")
        for mode in AGENT_MODES:
            st.write(f"- {mode}")
    with col2:
        st.markdown("#### Actors")
        for actor in AGENT_ACTORS:
            st.write(f"- {actor}")

    st.markdown("#### Key Constraints")
    st.write("- Default entry point: `app.py`")
    st.write("- Use `pip` + `requirements.txt` for dependencies")
    st.write("- Run post-edit checks and auto-fix attempts (max 5)")
    st.write("- Never deploy/publish automatically")
    st.write("- Ask for approval before editing secret/credential files")

