"""
pawpal_system.py — PawPal+ Backend
=====================================
All data models and scheduling logic live here, completely separate from the
Streamlit UI.  Import from this module in app.py and test_logic.py.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

# ─── Constants ──────────────────────────────────────────────────────────────────

ENERGY_LEVELS = ["High", "Medium", "Low"]
TASK_TYPES    = ["survival", "care", "hobby"]
ENERGY_SCORE  = {"High": 3, "Medium": 2, "Low": 1}

# ─── Data Models ────────────────────────────────────────────────────────────────

@dataclass
class CareTask:
    """A single pet care activity with scheduling metadata."""
    name: str
    duration_minutes: int
    priority: int          # 1 = critical (survival) → 5 = optional
    energy_level: str      # High | Medium | Low
    task_type: str         # survival | care | hobby
    tags: List[str] = field(default_factory=list)

    def is_survival(self) -> bool:
        return self.task_type == "survival" or self.priority == 1


@dataclass
class Pet:
    """The pet's identity, preferences, and sensitivities."""
    name: str
    species: str
    favorites: List[str] = field(default_factory=list)  # e.g. ["tennis balls", "fetch"]
    fears: List[str]     = field(default_factory=list)  # e.g. ["rain", "loud noises"]


@dataclass
class Owner:
    """The owner's daily constraints."""
    name: str
    available_time_minutes: int
    energy_battery: str    # High | Medium | Low


@dataclass
class ScheduledTask:
    """A task that made it onto the Tail-Wagging Timeline."""
    task: CareTask
    reason: str            # Pet's Perspective explanation
    locked: bool = False   # True for survival tasks


@dataclass
class SkippedTask:
    """A task that was left off today's plan, with a reason."""
    task: CareTask
    reason: str


# ─── Scheduler ──────────────────────────────────────────────────────────────────

class Scheduler:
    """
    Builds the Tail-Wagging Timeline by:
      1. Locking in all survival tasks (priority 1) — non-negotiable.
      2. Scoring optional tasks by priority, energy match, and pet preferences.
      3. Greedily filling remaining time, skipping fear-conflicting tasks.
    """

    def __init__(self, pet: Pet, owner: Owner, tasks: List[CareTask]):
        self.pet   = pet
        self.owner = owner
        self.tasks = tasks

    # ── helpers ─────────────────────────────────────────────────────────────────

    def _search_terms(self, task: CareTask) -> List[str]:
        return [t.lower() for t in task.tags] + [task.name.lower()]

    def _matches_pet_favorites(self, task: CareTask) -> List[str]:
        terms = self._search_terms(task)
        return [
            fav for fav in self.pet.favorites
            if any(fav.lower() in t or t in fav.lower() for t in terms)
        ]

    def _conflicts_with_fears(self, task: CareTask) -> List[str]:
        terms = self._search_terms(task)
        return [
            fear for fear in self.pet.fears
            if any(fear.lower() in t or t in fear.lower() for t in terms)
        ]

    def _score(self, task: CareTask) -> float:
        owner_e = ENERGY_SCORE.get(self.owner.energy_battery, 2)
        task_e  = ENERGY_SCORE.get(task.energy_level, 2)
        s  = (6 - task.priority) * 10                    # priority weight
        s -= max(0, task_e - owner_e) * 20               # energy mismatch penalty
        s += len(self._matches_pet_favorites(task)) * 25 # pet-favorite bonus
        s -= len(self._conflicts_with_fears(task)) * 100 # fear penalty
        return s

    # ── reason generators ───────────────────────────────────────────────────────

    def _survival_reason(self) -> str:
        return (
            f"Non-negotiable — {self.pet.name} needs this to stay healthy and safe. "
            "Survival tasks are always locked in first, no matter what."
        )

    def _optional_reason(self, task: CareTask, matched_favs: List[str]) -> str:
        pet, owner = self.pet, self.owner
        owner_e    = ENERGY_SCORE.get(owner.energy_battery, 2)
        task_e     = ENERGY_SCORE.get(task.energy_level, 2)
        parts: List[str] = []

        if owner_e == 1 and task_e == 1:
            parts.append(
                f"Since {owner.name} is running on low energy today, this gentle activity "
                f"keeps {pet.name} happy and engaged without draining you further."
            )
        elif owner_e == 1:
            parts.append(
                f"Even with limited energy today, {owner.name} can handle this — "
                f"a manageable way to add some joy to {pet.name}'s day."
            )
        elif owner_e == 3 and task_e == 3:
            parts.append(
                f"{owner.name} is full of energy today — perfect for this high-intensity "
                f"activity that will get {pet.name}'s tail flying!"
            )
        elif owner_e == 3:
            parts.append(
                f"With {owner.name} feeling great today, this is a smooth and joyful win for {pet.name}."
            )
        elif task_e > owner_e:
            parts.append(
                f"This is a slight energy stretch, but {pet.name} really benefits from it today."
            )
        else:
            parts.append(
                f"A comfortable fit for {owner.name}'s energy level, and a lovely activity for {pet.name}."
            )

        if matched_favs:
            fav_str = " and ".join(matched_favs)
            parts.append(
                f"{pet.name} absolutely loves {fav_str} — this one is a guaranteed tail-wagger! 🐾"
            )

        if task.priority == 2:
            parts.append("Scheduled as a high-importance well-being activity.")
        elif task.priority >= 4:
            parts.append("A lovely bonus that squeezed into today's plan!")

        return " ".join(parts) or f"A great fit for {pet.name} and {owner.name} today."

    # ── main build ──────────────────────────────────────────────────────────────

    def build_schedule(self) -> Tuple[List[ScheduledTask], List[SkippedTask], str]:
        survival = sorted(
            [t for t in self.tasks if t.is_survival()], key=lambda t: t.priority
        )
        optional = sorted(
            [t for t in self.tasks if not t.is_survival()], key=self._score, reverse=True
        )

        scheduled: List[ScheduledTask] = []
        skipped:   List[SkippedTask]   = []
        time_left = self.owner.available_time_minutes

        # Step 1 — Lock survival tasks (always included)
        for task in survival:
            scheduled.append(ScheduledTask(task=task, reason=self._survival_reason(), locked=True))
            time_left -= task.duration_minutes

        # Step 2 — Greedy fill with scored optional tasks
        for task in optional:
            fears = self._conflicts_with_fears(task)
            if fears:
                skipped.append(SkippedTask(
                    task=task,
                    reason=f"Skipped — {self.pet.name} has a fear of {' and '.join(fears)}.",
                ))
                continue
            if task.duration_minutes <= time_left:
                matched = self._matches_pet_favorites(task)
                scheduled.append(ScheduledTask(task=task, reason=self._optional_reason(task, matched)))
                time_left -= task.duration_minutes
            else:
                skipped.append(SkippedTask(
                    task=task,
                    reason=(
                        f"Couldn't fit — needs {task.duration_minutes} min but only "
                        f"{max(0, time_left)} min remain in {self.owner.name}'s schedule."
                    ),
                ))

        owner_e = ENERGY_SCORE.get(self.owner.energy_battery, 2)
        if owner_e == 1:
            note = (
                f"🌙 Easy day mode activated. Today's plan is light and loving — "
                f"{self.pet.name} will feel completely cared for, and so will you."
            )
        elif owner_e == 3:
            note = (
                f"⚡ Maximum paw-tential! {self.pet.name} is in for an action-packed, "
                f"tail-wagging adventure today!"
            )
        else:
            note = (
                f"🐾 A perfectly balanced day — enough enrichment to keep "
                f"{self.pet.name}'s tail wagging without overdoing it."
            )

        return scheduled, skipped, note
