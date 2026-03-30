# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

---

## Class Diagram (Reverse-Engineered)

```mermaid
classDiagram

    %% ── Data Models ──────────────────────────────────────────

    class CareTask {
        +str name
        +int duration_minutes
        +int priority
        +str energy_level
        +str task_type
        +List~str~ tags
        +is_survival() bool
    }

    class Pet {
        +str name
        +str species
        +List~str~ favorites
        +List~str~ fears
    }

    class Owner {
        +str name
        +int available_time_minutes
        +str energy_battery
    }

    %% ── Output Models ────────────────────────────────────────

    class ScheduledTask {
        +CareTask task
        +str reason
        +bool locked
    }

    class SkippedTask {
        +CareTask task
        +str reason
    }

    %% ── Scheduler Engine ─────────────────────────────────────

    class Scheduler {
        +Pet pet
        +Owner owner
        +List~CareTask~ tasks
        +build_schedule() Tuple
        -_score(CareTask) float
        -_search_terms(CareTask) List~str~
        -_matches_pet_favorites(CareTask) List~str~
        -_conflicts_with_fears(CareTask) List~str~
        -_survival_reason() str
        -_optional_reason(CareTask, List) str
    }

    %% ── Relationships ────────────────────────────────────────

    Scheduler "1" --> "1" Pet           : profiles
    Scheduler "1" --> "1" Owner         : profiles
    Scheduler "1" --> "0..*" CareTask   : receives tasks

    Scheduler "1" ..> "0..*" ScheduledTask : produces
    Scheduler "1" ..> "0..*" SkippedTask   : produces

    ScheduledTask "1" *-- "1" CareTask  : wraps
    SkippedTask   "1" *-- "1" CareTask  : wraps

    Pet   ..> CareTask : favorites / fears\nfilter tasks
    Owner ..> CareTask : energy + time\nshape ranking
```

### How the data flows

| Step | What happens |
|------|-------------|
| **1. Input** | `Pet`, `Owner`, and a list of `CareTask` objects are passed into `Scheduler.__init__` |
| **2. Lock survival** | `build_schedule` separates tasks where `priority == 1` or `task_type == "survival"` — these become locked `ScheduledTask` objects unconditionally |
| **3. Score & rank** | Every remaining `CareTask` gets a float score: priority weight − energy-mismatch penalty + pet-favorites bonus − fear conflict penalty |
| **4. Greedy fill** | Tasks are added in score order until `Owner.available_time_minutes` runs out; fear-conflicting tasks are skipped immediately |
| **5. Output** | Returns `(List[ScheduledTask], List[SkippedTask], summary_note)` — each `ScheduledTask` carries a natural-language *Pet's Perspective* reason |
