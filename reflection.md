# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
  - The initial design used a Model-View-Controller approach with five classes: `CareTask`, `Pet`, `Owner`, `ScheduledTask`, and `SkippedTask` as data models, and `Scheduler` as the central engine. The UML defined clear input → process → output flow.
- What classes did you include, and what responsibilities did you assign to each?
  - `CareTask` holds task metadata (name, duration, priority, energy level, type, tags). `Pet` stores preferences and fears. `Owner` stores daily constraints (time and energy). `Scheduler` handles all scoring, filtering, and explanation logic. `ScheduledTask` and `SkippedTask` carry the results with reasons attached.

**b. Design changes**

- Did your design change during implementation?
  - Yes.
- If yes, describe at least one change and why you made it.
  - The "Pet's Perspective" reason generation was moved from individual task objects into the `Scheduler` class. This was necessary because generating a personalized explanation requires comparing the owner's energy level with the pet's preferences simultaneously — information a `CareTask` object cannot access on its own.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
  - The scheduler considers four constraints: survival necessity, owner energy availability, pet fears, and total available time. Survival tasks bypass scoring entirely and are always locked in. Fears and time act as hard constraints — a feared task is never scheduled, and a task that won't fit is skipped. Energy and favorites are soft constraints that shape the scoring of everything else.
- How did you decide which constraints mattered most?
  - Survival and fears were treated as hardest because violating them has real consequences — a pet missing medication or being forced into a feared activity causes genuine harm, while skipping an enrichment activity does not.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
  - The scheduler uses a Greedy Algorithm — it picks the highest-scoring tasks first rather than finding the combination that fits the most total value into the available time.
- Why is that tradeoff reasonable for this scenario?
  - For pet care, completing high-priority essential needs is more important than packing in as many tasks as possible. A Knapsack optimization approach would be mathematically better but would add significant complexity without meaningfully improving real-world outcomes.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
  - AI was used to brainstorm the mathematical scoring formula, generate boilerplate for the Streamlit interface and SVG paw styling, and debug edge cases in the data editor validation logic.
- What kinds of prompts or questions were most helpful?
  - Prompts focused on specific logic challenges were most effective — for example, how to penalize energy mismatches without making high-energy tasks completely unreachable, or how to safely handle `NaN` values from pandas when a user adds an incomplete row.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
  - The AI suggestion to use a Knapsack optimization algorithm for scheduling was evaluated and rejected in favor of the simpler greedy sorting method.
- How did you evaluate or verify what the AI suggested?
  - The Knapsack approach would have made the code significantly harder to read and maintain, and would not allow the "Pet's Perspective" text to be generated cleanly alongside each decision. Keeping the algorithm simple meant the reasoning behind every scheduled task stayed transparent and explainable.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
  - The test suite verified six behavioral categories: fear-based task skipping, time constraint enforcement, survival task locking, pet favorites prioritization, energy level matching, and priority ordering.
- Why were these tests important?
  - These tests represent the core promises the app makes to the user — it will never suggest something the pet fears, never schedule something the owner cannot complete in time, and always protect the pet's non-negotiable survival needs.

**b. Confidence**

- How confident are you that your scheduler works correctly?
  - The 21 passing test cases provide high confidence across a range of owner-pet profiles. All core behaviors are verified and edge cases in the data layer (NaN handling, invalid energy strings) are guarded.
- What edge cases would you test next if you had more time?
  - Zero-minute time constraints, a pet whose fear list overlaps with a survival task's tags, duplicate tasks with identical scores, and very large task lists to check performance.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
  - The "Pet's Perspective" feature — every scheduled task gets a personalized, empathetic explanation that connects the scheduling logic directly to the pet's personality and the owner's current state, making the app feel supportive rather than prescriptive.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
  - Adding time-of-day windows to each `CareTask` so morning tasks like feeding are pinned to the correct part of the day. This would require a `preferred_time` field on `CareTask` and updating `build_schedule` to place tasks into time slots rather than just an ordered list.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
  - Defining clear hard constraints early — survival tasks that are always included and fears that are always excluded — creates a stable, trustworthy foundation that makes every other feature easier to build. When the boundaries of a system are explicit and enforced from the start, the creative and flexible parts of the logic can flourish on top of them without risk of producing harmful or nonsensical results.
