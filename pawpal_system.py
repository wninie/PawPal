"""PawPal — pet care app.

Implements the classes described in diagrams/uml.mmd:

- Task      : a single activity (title, time, duration, completion status).
- Pet       : pet details plus a backlog of tasks, generated plans, and
              scheduling constraints.
- Owner     : manages multiple pets and provides access to all their tasks.
- Plan      : the tasks selected for a single day, with a rationale.
- Constraints / TimeWindow : the scheduling rules a plan must satisfy.

Pet.generate_daily_plan is the "brain": it reads the pet's task backlog and
constraints and organizes a valid daily plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

# How far ahead the next occurrence of a recurring task is scheduled, keyed by
# Task.recurrence. Anything not listed here (e.g. "none") does not repeat.
RECURRENCE_DELTAS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


@dataclass
class Owner:
    owner_id: str
    name: str
    email: str
    phone: str
    # owns "*" Pet — an owner can care for many pets.
    pets: list[Pet] = field(default_factory=list)

    def create_profile(self) -> None:
        """Validate that the owner has the identity fields needed before use."""
        if not self.owner_id:
            raise ValueError("owner_id is required")
        if not self.name:
            raise ValueError("name is required")
        if not self.email or "@" not in self.email:
            raise ValueError("a valid email is required")

    def update_profile(self, **changes) -> None:
        """Update mutable profile fields (name, email, phone)."""
        for field_name in ("name", "email", "phone"):
            if field_name in changes:
                setattr(self, field_name, changes[field_name])

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner, avoiding duplicates by pet_id."""
        if any(p.pet_id == pet.pet_id for p in self.pets):
            return
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        """Remove the pet with the given id, if present."""
        self.pets = [p for p in self.pets if p.pet_id != pet_id]

    def all_tasks(self) -> list[Task]:
        """Provide access to every task across all of this owner's pets."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.tasks)
        return tasks

    def tasks_for_pet(self, pet_name: str) -> list[Task]:
        """Return the tasks belonging to the pet(s) with the given name.

        Matching is case-insensitive. If more than one pet shares the name,
        their tasks are combined.
        """
        target = pet_name.strip().lower()
        tasks: list[Task] = []
        for pet in self.pets:
            if pet.name.strip().lower() == target:
                tasks.extend(pet.tasks)
        return tasks

    def detect_conflicts(self, plan_date: date | None = None) -> list[str]:
        """Warn about tasks scheduled at the same time across all pets.

        The owner is the only object that sees every pet, so cross-pet clashes
        (e.g. two dogs both needing a walk at 08:00) are detected here. Pass
        `plan_date` to limit the check to a single day; otherwise the whole
        backlog is checked. Completed tasks are ignored. Returns warning
        strings (possibly empty) and never raises.
        """
        labeled: list[tuple[str, Task]] = []
        for pet in self.pets:
            for task in pet.tasks:
                if task.completed:
                    continue
                if plan_date is not None and task.due_time.date() != plan_date:
                    continue
                labeled.append((pet.name, task))
        return detect_time_conflicts(labeled)


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    category: str
    due_time: datetime
    # Needed so the planner can fit tasks into TimeWindows and honor
    # Constraints.priorities.
    duration_minutes: int = 0
    priority: int = 0
    completed: bool = False
    # How often this task repeats: "none", "daily", or "weekly". Recurring
    # tasks spawn a fresh copy for the next occurrence when completed.
    recurrence: str = "none"

    def edit(self, **changes) -> None:
        """Update editable fields of the task."""
        editable = {
            "title",
            "description",
            "category",
            "due_time",
            "duration_minutes",
            "priority",
            "recurrence",
        }
        for field_name, value in changes.items():
            if field_name in editable:
                setattr(self, field_name, value)

    def is_recurring(self) -> bool:
        """True if this task repeats (daily/weekly) rather than one-off."""
        return self.recurrence in RECURRENCE_DELTAS

    def next_occurrence(self, as_of: date | None = None) -> Task | None:
        """Build the next occurrence of a recurring task.

        Returns a fresh, uncompleted copy, or None if the task does not repeat.
        The new due date is computed from the completion date (`as_of`, which
        defaults to today) plus one recurrence interval, keeping the original
        time of day. Using `as_of` rather than the old due_time means a daily
        task completed today is always scheduled for today + 1 day, even if it
        was overdue. `timedelta` handles month/year rollovers automatically.
        The new task_id is suffixed with the next due date to stay unique.
        """
        delta = RECURRENCE_DELTAS.get(self.recurrence)
        if delta is None:
            return None
        base_date = as_of or date.today()
        # Anchor to the completion date at the task's original time of day,
        # then advance by one interval (e.g. today + timedelta(days=1)).
        next_due = datetime.combine(base_date, self.due_time.time()) + delta
        return Task(
            task_id=f"{self.task_id}-{next_due.date().isoformat()}",
            title=self.title,
            description=self.description,
            category=self.category,
            due_time=next_due,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            completed=False,
            recurrence=self.recurrence,
        )

    def mark_completed(self, as_of: date | None = None) -> Task | None:
        """Mark this task as done.

        If the task is recurring, returns the next occurrence to be scheduled
        (see next_occurrence); otherwise returns None. `as_of` is the
        completion date the next due date is measured from (defaults to today).
        Callers that own a backlog (e.g. Pet.complete_task) add the returned
        task so the next occurrence appears automatically.
        """
        self.completed = True
        return self.next_occurrence(as_of)

    def end_time(self) -> datetime:
        """When this task finishes: due_time plus its duration."""
        return self.due_time + timedelta(minutes=self.duration_minutes)

    def conflicts_with(self, other: Task) -> bool:
        """True if this task's time window overlaps `other`'s.

        Windows are half-open, [due_time, end_time), so back-to-back tasks
        (one ending exactly when the next begins) do NOT conflict. Two tasks
        that start at the same instant always conflict, even zero-duration
        ones, which is the "scheduled at the same time" case.
        """
        if self.due_time == other.due_time:
            return True
        return self.due_time < other.end_time() and other.due_time < self.end_time()

    @staticmethod
    def sort_by_time(tasks: list[Task]) -> list[Task]:
        """Return `tasks` in chronological order by due_time.

        A reusable helper so the owner or UI can display any task list
        (a backlog, an owner's combined tasks, a plan) in schedule order
        without going through the planner. `task_id` is a final tiebreaker
        so tasks sharing a due_time come out in a stable, reproducible order.
        """
        return sorted(tasks, key=lambda t: (t.due_time, t.task_id))


def _conflict_message(
    task_a: Task, task_b: Task, label_a: str = "", label_b: str = ""
) -> str:
    """Format one overlap into a human-readable warning line."""
    who_a = f"{label_a}'s " if label_a else ""
    who_b = f"{label_b}'s " if label_b else ""
    return (
        f"WARNING - time conflict: {who_a}'{task_a.title}' "
        f"({task_a.due_time.strftime('%H:%M')}-{task_a.end_time().strftime('%H:%M')}) "
        f"overlaps {who_b}'{task_b.title}' "
        f"({task_b.due_time.strftime('%H:%M')}-{task_b.end_time().strftime('%H:%M')})."
    )


def detect_time_conflicts(labeled_tasks: list[tuple[str, Task]]) -> list[str]:
    """Find every pair of overlapping tasks and describe them as warnings.

    `labeled_tasks` is a list of (label, task) pairs; the label names whose
    task it is (a pet's name) so warnings read clearly when tasks come from
    different pets. Returns a list of warning strings — possibly empty — and
    never raises, so callers can surface conflicts without stopping the app.

    Lightweight by design: sort by start time, then a pairwise scan. For a
    day's backlog this is trivially fast; the sort just makes the reported
    pairs deterministic (earliest-starting task first).
    """
    ordered = sorted(labeled_tasks, key=lambda lt: (lt[1].due_time, lt[1].task_id))
    warnings: list[str] = []
    for i in range(len(ordered)):
        label_a, task_a = ordered[i]
        for j in range(i + 1, len(ordered)):
            label_b, task_b = ordered[j]
            # Sorted by start time: once a later task begins at or after this
            # one ends (and isn't a same-start tie), nothing after it can
            # overlap task_a either, so stop scanning this row.
            if task_b.due_time >= task_a.end_time() and task_b.due_time != task_a.due_time:
                break
            if task_a.conflicts_with(task_b):
                warnings.append(_conflict_message(task_a, task_b, label_a, label_b))
    return warnings


@dataclass
class TimeWindow:
    """Represents an available time window used by Constraints.availableTimes."""

    start: datetime
    end: datetime

    def duration_minutes(self) -> int:
        """Length of the window in whole minutes."""
        return max(0, int((self.end - self.start).total_seconds() // 60))

    def contains(self, moment: datetime) -> bool:
        """True if `moment` falls within [start, end]."""
        return self.start <= moment <= self.end


@dataclass
class Constraints:
    constraint_id: str
    max_daily_tasks: int
    priorities: list[str] = field(default_factory=list)
    available_times: list[TimeWindow] = field(default_factory=list)
    budget: float = 0.0

    def validate(self, plan: Plan) -> bool:
        """Return True if `plan` fits the daily cap, time windows, and capacity."""
        if len(plan.tasks) > self.max_daily_tasks:
            return False

        # Every task must be due within one of the available windows.
        if self.available_times:
            for task in plan.tasks:
                if not any(w.contains(task.due_time) for w in self.available_times):
                    return False

            total_needed = sum(t.duration_minutes for t in plan.tasks)
            total_available = sum(w.duration_minutes() for w in self.available_times)
            if total_needed > total_available:
                return False

        return True


@dataclass
class Plan:
    plan_id: str
    date: date
    rationale: str
    # includes "*" Task — the tasks scheduled for this day, in chronological
    # (due_time) order so this reads as a schedule the owner can follow.
    tasks: list[Task] = field(default_factory=list)
    # The order the planner *selected* tasks in (by priority), kept so the
    # rationale can explain which work won out, even though `tasks` above is
    # displayed chronologically.
    selection_order: list[Task] = field(default_factory=list)
    # Non-fatal warnings about the plan (e.g. two tasks scheduled at the same
    # time). Populated by the planner; surfaced, never raised.
    warnings: list[str] = field(default_factory=list)

    def explain_reasons(self) -> str:
        """Human-readable explanation of why these tasks were scheduled.

        Tasks are listed chronologically (by due_time) so the plan reads as a
        daily schedule; the rationale still records the priority-based
        selection that produced it. Any scheduling warnings are appended last.
        """
        lines = [f"Plan for {self.date.isoformat()}:"]
        if self.rationale:
            lines.append(self.rationale)
        if not self.tasks:
            lines.append("No tasks were scheduled.")
        else:
            for task in self.tasks:
                lines.append(
                    f"- {task.title} at {task.due_time.strftime('%H:%M')} "
                    f"({task.duration_minutes} min, priority {task.priority}, "
                    f"category {task.category})"
                )
        for warning in self.warnings:
            lines.append(warning)
        return "\n".join(lines)


@dataclass
class Pet:
    pet_id: str
    name: str
    species: str
    breed: str
    age: int
    weight: float
    behaviors: list[str] = field(default_factory=list)
    # Source pool of tasks (backlog) the planner selects from.
    tasks: list[Task] = field(default_factory=list)
    # hasPlan "*" — generated daily plans, most-recent last.
    plans: list[Plan] = field(default_factory=list)
    # constrainedBy "1" — scheduling rules for this pet.
    constraints: Constraints | None = None

    def create_profile(self) -> None:
        """Validate that the pet has the identity fields needed before use."""
        if not self.pet_id:
            raise ValueError("pet_id is required")
        if not self.name:
            raise ValueError("name is required")
        if not self.species:
            raise ValueError("species is required")

    def update_profile(self, **changes) -> None:
        """Update mutable profile fields."""
        editable = {"name", "species", "breed", "age", "weight", "behaviors"}
        for field_name, value in changes.items():
            if field_name in editable:
                setattr(self, field_name, value)

    def has_behavior(self, behavior: str) -> bool:
        """Case-insensitive check for a recorded behavior."""
        target = behavior.strip().lower()
        return any(b.strip().lower() == target for b in self.behaviors)

    def add_task(self, task: Task) -> None:
        """Add a task to the backlog, avoiding duplicates by task_id."""
        if any(t.task_id == task.task_id for t in self.tasks):
            return
        self.tasks.append(task)

    def edit_task(self, task_id: str, **changes) -> None:
        """Edit a backlog task in place by id."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.edit(**changes)
                return
        raise KeyError(f"no task with id {task_id!r}")

    def remove_task(self, task_id: str) -> None:
        """Remove the task with the given id from the backlog, if present."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def complete_task(self, task_id: str, as_of: date | None = None) -> Task | None:
        """Mark a backlog task complete and auto-schedule its next occurrence.

        For a recurring ("daily"/"weekly") task this creates a fresh instance
        for the next occurrence and adds it to the backlog, returning the new
        task. For a one-off task it just marks completion and returns None.
        `as_of` is the completion date the next due date is measured from
        (defaults to today); the daily case yields today + 1 day.
        """
        for task in self.tasks:
            if task.task_id == task_id:
                next_task = task.mark_completed(as_of)
                if next_task is not None:
                    self.add_task(next_task)
                return next_task
        raise KeyError(f"no task with id {task_id!r}")

    def generate_daily_plan(self, plan_date: date) -> Plan:
        """Build a Plan for `plan_date` by selecting backlog tasks under `self.constraints`.

        The planner runs in four stages, in this order:

        1. **Filter** the backlog down to eligible candidates: not yet
           completed, due on `plan_date`, and (if constraints define time
           windows) falling inside one of those windows.
        2. **Sort** the eligible candidates by importance so the best work is
           first (see `sort_key` below).
        3. **Cap** the sorted list to `constraints.max_daily_tasks`.
        4. **Detect conflicts** among the selected tasks and record them as
           non-fatal warnings.

        Window filtering happens in stage 1, *before* the cap in stage 3, so an
        out-of-window task can never take up one of the limited daily slots and
        leave a valid task behind. The result is displayed chronologically but
        remembers its priority-selection order for the rationale.
        """
        # Constraint priorities (e.g. ["exercise", "feeding"]) rank tasks by
        # category. Pre-build a category -> rank lookup once so sort_key does an
        # O(1) dict lookup per task instead of an O(n) list.index() scan.
        priority_order: list[str] = (
            self.constraints.priorities if self.constraints else []
        )
        category_rank = {category: i for i, category in enumerate(priority_order)}

        # Stage 1 — Filter: keep uncompleted tasks due today that also fall
        # inside an available time window (if any windows are defined).
        windows = self.constraints.available_times if self.constraints else []

        def is_eligible(task: Task) -> bool:
            """True if `task` may be scheduled on `plan_date`.

            Stage-1 filter: the task must be uncompleted, due on the plan
            date, and — when constraints define windows — start inside one of
            them.
            """
            if task.completed or task.due_time.date() != plan_date:
                return False
            if windows and not any(w.contains(task.due_time) for w in windows):
                return False
            return True

        candidates = [t for t in self.tasks if is_eligible(t)]

        # Stage 2 — Sort by importance: constraint category priority first, then
        # the task's own priority (higher first), then earliest due time.
        def sort_key(task: Task):
            """Rank a task for stage-2 ordering (lower sorts first).

            Orders by constraint category priority, then the task's own
            priority (higher first), then earliest due time, then task_id.
            """
            # Unranked categories sort last (rank == len(priority_order)).
            # task_id is a final tiebreaker so tasks sharing category,
            # priority, and due_time still order deterministically.
            rank = category_rank.get(task.category, len(priority_order))
            return (rank, -task.priority, task.due_time, task.task_id)

        candidates.sort(key=sort_key)

        # Stage 3 — Cap to the daily maximum (candidates are already in
        # importance order, so this keeps the highest-value tasks).
        max_daily = self.constraints.max_daily_tasks if self.constraints else None
        selected = candidates[:max_daily] if max_daily is not None else candidates

        rationale = self._build_rationale(selected, len(candidates), priority_order)

        # Stage 4 — Detect conflicts: flag any tasks in this pet's own plan that
        # overlap in time. This is a warning, not an error: the tasks stay
        # scheduled so the owner decides.
        warnings = detect_time_conflicts([(self.name, t) for t in selected])

        # `selected` is in priority order (how the planner chose). Keep that for
        # the rationale, but display the plan chronologically so it reads as a
        # daily schedule.
        plan = Plan(
            plan_id=f"{self.pet_id}-{plan_date.isoformat()}",
            date=plan_date,
            rationale=rationale,
            tasks=Task.sort_by_time(selected),
            selection_order=selected,
            warnings=warnings,
        )

        self.plans.append(plan)
        return plan

    def _build_rationale(
        self,
        selected: list[Task],
        candidate_count: int,
        priority_order: list[str],
    ) -> str:
        """Describe how the plan was assembled, for explain_reasons()."""
        parts = [
            f"Selected {len(selected)} of {candidate_count} due task(s) "
            f"for {self.name}."
        ]
        if priority_order:
            parts.append("Ordered by priority: " + ", ".join(priority_order) + ".")
        if self.constraints:
            parts.append(
                f"Respecting a daily cap of {self.constraints.max_daily_tasks} "
                "task(s)."
            )
        return " ".join(parts)
