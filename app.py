import streamlit as st
from pawpal_system import Owner, Pet, Task, Plan, Constraints, TimeWindow
from datetime import datetime, date, time

# Maps the human-friendly priority labels used in the UI to the integer
# priority that Task.priority expects (higher = more important).
PRIORITY_LEVELS = {"low": 1, "medium": 2, "high": 3}
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner")
owner_name = st.text_input("Owner name", value="Jordan")
owner_email = st.text_input("Owner email", value="jordan@example.com")

# Keep a single Owner instance in the session "vault" so it survives reruns.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        owner_id="owner-1",
        name=owner_name,
        email=owner_email,
        phone="",
    )
owner = st.session_state.owner

# Sync the editable identity fields back onto the persisted instance.
owner.update_profile(name=owner_name, email=owner_email)

# Counter used to hand out unique ids to newly created tasks.
if "task_counter" not in st.session_state:
    st.session_state.task_counter = 0

st.divider()

st.subheader("Pets")
st.caption("Create a pet, then add it to the owner.")

pcol1, pcol2, pcol3 = st.columns(3)
with pcol1:
    pet_name = st.text_input("Pet name", value="Mochi")
with pcol2:
    species = st.selectbox("Species", ["dog", "cat", "other"])
with pcol3:
    breed = st.text_input("Breed", value="")

if st.button("Add pet"):
    pet = Pet(
        pet_id=f"pet-{pet_name.strip().lower()}",
        name=pet_name,
        species=species,
        breed=breed,
        age=0,
        weight=0.0,
    )
    owner.add_pet(pet)  # de-dupes by pet_id
    st.success(f"Added {pet_name}. Owner now has {len(owner.pets)} pet(s).")

if not owner.pets:
    st.info("No pets yet. Add one above to start scheduling tasks.")
    st.stop()

# Pick the pet we're currently scheduling for.
pet_labels = [f"{p.name} ({p.species})" for p in owner.pets]
active_index = st.selectbox(
    "Active pet",
    range(len(owner.pets)),
    format_func=lambda i: pet_labels[i],
)
active_pet = owner.pets[active_index]

st.divider()

st.subheader("Tasks")
st.caption(f"Add care tasks to {active_pet.name}'s backlog.")

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", list(PRIORITY_LEVELS), index=2)

col4, col5, col6 = st.columns(3)
with col4:
    category = st.selectbox(
        "Category", ["walk", "feeding", "medication", "grooming", "play"]
    )
with col5:
    due_date = st.date_input("Due date", value=date.today())
with col6:
    due_clock = st.time_input("Due time", value=time(9, 0))

# A recurring task re-schedules itself for the next occurrence when completed.
recurrence = st.selectbox("Repeats", ["none", "daily", "weekly"])

if st.button("Add task"):
    st.session_state.task_counter += 1
    task = Task(
        task_id=f"task-{st.session_state.task_counter}",
        title=task_title,
        description="",
        category=category,
        due_time=datetime.combine(due_date, due_clock),
        duration_minutes=int(duration),
        priority=PRIORITY_LEVELS[priority],
        recurrence=recurrence,
    )
    active_pet.add_task(task)  # de-dupes by task_id
    st.success(f"Added '{task_title}' to {active_pet.name}'s backlog.")

if active_pet.tasks:
    st.write(f"Current backlog for {active_pet.name}:")

    # Let the owner focus the backlog without deleting anything.
    show_done = st.checkbox("Show completed tasks", value=True)

    # Reuse the domain helper so the backlog reads in schedule order
    # (chronological) rather than the order tasks happened to be added.
    backlog = Task.sort_by_time(active_pet.tasks)
    if not show_done:
        backlog = [t for t in backlog if not t.completed]

    PRIORITY_LABELS = {v: k for k, v in PRIORITY_LEVELS.items()}
    st.table(
        [
            {
                "title": t.title,
                "category": t.category,
                "due": t.due_time.strftime("%Y-%m-%d %H:%M"),
                "duration (min)": t.duration_minutes,
                "priority": PRIORITY_LABELS.get(t.priority, t.priority),
                "repeats": t.recurrence,
                "status": "✓ done" if t.completed else "○ open",
            }
            for t in backlog
        ]
    )

    # Mark a task complete. Recurring tasks automatically spawn the next
    # occurrence (today + one interval) back into the backlog.
    open_tasks = [t for t in active_pet.tasks if not t.completed]
    if open_tasks:
        done_index = st.selectbox(
            "Mark complete",
            range(len(open_tasks)),
            format_func=lambda i: f"{open_tasks[i].title} "
            f"({open_tasks[i].due_time.strftime('%Y-%m-%d %H:%M')})",
        )
        if st.button("Complete task"):
            done_task = open_tasks[done_index]
            next_task = active_pet.complete_task(done_task.task_id)
            if next_task is not None:
                st.success(
                    f"Completed '{done_task.title}'. Next {done_task.recurrence} "
                    f"occurrence scheduled for "
                    f"{next_task.due_time.strftime('%Y-%m-%d %H:%M')}."
                )
            else:
                st.success(f"Completed '{done_task.title}'.")
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Constraints")
st.caption(
    f"The scheduling rules PawPal+ must respect when planning {active_pet.name}'s day."
)

ccol1, ccol2 = st.columns(2)
with ccol1:
    max_daily = st.number_input(
        "Max tasks per day", min_value=1, max_value=20, value=5
    )
with ccol2:
    budget = st.number_input(
        "Daily budget ($, optional)", min_value=0.0, value=0.0, step=5.0
    )

# Order categories so higher-priority ones are scheduled first.
priority_order = st.multiselect(
    "Category priority (highest first)",
    ["medication", "feeding", "walk", "grooming", "play"],
    default=["medication", "feeding", "walk"],
)

# Available time windows: only tasks that start inside a window are eligible
# to be scheduled (Constraints.available_times). Stored as (start, end) time
# pairs in session state and combined with the plan date at generate time.
st.markdown("**Available time windows**")
st.caption("The hours you're free to do tasks. Leave empty to allow any time of day.")

if "windows" not in st.session_state:
    st.session_state.windows = []

wcol1, wcol2, wcol3 = st.columns([2, 2, 1])
with wcol1:
    win_start = st.time_input("From", value=time(8, 0), key="win_start")
with wcol2:
    win_end = st.time_input("To", value=time(12, 0), key="win_end")
with wcol3:
    st.write("")  # spacer to line the button up with the time inputs
    st.write("")
    if st.button("Add window"):
        if win_end > win_start:
            st.session_state.windows.append((win_start, win_end))
        else:
            st.warning("A window's end time must be after its start time.")

if st.session_state.windows:
    st.table(
        [
            {"from": s.strftime("%H:%M"), "to": e.strftime("%H:%M")}
            for s, e in st.session_state.windows
        ]
    )
    if st.button("Clear windows"):
        st.session_state.windows = []
else:
    st.caption("No windows set — tasks may be scheduled at any time.")

st.divider()

st.subheader("Build Schedule")
st.caption("Generate a daily plan from the backlog using the constraints above.")

plan_date = st.date_input("Plan for", value=date.today(), key="plan_date")

if st.button("Generate schedule"):
    # Anchor each (start, end) time-of-day window to the plan date so the
    # planner can compare them against tasks' full datetimes.
    windows = [
        TimeWindow(
            start=datetime.combine(plan_date, s),
            end=datetime.combine(plan_date, e),
        )
        for s, e in st.session_state.windows
    ]
    active_pet.constraints = Constraints(
        constraint_id=f"{active_pet.pet_id}-constraints",
        max_daily_tasks=int(max_daily),
        priorities=priority_order,
        available_times=windows,
        budget=float(budget),
    )
    plan = active_pet.generate_daily_plan(plan_date)

    # Cross-pet conflicts: two pets needing attention at the same time.
    # Detected by the owner (the only object that sees every pet) and kept
    # separate from same-pet conflicts because they're physically impossible
    # to satisfy — you can't be in two places at once.
    cross_pet = [
        w for w in owner.detect_conflicts(plan_date) if w not in plan.warnings
    ]

    # Flag which scheduled tasks actually take part in a conflict so we can
    # mark those exact rows in the schedule table below.
    conflicted_titles = set()
    for warning in plan.warnings + cross_pet:
        for t in plan.tasks:
            if f"'{t.title}'" in warning:
                conflicted_titles.add(t.title)

    if plan.tasks:
        st.success(f"Scheduled {len(plan.tasks)} task(s) for {plan_date:%b %d}.")
        st.table(
            [
                {
                    "": "⚠️" if t.title in conflicted_titles else "",
                    "time": f"{t.due_time:%H:%M}–{t.end_time():%H:%M}",
                    "title": t.title,
                    "category": t.category,
                    "duration (min)": t.duration_minutes,
                    "priority": t.priority,
                }
                for t in plan.tasks
            ]
        )
    else:
        st.info("No tasks matched this day. Add tasks due on the plan date.")

    # --- Conflicts -------------------------------------------------------
    # Present conflicts as their own block so they aren't lost among the
    # plan, and make them actionable for a pet owner rather than raw logs.
    if cross_pet:
        # Highest severity: the owner literally can't do both at once.
        st.error(
            f"🚨 {len(cross_pet)} scheduling clash between pets — "
            "you can't be in two places at once. Move one task to another time."
        )
        for warning in cross_pet:
            st.markdown(f"- {warning.removeprefix('WARNING - ')}")

    if plan.warnings:
        st.warning(
            f"⚠️ {len(plan.warnings)} overlap in {active_pet.name}'s day. "
            "Consider rescheduling one task or shortening its duration."
        )
        for warning in plan.warnings:
            st.markdown(f"- {warning.removeprefix('WARNING - ')}")

    if plan.tasks and not plan.warnings and not cross_pet:
        st.caption("✅ No time conflicts detected.")

    with st.expander("Why this plan?"):
        st.text(plan.explain_reasons())
