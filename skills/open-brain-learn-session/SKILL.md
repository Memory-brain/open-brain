---
name: open-brain-learn-session
description: 'Entry point for all learning work. Routes to the right skill sequence — prevents going straight
  to extraction without activating prior knowledge first. Triggers: I want to learn, learning session,
  I have this book, what do I know about, open-brain learn'
metadata:
  folded_from_top_level:
    version: 1.0.0
  version: 1.0.0
  status: canonical
  consumes:
  - A signal that the user wants to start learning work (new content, practice, evaluation, or an open/undecided
    session)
  - The current vault state, to check what prior knowledge already exists on the topic
  produces:
  - A diagnosed session mode (A/B/C/D) and a proposed sequence of open-brain-* skills
  - An ephemeral in-conversation session log tracking skills run and notes created
  - 'A session-close checklist result: practice check, convergence prompt, ideas check, next-session seed'
  handoffs:
  - skill: open-brain-retrieve
    when: always, before running any other learning or vault skill, to surface prior knowledge
    requires_approval: true
  - skill: open-brain-analyze
    when: Mode A (new content) standard or high-value sequence
    requires_approval: true
  - skill: open-brain-extract
    when: after open-brain-analyze, to turn new insights into Literature Notes
    requires_approval: true
  - skill: open-brain-promote
    when: convergences with existing notes are detected after extraction
    requires_approval: true
  - skill: open-brain-execute
    when: Mode A high-value content, or Mode B applying knowledge to a real problem
    requires_approval: true
  - skill: open-brain-improve
    when: Mode B testing understanding or running a full practice loop
    requires_approval: true
  - skill: open-brain-panel
    when: Mode B full practice loop feedback, or Mode C evaluation (expert panel + synthesis)
    requires_approval: true
  - skill: open-brain-health
    when: Mode D open session, to run a lightweight check for the highest-value activity
    requires_approval: true
---

# Open Brain — Learn Session

Entry point for all learning work. Diagnose what the user needs, retrieve what they already know, and design the right skill sequence before any other learning or vault skill runs. The reason this entry point exists: going directly to open-brain-analyze or extraction skips the most important step — activating prior knowledge before acquiring new knowledge increases retention and transfer.

---

## Step 1: Identify the Session Mode

Ask the user or infer from context:

**Mode A — New Content**
The user has material they haven't studied yet (book, article, PDF, video transcript). Goal: extract maximum knowledge AND ensure it connects to what they already know.

**Mode B — Active Practice**
The user wants to work with something they've already studied. Goal: test understanding, apply to real problems, or improve a skill.

**Mode C — Evaluation**
The user has produced work (document, decision, plan) and wants expert feedback. Goal: identify gaps and improvement priorities.

**Mode D — Open Session**
The user isn't sure what to do. Goal: surface the highest-value activity based on vault state.

If the mode isn't obvious from context, ask one question:
> "Do you have new content to process, do you want to practice something you've already studied, or do you want feedback on something you've produced?"

---

## Step 2: Retrieve Prior Knowledge (always, before anything else)

Before running any other skill, call `open-brain-retrieve` on the topic or domain.

Tell the user what was found:
> "Before we start: I found [N] notes on [topic] in your vault — [list top 3]. Especially [[Note X]], which already captures [idea]. I'll focus on what's missing and on connecting to what you already have."

If the vault is empty on this topic:
> "You have no prior notes on [topic]. We start from scratch — I'll pay special attention to connections with your strongest domains ([Domain A], [Domain B])."

Why: the user may already have substantial knowledge on this topic. If so, adjust the open-brain-analyze output to focus on what's NEW, surface existing PNs the new content should connect to, and identify which layers are already covered (to avoid re-extracting what's already there).

---

## Step 3: Design the Session Sequence

Based on Mode and vault state, propose a specific sequence:

### Mode A — New Content sequences

**Standard (most content):**
```
open-brain-analyze → [Activation Prompt response] → open-brain-extract → open-brain-promote (if convergences)
```

**High-value content (rating 5 / directly applicable to current work):**
```
open-brain-analyze → [Activation Prompt] → open-brain-extract → open-brain-execute → open-brain-improve → open-brain-promote
```

**Already have LNs from this source (second pass):**
```
open-brain-extract (layers 4-7 only) → open-brain-promote
```

### Mode B — Practice sequences

**Test understanding:**
```
open-brain-retrieve → open-brain-improve (Diagnosis + Practice layers)
```

**Apply to real problem:**
```
open-brain-retrieve → open-brain-execute (Application + Decision layers)
```

**Full practice loop:**
```
open-brain-retrieve → open-brain-improve → [user does the exercise] → open-brain-panel (feedback) → open-brain-promote (if new insights)
```

### Mode C — Evaluation sequences

```
open-brain-panel (expert reviews + synthesis) → open-brain-analyze or open-brain-improve (worst gap)
```

### Mode D — Open Session

Run a lightweight `open-brain-health` check:
- Unprocessed inbox items? → Mode A on the oldest/highest-value
- PNs with `times_retrieved: 0` in high-priority domains? → Mode B
- Work in progress (cases, OKRs, active projects)? → Mode C

---

## Step 4: Confirm and Launch

Present the proposed sequence to the user:

> "**Today's session:**
> 1. open-brain-analyze on [topic] → extract Knowledge + Compression + Mental Models + Manifest
> 2. Your answer to the Activation Prompt (5 minutes of active reflection)
> 3. open-brain-extract → Literature Notes with the new insights
> 4. open-brain-promote if we detect convergences with your notes on [related domain]
>
> Shall we start?"

Keep it short. If the user says "yes" or equivalent, launch the first skill immediately — don't ask more questions.

---

## Step 5: Track Session Progress

Keep a lightweight session log in the conversation (not in the vault — this is ephemeral):

```
Session: [Topic] — [Date]
Mode: A / B / C / D
Prior knowledge found: [N] notes on [topic]
Skills run: open-brain-analyze ✅ → open-brain-extract 🔄 → ...
Notes created this session: [N LNs, N PNs]
Key insight: [one sentence]
Practice completed: yes/no
Activation Prompt answered: yes/no
```

---

## Step 6: Session Close

At the end of every session, regardless of mode, do four things:

**1. Practice check** — Did the user do at least one active practice activity this session? (Answering the Activation Prompt, doing an open-brain-improve exercise, applying a concept to a real problem.) If not:
> "Before we close: is there anything we covered today you'd like to apply to something concrete in the next few days? Tell me the situation and I'll design a 10-minute exercise."

**2. Convergence prompt** — Are there new connections to surface?
> "I noticed that [Insight X] from today converges with [[Existing PN]]. Do you want me to synthesize it into a Permanent Note now or in the next session?"

**3. Ideas check** — At the close of any Mode A or Mode C session, ask explicitly:
> "Does anything we covered today have material for a post?"

If yes, create a 3-line note in `Ideas/` (title, the idea in one sentence, why it matters). If no, skip silently — but always ask, don't assume.

**4. Next session seed** — Plant the next step:
> "For the next session: you have [N] LNs not yet promoted in [domain], [N] LNs with `Your extension` still empty, and [Book Y] in your inbox unprocessed. What has more priority?"

---

## Why Each Step Exists

- **Step 2 (prior knowledge first)**: Without this, new knowledge gets added without connecting to what's already there. Connections are how knowledge becomes retrievable and transferable.
- **Step 4 (explicit sequence)**: Without a plan, sessions drift. The hardest part of learning is doing the right thing, not doing something.
- **Step 5 (session log)**: Ephemeral tracking keeps the session coherent across multiple skill invocations.
- **Step 6 (practice check)**: Encoding without retrieval/application produces weak long-term retention. The Activation Prompt is the minimum — but real practice is stronger.

---

## What NOT To Do

- Do NOT run open-brain-analyze without first checking prior knowledge (Step 2).
- Do NOT skip the session sequence proposal — always make the plan explicit before running.
- Do NOT let a session end without asking the practice check question.
- Do NOT save the session log to the vault — it's ephemeral scaffolding, not knowledge.
