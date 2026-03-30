"""
tests/test_pawpal.py — PawPal+ Unit Tests
==========================================
Tests for Task, Pet, Owner, and Scheduler classes.
Run with:

    pytest tests/test_pawpal.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pawpal_system import Task, Pet, Owner, Scheduler


# ─── Helpers ─────────────────────────────────────────────────────────────────

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


def make_scheduler(
    tasks,
    favorites=None,
    fears=None,
    available=120,
    energy="Medium",
    pet_name="Mochi",
    owner_name="Jordan",
):
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


# ─── Task Tests ───────────────────────────────────────────────────────────────

class TestTask:

    def test_task_is_created_with_correct_attributes(self):
        """Task stores all fields exactly as provided."""
        task = make_task(name="Walk", duration=20, priority=2,
                         energy="High", task_type="care", frequency="weekly",
                         tags=["outdoor"])
        assert task.name             == "Walk"
        assert task.duration_minutes == 20
        assert task.priority         == 2
        assert task.energy_level     == "High"
        assert task.task_type        == "care"
        assert task.frequency        == "weekly"
        assert task.tags             == ["outdoor"]

    def test_task_defaults_to_not_completed(self):
        """A freshly created task should not be marked complete."""
        task = make_task()
        assert task.completed is False

    def test_mark_complete_sets_flag(self):
        """mark_complete() should set completed to True."""
        task = make_task()
        task.mark_complete()
        assert task.completed is True

    def test_mark_complete_changes_status(self):
        """mark_complete() must actually change the status from False to True."""
        task = make_task(name="Feeding")
        before = task.completed        # False
        task.mark_complete()
        after = task.completed         # True
        assert before is False
        assert after  is True
        assert before != after         # status genuinely changed

    def test_reset_clears_flag(self):
        """reset() should set completed back to False."""
        task = make_task()
        task.mark_complete()
        task.reset()
        assert task.completed is False

    def test_is_survival_true_for_priority_one(self):
        """Priority-1 tasks are survival tasks."""
        task = make_task(priority=1, task_type="care")
        assert task.is_survival() is True

    def test_is_survival_true_for_survival_type(self):
        """task_type='survival' makes is_survival() True regardless of priority."""
        task = make_task(priority=3, task_type="survival")
        assert task.is_survival() is True

    def test_is_survival_false_for_optional_task(self):
        """Non-survival, non-priority-1 tasks should return False."""
        task = make_task(priority=4, task_type="hobby")
        assert task.is_survival() is False


# ─── Pet Tests ────────────────────────────────────────────────────────────────

class TestPet:

    def test_pet_stores_name_and_species(self):
        pet = Pet(name="Luna", species="Cat")
        assert pet.name    == "Luna"
        assert pet.species == "Cat"

    def test_add_task_appends_to_list(self):
        pet  = Pet(name="Mochi", species="Dog")
        task = make_task(name="Walk")
        pet.add_task(task)
        assert task in pet.tasks

    def test_add_task_increases_task_count(self):
        """Each call to add_task() should increase the pet's task count by one."""
        pet = Pet(name="Mochi", species="Dog")
        assert len(pet.tasks) == 0

        pet.add_task(make_task(name="Walk"))
        assert len(pet.tasks) == 1

        pet.add_task(make_task(name="Feeding"))
        assert len(pet.tasks) == 2

        pet.add_task(make_task(name="Cuddle Time"))
        assert len(pet.tasks) == 3

    def test_remove_task_by_name(self):
        task = make_task(name="Walk")
        pet  = Pet(name="Mochi", species="Dog", tasks=[task])
        pet.remove_task("Walk")
        assert task not in pet.tasks

    def test_pending_tasks_excludes_completed(self):
        """pending_tasks() should only return incomplete tasks."""
        t1 = make_task(name="Walk")
        t2 = make_task(name="Feeding")
        t2.mark_complete()
        pet = Pet(name="Mochi", species="Dog", tasks=[t1, t2])
        assert len(pet.pending_tasks()) == 1
        assert pet.pending_tasks()[0].name == "Walk"

    def test_completed_tasks_returns_done_tasks(self):
        t1 = make_task(name="Walk")
        t2 = make_task(name="Feeding")
        t2.mark_complete()
        pet = Pet(name="Mochi", species="Dog", tasks=[t1, t2])
        assert len(pet.completed_tasks()) == 1
        assert pet.completed_tasks()[0].name == "Feeding"

    def test_reset_day_clears_all_completed_flags(self):
        t1 = make_task(name="Walk")
        t2 = make_task(name="Feeding")
        t1.mark_complete()
        t2.mark_complete()
        pet = Pet(name="Mochi", species="Dog", tasks=[t1, t2])
        pet.reset_day()
        assert all(not t.completed for t in pet.tasks)


# ─── Owner Tests ──────────────────────────────────────────────────────────────

class TestOwner:

    def test_owner_stores_attributes(self):
        owner = Owner(name="Jordan", available_time_minutes=60,
                      energy_battery="High")
        assert owner.name                   == "Jordan"
        assert owner.available_time_minutes == 60
        assert owner.energy_battery         == "High"

    def test_add_pet(self):
        owner = Owner(name="Jordan", available_time_minutes=60,
                      energy_battery="Medium")
        pet = Pet(name="Mochi", species="Dog")
        owner.add_pet(pet)
        assert pet in owner.pets

    def test_remove_pet(self):
        pet   = Pet(name="Mochi", species="Dog")
        owner = Owner(name="Jordan", available_time_minutes=60,
                      energy_battery="Medium", pets=[pet])
        owner.remove_pet("Mochi")
        assert pet not in owner.pets

    def test_get_pet_returns_correct_pet(self):
        pet   = Pet(name="Luna", species="Cat")
        owner = Owner(name="Jordan", available_time_minutes=60,
                      energy_battery="Medium", pets=[pet])
        assert owner.get_pet("Luna") is pet

    def test_get_pet_raises_for_unknown_name(self):
        owner = Owner(name="Jordan", available_time_minutes=60,
                      energy_battery="Medium")
        with pytest.raises(ValueError):
            owner.get_pet("Ghost")

    def test_pending_tasks_aggregates_across_pets(self):
        """Owner.pending_tasks() should combine pending tasks from all pets."""
        pet1 = Pet(name="Mochi", species="Dog",
                   tasks=[make_task(name="Walk"), make_task(name="Feeding")])
        pet2 = Pet(name="Luna",  species="Cat",
                   tasks=[make_task(name="Laser Play")])
        owner = Owner(name="Jordan", available_time_minutes=120,
                      energy_battery="Medium", pets=[pet1, pet2])
        assert len(owner.pending_tasks()) == 3

    def test_pending_tasks_excludes_completed(self):
        task = make_task(name="Walk")
        task.mark_complete()
        pet   = Pet(name="Mochi", species="Dog", tasks=[task])
        owner = Owner(name="Jordan", available_time_minutes=60,
                      energy_battery="Medium", pets=[pet])
        assert len(owner.pending_tasks()) == 0


# ─── Scheduler Tests ──────────────────────────────────────────────────────────

class TestScheduler:

    def test_empty_task_list_returns_empty_schedule(self):
        scheduler = make_scheduler(tasks=[])
        scheduled, skipped, note = scheduler.build_schedule()
        assert scheduled == []
        assert skipped   == []
        assert isinstance(note, str) and len(note) > 0

    def test_survival_task_always_scheduled(self):
        scheduler = make_scheduler(
            tasks=[make_task(name="Feeding", duration=10, priority=1,
                             task_type="survival")],
            available=5,
        )
        scheduled, _, _ = scheduler.build_schedule()
        assert "Feeding" in scheduled_names(scheduled)

    def test_survival_task_is_locked(self):
        scheduler = make_scheduler(
            tasks=[make_task(name="Medication", duration=5, priority=1,
                             task_type="survival")],
        )
        scheduled, _, _ = scheduler.build_schedule()
        assert scheduled[0].locked is True

    def test_optional_task_is_not_locked(self):
        scheduler = make_scheduler(
            tasks=[make_task(name="Cuddle Time", priority=4, task_type="hobby")],
        )
        scheduled, _, _ = scheduler.build_schedule()
        assert scheduled[0].locked is False

    def test_feared_task_is_skipped(self):
        scheduler = make_scheduler(
            tasks=[make_task(name="Vacuum Session", tags=["vacuum", "indoor"])],
            fears=["vacuum"],
        )
        scheduled, skipped, _ = scheduler.build_schedule()
        assert "Vacuum Session" not in scheduled_names(scheduled)
        assert "Vacuum Session" in skipped_names(skipped)

    def test_fear_skip_reason_mentions_fear_word(self):
        scheduler = make_scheduler(
            tasks=[make_task(name="Thunder Walk", tags=["thunderstorm"])],
            fears=["thunder"],
        )
        _, skipped, _ = scheduler.build_schedule()
        assert "thunder" in skipped[0].reason.lower()

    def test_task_skipped_when_too_long(self):
        scheduler = make_scheduler(
            tasks=[make_task(name="Long Walk", duration=60)],
            available=10,
        )
        _, skipped, _ = scheduler.build_schedule()
        assert "Long Walk" in skipped_names(skipped)

    def test_skip_reason_mentions_duration_and_remaining(self):
        scheduler = make_scheduler(
            tasks=[make_task(name="Long Walk", duration=60)],
            available=10,
        )
        _, skipped, _ = scheduler.build_schedule()
        assert "60" in skipped[0].reason
        assert "10" in skipped[0].reason

    def test_task_fits_exactly_in_available_time(self):
        scheduler = make_scheduler(
            tasks=[make_task(name="Fetch", duration=20)],
            available=20,
        )
        scheduled, _, _ = scheduler.build_schedule()
        assert "Fetch" in scheduled_names(scheduled)

    def test_total_time_never_exceeds_available(self):
        scheduler = make_scheduler(
            tasks=[make_task(name=f"Task {i}", duration=15) for i in range(8)],
            available=60,
        )
        scheduled, _, _ = scheduler.build_schedule()
        total = sum(s.task.duration_minutes for s in scheduled)
        assert total <= 60

    def test_higher_priority_scheduled_over_lower(self):
        scheduler = make_scheduler(
            tasks=[
                make_task(name="Grooming",    duration=20, priority=2),
                make_task(name="Bonus Sniff", duration=20, priority=5),
            ],
            available=20,
        )
        scheduled, skipped, _ = scheduler.build_schedule()
        assert "Grooming"    in scheduled_names(scheduled)
        assert "Bonus Sniff" in skipped_names(skipped)

    def test_favorite_task_preferred_over_non_favorite(self):
        scheduler = make_scheduler(
            tasks=[
                make_task(name="Fetch",      duration=20, priority=3,
                          tags=["fetch", "ball"]),
                make_task(name="Boring Sit", duration=20, priority=3,
                          tags=["training"]),
            ],
            favorites=["fetch"],
            available=20,
        )
        scheduled, _, _ = scheduler.build_schedule()
        assert "Fetch" in scheduled_names(scheduled)
        assert "Boring Sit" not in scheduled_names(scheduled)

    def test_favorite_appears_in_scheduled_reason(self):
        scheduler = make_scheduler(
            tasks=[make_task(name="Cuddle Session", tags=["cuddles"])],
            favorites=["cuddles"],
        )
        scheduled, _, _ = scheduler.build_schedule()
        assert "cuddles" in scheduled[0].reason.lower()

    def test_low_energy_owner_prefers_low_energy_tasks(self):
        scheduler = make_scheduler(
            tasks=[
                make_task(name="Gentle Stretch", duration=10, priority=3,
                          energy="Low"),
                make_task(name="Agility Run",    duration=10, priority=3,
                          energy="High"),
            ],
            energy="Low",
            available=20,
        )
        scheduled, _, _ = scheduler.build_schedule()
        names = scheduled_names(scheduled)
        assert names.index("Gentle Stretch") < names.index("Agility Run")

    def test_scheduled_task_carries_pet_reference(self):
        scheduler = make_scheduler(
            tasks=[make_task(name="Morning Walk", duration=20, priority=2)],
            pet_name="Mochi",
        )
        scheduled, _, _ = scheduler.build_schedule()
        assert scheduled[0].pet.name == "Mochi"

    def test_summary_note_differs_by_energy(self):
        _, _, note_low  = make_scheduler([], energy="Low").build_schedule()
        _, _, note_high = make_scheduler([], energy="High").build_schedule()
        assert note_low != note_high
