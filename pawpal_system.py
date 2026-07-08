"""PawPal — pet care app class skeleton.

Generated from diagrams/uml.mmd. Method bodies are left as stubs (pass)
for you to implement. Objects like Pet and Task use dataclasses to keep
the attribute definitions clean.
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

    def create_profile(self) -> None:
        pass

    def update_profile(self) -> None:
        pass


@dataclass
class Pet:
    pet_id: str
    name: str
    species: str
    breed: str
    age: int
    weight: float
    behaviors: list[str] = field(default_factory=list)

    def create_profile(self) -> None:
        pass

    def update_profile(self) -> None:
        pass

    def has_behavior(self, behavior: str) -> bool:
        pass


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    category: str
    due_time: datetime
    completed: bool = False

    def add_task(self) -> None:
        pass

    def edit_task(self) -> None:
        pass

    def remove_task(self) -> None:
        pass


@dataclass
class TimeWindow:
    """Represents an available time window used by Constraints.availableTimes."""

    start: datetime
    end: datetime


@dataclass
class Plan:
    plan_id: str
    date: date
    rationale: str
    tasks: list[Task] = field(default_factory=list)

    def generate_daily_plan(self) -> "Plan":
        pass

    def explain_reasons(self) -> str:
        pass


@dataclass
class Constraints:
    constraint_id: str
    max_daily_tasks: int
    priorities: list[str] = field(default_factory=list)
    available_times: list[TimeWindow] = field(default_factory=list)
    budget: float = 0.0

    def validate(self, plan: Plan) -> bool:
        pass
