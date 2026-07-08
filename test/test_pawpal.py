"""Tests for the PawPal system.

Organized by concern:
  - Task basics (status, end_time)
  - Recurrence (the highest-risk logic)
  - Conflict detection (the "same time" edge case)
  - Planning: filter / sort / cap
  - Owner: multi-pet access and cross-pet conflicts
  - Empty / boundary happy paths
  - De-dupe and error handling
"""

from datetime import date, datetime, timedelta

import pytest

from pawpal_system import (
    Constraints,
    Owner,
    Pet,
    Plan,
    Task,
    TimeWindow,
)

# A fixed reference day so tests are deterministic regardless of "today".
DAY = date(2026, 7, 7)


def at(hour, minute=0):
    """A datetime on the reference DAY at the given time."""
    return datetime(DAY.year, DAY.month, DAY.day, hour, minute)


def make_task(task_id="t1", **overrides):
    kwargs = dict(
        task_id=task_id,
        title="Morning walk",
        description="Walk around the block",
        category="exercise",
        due_time=at(9, 0),
        duration_minutes=30,
        priority=1,
    )
    kwargs.update(overrides)
    return Task(**kwargs)


def make_pet(pet_id="p1", name="Rex", constraints=None, tasks=None):
    pet = Pet(
        pet_id=pet_id,
        name=name,
        species="dog",
        breed="Labrador",
        age=3,
        weight=25.0,
        constraints=constraints,
    )
    for t in tasks or []:
        pet.add_task(t)
    return pet


# --------------------------------------------------------------------------
# Task basics
# --------------------------------------------------------------------------


def test_mark_completed_changes_status():
    """Calling mark_completed() changes the task's status to done."""
    task = make_task()
    assert task.completed is False

    task.mark_completed()

    assert task.completed is True


def test_end_time_is_due_plus_duration():
    task = make_task(due_time=at(9, 0), duration_minutes=45)
    assert task.end_time() == at(9, 45)


def test_add_task_increases_pet_task_count():
    """Adding a task to a pet increases the pet's task count."""
    pet = make_pet()
    assert len(pet.tasks) == 0

    pet.add_task(make_task())

    assert len(pet.tasks) == 1


# --------------------------------------------------------------------------
# Recurrence
# --------------------------------------------------------------------------


def test_daily_recurrence_schedules_next_day_uncompleted():
    """Completing a daily task yields tomorrow's occurrence, not done."""
    task = make_task(due_time=at(8, 0), recurrence="daily")

    nxt = task.mark_completed(as_of=DAY)

    assert nxt is not None
    assert nxt.completed is False
    assert nxt.due_time == datetime(DAY.year, DAY.month, DAY.day, 8, 0) + timedelta(days=1)
    # Time of day is preserved.
    assert nxt.due_time.time() == task.due_time.time()


def test_weekly_recurrence_schedules_seven_days_out():
    task = make_task(recurrence="weekly")
    nxt = task.next_occurrence(as_of=DAY)
    assert nxt is not None
    assert nxt.due_time.date() == DAY + timedelta(weeks=1)


def test_next_occurrence_has_unique_id():
    """The spawned occurrence must not collide with the original id."""
    task = make_task(task_id="feed", recurrence="daily")
    nxt = task.next_occurrence(as_of=DAY)
    assert nxt.task_id != task.task_id


def test_one_off_task_does_not_recur():
    task = make_task(recurrence="none")
    assert task.is_recurring() is False
    assert task.mark_completed(as_of=DAY) is None


def test_next_occurrence_anchors_to_completion_date_not_old_due():
    """An overdue daily task still lands in the future (as_of + 1 day)."""
    overdue = make_task(due_time=at(8, 0), recurrence="daily")
    completion_day = DAY + timedelta(days=30)
    nxt = overdue.next_occurrence(as_of=completion_day)
    assert nxt.due_time.date() == completion_day + timedelta(days=1)


def test_complete_task_adds_next_occurrence_to_backlog():
    task = make_task(task_id="walk", recurrence="daily")
    pet = make_pet(tasks=[task])

    nxt = pet.complete_task("walk", as_of=DAY)

    assert nxt is not None
    assert nxt in pet.tasks
    assert len(pet.tasks) == 2  # original (completed) + new occurrence


# --------------------------------------------------------------------------
# Conflict detection
# --------------------------------------------------------------------------


def test_tasks_at_exact_same_time_conflict():
    a = make_task(task_id="a", due_time=at(8, 0), duration_minutes=30)
    b = make_task(task_id="b", due_time=at(8, 0), duration_minutes=10)
    assert a.conflicts_with(b) is True


def test_zero_duration_same_start_still_conflicts():
    a = make_task(task_id="a", due_time=at(8, 0), duration_minutes=0)
    b = make_task(task_id="b", due_time=at(8, 0), duration_minutes=0)
    assert a.conflicts_with(b) is True


def test_back_to_back_tasks_do_not_conflict():
    """Half-open windows: one ending exactly as the next starts is fine."""
    a = make_task(task_id="a", due_time=at(9, 0), duration_minutes=30)  # ends 9:30
    b = make_task(task_id="b", due_time=at(9, 30), duration_minutes=30)  # starts 9:30
    assert a.conflicts_with(b) is False


def test_overlapping_tasks_conflict():
    a = make_task(task_id="a", due_time=at(9, 0), duration_minutes=30)  # 9:00-9:30
    b = make_task(task_id="b", due_time=at(9, 15), duration_minutes=30)  # 9:15-9:45
    assert a.conflicts_with(b) is True


def test_same_pet_conflict_surfaces_in_plan_warnings():
    c = Constraints(constraint_id="c", max_daily_tasks=5)
    pet = make_pet(
        constraints=c,
        tasks=[
            make_task(task_id="a", due_time=at(8, 0), duration_minutes=30),
            make_task(task_id="b", due_time=at(8, 0), duration_minutes=15),
        ],
    )
    plan = pet.generate_daily_plan(DAY)
    assert len(plan.warnings) == 1


# --------------------------------------------------------------------------
# Planning: filter / sort / cap
# --------------------------------------------------------------------------


def test_plan_excludes_tasks_due_on_a_different_day():
    c = Constraints(constraint_id="c", max_daily_tasks=5)
    pet = make_pet(
        constraints=c,
        tasks=[
            make_task(task_id="today", due_time=at(9, 0)),
            make_task(task_id="tomorrow", due_time=at(9, 0) + timedelta(days=1)),
        ],
    )
    plan = pet.generate_daily_plan(DAY)
    ids = {t.task_id for t in plan.tasks}
    assert ids == {"today"}


def test_plan_excludes_completed_tasks():
    c = Constraints(constraint_id="c", max_daily_tasks=5)
    done = make_task(task_id="done", completed=True)
    pet = make_pet(constraints=c, tasks=[done, make_task(task_id="open")])
    plan = pet.generate_daily_plan(DAY)
    assert {t.task_id for t in plan.tasks} == {"open"}


def test_max_daily_cap_keeps_highest_priority_tasks():
    """With a cap of 2, the two highest-priority tasks win."""
    c = Constraints(constraint_id="c", max_daily_tasks=2)
    pet = make_pet(
        constraints=c,
        tasks=[
            make_task(task_id="low", priority=1, due_time=at(9, 0)),
            make_task(task_id="high", priority=3, due_time=at(10, 0)),
            make_task(task_id="mid", priority=2, due_time=at(11, 0)),
        ],
    )
    plan = pet.generate_daily_plan(DAY)
    assert len(plan.tasks) == 2
    assert {t.task_id for t in plan.tasks} == {"high", "mid"}


def test_category_priority_beats_task_priority():
    """Constraint category order ranks first; task priority breaks ties."""
    c = Constraints(
        constraint_id="c",
        max_daily_tasks=5,
        priorities=["medication", "feeding"],
    )
    pet = make_pet(
        constraints=c,
        tasks=[
            make_task(task_id="feed", category="feeding", priority=3, due_time=at(9, 0)),
            make_task(task_id="med", category="medication", priority=1, due_time=at(10, 0)),
        ],
    )
    plan = pet.generate_daily_plan(DAY)
    # Even though "feed" has higher task priority, "med" is in a
    # higher-ranked category, so it is selected first.
    assert plan.selection_order[0].task_id == "med"


def test_out_of_window_task_does_not_consume_a_capped_slot():
    """Stage-1 window filter runs before the stage-3 cap.

    An out-of-window task must be dropped in filtering, so it can't take a
    limited daily slot away from an in-window task.
    """
    window = TimeWindow(start=at(6, 0), end=at(12, 0))
    c = Constraints(
        constraint_id="c",
        max_daily_tasks=1,
        available_times=[window],
    )
    pet = make_pet(
        constraints=c,
        tasks=[
            # Out of window (evening) but higher priority — must NOT win the slot.
            make_task(task_id="evening", priority=3, due_time=at(20, 0)),
            # In window, lower priority — should be the one scheduled.
            make_task(task_id="morning", priority=1, due_time=at(9, 0)),
        ],
    )
    plan = pet.generate_daily_plan(DAY)
    assert {t.task_id for t in plan.tasks} == {"morning"}


def test_plan_tasks_are_sorted_chronologically():
    c = Constraints(constraint_id="c", max_daily_tasks=5)
    pet = make_pet(
        constraints=c,
        tasks=[
            make_task(task_id="late", due_time=at(18, 0)),
            make_task(task_id="early", due_time=at(7, 0)),
            make_task(task_id="mid", due_time=at(12, 0)),
        ],
    )
    plan = pet.generate_daily_plan(DAY)
    times = [t.due_time for t in plan.tasks]
    assert times == sorted(times)


def test_no_constraints_means_no_cap_and_no_window_filter():
    pet = make_pet(
        constraints=None,
        tasks=[make_task(task_id=f"t{i}", due_time=at(8 + i)) for i in range(6)],
    )
    plan = pet.generate_daily_plan(DAY)
    assert len(plan.tasks) == 6


# --------------------------------------------------------------------------
# Task.sort_by_time
# --------------------------------------------------------------------------


def test_sort_by_time_orders_and_breaks_ties_by_id():
    t_late = make_task(task_id="z", due_time=at(10, 0))
    t_b = make_task(task_id="b", due_time=at(9, 0))
    t_a = make_task(task_id="a", due_time=at(9, 0))  # same time as t_b
    ordered = Task.sort_by_time([t_late, t_b, t_a])
    assert [t.task_id for t in ordered] == ["a", "b", "z"]


# --------------------------------------------------------------------------
# Owner: multi-pet access and cross-pet conflicts
# --------------------------------------------------------------------------


def test_all_tasks_combines_every_pets_backlog():
    owner = Owner(owner_id="o1", name="Jo", email="jo@x.com", phone="")
    owner.add_pet(make_pet(pet_id="p1", name="A", tasks=[make_task(task_id="a")]))
    owner.add_pet(make_pet(pet_id="p2", name="B", tasks=[make_task(task_id="b")]))
    assert {t.task_id for t in owner.all_tasks()} == {"a", "b"}


def test_tasks_for_pet_is_case_insensitive():
    owner = Owner(owner_id="o1", name="Jo", email="jo@x.com", phone="")
    owner.add_pet(make_pet(pet_id="p1", name="Mochi", tasks=[make_task(task_id="a")]))
    assert len(owner.tasks_for_pet("MOCHI")) == 1
    assert owner.tasks_for_pet("nobody") == []


def test_cross_pet_conflict_detected_by_owner():
    owner = Owner(owner_id="o1", name="Jo", email="jo@x.com", phone="")
    owner.add_pet(
        make_pet(pet_id="p1", name="Dog", tasks=[make_task(task_id="a", due_time=at(8, 0))])
    )
    owner.add_pet(
        make_pet(pet_id="p2", name="Cat", tasks=[make_task(task_id="b", due_time=at(8, 0))])
    )
    warnings = owner.detect_conflicts(DAY)
    assert len(warnings) == 1


def test_detect_conflicts_ignores_completed_tasks():
    owner = Owner(owner_id="o1", name="Jo", email="jo@x.com", phone="")
    owner.add_pet(
        make_pet(
            pet_id="p1",
            name="Dog",
            tasks=[make_task(task_id="a", due_time=at(8, 0), completed=True)],
        )
    )
    owner.add_pet(
        make_pet(pet_id="p2", name="Cat", tasks=[make_task(task_id="b", due_time=at(8, 0))])
    )
    assert owner.detect_conflicts(DAY) == []


def test_detect_conflicts_respects_date_filter():
    owner = Owner(owner_id="o1", name="Jo", email="jo@x.com", phone="")
    owner.add_pet(
        make_pet(pet_id="p1", name="Dog", tasks=[make_task(task_id="a", due_time=at(8, 0))])
    )
    owner.add_pet(
        make_pet(
            pet_id="p2",
            name="Cat",
            tasks=[make_task(task_id="b", due_time=at(8, 0) + timedelta(days=1))],
        )
    )
    # Same clock time but different days -> no conflict for DAY.
    assert owner.detect_conflicts(DAY) == []


# --------------------------------------------------------------------------
# Empty / boundary happy paths
# --------------------------------------------------------------------------


def test_pet_with_no_tasks_produces_empty_plan():
    pet = make_pet(constraints=Constraints(constraint_id="c", max_daily_tasks=5))
    plan = pet.generate_daily_plan(DAY)
    assert plan.tasks == []
    assert plan.warnings == []
    assert "No tasks were scheduled." in plan.explain_reasons()


def test_explain_reasons_lists_scheduled_tasks():
    c = Constraints(constraint_id="c", max_daily_tasks=5)
    pet = make_pet(constraints=c, tasks=[make_task(task_id="a", title="Feed")])
    text = pet.generate_daily_plan(DAY).explain_reasons()
    assert "Feed" in text


# --------------------------------------------------------------------------
# De-dupe and error handling
# --------------------------------------------------------------------------


def test_add_task_dedupes_by_id():
    pet = make_pet()
    pet.add_task(make_task(task_id="dup", title="first"))
    pet.add_task(make_task(task_id="dup", title="second"))
    assert len(pet.tasks) == 1
    assert pet.tasks[0].title == "first"  # first wins; duplicate ignored


def test_add_pet_dedupes_by_id():
    owner = Owner(owner_id="o1", name="Jo", email="jo@x.com", phone="")
    owner.add_pet(make_pet(pet_id="p1"))
    owner.add_pet(make_pet(pet_id="p1"))
    assert len(owner.pets) == 1


def test_complete_unknown_task_raises_keyerror():
    pet = make_pet()
    with pytest.raises(KeyError):
        pet.complete_task("nope")


def test_edit_unknown_task_raises_keyerror():
    pet = make_pet()
    with pytest.raises(KeyError):
        pet.edit_task("nope", title="x")


# --------------------------------------------------------------------------
# Constraints.validate
# --------------------------------------------------------------------------


def test_validate_rejects_plan_over_daily_cap():
    c = Constraints(constraint_id="c", max_daily_tasks=1)
    plan = Plan(plan_id="pl", date=DAY, rationale="", tasks=[make_task("a"), make_task("b")])
    assert c.validate(plan) is False


def test_validate_rejects_task_outside_window():
    c = Constraints(
        constraint_id="c",
        max_daily_tasks=5,
        available_times=[TimeWindow(start=at(6, 0), end=at(12, 0))],
    )
    plan = Plan(plan_id="pl", date=DAY, rationale="", tasks=[make_task("a", due_time=at(20, 0))])
    assert c.validate(plan) is False


def test_validate_accepts_plan_within_all_constraints():
    c = Constraints(
        constraint_id="c",
        max_daily_tasks=5,
        available_times=[TimeWindow(start=at(6, 0), end=at(12, 0))],
    )
    plan = Plan(plan_id="pl", date=DAY, rationale="", tasks=[make_task("a", due_time=at(9, 0))])
    assert c.validate(plan) is True
