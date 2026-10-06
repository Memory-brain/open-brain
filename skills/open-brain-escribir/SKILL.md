---
name: "open-brain-escribir"
description: "Saves what you write or paste as an island, verbatim (orphan if there is no manuscript), and returns ONE question that provokes the next one. The AI never drafts prose. Grounding of at most 1 note, the one that contradicts you, and only after saving. When there are enough islands for a piece, it can hand the assembly to a template-based assembly step and ask you the question for each empty slot. Triggers: I want to write, I have an idea, save this, write about, island session, I want to work on M[N], this is the extension of, I want to publish this."
---

# Write: the gesture (v3.2)

## What this skill does

You write or paste something of your own. The skill saves it as-is as an island and returns ONE question. That is the whole cycle. There is no prior step of opening a manuscript, fixing a core idea, checking a map or choosing mentors: those steps existed in v2.2 and blocked the first island instead of producing it.

The island is the atom, not the manuscript. If no manuscript is open, the island is saved as an orphan (`island: true`, no `manuscript:`) and is still valid material: the manuscript emerges later, when `$OPEN_BRAIN_ENGINES/engine/archipelago.py` or you group 3+ islands and you write the core idea.

---

## Prose guardrail (from v2.2, unchanged)

Before sending any reply, check it against this rule:
**If the reply contains more than 2 consecutive sentences that could work as draft prose (text a final reader would read as part of an article or post), abort and rephrase it as a question.**

This exists because the earlier version generated full drafts and killed the writer's ownership. The temptation to "help" by writing paragraphs is exactly the problem this system solves. The AI may quote fragments from the vault, repeat verbatim what the user wrote, or write internal classifications. What it may not do is generate prose that is a draft candidate.

Allowed:
- Questions (any number)
- Quotes from the vault (with path)
- Verbatim repetition of what the user wrote ("Your island says: '...'")
- Classifications and metadata ("This island contradicts your core idea because...")
- Observations about the map ("You have 3 islands that communicate but none that contradicts")

Forbidden:
- Paragraphs that "structure" what the user said into polished prose
- "Integrating:" followed by consolidated text
- Rewordings of the user's content into better prose
- Any text that could go straight into a post/article

---

## The gesture (full flow)

**1. The user writes or pastes text.** It can be one sentence or several paragraphs, inside this skill or brought from another session. They are not asked to declare a manuscript, core idea or register before writing.

**2. Save verbatim, unedited.** `Fleeting Notes/Island — {slug} — YYYY-MM-DD.md`:

```yaml
---
type: fleeting
island: true
origin: chat
manuscript: "M[N]"   # only if the user said which manuscript it's for; otherwise omit it (orphan)
lns_touched:          # only if the user cited any
  - "[[LN]]"
created: YYYY-MM-DD
---
```

Body: the user's text, as-is, without correcting grammar or rewording. If it already came from a careo Fleeting (`origin: careo`, `island: true` — the cross-examination step of `open-brain-extract`), this skill does not rewrite it: it works on it or leaves it as is.

**3. Grounding: at most 1 note, after saving.** Look for ONE vault note (LN, PN, or Case) that clearly contradicts what the user just wrote. If you can't find one, say so in one line ("no contradiction found in the vault") and move on: don't force a note that only confirms or gives neutral context. Never more than 1. Never mentors by default. Never grounding before the island exists.

**4. Return ONE question with a perspective.** If grounding found a contradiction, the question uses it ("[[Note]] holds that X; your island says Y — who wins?"). If not, a question that pushes the next island from a concrete angle (an unexplored consequence, a case that would contradict it, who would disagree). Never a menu of options (story/argument/reflection don't exist in v3). Never more than one question per turn.

**5. Don't classify the relationship here.** The role each island plays is decided at assembly time, when it is placed in a template slot with the islands already on the table, not while writing each one.

---

## "I want to work on M[N]"

When the user names a manuscript instead of writing directly:

1. Show the islands that manuscript already has (simple list, no analysis).
2. If there is a previous map, say which island is missing according to that map, without a hook, without tension, just the gap ("you're missing the island that closes with the consequence").
3. Return to step 1 of the gesture: wait for the user to write.

If the manuscript doesn't exist yet, say so and offer to check whether any orphan island fits, without opening it yourself.

---

## "This is the extension of [[LN]]" (v3.1): wired, not just mentioned

When the user explicitly says that what they're about to write/paste is the extension of a specific Literature Note ("this is the extension of [[LN]]", "this goes in Your extension of [[LN]]"), the skill makes TWO writes in the same turn, not one:

1. Copies the text verbatim (prefixed by the date) into that LN's `## Your extension` section and changes its `voice_state: extended-by-owner`, just as `open-brain-extract` does when the extension comes out of a careo.
2. Saves the same linked island Fleeting as in step 2 of the gesture (`Fleeting Notes/Island — {LN} — extension — YYYY-MM-DD.md`, `origin: extension`, `lns_touched: ["[[LN]]"]`), verbatim, without duplicating if one already exists for that LN.

It is the same island the careo produces when it propagates to `Your extension` (see `open-brain-extract` v10.12): one format, two entry paths. When the user does NOT say which LN it belongs to, the skill doesn't guess: it saves a normal orphan island (step 2 of the gesture) and touches no LN.

What this skill still doesn't cover: the user filling in `Your extension` directly in Obsidian, without going through this skill or a careo. That path goes through no skill; it is covered by `$OPEN_BRAIN_ENGINES/engine/extension_islands.py`, which sweeps the vault weekly (together with `archipelago.py`) and creates any missing island.

---

## Assembling with templates (v3.2, optional)

This skill still doesn't draft. What changes is where the islands go when there's a piece.

This section applies only if you keep writing templates — one note per piece type, each with named slots and the question that fills each slot — e.g. in `Resources/Writing Templates/`, and assemble pieces from them (by hand, or with a separate drafting/assembly tool of your choice).

**1. Offer the assembly, in one line.** When the user says "I want to publish this" or "assemble it", or when there are 3 or more islands on the same thing: *"Shall I assemble it with a template?"*. The user decides. If yes, pass to the assembly step the list of islands (wikilinks with the full title) and whatever the user said about channel or form.

**2. The assembly step picks the template and announces it.** From then on the template is active in the session.

**3. When the assembly step reports an empty slot,** this skill asks the question. It is the slot's question in the template, adapted to what the user has already written, and it is still a single question per turn. The answer is saved as an island with two extra frontmatter fields:

```yaml
template: "Story essay"
slot: "Honest result"
```

and goes back to the assembly step, which keeps assembling.

**4. With an active template, step 4 of the gesture changes source.** The question with a perspective comes from the heaviest empty slot, not from a free angle. If no empty slot remains, go back to the normal step 4.

**What does not change:** the prose guardrail, verbatim saving and one-note grounding. The slot question asks the user for material; it never suggests the answer or drafts it.

---

## What this skill NO LONGER does (vs. v2.2)

- Doesn't require a manuscript or core idea before the first island.
- Doesn't have a "map check" step before writing.
- Doesn't do 5-8 note grounding or pick mentors by default: 1 note, the one that contradicts, and only after saving.
- Doesn't offer a perspective menu (story/argument/reflection).
- Doesn't classify the island's relationship to the core idea at the moment of writing it.

## What this skill still doesn't do (same as v2.2)

- Doesn't generate drafts. Assembly works with the user's verbatim islands and only adds marked transitions. If the user says "you write it", the answer is a question, not prose.
- Doesn't reword the user's islands into "better" prose.
- Doesn't chain to anything automatically: it offers the assembly in one line (see "Assembling with templates"), and the user decides.

---

## Relationship with the system

Layer 3 of Islands & Bridges. Since v3.2, assembly happens through templates (e.g. `Resources/Writing Templates/`). Islands are born here, in the careo (`open-brain-extract` v10.11+, answers >~80 words), or in the `Your extension` section of a Literature Note (linked island Fleeting). `$OPEN_BRAIN_ENGINES/engine/archipelago.py` groups orphan islands weekly by LN/domain/search term/autolink and proposes at most 2 groups; if one fits, the user writes the core idea and that opens the manuscript — never this skill.

---

## Example

> **User**: "For three months I've been thinking that my team's problem isn't that they don't measure, it's that they measure what's easy to measure instead of what matters."
>
> **AI** (saves the orphan island, looks for a contradiction, finds none clear, asks): "If tomorrow you had to back that sentence with a concrete case of your own, not in the abstract, which one would it be?"

> **User**: "I want to work on M4"
>
> **AI**: "M4 has 2 islands: the hook one and the one with the consulting-study evidence. According to the map, the contradiction island is missing — something pushing in the opposite direction. Will you write something?"

> **User**: "I want to publish this" (with three islands about agents failing in production)
>
> **AI**: "Shall I assemble it with a template?" · User: "yes" · Assembly step: "Template: Story essay · 600-word ceiling · because it's for a social post, first person, with a process told. The Scene slot is empty." · **AI**: "At what concrete moment did you see a chain of agents fail, and what did someone there say, in their own words?"
