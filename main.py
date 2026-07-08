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

    task1 = Task(
        task_id="01",
        title="wake up",
        description= "wake the dog up",
        category="daily task",
        due_time=datetime(today.year, today.month, today.day, 8, 0),
        duration_minutes=30,
        priority=1,
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

    pet1.add_task(task1)
    pet1.add_task(task3)
    pet2.add_task(task2)

    pet1_plan = pet1.generate_daily_plan(today)
    pet2_plan = pet2.generate_daily_plan(today)



    print("=== Today's Schedule ===")
    for pet, plan in [(pet1, pet1_plan), (pet2, pet2_plan)]:
        print(f"\n{pet.name} ({pet.species}):")
        print(plan.explain_reasons())
 
if __name__ == "__main__":
    main()