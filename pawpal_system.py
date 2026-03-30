"""
pawpal_system.py — PawPal+ Backend
=====================================
Four core classes with clear, separated responsibilities:

  Task      — a single care activity (description, time, frequency, completion)
  Pet       — pet profile + owns its task list
  Owner     — manages multiple pets, exposes aggregate task access
  Scheduler — the "brain": retrieves, organises, and ranks tasks across pets

Improvements applied
--------------------
  #1  Round-robin interleaving  — optional tasks alternate across pets in output
  #2  Frequency-aware filtering — tasks with a future next_due_date are skipped
  #3  0/1 knapsack selection    — optimal fill instead of greedy left-to-right
  #4  Survival budget warning   — flags when survival tasks exceed available time
  #5  Score-per-minute          — normalises score by duration for fair comparison
  #6  Whole-word fear matching  — prevents false substring conflicts (e.g. "loud"≠"cloud")
  #7  Frequency weight          — daily tasks get a score bonus vs. weekly/as-needed
  #8  Priority validation       — __post_init__ enforces priority 1–5
  #9  Task deduplication        — id() guard in Owner stops double-scheduling shared tasks
  #10 Free-time display         — available in scheduler.warnings / printed in main.py
  #11 preferred_time field      — tasks carry "morning"/"afternoon"/"evening" for natural ordering
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import List, Optional, Tuple

# ─── Constants ──────────────────────────────────────────────────────────────────

ENERGY_LEVELS = ["High", "Medium", "Low"]
TASK_TYPES    = ["survival", "care", "hobby"]
FREQUENCY     = ["daily", "weekly", "as-needed"]
ENERGY_SCORE  = {"High": 3, "Medium": 2, "Low": 1}
TIME_ORDER    = {"morning": 0, "afternoon": 1, "evening": 2, "": 3}  # improvement #11


# ─── Task ───────────────────────────────────────────────────────────────────────

@dataclass
class Task:
    """
    Represents a single care activity.

    Attributes
    ----------
    name             : Short label shown in the UI, e.g. "Morning Walk"
    description      : Plain-English detail of what the task involves
    duration_minutes : How long the activity takes
    priority         : 1 (critical / survival) → 5 (optional bonus)  [validated]
    energy_level     : Energy the owner needs — "High" | "Medium" | "Low"
    task_type        : Category — "survival" | "care" | "hobby"
    frequency        : How often it recurs — "daily" | "weekly" | "as-needed"
    completed        : Marked True once the task is done for the day
    tags             : Keywords used to match pet favorites and fears
    next_due_date    : If set, task is skipped until on/after this date  [#2]
    preferred_time   : Hint for natural ordering — "morning"|"afternoon"|"evening"|""  [#11]
    """

    name: str
    description: str
    duration_minutes: int
    priority: int
    energy_level: str
    task_type: str
    frequency: str
    completed: bool          = False
    tags: List[str]          = field(default_factory=list)
    next_due_date: Optional[date] = None   # improvement #2
    preferred_time: str      = ""          # improvement #11

    # improvement #8 — validate priority range at construction time
    def __post_init__(self) -> None:
        if not 1 <= self.priority <= 5:
            raise ValueError(
                f"Task '{self.name}': priority must be 1–5, got {self.priority}."
            )

    # ── behaviour ───────────────────────────────────────────────────────────────

    def is_survival(self) -> bool:
        """Return True when this task is non-negotiable (feeding, meds, etc.)."""
        return self.task_type == "survival" or self.priority == 1

    def is_due(self, today: Optional[date] = None) -> bool:
        """Return True if next_due_date is unset or on/before today.  [#2]"""
        if self.next_due_date is None:
            return True
        return self.next_due_date <= (today or date.today())

    def mark_complete(self) -> None:
        """Record that this task has been done today."""
        self.completed = True

    def next_occurrence(self) -> Optional["Task"]:
        """
        Return a new Task instance due on the next occurrence date.

        - daily  → due tomorrow (or next_due_date + 1 day if that was set)
        - weekly → due in 7 days (or next_due_date + 7 days if that was set)
        - as-needed → returns None (no automatic rescheduling)

        The new instance is a full copy with completed reset to False and
        next_due_date advanced to the correct future date.
        """
        if self.frequency == "daily":
            delta = timedelta(days=1)
        elif self.frequency == "weekly":
            delta = timedelta(weeks=1)
        else:
            return None
        base = self.next_due_date if self.next_due_date is not None else date.today()
        return replace(self, completed=False, next_due_date=base + delta)

    def reset(self) -> None:
        """Clear the completion flag at the start of a new day."""
        self.completed = False


# ─── Pet ────────────────────────────────────────────────────────────────────────

@dataclass
class Pet:
    """
    Stores pet details and owns the list of care tasks for that pet.

    Attributes
    ----------
    name      : Pet's name
    species   : e.g. "Dog", "Cat", "Rabbit"
    favorites : Activities or items the pet loves — boosts matching tasks
    fears     : Things the pet dislikes — conflicting tasks are always skipped
    tasks     : Every Task that belongs to this pet
    """

    name: str
    species: str
    favorites: List[str] = field(default_factory=list)
    fears: List[str]     = field(default_factory=list)
    tasks: List[Task]    = field(default_factory=list)

    # ── task management ─────────────────────────────────────────────────────────

    def add_task(self, task: Task) -> None:
        """Add a new task, ignoring duplicates by object identity.  [#9]"""
        if id(task) not in {id(t) for t in self.tasks}:
            self.tasks.append(task)

    def remove_task(self, task_name: str) -> None:
        """Remove a task by name."""
        self.tasks = [t for t in self.tasks if t.name != task_name]

    def pending_tasks(self) -> List[Task]:
        """Return only tasks that have not been completed yet."""
        return [t for t in self.tasks if not t.completed]

    def completed_tasks(self) -> List[Task]:
        """Return tasks already marked done today."""
        return [t for t in self.tasks if t.completed]

    def complete_task(self, task_name: str) -> Optional[Task]:
        """
        Mark a task complete by name and, for daily/weekly tasks, automatically
        append the next occurrence to this pet's task list.

        Returns the newly created next-occurrence Task, or None for as-needed tasks.
        Raises ValueError if no task with that name exists.
        """
        for task in self.tasks:
            if task.name == task_name:
                task.mark_complete()
                next_task = task.next_occurrence()
                if next_task is not None:
                    self.add_task(next_task)
                return next_task
        raise ValueError(f"No task named '{task_name}' found for {self.name}.")

    def reset_day(self) -> None:
        """Reset all tasks so the pet is ready for a fresh schedule tomorrow."""
        for task in self.tasks:
            task.reset()


# ─── Owner ──────────────────────────────────────────────────────────────────────

@dataclass
class Owner:
    """
    Manages one or more pets and provides aggregate access to all their tasks.

    Attributes
    ----------
    name                   : Owner's name
    available_time_minutes : Total free time available today
    energy_battery         : Current energy level — "High" | "Medium" | "Low"
    pets                   : Every pet this owner is responsible for
    """

    name: str
    available_time_minutes: int
    energy_battery: str
    pets: List[Pet] = field(default_factory=list)

    # ── pet management ──────────────────────────────────────────────────────────

    def add_pet(self, pet: Pet) -> None:
        """Register a new pet under this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> None:
        """Remove a pet by name."""
        self.pets = [p for p in self.pets if p.name != pet_name]

    def get_pet(self, pet_name: str) -> Pet:
        """Look up a pet by name; raises ValueError if not found."""
        for pet in self.pets:
            if pet.name == pet_name:
                return pet
        raise ValueError(f"No pet named '{pet_name}' found.")

    # ── aggregate task access ───────────────────────────────────────────────────

    def all_tasks(self) -> List[Tuple[Task, "Pet"]]:
        """Return every task across all pets, deduplicating shared Task objects.  [#9]"""
        seen: set = set()
        result: List[Tuple[Task, "Pet"]] = []
        for pet in self.pets:
            for task in pet.tasks:
                if id(task) not in seen:
                    seen.add(id(task))
                    result.append((task, pet))
        return result

    def pending_tasks(self) -> List[Tuple[Task, "Pet"]]:
        """Return only incomplete tasks across all pets, deduplicating shared objects.  [#9]"""
        seen: set = set()
        result: List[Tuple[Task, "Pet"]] = []
        for pet in self.pets:
            for task in pet.pending_tasks():
                if id(task) not in seen:
                    seen.add(id(task))
                    result.append((task, pet))
        return result


# ─── Output Models ───────────────────────────────────────────────────────────────

@dataclass
class ScheduledTask:
    """A Task that made it onto the Tail-Wagging Timeline."""
    task: Task
    pet: Pet
    reason: str
    locked: bool = False


@dataclass
class SkippedTask:
    """A Task left off today's plan, with the reason why."""
    task: Task
    pet: Pet
    reason: str


# ─── Scheduler ──────────────────────────────────────────────────────────────────

class Scheduler:
    """
    The brain of PawPal+.

    Receives an Owner (who holds Pets, who hold Tasks) and builds the
    Tail-Wagging Timeline by:
      1. Filtering out tasks that are not due today (next_due_date).
      2. Locking in survival tasks unconditionally; warning if they exceed budget.
      3. Removing any optional task whose tags conflict with a pet's fears.
      4. Running a 0/1 knapsack to optimally fill remaining time with scored tasks.
      5. Interleaving selected optional tasks across pets in round-robin order.
      6. Sorting survival tasks and each pet's optional tasks by preferred_time.
      7. Generating a personalised Pet's Perspective reason for every decision.

    After build_schedule() completes, check self.warnings for any budget alerts.
    """

    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self.warnings: List[str] = []

    # ── private helpers ─────────────────────────────────────────────────────────

    def _search_terms(self, task: Task) -> List[str]:
        """Flat list of lowercase strings to match against favorites/fears."""
        return [tag.lower() for tag in task.tags] + [task.name.lower()]

    def _word_overlap(self, phrase: str, terms: List[str]) -> bool:
        """
        True when any whole word in phrase appears in any of terms.  [#6]
        Uses set intersection on split tokens to avoid false substring matches
        (e.g. fear "loud" no longer blocks a task tagged "cloud").
        """
        phrase_words = set(phrase.lower().split())
        for t in terms:
            if phrase_words & set(t.split()):
                return True
        return False

    def _matches_pet_favorites(self, task: Task, pet: Pet) -> List[str]:
        """Subset of pet.favorites that overlap (whole-word) with task search terms."""
        terms = self._search_terms(task)
        return [fav for fav in pet.favorites if self._word_overlap(fav, terms)]

    def _conflicts_with_fears(self, task: Task, pet: Pet) -> List[str]:
        """Subset of pet.fears that overlap (whole-word) with task search terms."""
        terms = self._search_terms(task)
        return [fear for fear in pet.fears if self._word_overlap(fear, terms)]

    def _score(self, task: Task, pet: Pet) -> float:
        """
        Score-per-minute for a task.  [#5, #7]

        Raw score components:
          + (6 - priority) * 10   — higher priority → higher score
          - energy mismatch * 20  — penalise tasks above owner's energy
          + favorites match * 25  — bonus for each matching pet favourite
          - fear conflict * 100   — heavy penalty (fear tasks are pre-filtered anyway)
          + 15 if daily           — daily tasks must not be missed  [#7]

        Dividing by duration_minutes converts to score-per-minute so short,
        high-quality tasks aren't buried by long mediocre ones.  [#5]
        """
        owner_e = ENERGY_SCORE.get(self.owner.energy_battery, 2)
        task_e  = ENERGY_SCORE.get(task.energy_level, 2)
        s  = (6 - task.priority) * 10
        s -= max(0, task_e - owner_e) * 20
        s += len(self._matches_pet_favorites(task, pet)) * 25
        s -= len(self._conflicts_with_fears(task, pet)) * 100
        if task.frequency == "daily":
            s += 15                          # improvement #7
        return s / max(1, task.duration_minutes)  # improvement #5

    def _knapsack(
        self,
        candidates: List[Tuple[Task, Pet, float]],
        capacity: int,
    ) -> List[Tuple[Task, Pet, float]]:
        """
        0/1 knapsack: select the subset of candidates that maximises total
        score-per-minute within `capacity` minutes.  [#3]

        Uses a standard DP table (n × capacity) with backtracking.
        Complexity: O(n × capacity) — fine for typical pet-care task counts.
        """
        n = len(candidates)
        if n == 0 or capacity <= 0:
            return []

        # dp[i][w] = best total score using the first i candidates with w minutes
        dp: List[List[float]] = [[0.0] * (capacity + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            task, _, score = candidates[i - 1]
            w = task.duration_minutes
            for cap in range(capacity + 1):
                dp[i][cap] = dp[i - 1][cap]          # skip item i
                if cap >= w:
                    take = dp[i - 1][cap - w] + score
                    if take > dp[i][cap]:
                        dp[i][cap] = take             # take item i

        # Backtrack to recover the selected items
        selected: List[Tuple[Task, Pet, float]] = []
        cap = capacity
        for i in range(n, 0, -1):
            if dp[i][cap] > dp[i - 1][cap] + 1e-9:
                selected.append(candidates[i - 1])
                cap -= candidates[i - 1][0].duration_minutes

        return selected

    def _interleave_by_pet(self, tasks: List[ScheduledTask]) -> List[ScheduledTask]:
        """
        Round-robin across pets so both animals get attention before any pet
        receives a second optional slot.  Within each pet's queue, tasks are
        ordered by preferred_time.  [#1, #11]
        """
        by_pet: dict = defaultdict(list)
        for st in tasks:
            by_pet[st.pet.name].append(st)

        # Sort each pet's tasks into time-of-day order
        for name in by_pet:
            by_pet[name].sort(
                key=lambda st: TIME_ORDER.get(st.task.preferred_time, 3)
            )

        # Build a deque of deques for O(1) round-robin rotation
        queues: deque = deque(
            deque(by_pet[p.name])
            for p in self.owner.pets
            if by_pet.get(p.name)
        )

        result: List[ScheduledTask] = []
        while queues:
            q = queues.popleft()
            result.append(q.popleft())
            if q:
                queues.append(q)   # return non-exhausted queue to the rotation

        return result

    def _survival_reason(self, pet: Pet) -> str:
        """Return the standard locked-in explanation used for all survival tasks."""
        return (
            f"Non-negotiable — {pet.name} needs this to stay healthy and safe. "
            "Survival tasks are always locked in first, no matter what."
        )

    def _optional_reason(self, task: Task, pet: Pet, matched_favs: List[str]) -> str:
        """Build a personalised Pet's Perspective sentence for an optional task."""
        owner   = self.owner
        owner_e = ENERGY_SCORE.get(owner.energy_battery, 2)
        task_e  = ENERGY_SCORE.get(task.energy_level, 2)
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
        """
        Retrieve all pending tasks from Owner → Pets, then build the timeline.

        Returns
        -------
        scheduled  : Ordered list of ScheduledTask (survival first by time-of-day,
                     then optional tasks interleaved across pets)
        skipped    : Tasks left out — not due today, fear conflict, or not optimal
        note       : Plain-English summary of today's plan

        Side-effects
        ------------
        self.warnings is populated with any budget alerts.  [#4, #10]
        """
        self.warnings = []
        today = date.today()
        all_pending = self.owner.pending_tasks()

        # ── Improvement #2: frequency-aware due-date filtering ──────────────────
        not_due: List[SkippedTask] = [
            SkippedTask(
                task=t, pet=p,
                reason=f"Not due until {t.next_due_date} — skipping today.",
            )
            for t, p in all_pending if not t.is_due(today)
        ]
        due_today = [(t, p) for t, p in all_pending if t.is_due(today)]

        survival = sorted(
            [(t, p) for t, p in due_today if t.is_survival()],
            key=lambda x: (TIME_ORDER.get(x[0].preferred_time, 3), x[0].priority),
        )
        optional_candidates = [(t, p) for t, p in due_today if not t.is_survival()]

        scheduled: List[ScheduledTask] = []
        skipped:   List[SkippedTask]   = list(not_due)
        time_left = self.owner.available_time_minutes

        # ── Improvement #4: warn when survival tasks alone bust the budget ───────
        survival_time = sum(t.duration_minutes for t, _ in survival)
        if survival_time > self.owner.available_time_minutes:
            self.warnings.append(
                f"⚠️  Survival tasks alone ({survival_time} min) exceed your available "
                f"time ({self.owner.available_time_minutes} min). "
                "Consider freeing up more time today."
            )

        # Step 1 — Lock survival tasks (always included)
        for task, pet in survival:
            scheduled.append(ScheduledTask(
                task=task, pet=pet,
                reason=self._survival_reason(pet),
                locked=True,
            ))
            time_left -= task.duration_minutes

        # Step 2 — Filter fear conflicts before scoring
        knapsack_candidates: List[Tuple[Task, Pet, float]] = []
        for task, pet in optional_candidates:
            fears = self._conflicts_with_fears(task, pet)
            if fears:
                skipped.append(SkippedTask(
                    task=task, pet=pet,
                    reason=f"Skipped — {pet.name} has a fear of {' and '.join(fears)}.",
                ))
            else:
                knapsack_candidates.append((task, pet, self._score(task, pet)))

        # ── Improvement #3: 0/1 knapsack for optimal optional selection ──────────
        selected = self._knapsack(knapsack_candidates, max(0, time_left))
        selected_ids = {id(t) for t, _, _ in selected}

        for task, pet, _ in knapsack_candidates:
            if id(task) in selected_ids:
                matched = self._matches_pet_favorites(task, pet)
                scheduled.append(ScheduledTask(
                    task=task, pet=pet,
                    reason=self._optional_reason(task, pet, matched),
                ))
            else:
                if task.duration_minutes > max(0, time_left):
                    reason = (
                        f"Couldn't fit — needs {task.duration_minutes} min but only "
                        f"{max(0, time_left)} min remain in {self.owner.name}'s schedule."
                    )
                else:
                    reason = (
                        "Not selected — the optimal schedule fills available time "
                        "more efficiently without this task."
                    )
                skipped.append(SkippedTask(task=task, pet=pet, reason=reason))

        # ── Improvements #1 & #11: interleave optional tasks across pets by time ─
        survival_scheduled = [s for s in scheduled if s.locked]
        optional_scheduled = [s for s in scheduled if not s.locked]
        final_scheduled = survival_scheduled + self._interleave_by_pet(optional_scheduled)

        # ── Improvement #10: report remaining free time ──────────────────────────
        total_used = sum(s.task.duration_minutes for s in final_scheduled)
        free_time  = self.owner.available_time_minutes - total_used
        if free_time > 0:
            self.warnings.append(
                f"ℹ️  {free_time} min of free time remains after today's schedule."
            )

        # Summary note
        owner_e   = ENERGY_SCORE.get(self.owner.energy_battery, 2)
        pet_names = " & ".join(p.name for p in self.owner.pets) or "your pet"
        if owner_e == 1:
            note = (
                f"🌙 Easy day mode activated. Today's plan is light and loving — "
                f"{pet_names} will feel completely cared for, and so will you."
            )
        elif owner_e == 3:
            note = (
                f"⚡ Maximum paw-tential! {pet_names} is in for an action-packed, "
                f"tail-wagging adventure today!"
            )
        else:
            note = (
                f"🐾 A perfectly balanced day — enough enrichment to keep "
                f"{pet_names}'s tail wagging without overdoing it."
            )

        return final_scheduled, skipped, note
