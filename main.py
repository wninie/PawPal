from pawpal_system import Owner, Pet, Task, Plan, Constraints, TimeWindow
from datetime import datetime, date

def main():
    today = date.today()

    owner = Owner(
        owner_id="01",
        name="Nini",
        email="lnini1080@gmail.com",
        phone="123-123-1223",
    )

    pet1_constraints = Constraints(
        constraint_id="c1",
        max_daily_tasks=5,
        priorities=["exercise", "feeding", "health"],
        available_times=[
            TimeWindow(
                start=datetime(today.year, today.month, today.day, 6, 0),
                end=datetime(today.year, today.month, today.day, 21, 0),
            )
        ],
        budget=50.0,
    )

    pet2_constraints = Constraints(
        constraint_id="c2",
        max_daily_tasks=2,
        priorities=["eat", "sleep", "water"],
        available_times=[
            TimeWindow(
                start=datetime(today.year, today.month, today.day, 6, 0),
                end=datetime(today.year, today.month, today.day, 23, 0)
            )
        ] ,
        budget=90
    )

    pet1 = Pet(
        pet_id="01",
        name="pet1",
        species="dog",
        breed="dog breed",
        age=1,
        weight= 10920912.2,
        behaviors=["sleepy", "mooody"],
        constraints= pet1_constraints,
    )

    pet2 = Pet(
        pet_id = "02",
        name="pet2",
        species="cat",
        breed="british cat",
        age= 9218,
        weight= 0.123,
        behaviors=["sassy"],
        constraints= pet2_constraints,
    )

    owner.add_pet(pet1)
    owner.add_pet(pet2)

    # Tasks are added out of chronological order on purpose so the sorting
    # method below has something to actually reorder.
    task1 = Task(
        task_id="01",
        title="wake up",
        description= "wake the dog up",
        category="daily task",
        due_time=datetime(today.year, today.month, today.day, 8, 0),
        duration_minutes=30,
        priority=1,
        recurrence="daily",
    )

    task2 = Task(
        task_id="t2",
        title="Feed Cat",
        description="Give cat breakfast",
        category="feeding",
        due_time=datetime(today.year, today.month, today.day, 9, 0),
        duration_minutes=10,
        priority=3,
    )

    task3 = Task(
        task_id="t3",
        title="Evening Walk",
        description="Walk dog before dinner",
        category="exercise",
        due_time=datetime(today.year, today.month, today.day, 18, 0),
        duration_minutes=30,
        priority=2,
    )

    task4 = Task(
        task_id="t4",
        title="Midday Nap",
        description="Let the cat nap in the sun",
        category="sleep",
        due_time=datetime(today.year, today.month, today.day, 13, 0),
        duration_minutes=60,
        priority=1,
    )

    # Deliberately clashes with pet1's 08:00 "wake up" to show cross-pet
    # conflict detection (both pets need attention at the same moment).
    task5 = Task(
        task_id="t5",
        title="Morning Meds",
        description="Give the cat morning medication",
        category="health",
        due_time=datetime(today.year, today.month, today.day, 8, 0),
        duration_minutes=15,
        priority=3,
    )

    # A SECOND pet1 task scheduled at the exact same time as "wake up" (08:00).
    # Both land in pet1's plan, so the schedule should flag a same-pet clash.
    task6 = Task(
        task_id="t6",
        title="Give Medicine",
        description="Morning pill with breakfast",
        category="health",
        due_time=datetime(today.year, today.month, today.day, 8, 0),
        duration_minutes=10,
        priority=3,
    )

    # Add tasks out of order (evening walk before the morning wake-up, etc.).
    pet1.add_task(task3)  # 18:00
    pet1.add_task(task1)  # 08:00
    pet1.add_task(task6)  # 08:00 — overlaps pet1's own wake up (same-pet clash)
    pet2.add_task(task4)  # 13:00
    pet2.add_task(task2)  # 09:00
    pet2.add_task(task5)  # 08:00 — overlaps pet1's wake up (cross-pet clash)

    pet1_plan = pet1.generate_daily_plan(today)
    pet2_plan = pet2.generate_daily_plan(today)

    print("=== Today's Schedule ===")
    for pet, plan in [(pet1, pet1_plan), (pet2, pet2_plan)]:
        print(f"\n{pet.name} ({pet.species}):")
        print(plan.explain_reasons())

    # --- Filtering: pull tasks for a specific pet by name (Owner.tasks_for_pet) ---
    print("\n=== Filtered: tasks for 'pet1' ===")
    for task in Task.sort_by_time(owner.tasks_for_pet("pet1")):
        print(f"- {task.title} at {task.due_time.strftime('%H:%M')}")

    # --- Sorting: every task across all pets, back in chronological order ---
    print("\n=== All tasks (added out of order, now sorted by time) ===")
    for task in Task.sort_by_time(owner.all_tasks()):
        print(
            f"- {task.due_time.strftime('%H:%M')}  {task.title} "
            f"({task.category})"
        )

    # --- Conflict detection: overlapping tasks across all pets today ---
    print("\n=== Schedule conflicts (all pets, today) ===")
    conflicts = owner.detect_conflicts(today)
    if conflicts:
        for warning in conflicts:
            print(warning)
    else:
        print("No time conflicts detected.")

    # --- Recurrence: completing a daily task auto-schedules the next one ---
    print("\n=== Completing the daily 'wake up' task ===")
    next_task = pet1.complete_task("01")
    print(f"Marked 'wake up' complete on {today.isoformat()}.")
    if next_task is not None:
        print(
            f"Next occurrence auto-created: {next_task.title} "
            f"due {next_task.due_time.strftime('%Y-%m-%d %H:%M')} "
            f"(id {next_task.task_id})."
        )

if __name__ == "__main__":
    main()