"""
main.py — PawPal+ Demo
======================
Creates a sample Owner → Pet → Task hierarchy and prints Today's Schedule.

New fields used here
--------------------
  preferred_time   : "morning" | "afternoon" | "evening" — natural day ordering  [#11]
  next_due_date    : date the task is next due; tasks before that date are skipped [#2]

Out-of-order stress-test section
---------------------------------
  New tasks are added via add_task() in intentionally scrambled time order
  (evening → afternoon → morning) to verify the scheduler re-sorts them into a
  natural daily flow.  The section also exercises:
    - #2  next_due_date filtering   (puzzle_feeder skipped; dental chew due today)
    - #6  whole-word fear matching  (vacuum task skipped for Mochi)
    - #9  deduplication             (re-adding morning_feeding is silently ignored)
"""

from datetime import date

from pawpal_system import Task, Pet, Owner, Scheduler


# ── Tasks for Mochi (Dog) ────────────────────────────────────────────────────

morning_feeding = Task(
    name="Morning Feeding",
    description="Bowl of kibble with a splash of warm water.",
    duration_minutes=10,
    priority=1,
    energy_level="Low",
    task_type="survival",
    frequency="daily",
    tags=["food", "meal"],
    preferred_time="morning",
)

park_walk = Task(
    name="Park Walk",
    description="30-minute off-leash romp at the neighbourhood park.",
    duration_minutes=30,
    priority=2,
    energy_level="High",
    task_type="care",
    frequency="daily",
    tags=["outdoor", "walk", "fetch"],
    preferred_time="morning",
)

cuddle_time = Task(
    name="Cuddle Time",
    description="Quiet sofa snuggles and belly rubs.",
    duration_minutes=15,
    priority=4,
    energy_level="Low",
    task_type="hobby",
    frequency="daily",
    tags=["cuddles", "calm", "indoor"],
    preferred_time="evening",
)

mochi = Pet(
    name="Mochi",
    species="Dog",
    favorites=["fetch", "cuddles"],
    fears=["vacuum"],
    tasks=[morning_feeding, park_walk, cuddle_time],
)


# ── Tasks for Luna (Cat) ─────────────────────────────────────────────────────

medication = Task(
    name="Medication",
    description="Half a pill wrapped in a soft treat.",
    duration_minutes=5,
    priority=1,
    energy_level="Low",
    task_type="survival",
    frequency="daily",
    tags=["medicine", "health"],
    preferred_time="morning",
)

laser_play = Task(
    name="Laser Play",
    description="10 minutes of laser-pointer chase around the living room.",
    duration_minutes=10,
    priority=3,
    energy_level="Medium",
    task_type="hobby",
    frequency="daily",
    tags=["laser", "play", "indoor"],
    preferred_time="evening",
)

grooming = Task(
    name="Brushing Session",
    description="Weekly brush-out to keep Luna's coat silky.",
    duration_minutes=20,
    priority=3,
    energy_level="Low",
    task_type="care",
    frequency="weekly",
    tags=["grooming", "brush", "calm"],
    preferred_time="afternoon",
    next_due_date=date(2026, 4, 6),    # not due until next Monday — skipped today
)

luna = Pet(
    name="Luna",
    species="Cat",
    favorites=["laser", "calm"],
    fears=["loud noises"],
    tasks=[medication, laser_play, grooming],
)


# ── Out-of-order task additions (stress-test) ─────────────────────────────────
# Each pet's new tasks are registered in REVERSE time order (evening → afternoon
# → morning) to prove the scheduler re-sorts them into a natural daily flow.

# ·· Mochi — added evening-first, then afternoon, then morning ·················

mochi.add_task(Task(                       # 1st added — evening slot
    name="Evening Treat",
    description="Bedtime reward biscuit.",
    duration_minutes=5,
    priority=4,
    energy_level="Low",
    task_type="hobby",
    frequency="daily",
    tags=["treat", "calm"],
    preferred_time="evening",              # should sort to end
))

mochi.add_task(Task(                       # 2nd added — afternoon slot
    name="Afternoon Training",
    description="10-minute sit/stay/fetch drills in the garden.",
    duration_minutes=10,
    priority=2,
    energy_level="Medium",
    task_type="care",
    frequency="daily",
    tags=["training", "fetch", "outdoor"],
    preferred_time="afternoon",            # should sort to middle
))

mochi.add_task(Task(                       # 3rd added — morning slot
    name="Dental Chew",
    description="Enzymatic chew for oral health.",
    duration_minutes=5,
    priority=3,
    energy_level="Low",
    task_type="care",
    frequency="weekly",
    tags=["dental", "health"],
    preferred_time="morning",              # should sort to front
    next_due_date=date.today(),            # due today — must be included  [#2]
))

mochi.add_task(Task(                       # fear-conflict test  [#6]
    name="Vacuum Desensitisation",
    description="Gradual exposure to the vacuum cleaner.",
    duration_minutes=15,
    priority=3,
    energy_level="Medium",
    task_type="care",
    frequency="as-needed",
    tags=["vacuum", "indoor"],             # "vacuum" matches Mochi's fear — skip
    preferred_time="afternoon",
))

mochi.add_task(morning_feeding)            # duplicate object test — #9 blocks this

# ·· Luna — added evening-first, then afternoon, then morning ··················

luna.add_task(Task(                        # 1st added — evening slot
    name="Evening Window Perch",
    description="Bird-watching from the window seat at dusk.",
    duration_minutes=10,
    priority=4,
    energy_level="Low",
    task_type="hobby",
    frequency="daily",
    tags=["calm", "indoor", "window"],
    preferred_time="evening",              # should sort to end
))

luna.add_task(Task(                        # 2nd added — afternoon slot
    name="Puzzle Feeder",
    description="Puzzle feeder to keep Luna's mind sharp.",
    duration_minutes=15,
    priority=3,
    energy_level="Low",
    task_type="care",
    frequency="as-needed",
    tags=["puzzle", "food", "indoor"],
    preferred_time="afternoon",
    next_due_date=date(2026, 4, 20),       # not due for 3 weeks — skipped  [#2]
))

luna.add_task(Task(                        # 3rd added — morning slot
    name="Morning Wet Food",
    description="Spoonful of pâté to start the day.",
    duration_minutes=5,
    priority=1,
    energy_level="Low",
    task_type="survival",
    frequency="daily",
    tags=["food", "meal"],
    preferred_time="morning",              # should sort to front with other survival
))


# ── Owner ────────────────────────────────────────────────────────────────────

jordan = Owner(
    name="Jordan",
    available_time_minutes=120,            # bumped to fit the expanded task list
    energy_battery="Medium",
    pets=[mochi, luna],
)


# ── Build schedule ───────────────────────────────────────────────────────────

scheduler = Scheduler(owner=jordan)
scheduled, skipped, note = scheduler.build_schedule()


# ── Print Today's Schedule ───────────────────────────────────────────────────

print("=" * 60)
print("         PAWPAL+  —  Today's Schedule")
print("=" * 60)
print(f"  Owner : {jordan.name}")
print(f"  Energy: {jordan.energy_battery}   |   Available: {jordan.available_time_minutes} min")
print("=" * 60)

print("\n🐾  TAIL-WAGGING TIMELINE\n")
for i, item in enumerate(scheduled, start=1):
    lock_badge = " [LOCKED]" if item.locked else ""
    time_badge = f" — {item.task.preferred_time}" if item.task.preferred_time else ""
    print(f"  {i}. {item.task.name}{lock_badge}{time_badge}  ({item.task.duration_minutes} min | {item.task.frequency})")
    print(f"     Pet     : {item.pet.name}")
    print(f"     Reason  : {item.reason}")
    print()

total_time = sum(s.task.duration_minutes for s in scheduled)
free_time  = jordan.available_time_minutes - total_time
print(f"  Total scheduled time : {total_time} / {jordan.available_time_minutes} min")
print(f"  Free time remaining  : {free_time} min")

if skipped:
    print("\n⏭  SKIPPED TASKS\n")
    for item in skipped:
        print(f"  • {item.task.name} ({item.pet.name})  —  {item.reason}")

if scheduler.warnings:
    print("\n💬  NOTES\n")
    for w in scheduler.warnings:
        print(f"  {w}")

print("\n" + "-" * 60)
print(f"  {note}")
print("-" * 60 + "\n")


# ── Auto-reschedule demo ──────────────────────────────────────────────────────
# Mark one daily task, one weekly task, and one as-needed task complete, then
# show that the correct next-occurrence instances were (or were not) created.

print("=" * 60)
print("  AUTO-RESCHEDULE DEMO")
print("=" * 60)

CASES = [
    (mochi, "Park Walk"),           # daily  → next occurrence tomorrow
    (luna,  "Brushing Session"),    # weekly → next occurrence in 7 days
    (mochi, "Vacuum Desensitisation"),  # as-needed → no new instance
]

for pet, task_name in CASES:
    # Find the task so we can show its current next_due_date before completing it
    original = next(t for t in pet.tasks if t.name == task_name)
    base_label = str(original.next_due_date) if original.next_due_date else "today"

    next_task = pet.complete_task(task_name)

    print(f"\n  ✔  {pet.name} — '{task_name}'  [{original.frequency}]")
    print(f"     Completed instance  : next_due_date was {base_label}")
    if next_task:
        print(f"     Next occurrence     : next_due_date = {next_task.next_due_date}")
        print(f"     Now in task list    : {next_task.name!r}  (completed={next_task.completed})")
    else:
        print(f"     as-needed — no next occurrence created")

# Confirm totals
print()
print(f"  Mochi total tasks : {len(mochi.tasks)}")
print(f"  Luna  total tasks : {len(luna.tasks)}")
print()
print("  Task list after completions:")
for pet in [mochi, luna]:
    print(f"\n  {pet.name}:")
    for t in pet.tasks:
        status = "✔ done" if t.completed else f"due {t.next_due_date or 'today'}"
        print(f"    • {t.name:<30} [{t.frequency:<9}]  {status}")
print()
