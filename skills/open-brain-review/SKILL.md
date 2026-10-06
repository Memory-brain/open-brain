---
name: open-brain-review
description: 'Weekly review of sessions. What was practiced, ideas not captured, patterns across the week.
  Triggers: weekly review, what did I do this week, session summary, open-brain review'
metadata:
  version: null
  status: canonical
  status_note: No version declared yet.
  consumes:
  - A request for a weekly (or custom N-day) review of your recent assistant sessions/chats
  produces:
  - 'A brief presented in-conversation: an activity table (session/domain/output/practice-log status),
    detected patterns, and uncaptured post ideas'
  - Optionally, new notes in Ideas/ or a saved review note in Practice Log/
  handoffs:
  - skill: open-brain-practice-log
    when: chaining right after practice-log harvest to complement sessions that never went through practice-log
    requires_approval: true
  - skill: open-brain-escribir
    when: uncaptured post ideas detected in the review feed into drafting
    requires_approval: true
  - skill: open-brain-graph
    when: cross-checking whether the week's sessions touched fertile PNs or a dead zone of the vault
    requires_approval: true
---

# Open Brain — Review

Reviews your assistant chat sessions from the last N days, identifies what was done in each session, detects patterns, and produces an activity brief. It is the source of truth for what you actually practiced — it does not depend on you having opened a practice-log.

## When to use

The user says: "what did I do this week", "summary of my sessions", "weekly review", "open-brain review", "what did I practice these days", "chat summary", "which sessions did I have", "give me a brief of the week", "harvest my chats".

It can also be chained after `practice-log harvest` to complement it with sessions that never went through practice-log.

## Flow

### Step 1 — List recent sessions

Use your environment's session-listing tool (e.g. `list_sessions`) with a limit large enough to cover the requested period (7 days by default). Sessions come with a title and ID. Filter for those with relevant titles — ignore trivial or setup sessions.

```
list_sessions(limit: 50)
```

If the user specifies a different period ("last 3 days", "this week", "last 14 days"), adjust. If not specified, use 7 days.

If your environment has no session-listing or transcript-reading tool, say so and ask the user to paste or point to the session summaries instead.

### Step 2 — Read relevant transcripts

For each session that looks substantive (by its title), read the transcript:

```
read_transcript(session_id: "<session id>", limit: 30)
```

Reading the last 30 messages of each session is enough to capture the bulk of the work. If a session is very long and clearly important, read more.

Process up to ~15 sessions. If there are more than 15, prioritize by title relevance. Setup sessions, quick tests or simple questions can be skipped with just the title.

### Step 3 — Classify each session

For each session read, extract:

1. **What was done** — in 1-2 sentences. Not the whole transcript, the concrete activity.
2. **Domain** — one or more of: PKM, Writing, Product/Work, AI/Agents, Learning, Meta-system (skills, plugins), Analysis/Data, Communication, Other.
3. **Tangible output** — did it produce anything? (file created, skill modified, vault note, draft, dashboard, documented decision). If it produced no output, say so.
4. **Post ideas detected** — if publishable material came up in the conversation, even if it was not recorded. Look for energetic phrasing, diagnoses, insights, "aha" moments.
5. **Did it go through practice-log?** — if the transcript mentions practice-log open/close, mark it as recorded. Otherwise, mark it as not recorded.

### Step 4 — Detect patterns

With all sessions classified, analyze:

**Time distribution**:
- How many sessions per domain?
- How many produced tangible output vs. how many were exploration/conversation?
- How many were recorded in practice-log vs. how many were lost?

**Work patterns**:
- Is there a domain that dominates the week? Is one missing that should be there?
- How much was real work (projects, writing, decisions) vs. meta-work (skills, vault, system)?
- Was anything published? Did anything get close to publishing?

**Uncaptured ideas**:
- Which post ideas came up in conversations but were not recorded in Ideas/?
- Are there sessions with rich material that was lost because there was no practice-log close?

**Relation to your output goal** (if you have one, e.g. a "publish first" rule):
- How many sessions moved you toward your output goals?
- How many were meta-work disguised as progress?
- Output / meta-work ratio for the week.

### Step 5 — Produce the brief

The output is a summary presented directly in the conversation (not a file, unless the user asks for one). Structure:

**1. Activity this week** (summary table):
- Session | Domain | Output | Practice-log

**2. Detected patterns** (3-5 observations in prose):
- What dominated, what was missing, work/meta-work ratio.

**3. Uncaptured post ideas** (if any):
- Ideas that came up in chats but never reached Ideas/. For each: source session + the sentence that captures it.
- Ask the user: "Do you want me to create notes in Ideas/ for these?"

**4. Suggestions** (1-3 max):
- Based on the patterns. Concrete, not generic.
- If the meta-work ratio is high: say so directly.
- If there are ideas ready to become a post: point them out.

### Step 6 — Optional actions

If the user asks:
- Create notes in Ideas/ for the uncaptured ideas.
- Save the brief as a note in `Practice Log/` named `YYYY-MM-DD — weekly review.md`.
- Cross-check against the existing `Practice Log/` to detect which sessions were never recorded.

## Rules

1. **Do not read ALL transcripts.** Filter by title first. A session titled "How to change the editor theme" is probably not substantive practice.
2. **Do not judge.** The review reports facts and patterns. If the meta-work ratio is high, say it without a sermon.
3. **Be brief.** The brief should take no more than 3-5 minutes to read. If there are 20 sessions, the table summarizes them; only the 3-5 most relevant deserve a sentence of detail.
4. **Post ideas are gold.** The most valuable function of the review is rescuing ideas that were said in a chat and never recorded. Look for them actively.
5. **Respect your output goal.** If you have set one, the review always evaluates: did this week move closer to publishing/shipping or further away?

## Example output

```
## Weekly review — May 8-15

### Activity

| Session | Domain | Output | PLog |
|---|---|---|---|
| Plan a spring vegetable garden | Gardening | Planting calendar | No |
| Read two chapters on Roman history | History | New Literature Notes | Yes |
| Reorganize my note templates | Meta-system | Simplified templates | No |
| Learn basic sourdough fermentation | Cooking | First bake, notes on timing | No |
| Practice chord changes on guitar | Music | 3 practice sessions logged | No |
| Compare two statistics textbooks | Statistics | Reading plan | No |

### Patterns

Of 6 substantive sessions, 1 was meta-work on the system (templates),
3 were hands-on practice (garden plan, sourdough, guitar), and 2 were
learning from sources (Roman history, statistics).

Only 1 of 6 went through practice-log. The other 5 were not recorded,
even though three of them were exactly the kind of deliberate practice
practice-log exists for.

Notes written from your own experience: 0. The practice happened, but
none of it was captured as judgment you could reuse.

### Uncaptured ideas

1. "Learn basic sourdough fermentation" — you found that timing mattered
   more than the recipe. That is a candidate Case: "what my first bakes
   taught me about reading the dough instead of the clock."
2. "Practice chord changes on guitar" — the observation that slow, clean
   repetitions beat fast sloppy ones connects to your notes on deliberate
   practice.

Should I create notes in Ideas/ for these?

### Suggestions

1. The sourdough Case is the closest to being written. Next session:
   `open-brain escribir` on that idea.
2. Three practice sessions went unlogged. Next week, run practice-log at the
   end of each one, even a short entry.
```

## Relation to other sub-capabilities

- **practice-log harvest** (`open-brain-practice-log`) consolidates what WAS recorded. Review complements it with what was NOT.
- **escribir** (`open-brain-escribir`) feeds on the uncaptured ideas the review detects.
- **graph** (`open-brain-graph`) can be cross-checked: did the week's sessions touch fertile PNs or a dead zone of the vault?
