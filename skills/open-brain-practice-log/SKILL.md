---
name: "open-brain-practice-log"
description: 'Command surface «open brain start / stop / harvest»: opens, closes and harvests a practice session
  when the user explicitly asks for it, with a fleeting-note harvest at close. Always writes through
  engine/practice_log.py (same note and validation for every entry point). Triggers:
  open-brain start, open-brain stop, open-brain harvest, practice-log open, practice-log close, practice-log harvest.'
metadata:
  folded_from_top_level:
    version: 3.0.1
  version: 3.1.0
  status: canonical
  consumes:
  - 'The user explicitly invoking a mode: open (starting a task), close (ending it), or harvest (consolidating
    a domain)'
  - 'For open: the Skills/<Domain>/<Capability>/ tree and any existing feeder-pns.md for the chosen capabilities'
  - 'For close: the user''s verbatim answers to the four closing questions'
  produces:
  - A Practice Log note per session (open/close) with capabilities, ammunition PNs, and a Cierre (close) section
  - Appended entries in Skills/<Domain>/<Capability>/gaps.md and, conditionally, promote-feedback.md
  - Proposed and created Fleeting Notes (and optionally Ideas/ notes) harvested from the session
  - A harvest brief aggregating trained capabilities, recurring gaps/patterns, and emergent capabilities
  handoffs:
  - skill: open-brain-retrieve
    when: indexing Practice Log notes for later search by task_type, domain, or capability
    requires_approval: true
  - skill: open-brain-synthesize
    when: a recurring pattern across 3+ closed sessions looks like it deserves becoming a new PN
    requires_approval: true
  - skill: open-brain-flashcards
    when: the user wants a challenge session in a domain, pasting the harvest brief into the flashcards
      prompt
    requires_approval: true
  - skill: open-brain-course
    when: more than 3 closed sessions in a domain haven't been harvested, or gaps total >=3 new since
      last course generation
    requires_approval: true
  - skill: open-brain-promote
    when: friction against a specific PN was recorded at close and needs review via --review-friction
    requires_approval: true
---

# Open Brain — Practice Log

Records the user's AI practice sessions in the vault and connects each session to the learning system. It exists to close a loop: when the user does a non-trivial task with AI, it leaves a record of what domain was trained, what specific capability was used, what wasn't applied, and what friction recurred. That log feeds `open-brain-flashcards` when the user requests a challenge in a domain. The skill does NOT decide which tasks deserve a log and does NOT interrupt other skill flows. It only runs when the user explicitly invokes it.

**v3.1.0: every write goes through the engine `$OPEN_BRAIN_ENGINES/engine/practice_log.py`.** Earlier versions created and closed the note by hand, with the domain as free text and without the engine's validation. Now every write uses the same rules: domain and capabilities validated against `Skills/`, pipeline `task_type` values rejected, and a close that leaves `status: closed`.

v2 integrates with open-brain-course: `open` prioritizes PNs with `endorsement_state: endorsed`; `close` adds an optional slot for recording friction against a specific PN (written to `Skills/<Domain>/<Skill>/promote-feedback.md`); and gaps are appended to `gaps.md`. This skill does NOT modify `endorsement_state` and does NOT write to `feeder-pns.md`.

Below, `practice_log.py` means `python3 "$OPEN_BRAIN_ENGINES/engine/practice_log.py"`.

---

## Three modes

The skill has three disjoint modes. The user indicates the mode in the message (or it is inferred from context). If ambiguous, ask before acting.

---

## Mode `open` — open session

The user says something like *"practice-log open: I'm going to write Thursday's post"* or *"open log: weekly report for a client"*.

### Steps

**1. The closed list of valid capabilities is the folder tree `Skills/<Domain>/<Capability>/`** (the engine validates against it; `Resources/Practice Capabilities.md` is a human-readable companion, not the source of truth).

**2. Identify the parent domain** (one only). It must be a folder in `Skills/`. If the task crosses domains, pick the dominant one and mention the others as context in the body. If you pass one that doesn't exist, the engine returns the valid list: retry with one of them.

**3. Identify 1-3 concrete capabilities** from the closed list. If a capability doesn't fit the list, propose it as an emergent capability — don't invent it silently; say: *"I propose an emergent capability: 'cross-team incident framing' — shall I add it to the log and to Practice Capabilities.md as emergent?"*. If the user says yes, add it to frontmatter `emergent_capabilities` AND add a bullet to the `## Emergent` section of `Practice Capabilities.md`:
`- **[Name]** — [definition] · *domain: X* · *first seen: YYYY-MM-DD* · *count: 1*` (if it already exists, increment the count).

**4. Find ammunition PNs — with endorsement_state prioritization (v2)**:

For each capability from Step 3:

a. Resolve `Skills/<Domain>/<Capability>/feeder-pns.md`.
b. If feeder-pns.md exists: read the Endorsed and Provisional sections. Pre-populate the ammunition with those PNs.
c. If it doesn't exist: fall back to open-brain-retrieve by keyword — without endorsement prioritization.
d. Independently, list related Cases.

The briefing output must visually distinguish:
- **Endorsed PNs** (no marker): ratified by the user. Maximum epistemic weight.
- **Provisional PNs** (⚠️): not validated. Legitimate ammunition but the user should watch them — if one doesn't fit when applied, record friction at close.
- **PNs without endorsement_state** (⚠️ legacy): old PNs not yet migrated. Treat them as provisional but mark them as legacy. This session does NOT migrate the frontmatter.

**No passive migration**: this skill does NOT write `endorsement_state: provisional` to PNs missing the field. It only reads and reports.

**5. Detect hanging logs.** Run `practice_log.py hanging`. If any log has been open >12h, mention it: *"there's a log open since <date> about X — shall I close it as `abandoned` or do you want to harvest it?"*. Wait for the response before continuing.

**6. Create the note with the engine**, never by hand: `practice_log.py open --json '{"domain": ..., "capabilities": [...], "task_type": ..., "task_short": ..., "linked_pns": [...]}'`. The engine writes this structure (shown for reference):

```yaml
---
domain: Communication
capabilities: [Hook design, Falsifiability framing]
emergent_capabilities: []
task_type: social-post
linked_skill:
linked_artifact:
linked_pns:
  - "[[PN title 1]]"
  - "[[PN title 2]]"
linked_cases: []
started: 2026-05-02T14:23
closed:
status: open
---

## Briefing

You are training **Communication / Hook design + Falsifiability framing** in a task of type `social-post`.

PNs available as ammunition:
- [[PN title 1]] — what it brings
- [[PN title 2]] — what it brings

Proposed emergent capability: *(if applicable)*

## Cierre

*(filled in with `practice-log close`)*
```

(`## Cierre` — "close" — is the section heading the engine writes; keep it as is.)

**7. Return a short 3-5 line message** to the user with domain, capabilities, PNs, and the log path. Example:

> Log opened: `Practice Log/2026-05-02 — Thursday post.md`
> Domain: Communication · Capabilities: Hook design, Falsifiability framing
> Ammunition: [[<PN title>]], [[…]]
> When you're done: `practice-log close`.

---

## Mode `close` — close session

The user says "practice-log close" or "close the log".

**1. Locate the open session.** List `Practice Log/` with `status: open`. If several, ask which; if one, assume it; if zero, say so and stop.

**2. Capture the close with four questions in a single call (v2)**:

a. "What did you *not* manage to apply/change that you wanted to?" (habitual gap)
b. "What recurring friction or doubt came up during the task?" (pattern)
c. "What would you do differently next time?" (insight)
d. "Did any ammunition PN NOT fit when you applied it?" (friction against a specific PN — v2)

Question d is **special**:
- Options: "None" (default) or one option per ammunition PN listed at open.
- If the user selects a PN, blocking follow-up: ask for `friction_type` (closed list from the unified schema) and a short owner note.
- If the user selects none: skip writing to promote-feedback.md.
- **Do NOT infer friction.** Only record it if the user marks it explicitly.

For questions a-c: present them as `multiSelect: false` with a couple of generic options + the automatic "Other" slot for the user to write freely. Generic options are suggestions of patterns the user tends to repeat (e.g., for Communication: "I didn't make the thesis falsifiable", "the hook ended up generic", "I packed in more than fits").

> **Since v3.1.0, steps 3, 3.5 and 3.6 describe the content; they are not written by hand**: the engine call in step 4 writes them. If you write them yourself and also call the engine, the gaps end up duplicated.

**3. Write to the note** the `## Cierre` section with three subsections (`### Gaps`, `### Patterns`, `### Insights`) using exactly what the user said. **Do not rewrite their texts** — keep verbatim what they write.

**3.5. Write to `Skills/<Domain>/<Capability>/gaps.md`** (v2):

For each capability in the session's frontmatter:

a. Resolve `Skills/<Domain>/<Capability>/gaps.md`. If it doesn't exist, skip this step silently (the capability may not have a Skill scaffolded yet — that's OK).
b. For each text the user wrote in the Cierre section (Gaps + Patterns + Insights), evaluate whether it's a skill gap. Heuristic: if the text describes something the user could NOT apply or something they keep doing wrong, it's a gap. If it's a neutral or positive insight, it's NOT a gap.
c. Append a block to gaps.md following the unified schema:

```markdown
---

## YYYY-MM-DDTHH:MM · practice-log · capability:Hook design

**Source**: practice-log
**Source ref**: [[Practice Log/2026-05-09 — post Hook design]]
**Capability**: Hook design
**Gap**: "<the user's literal text from the close>"
**Status**: open
```

Rules:
- The user's literal text. Do NOT reformulate.
- If the user gave several gaps, write several blocks (atomicity).
- If the session declared 2-3 capabilities, write the gap to ALL relevant capabilities.

**3.6. Write to `Skills/<Domain>/<Capability>/promote-feedback.md`** (v2):

Only if the user marked friction against a specific PN in question (d) of Step 2.

a. Resolve the file. Create it if it doesn't exist (with the schema header).
b. Append a block following the unified schema:

```markdown
---

## YYYY-MM-DDTHH:MM · practice-log · pn:[[<PN title>]]

**Source**: practice-log
**Source ref**: [[Practice Log/2026-05-09 — post Hook design]]
**PN**: [[exact PN title]]
**Case**: [[most relevant Case from the session]]
**Friction type**: <value from the closed list — chosen by the user in Step 2.d>
**Owner note**: "<the user's literal text>"
**Status**: pending-review
```

Rules:
- Literal text. Do NOT reformulate.
- One friction per session (v2 limitation).
- If the session has several capabilities, write the block to the dominant capability's promote-feedback.md.

**4. Close with the engine**: `practice_log.py close --json '{"log_file": ..., "gaps": [...], "patterns": [...], "insights": [...], "friction": {...}}'` writes the Cierre section, `gaps.md`, `promote-feedback.md` and sets `status: closed` + `closed`. Steps 3, 3.5 and 3.6 above describe what goes in; the engine does the writing. Then ask the user in one line *«did this practice help? 0-5 and why»* and run `practice_log.py outcome --file "<log>" --score N --note "<their literal sentence>"`. Add `linked_artifact` or `linked_skill` if the user provided them.

**5. Cross-connections**: add wikilinks `[[Domains/<domain>]]` and `[[Resources/Practice Capabilities]]` at the end of the body for Obsidian indexing.

**5.5. Fleeting notes harvest** — after recording gaps/patterns/insights, reflect on the ENTIRE session and propose fleeting notes.

**Principle: fleeting notes are volume, not quality.** Quality comes later, in promote. Here we capture raw signal — ideas, theses, observations, patterns, intuitions. Better 8 mediocre fleeting notes than 1 perfect one, because promote will filter. This matters because the best ideas come from real practice, not abstract brainstorms — and they cool down fast if not captured.

**Process:**

a. **Reflect silently** on what ideas, theses, observations or patterns emerged during the session. Consider:
   - What the user said/wrote during the task
   - Conversations or transcripts that were cited
   - Patterns that repeated in the data/examples
   - Arguments that were built and why they work
   - Gaps that reveal an implicit thesis
   - Non-obvious connections between concepts that emerged

b. **Propose a list of 4-8 fleeting notes** with a title and one line of context each. Present them numbered. Example:
   > Fleeting notes from this session:
   > 1. **A rule of thumb you never wrote down is a rule you will relearn** — every session generates patterns that evaporate. The cost isn't obvious until you repeat a mistake you had already solved once.
   > 2. **Readers skip the setup and go straight to the example** — a pattern across three different drafts this week.
   > 3. ...

c. **Ask the user**: "Which ones do I keep? Do you want to add any?" using AskUserQuestion with multiSelect:true listing the proposals + an "All" option + an "I want to add more (I'll write in Other)" option.

d. **Wait for the response**. If the user adds their own, include them as-is (literal text, do not reformulate).

e. **Create each selected fleeting note** in `Fleeting Notes/` with this format:
   ```yaml
   ---
   type: fleeting
   created: YYYY-MM-DD
   source: practice-session
   cluster: "[shared thematic cluster if there's an obvious one]"
   ---

   # [Fleeting note title]

   [Thesis or idea in 1-3 sentences — the user's literal text if they wrote it, or the proposal if they approved it]

   Context: [brief reference to the practice session and what originated it]
   ```

f. **Confirm to the user** with the list of fleeting notes created. Titles only — don't explain each one.

g. **Bonus — Ideas/ for posts**: if any fleeting note is clearly publishable (has a clear audience and a falsifiable thesis), IN ADDITION to the fleeting note, create a note in `Ideas/` with a 3-line format:
   ```
   [The idea in one sentence — what the post would say]
   [Why it's publishable / why the audience would care]
   [Where it comes from — reference to the practice session]
   ```
   But this is a bonus, not the main flow. Do NOT ask "is there material for a post?" — that's too narrow. The fleeting notes already capture everything; promote will decide what rises.

**Rules:**
- Do NOT ask for "one idea in one sentence" — that's too narrow. Propose SEVERAL.
- Do NOT create only Ideas/ (posts). Fleeting notes are the correct format here — more atomic, more volume, no "publishability" pressure.
- The user's texts: literal. Do not reformulate.
- The cluster in the frontmatter is optional but recommended when 3+ fleeting notes from the same session revolve around the same theme — it makes the later promote easier.

**6. Return a short message** — one line confirming the close + conditional reports (v2):
- Base message: "✅ Log closed: [[YYYY-MM-DD — task]]"
- If written to gaps.md: "Gaps recorded: N in gaps.md of Hook design"
- If written to promote-feedback.md: "Friction recorded against [[PN]] · pending review (when you can: open-brain-promote --review-friction)"
- If >3 closed sessions in the domain without a harvest: "Consider practice-log harvest [domain]"
- If the skill has a generated course and gaps total ≥3 new since the last generation: "Consider regenerating the course: open-brain-course Communication Hook design"

Do not exceed 4 lines in total. Friction kills the ritual.

---

## Mode `harvest` — harvest for a challenge

The user says "practice-log harvest [domain]" or "harvest the Communication log" or "what patterns have I had this month". This mode **does not generate flashcards** — it prepares material that `open-brain-flashcards` will consume.

**1. Filter logs** for the requested domain (or all if unspecified) in `Practice Log/` with `status: closed` from the last 30 days.

**2. Aggregate signals**:
- **Most trained capabilities** (count desc).
- **Recurring gaps** — similar phrases appearing in ≥2 sessions. No literal match required: group by concept (e.g., "I didn't falsify it", "generic thesis", "weak claim" → same pattern).
- **Recurring patterns** — same.
- **Emergent capabilities with count ≥3** — candidates for promotion to the official list.

**3. Return a markdown brief** structured as:

```markdown
## Practice Log Harvest — <domain> — <date range>

**Sessions**: N closed, M abandoned, K open.

### Trained capabilities
- Hook design — 5 sessions
- Falsifiability framing — 3 sessions

### Recurring gaps (≥2)
1. **Generic thesis at the close** — appears in 4 sessions. Sessions: [[…]], [[…]], …
2. **Hook forgets the concrete friction** — 2 sessions.

### Recurring patterns
1. **I reread after writing and see I copied the average social-post pattern** — 3 sessions.

### Emergent capabilities to promote
- "Cross-team incident framing" — 4 appearances — suggest promotion to Communication.

### Suggestion for flashcards
The next flashcards session in this domain should emphasize: [...]. To invoke: `flashcards Communication`.
```

**4. Do not invoke flashcards.** The skill ends here. The user decides when and whether to launch flashcards.

**5. If there are promotable emergent capabilities**, offer (without auto-applying): *"do you want me to move 'Cross-team incident framing' from Emergent to official Communication in `Practice Capabilities.md`?"*

---

## Standing rules

**Respect the user's texts.** When the user writes gaps/patterns/insights, copy them verbatim. Do not reformulate, clean up, or translate. The log is raw signal.

**Do not overcomplicate.** If the user says "practice-log open: post", do not interview them for 5 minutes to extract capabilities. Make the best inference, tell them, let them correct it if needed.

**Note naming**: `YYYY-MM-DD — [short-task].md`. The short task must be human-readable and unique within the day. If the user opens two logs the same day with similar tasks, suffix `(2)`, `(3)`.

**If the engine rejects the domain**: retry with one from the list it returns. Do not improvise capabilities without the list — it destroys later aggregation.

**Log hygiene**: on each `open`, run `hanging` for logs open >12h and offer to close them as `abandoned` or let the user harvest them. Do not close anything without permission.

**Capability granularity**: 1-3 per session. If you're proposing 3 you're already being generous; 4+ means the session is too wide or the list is poorly segmented — ask the user.

**Respect endorsement_state (v2)**: endorsed PNs are first-class ammunition. Provisional ones are valid but marked ⚠️. Rejected PNs are NOT offered as ammunition (they should be in `Permanent Notes/Rejected/` — feeder-pns.md should already exclude them, but verify when loading).

**Do NOT migrate PNs (v2)**: this skill does NOT write `endorsement_state: provisional` to PNs missing the field. It only reads, reports, and lists. Passive migration is done by open-brain-course (when building feeder-pns.md for the first time) or open-brain-promote.

**Do NOT write to feeder-pns.md (v2)**: the skill's PN feeder list is the responsibility of the user + open-brain-course + open-brain-promote. This skill reads it, it does not modify it.

---

## What this skill does NOT do

- Does not invoke other skills automatically. If the user wants flashcards, they ask for it.
- Does not open a log automatically when the user invokes another skill. Opening is always manual.
- Does not reformulate the user's texts.
- Does not mark tasks as "failed" or "successful". The log captures training, not verdicts.
- Does not send anything outside the vault.

---

## Compatibility with other skills

- **`open-brain-retrieve`** — indexes `Practice Log/` like any vault note. Allows searching by `task_type`, domain, capability using body wikilinks and frontmatter.
- **`open-brain-synthesize`** — can detect that a recurring pattern (≥3 closed sessions) deserves becoming a new PN. `practice-log harvest` signals it but does not force creation.
- **Voice/style review (optional)** — if the domain trained is `Public Speaking`, `Communication`, or `Writing Craft` and you keep a voice or style profile, the recurring gaps are good input for reviewing it.
- **`open-brain-flashcards`** — integration pending. Current bridge: the user runs `practice-log harvest <domain>`, receives the brief, and when invoking `flashcards <domain>` pastes the brief at the start of the prompt so the session weights the detected patterns.

---

## Frontmatter reference

Keep it identical to `Practice Log/README.md` if you keep one. If it changes in the future, update both the skill and the README at the same time.
