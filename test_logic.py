"""
test_logic.py — PawPal+ Scheduler Tests
========================================
Each test "pretends" to be a user setting up a scenario and checks that the
Scheduler responds correctly.  Run with:

    pytest test_logic.py -v
"""

import pytest
from pawpal_system import CareTask, Pet, Owner, ScheduledTask, SkippedTask, Scheduler


# ─── Helpers ────────────────────────────────────────────────────────────────────

def make_task(
    name="Generic Task",
    duration=15,
    priority=3,
    energy="Medium",
    task_type="hobby",
    tags=None,
):
    """Quick-build a CareTask with sensible defaults."""
    return CareTask(
        name=name,
        duration_minutes=duration,
        priority=priority,
        energy_level=energy,
        task_type=task_type,
        tags=tags or [],
    )


def make_owner(name="Jordan", available=120, energy="Medium"):
    return Owner(name=name, available_time_minutes=available, energy_battery=energy)


def make_pet(name="Mochi", species="Dog", favorites=None, fears=None):
    return Pet(name=name, species=species, favorites=favorites or [], fears=fears or [])


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
        pet   = make_pet(fears=["rain"])
        owner = make_owner(available=120)
        tasks = [make_task(name="Outdoor Rainy Walk", tags=["outdoor", "rain", "walk"])]

        scheduler = Scheduler(pet=pet, owner=owner, tasks=tasks)
        scheduled, skipped, _ = scheduler.build_schedule()

        assert "Outdoor Rainy Walk" not in scheduled_names(scheduled)
        assert "Outdoor Rainy Walk" in skipped_names(skipped)

    def test_fear_skip_reason_mentions_fear(self):
        """The skip reason should tell the owner exactly why it was skipped."""
        pet   = make_pet(fears=["loud noises"])
        owner = make_owner(available=120)
        tasks = [make_task(name="Fireworks Show", tags=["loud noises", "outdoor"])]

        _, skipped, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert len(skipped) == 1
        assert "loud noises" in skipped[0].reason.lower()

    def test_non_feared_task_is_not_skipped(self):
        """A task with no fear overlap should make it onto the schedule."""
        pet   = make_pet(fears=["rain"])
        owner = make_owner(available=60)
        tasks = [make_task(name="Indoor Play", tags=["indoor", "play"])]

        scheduled, skipped, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "Indoor Play" in scheduled_names(scheduled)
        assert "Indoor Play" not in skipped_names(skipped)

    def test_partial_tag_match_triggers_fear_skip(self):
        """Fear matching should work even when the fear word is a substring of a tag."""
        pet   = make_pet(fears=["thunder"])
        owner = make_owner(available=60)
        tasks = [make_task(name="Thunder Walk", tags=["thunderstorm", "outdoor"])]

        _, skipped, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "Thunder Walk" in skipped_names(skipped)

    def test_fear_skips_task_even_with_plenty_of_time(self):
        """Even with 8 hours available, a feared task must be skipped."""
        pet   = make_pet(fears=["vacuum"])
        owner = make_owner(available=480)
        tasks = [make_task(name="Vacuum Cleaning", tags=["vacuum", "indoor", "chore"])]

        scheduled, skipped, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "Vacuum Cleaning" not in scheduled_names(scheduled)


# ─── Time Constraint Tests ───────────────────────────────────────────────────────

class TestTimeConstraints:

    def test_task_skipped_when_too_long_for_available_time(self):
        """
        Scenario: owner only has 10 minutes but the task needs 30.
        The scheduler must skip the task and report the correct remaining time.
        """
        owner = make_owner(available=10)
        pet   = make_pet()
        tasks = [make_task(name="Long Walk", duration=30)]

        scheduled, skipped, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "Long Walk" not in scheduled_names(scheduled)
        assert "Long Walk" in skipped_names(skipped)

    def test_skip_reason_mentions_time(self):
        """The skip reason should include how much time was needed vs available."""
        owner = make_owner(available=10)
        pet   = make_pet()
        tasks = [make_task(name="Long Walk", duration=30)]

        _, skipped, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "30" in skipped[0].reason  # 30 min needed
        assert "10" in skipped[0].reason  # 10 min remaining

    def test_task_fits_exactly_in_available_time(self):
        """A task whose duration exactly equals available time should be scheduled."""
        owner = make_owner(available=20)
        pet   = make_pet()
        tasks = [make_task(name="Fetch", duration=20)]

        scheduled, skipped, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "Fetch" in scheduled_names(scheduled)

    def test_multiple_tasks_fill_time_greedily(self):
        """
        Three tasks: 20 min, 20 min, 20 min.  Owner has 40 min.
        Exactly two should fit; the third should be skipped.
        """
        owner = make_owner(available=40)
        pet   = make_pet()
        tasks = [
            make_task(name="Task A", duration=20, priority=2),
            make_task(name="Task B", duration=20, priority=3),
            make_task(name="Task C", duration=20, priority=4),
        ]

        scheduled, skipped, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert len(scheduled) == 2
        assert len(skipped) == 1

    def test_total_scheduled_time_never_exceeds_available(self):
        """The sum of scheduled durations must never exceed the owner's available time."""
        owner = make_owner(available=60)
        pet   = make_pet()
        tasks = [make_task(name=f"Task {i}", duration=15, priority=i % 5 + 1) for i in range(10)]

        scheduled, _, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()
        total = sum(s.task.duration_minutes for s in scheduled)

        assert total <= 60


# ─── Survival Task Tests ─────────────────────────────────────────────────────────

class TestSurvivalTasks:

    def test_survival_tasks_always_scheduled(self):
        """Priority-1 tasks must appear in the schedule no matter what."""
        owner = make_owner(available=5)   # barely any time
        pet   = make_pet()
        tasks = [
            make_task(name="Morning Feeding", duration=10, priority=1, task_type="survival"),
            make_task(name="Fun Walk",        duration=30, priority=3),
        ]

        scheduled, _, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "Morning Feeding" in scheduled_names(scheduled)

    def test_survival_tasks_are_locked(self):
        """ScheduledTask.locked must be True for every survival task."""
        owner = make_owner(available=120)
        pet   = make_pet()
        tasks = [make_task(name="Medication", duration=5, priority=1, task_type="survival")]

        scheduled, _, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        locked = [s for s in scheduled if s.task.name == "Medication"]
        assert len(locked) == 1
        assert locked[0].locked is True

    def test_optional_tasks_are_not_locked(self):
        """Non-survival scheduled tasks should have locked=False."""
        owner = make_owner(available=120)
        pet   = make_pet()
        tasks = [make_task(name="Cuddle Time", duration=15, priority=4, task_type="hobby")]

        scheduled, _, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert scheduled[0].locked is False

    def test_survival_task_scheduled_even_when_feared(self):
        """
        Survival tasks override everything — even if it would normally conflict
        with the pet's fears, it is locked in.  (Feeding must happen regardless.)
        """
        pet   = make_pet(fears=["food"])   # edge-case: pet 'fears' food keyword
        owner = make_owner(available=120)
        tasks = [make_task(name="Morning Feeding", duration=10, priority=1,
                           task_type="survival", tags=["food", "meal"])]

        scheduled, _, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "Morning Feeding" in scheduled_names(scheduled)


# ─── Pet Favorites Tests ─────────────────────────────────────────────────────────

class TestPetFavorites:

    def test_favorite_task_preferred_over_non_favorite(self):
        """
        Owner has only 20 min.  Two 20-min tasks: one matches pet's favorite,
        one does not.  The favorite should win.
        """
        pet   = make_pet(favorites=["tennis ball"])
        owner = make_owner(available=20)
        tasks = [
            make_task(name="Fetch",       duration=20, priority=3, tags=["tennis ball", "fetch"]),
            make_task(name="Boring Sit",  duration=20, priority=3, tags=["training"]),
        ]

        scheduled, _, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "Fetch" in scheduled_names(scheduled)
        assert "Boring Sit" not in scheduled_names(scheduled)

    def test_reason_mentions_pet_favorite(self):
        """The Pet's Perspective reason should call out the matching favorite."""
        pet   = make_pet(favorites=["cuddles"])
        owner = make_owner(available=60)
        tasks = [make_task(name="Cuddle Session", duration=15, tags=["cuddles", "calm"])]

        scheduled, _, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        reason = scheduled[0].reason.lower()
        assert "cuddles" in reason


# ─── Energy Matching Tests ───────────────────────────────────────────────────────

class TestEnergyMatching:

    def test_low_energy_owner_gets_low_energy_tasks_prioritised(self):
        """
        Owner energy = Low, same priority tasks.
        The Low-energy task should rank above the High-energy one.
        """
        pet   = make_pet()
        owner = make_owner(available=20, energy="Low")
        tasks = [
            make_task(name="Laser Play",  duration=10, priority=3, energy="Low"),
            make_task(name="Agility Run", duration=10, priority=3, energy="High"),
        ]

        scheduled, _, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        # With only 20 min and two 10-min tasks both fit, but ordering shows preference
        names = scheduled_names(scheduled)
        assert names.index("Laser Play") < names.index("Agility Run")

    def test_high_energy_owner_can_schedule_high_energy_task(self):
        """A High-energy task should not be penalised when the owner is also High energy."""
        pet   = make_pet()
        owner = make_owner(available=60, energy="High")
        tasks = [make_task(name="Big Hike", duration=30, priority=2, energy="High")]

        scheduled, skipped, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "Big Hike" in scheduled_names(scheduled)


# ─── Priority Ordering Tests ─────────────────────────────────────────────────────

class TestPriorityOrdering:

    def test_higher_priority_task_scheduled_before_lower(self):
        """
        Two tasks that both fit but only one slot of time exists.
        Priority 2 should beat Priority 4.
        """
        pet   = make_pet()
        owner = make_owner(available=20)
        tasks = [
            make_task(name="Grooming",    duration=20, priority=2),
            make_task(name="Bonus Sniff", duration=20, priority=4),
        ]

        scheduled, skipped, _ = Scheduler(pet=pet, owner=owner, tasks=tasks).build_schedule()

        assert "Grooming" in scheduled_names(scheduled)
        assert "Bonus Sniff" in skipped_names(skipped)

    def test_empty_task_list_returns_empty_schedule(self):
        """Graceful handling: no tasks → empty schedule and no crash."""
        pet   = make_pet()
        owner = make_owner(available=120)

        scheduled, skipped, note = Scheduler(pet=pet, owner=owner, tasks=[]).build_schedule()

        assert scheduled == []
        assert skipped   == []
        assert isinstance(note, str) and len(note) > 0

    def test_summary_note_reflects_owner_energy(self):
        """The summary note wording should change based on owner energy level."""
        pet = make_pet()

        _, _, note_low  = Scheduler(pet, make_owner(energy="Low"),  []).build_schedule()
        _, _, note_high = Scheduler(pet, make_owner(energy="High"), []).build_schedule()

        assert note_low  != note_high
        assert "easy" in note_low.lower() or "light" in note_low.lower()
