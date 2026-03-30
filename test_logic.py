"""
test_logic.py — PawPal+ Scheduler Tests
========================================
Each test "pretends" to be a user setting up a scenario and checks that the
Scheduler responds correctly.  Run with:

    pytest test_logic.py -v
"""

import pytest
from pawpal_system import Task, Pet, Owner, Scheduler


# ─── Helpers ────────────────────────────────────────────────────────────────────

def make_task(
    name="Generic Task",
    description="A care activity",
    duration=15,
    priority=3,
    energy="Medium",
    task_type="hobby",
    frequency="daily",
    tags=None,
):
    """Quick-build a Task with sensible defaults."""
    return Task(
        name=name,
        description=description,
        duration_minutes=duration,
        priority=priority,
        energy_level=energy,
        task_type=task_type,
        frequency=frequency,
        tags=tags or [],
    )


def make_scheduler(tasks, favorites=None, fears=None, available=120, energy="Medium",
                   pet_name="Mochi", owner_name="Jordan"):
    """
    Build the full Owner → Pet → Scheduler hierarchy from a flat task list.
    This mirrors exactly how the app constructs objects before calling build_schedule.
    """
    pet   = Pet(name=pet_name, species="Dog",
                favorites=favorites or [], fears=fears or [],
                tasks=tasks)
    owner = Owner(name=owner_name, available_time_minutes=available,
                  energy_battery=energy, pets=[pet])
    return Scheduler(owner=owner)


def scheduled_names(scheduled):
    return [s.task.name for s in scheduled]


def skipped_names(skipped):
    return [s.task.name for s in skipped]


# ─── Fear Tests ─────────────────────────────────────────────────────────────────

class TestFearBasedSkipping:

    def test_task_matching_pet_fear_is_skipped(self):
        """
        Scenario: Mochi is afraid of rain.
        The owner adds an 'Outdoor Rainy Walk' tagged with 'rain'.
        The scheduler should skip it entirely.
        """
        scheduler = make_scheduler(
            tasks=[make_task(name="Outdoor Rainy Walk", tags=["outdoor", "rain", "walk"])],
            fears=["rain"],
        )
        scheduled, skipped, _ = scheduler.build_schedule()

        assert "Outdoor Rainy Walk" not in scheduled_names(scheduled)
        assert "Outdoor Rainy Walk" in skipped_names(skipped)

    def test_fear_skip_reason_mentions_fear(self):
        """The skip reason should tell the owner exactly why it was skipped."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Fireworks Show", tags=["loud noises", "outdoor"])],
            fears=["loud noises"],
        )
        _, skipped, _ = scheduler.build_schedule()

        assert len(skipped) == 1
        assert "loud noises" in skipped[0].reason.lower()

    def test_non_feared_task_is_not_skipped(self):
        """A task with no fear overlap should make it onto the schedule."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Indoor Play", tags=["indoor", "play"])],
            fears=["rain"],
        )
        scheduled, skipped, _ = scheduler.build_schedule()

        assert "Indoor Play" in scheduled_names(scheduled)
        assert "Indoor Play" not in skipped_names(skipped)

    def test_partial_tag_match_triggers_fear_skip(self):
        """Fear matching should work even when the fear word is a substring of a tag."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Thunder Walk", tags=["thunderstorm", "outdoor"])],
            fears=["thunder"],
        )
        _, skipped, _ = scheduler.build_schedule()

        assert "Thunder Walk" in skipped_names(skipped)

    def test_fear_skips_task_even_with_plenty_of_time(self):
        """Even with 8 hours available, a feared task must be skipped."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Vacuum Cleaning", tags=["vacuum", "indoor", "chore"])],
            fears=["vacuum"],
            available=480,
        )
        scheduled, skipped, _ = scheduler.build_schedule()

        assert "Vacuum Cleaning" not in scheduled_names(scheduled)


# ─── Time Constraint Tests ───────────────────────────────────────────────────────

class TestTimeConstraints:

    def test_task_skipped_when_too_long_for_available_time(self):
        """
        Scenario: owner only has 10 minutes but the task needs 30.
        The scheduler must skip the task.
        """
        scheduler = make_scheduler(
            tasks=[make_task(name="Long Walk", duration=30)],
            available=10,
        )
        scheduled, skipped, _ = scheduler.build_schedule()

        assert "Long Walk" not in scheduled_names(scheduled)
        assert "Long Walk" in skipped_names(skipped)

    def test_skip_reason_mentions_time(self):
        """The skip reason should include how much time was needed vs available."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Long Walk", duration=30)],
            available=10,
        )
        _, skipped, _ = scheduler.build_schedule()

        assert "30" in skipped[0].reason
        assert "10" in skipped[0].reason

    def test_task_fits_exactly_in_available_time(self):
        """A task whose duration exactly equals available time should be scheduled."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Fetch", duration=20)],
            available=20,
        )
        scheduled, _, _ = scheduler.build_schedule()

        assert "Fetch" in scheduled_names(scheduled)

    def test_multiple_tasks_fill_time_greedily(self):
        """
        Three 20-min tasks, 40 min available.
        Exactly two should fit; the third is skipped.
        """
        scheduler = make_scheduler(
            tasks=[
                make_task(name="Task A", duration=20, priority=2),
                make_task(name="Task B", duration=20, priority=3),
                make_task(name="Task C", duration=20, priority=4),
            ],
            available=40,
        )
        scheduled, skipped, _ = scheduler.build_schedule()

        assert len(scheduled) == 2
        assert len(skipped)   == 1

    def test_total_scheduled_time_never_exceeds_available(self):
        """Sum of scheduled durations must never exceed the owner's available time."""
        scheduler = make_scheduler(
            tasks=[make_task(name=f"Task {i}", duration=15, priority=i % 5 + 1)
                   for i in range(10)],
            available=60,
        )
        scheduled, _, _ = scheduler.build_schedule()
        total = sum(s.task.duration_minutes for s in scheduled)

        assert total <= 60


# ─── Survival Task Tests ─────────────────────────────────────────────────────────

class TestSurvivalTasks:

    def test_survival_tasks_always_scheduled(self):
        """Priority-1 tasks must appear in the schedule no matter what."""
        scheduler = make_scheduler(
            tasks=[
                make_task(name="Morning Feeding", duration=10, priority=1, task_type="survival"),
                make_task(name="Fun Walk",         duration=30, priority=3),
            ],
            available=5,   # barely any time
        )
        scheduled, _, _ = scheduler.build_schedule()

        assert "Morning Feeding" in scheduled_names(scheduled)

    def test_survival_tasks_are_locked(self):
        """ScheduledTask.locked must be True for every survival task."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Medication", duration=5, priority=1, task_type="survival")],
        )
        scheduled, _, _ = scheduler.build_schedule()

        locked = [s for s in scheduled if s.task.name == "Medication"]
        assert len(locked) == 1
        assert locked[0].locked is True

    def test_optional_tasks_are_not_locked(self):
        """Non-survival scheduled tasks should have locked=False."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Cuddle Time", duration=15, priority=4, task_type="hobby")],
        )
        scheduled, _, _ = scheduler.build_schedule()

        assert scheduled[0].locked is False

    def test_survival_task_scheduled_even_when_feared(self):
        """
        Survival tasks override everything — locked in before fear logic runs.
        """
        scheduler = make_scheduler(
            tasks=[make_task(name="Morning Feeding", duration=10, priority=1,
                             task_type="survival", tags=["food", "meal"])],
            fears=["food"],
        )
        scheduled, _, _ = scheduler.build_schedule()

        assert "Morning Feeding" in scheduled_names(scheduled)


# ─── Pet Favorites Tests ─────────────────────────────────────────────────────────

class TestPetFavorites:

    def test_favorite_task_preferred_over_non_favorite(self):
        """
        Owner has only 20 min.  Two 20-min tasks: one matches pet's favorite,
        one does not.  The favorite should win.
        """
        scheduler = make_scheduler(
            tasks=[
                make_task(name="Fetch",       duration=20, priority=3, tags=["tennis ball", "fetch"]),
                make_task(name="Boring Sit",  duration=20, priority=3, tags=["training"]),
            ],
            favorites=["tennis ball"],
            available=20,
        )
        scheduled, _, _ = scheduler.build_schedule()

        assert "Fetch"      in scheduled_names(scheduled)
        assert "Boring Sit" not in scheduled_names(scheduled)

    def test_reason_mentions_pet_favorite(self):
        """The Pet's Perspective reason should call out the matching favorite."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Cuddle Session", duration=15, tags=["cuddles", "calm"])],
            favorites=["cuddles"],
        )
        scheduled, _, _ = scheduler.build_schedule()

        assert "cuddles" in scheduled[0].reason.lower()


# ─── Energy Matching Tests ───────────────────────────────────────────────────────

class TestEnergyMatching:

    def test_low_energy_owner_gets_low_energy_tasks_prioritised(self):
        """
        Owner energy = Low, same priority tasks.
        The Low-energy task should rank above the High-energy one.
        """
        scheduler = make_scheduler(
            tasks=[
                make_task(name="Laser Play",  duration=10, priority=3, energy="Low"),
                make_task(name="Agility Run", duration=10, priority=3, energy="High"),
            ],
            energy="Low",
            available=20,
        )
        scheduled, _, _ = scheduler.build_schedule()

        names = scheduled_names(scheduled)
        assert names.index("Laser Play") < names.index("Agility Run")

    def test_high_energy_owner_can_schedule_high_energy_task(self):
        """A High-energy task should not be penalised when the owner is also High energy."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Big Hike", duration=30, priority=2, energy="High")],
            energy="High",
            available=60,
        )
        scheduled, skipped, _ = scheduler.build_schedule()

        assert "Big Hike" in scheduled_names(scheduled)


# ─── Priority Ordering Tests ─────────────────────────────────────────────────────

class TestPriorityOrdering:

    def test_higher_priority_task_scheduled_before_lower(self):
        """Priority 2 should beat Priority 4 when only one slot exists."""
        scheduler = make_scheduler(
            tasks=[
                make_task(name="Grooming",    duration=20, priority=2),
                make_task(name="Bonus Sniff", duration=20, priority=4),
            ],
            available=20,
        )
        scheduled, skipped, _ = scheduler.build_schedule()

        assert "Grooming"    in scheduled_names(scheduled)
        assert "Bonus Sniff" in skipped_names(skipped)

    def test_empty_task_list_returns_empty_schedule(self):
        """Graceful handling: no tasks → empty schedule and no crash."""
        scheduler = make_scheduler(tasks=[])
        scheduled, skipped, note = scheduler.build_schedule()

        assert scheduled == []
        assert skipped   == []
        assert isinstance(note, str) and len(note) > 0

    def test_summary_note_reflects_owner_energy(self):
        """The summary note wording should change based on owner energy level."""
        _, _, note_low  = make_scheduler([], energy="Low").build_schedule()
        _, _, note_high = make_scheduler([], energy="High").build_schedule()

        assert note_low  != note_high
        assert "easy" in note_low.lower() or "light" in note_low.lower()


# ─── New Relationship Tests ───────────────────────────────────────────────────────

class TestOwnerPetRelationships:

    def test_pet_pending_tasks_excludes_completed(self):
        """Pet.pending_tasks() should not return already-completed tasks."""
        t1 = make_task(name="Walk",   duration=20)
        t2 = make_task(name="Feeding", duration=10, priority=1, task_type="survival")
        t2.mark_complete()

        pet = Pet(name="Mochi", species="Dog", tasks=[t1, t2])
        assert len(pet.pending_tasks()) == 1
        assert pet.pending_tasks()[0].name == "Walk"

    def test_owner_pending_tasks_aggregates_across_pets(self):
        """Owner.pending_tasks() should combine pending tasks from all pets."""
        pet1 = Pet(name="Mochi", species="Dog",
                   tasks=[make_task(name="Walk"), make_task(name="Feeding", priority=1, task_type="survival")])
        pet2 = Pet(name="Bella", species="Cat",
                   tasks=[make_task(name="Laser Play")])

        owner = Owner(name="Jordan", available_time_minutes=120,
                      energy_battery="Medium", pets=[pet1, pet2])

        assert len(owner.pending_tasks()) == 3

    def test_task_frequency_is_stored(self):
        """Task.frequency should persist correctly for daily, weekly, as-needed."""
        daily  = make_task(name="Walk",     frequency="daily")
        weekly = make_task(name="Grooming", frequency="weekly")
        adhoc  = make_task(name="Vet",      frequency="as-needed")

        assert daily.frequency  == "daily"
        assert weekly.frequency == "weekly"
        assert adhoc.frequency  == "as-needed"

    def test_task_mark_complete_and_reset(self):
        """mark_complete() and reset() should toggle the completed flag."""
        task = make_task(name="Feeding")
        assert task.completed is False

        task.mark_complete()
        assert task.completed is True

        task.reset()
        assert task.completed is False

    def test_scheduled_task_carries_pet_reference(self):
        """Each ScheduledTask should know which pet it belongs to."""
        scheduler = make_scheduler(
            tasks=[make_task(name="Morning Walk", duration=20, priority=2)],
            pet_name="Mochi",
        )
        scheduled, _, _ = scheduler.build_schedule()

        assert scheduled[0].pet.name == "Mochi"
