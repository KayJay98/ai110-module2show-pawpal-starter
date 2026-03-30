"""
pawpal_skeleton.py — Class Skeletons (from UML)
=================================================
This file contains the names, attributes, and empty method stubs for every
class in the PawPal+ UML diagram.  No logic is implemented here — it is a
blueprint only.  The full implementation lives in pawpal_system.py.

Use this file as a reference for how the UML maps to Python code.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


# ─── Data Models ────────────────────────────────────────────────────────────────

@dataclass
class CareTask:
    """
    Represents a single pet care activity.

    Attributes
    ----------
    name             : Human-readable label, e.g. "Morning Walk"
    duration_minutes : How long the task takes
    priority         : 1 (critical / survival) → 5 (optional bonus)
    energy_level     : Energy required — "High" | "Medium" | "Low"
    task_type        : Category — "survival" | "care" | "hobby"
    tags             : Keywords used for favorite/fear matching
    """

    name: str
    duration_minutes: int
    priority: int
    energy_level: str
    task_type: str
    tags: List[str] = field(default_factory=list)

    def is_survival(self) -> bool:
        """Return True if this task is non-negotiable (priority 1 or type survival)."""
        ...


@dataclass
class Pet:
    """
    Stores the pet's profile and personal preferences.

    Attributes
    ----------
    name      : Pet's name
    species   : e.g. "Dog", "Cat", "Rabbit"
    favorites : Activities or items the pet loves — boosts matching tasks
    fears     : Things the pet dislikes — conflicting tasks are skipped
    """

    name: str
    species: str
    favorites: List[str] = field(default_factory=list)
    fears: List[str]     = field(default_factory=list)


@dataclass
class Owner:
    """
    Stores the owner's daily constraints.

    Attributes
    ----------
    name                   : Owner's name
    available_time_minutes : Total free time available today
    energy_battery         : Current energy level — "High" | "Medium" | "Low"
    """

    name: str
    available_time_minutes: int
    energy_battery: str


# ─── Output Models ───────────────────────────────────────────────────────────────

@dataclass
class ScheduledTask:
    """
    A CareTask that made it onto the Tail-Wagging Timeline.

    Attributes
    ----------
    task   : The underlying CareTask
    reason : Pet's Perspective explanation of why this task was chosen
    locked : True when the task is a non-negotiable survival task
    """

    task: CareTask
    reason: str
    locked: bool = False


@dataclass
class SkippedTask:
    """
    A CareTask that was left off today's plan, along with the reason why.

    Attributes
    ----------
    task   : The underlying CareTask
    reason : Explanation — e.g. not enough time, or pet fears the activity
    """

    task: CareTask
    reason: str


# ─── Scheduler Engine ────────────────────────────────────────────────────────────

class Scheduler:
    """
    The core planning engine.

    Receives a Pet, an Owner, and a list of CareTasks.
    Produces a Tail-Wagging Timeline: an ordered list of ScheduledTasks
    and a list of SkippedTasks, along with a plain-English summary note.

    Relationships (from UML)
    ------------------------
    Scheduler  -->  Pet          (1-to-1 : owner profile)
    Scheduler  -->  Owner        (1-to-1 : owner profile)
    Scheduler  -->  CareTask     (1-to-many : input tasks)
    Scheduler  ..>  ScheduledTask  (produces 0 or more)
    Scheduler  ..>  SkippedTask    (produces 0 or more)
    """

    def __init__(self, pet: Pet, owner: Owner, tasks: List[CareTask]) -> None:
        """Store the pet profile, owner profile, and candidate task list."""
        self.pet: Pet              = pet
        self.owner: Owner          = owner
        self.tasks: List[CareTask] = tasks

    # ── Public API ───────────────────────────────────────────────────────────────

    def build_schedule(self) -> Tuple[List[ScheduledTask], List[SkippedTask], str]:
        """
        Build and return the day's plan.

        Steps
        -----
        1. Separate survival tasks (priority 1) from optional tasks.
        2. Lock all survival tasks into the schedule unconditionally.
        3. Score and rank optional tasks.
        4. Greedily add optional tasks until time runs out or all are processed.
        5. Return (scheduled_tasks, skipped_tasks, summary_note).
        """
        ...

    # ── Private Helpers ──────────────────────────────────────────────────────────

    def _search_terms(self, task: CareTask) -> List[str]:
        """
        Return a flat list of lowercase strings to match against.
        Combines all tags plus the task name itself.
        """
        ...

    def _matches_pet_favorites(self, task: CareTask) -> List[str]:
        """
        Return the subset of pet.favorites that overlap with this task's
        search terms.  Used to add a bonus to the task's score and to
        personalise the Pet's Perspective reason.
        """
        ...

    def _conflicts_with_fears(self, task: CareTask) -> List[str]:
        """
        Return the subset of pet.fears that overlap with this task's
        search terms.  Any non-empty result causes the task to be skipped.
        """
        ...

    def _score(self, task: CareTask) -> float:
        """
        Compute a numeric score for ranking optional tasks.

        Higher score  →  scheduled earlier.

        Factors
        -------
        + Priority weight        : lower priority number = higher score
        - Energy mismatch penalty: penalise tasks that demand more energy than the owner has
        + Pet-favorite bonus     : boost tasks matching the pet's favorites
        - Fear conflict penalty  : heavily penalise tasks that trigger a fear
        """
        ...

    def _survival_reason(self) -> str:
        """
        Return the standard Pet's Perspective sentence used for all
        locked survival tasks.
        """
        ...

    def _optional_reason(self, task: CareTask, matched_favs: List[str]) -> str:
        """
        Build a personalised Pet's Perspective sentence for an optional task.

        Takes into account
        ------------------
        - Owner's energy battery vs. task energy level
        - Any pet favorites that matched this task
        - Task priority (adds context for high-importance or bonus tasks)
        """
        ...
