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
from datetime import date, datetime


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

    def edit(self, **changes) -> None:
        """Update editable fields of the task."""
        editable = {
            "title",
            "description",
            "category",
            "due_time",
            "duration_minutes",
            "priority",
        }
        for field_name, value in changes.items():
            if field_name in editable:
                setattr(self, field_name, value)

    def mark_completed(self) -> None:
        """Mark this task as done."""
        self.completed = True


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
    # includes "*" Task — the tasks scheduled for this day.
    tasks: list[Task] = field(default_factory=list)

    def explain_reasons(self) -> str:
        """Human-readable explanation of why these tasks were scheduled."""
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

    def generate_daily_plan(self, plan_date: date) -> Plan:
        """Build a Plan for `plan_date` by selecting backlog tasks under `self.constraints`."""
        # Candidate tasks: not yet completed and due on the target day.
        candidates = [
            t
            for t in self.tasks
            if not t.completed and t.due_time.date() == plan_date
        ]

        # Order by the highest-value work first: constraint priorities take
        # precedence, then the task's own priority, then earliest due time.
        priority_order: list[str] = (
            self.constraints.priorities if self.constraints else []
        )

        def sort_key(task: Task):
            try:
                category_rank = priority_order.index(task.category)
            except ValueError:
                category_rank = len(priority_order)
            return (category_rank, -task.priority, task.due_time)

        candidates.sort(key=sort_key)

        # Apply the daily cap.
        selected = candidates
        max_daily = self.constraints.max_daily_tasks if self.constraints else None
        if max_daily is not None:
            selected = candidates[:max_daily]

        # Drop tasks that fall outside the available time windows.
        if self.constraints and self.constraints.available_times:
            windows = self.constraints.available_times
            selected = [
                t for t in selected if any(w.contains(t.due_time) for w in windows)
            ]

        rationale = self._build_rationale(selected, len(candidates), priority_order)

        plan = Plan(
            plan_id=f"{self.pet_id}-{plan_date.isoformat()}",
            date=plan_date,
            rationale=rationale,
            tasks=selected,
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
