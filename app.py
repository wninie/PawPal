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
    st.table(
        [
            {
                "title": t.title,
                "category": t.category,
                "due": t.due_time.strftime("%Y-%m-%d %H:%M"),
                "duration (min)": t.duration_minutes,
                "priority": t.priority,
                "repeats": t.recurrence,
                "done": t.completed,
            }
            for t in active_pet.tasks
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

st.subheader("Build Schedule")
st.caption("Generate a daily plan from the backlog using the pet's constraints.")

scol1, scol2 = st.columns(2)
with scol1:
    plan_date = st.date_input("Plan for", value=date.today(), key="plan_date")
with scol2:
    max_daily = st.number_input(
        "Max tasks per day", min_value=1, max_value=20, value=5
    )

# Order categories so higher-priority ones are scheduled first.
priority_order = st.multiselect(
    "Category priority (highest first)",
    ["medication", "feeding", "walk", "grooming", "play"],
    default=["medication", "feeding", "walk"],
)

if st.button("Generate schedule"):
    active_pet.constraints = Constraints(
        constraint_id=f"{active_pet.pet_id}-constraints",
        max_daily_tasks=int(max_daily),
        priorities=priority_order,
    )
    plan = active_pet.generate_daily_plan(plan_date)

    if plan.tasks:
        st.success(f"Scheduled {len(plan.tasks)} task(s).")
        st.table(
            [
                {
                    "time": t.due_time.strftime("%H:%M"),
                    "title": t.title,
                    "category": t.category,
                    "duration (min)": t.duration_minutes,
                    "priority": t.priority,
                }
                for t in plan.tasks
            ]
        )
    else:
        st.warning("No tasks matched this day. Add tasks due on the plan date.")

    # Same-pet conflicts found while building this plan.
    for warning in plan.warnings:
        st.warning(warning)

    # Cross-pet conflicts: two pets needing attention at the same time.
    cross_pet = [
        w for w in owner.detect_conflicts(plan_date) if w not in plan.warnings
    ]
    for warning in cross_pet:
        st.warning(warning)

    st.markdown("**Why this plan?**")
    st.text(plan.explain_reasons())
