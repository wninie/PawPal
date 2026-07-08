"""Tests for the PawPal system."""

from datetime import datetime

from pawpal_system import Pet, Task


def make_task(task_id="t1"):
    return Task(
        task_id=task_id,
        title="Morning walk",
        description="Walk around the block",
        category="exercise",
        due_time=datetime(2026, 7, 7, 9, 0),
        duration_minutes=30,
    )


def test_mark_completed_changes_status():
    """Calling mark_completed() changes the task's status to done."""
    task = make_task()
    assert task.completed is False

    task.mark_completed()

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a pet increases the pet's task count."""
    pet = Pet(
        pet_id="p1",
        name="Rex",
        species="dog",
        breed="Labrador",
        age=3,
        weight=25.0,
    )
    assert len(pet.tasks) == 0

    pet.add_task(make_task())

    assert len(pet.tasks) == 1
