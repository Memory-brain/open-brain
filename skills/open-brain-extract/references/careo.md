# Step 11 — Careo

> The full Careo ("cross-examination"): why it exists, the golden rule of concrete stimulus, preparation by mining first, the mandatory alias citation format, the label-resolution gate, the three questions, verbatim capture with its template, orphan islands, the bets ledger, the closing thermometer and unattended mode. Read it every time before formulating the Careo.
>
> Identifiers kept in Spanish because other skills and engines parse them: the `Resources/Careo/` folder, `origin: careo`, `type: careo-pendiente`, the `Careo — …` and `Pendiente — …` ("pending") file names, and `apuestas.jsonl` ("bets").

---

## Step 11: Careo (MANDATORY — after the report, before closing)

**Why it exists**: extraction produces notes; the Careo produces judgment. The elaborative-encoding gate (an empty `Your extension`) is passive — it waits for the user to come back, and in practice they rarely do. The Careo is the active version of that gate: at the moment of maximum context (source just extracted, fresh convergences, active projects in mind), Claude prepares the stimulus and the user produces the verdict. It is the **inverse of gotcha G5**: Claude NEVER answers the questions — it only loads them with concrete material.

**Golden rule — concrete stimulus, with names.** "Which note contradicts you?" is weak: it invites a "hmm, several". "The note from {source} holds that {claim in one sentence}; your permanent note that {opposite claim in one sentence} defends the opposite, and in {active project} you do the latter. Who wins?" cannot be dodged. Each question must cite LNs, PNs, vault practices or concrete projects with wikilinks — **and say what each cited thing asserts**. The wikilink is the address; the claim is the content. A Careo with addresses and no content is as useless as a generic one.

### Preparation (internal, before asking)

1. The raw material is already in context: the Step 5 convergences, the Step 7 enumeration, the Step 8 tier. Don't re-read the source.
2. Read the vault's list of active projects (`Projects/` folders with active status, or the equivalent index). If there's no clear index, ask the user once which projects are active and use their answer.
3. **Mine before asking.** Before formulating P1/P2/P3, search `Resources/Session Log.md` and any session or decision log you keep (e.g. a Hot Cache file) for whether the clash you're about to raise **already has a dated decision**. A grep for the two or three central terms of the clash is enough; don't read the files whole.
   - If found: cite the decision in the question — "on YYYY-MM-DD you decided X; this source says Y" — instead of asking from scratch. A Careo that makes the user answer the same thing twice stops being answered.
   - If not found: say so in one line when opening the Careo ("I searched the log and there was nothing previous on this"). A declared absence counts; a silent absence is indistinguishable from not having searched.
   - Why these files and not `git log`: in a personal vault the history usually lives in the session or decision logs, not in commits.
4. Load the three questions below. Maximum 3 per extraction — target: under 5 minutes of the user's time. A long Careo is a Careo that stops being answered.

### How to cite a note (mandatory format)

Most Literature Notes carry a code prefix in the filename, and filenames are long. Since in Obsidian the wikilink *is* the filename, both obvious options are bad: the full wikilink turns the question into a wall of text, and the bare prefix makes it unreadable. The right answer is the alias:

```
[[ABC-05 - Fluent narratives mask fragile causal processes|fluent narratives mask fragile causal processes]]
```

The claim comes from the note's `description` field, which is written exactly for this (`description` as a claim). Two cases break the shortcut: if the `description` is cut off mid-sentence (in some notes it is a mechanical cut of the body's first line), or if the note has no `description` — then write the claim in prose in your own words and put the wikilink at the end. **Never invent the claim**: if you can't read it from the note, open it.

The same applies to everything else you cite: a Hot Cache thread, a rule from your agent instructions file, a section of a playbook, a bet from the ledger. The identifier is the address; the claim is the content.

### Label-resolution gate (condition for showing the Careo)

**Do not show the Careo if any of the three questions cites a note, thread, principle or section without saying what it asserts.** This is not a style warning or an optional re-read: it is the publishing condition. The Careo is consumed in chat, which is not searchable and gets quoted out of context — the worst possible place for a label without content, where every reused label is serious unless it carries its content alongside every time.

If you decide to show it anyway, log one line in the Careo fleeting note: `Label gate skipped — reason: {what happened}`. Without that log the gate is ignored silently, and the times it's skipped on purpose are exactly the ones that would tell whether it's miscalibrated.

**Why a gate and not a self-check**: an earlier version said "re-read the questions as if you knew nothing about the vault". That was self-reporting — only the agent itself could declare it fulfilled — and it did not stop bare-code citations from slipping through.

### The three questions (one at a time — wait for each answer before launching the next)

**No slot stays "pending".** Each of the three ends in one of two things: formulated, or declared omitted with its reason in one line. A slot shown empty and abandoned meets the letter of "don't skip silently" and fails its purpose. And with the user absent, **P3 is not formulated**: a bet nobody answers enters the ledger with `status: open`, and nothing reads that ledger yet.

**P1 — The clash** (always). Pick THE strongest tension in the batch: new LN vs existing PN, vs a documented vault practice, or vs how something is done today in an active project. Phrase it as a cross-examination with wikilinks and ask for a verdict ("who wins and why?", "do you keep your practice or change it?"). If there's no real tension, say so explicitly ("No clash in this batch — the source confirms more than it contradicts") and move to P2. **Never invent tension to fill the slot** — same principle as Step 7's "never create a note to fill a slot".

**P2 — The steal** (conditional — only if the source describes processes, metrics or ways of evaluating). Nominate 2–3 concrete "they do this and you don't" candidates, each mapped to an active project or to the vault system itself. The user picks one or rejects them with a reason — **rejecting with a reason is also thinking, and is also recorded**. If the source is purely conceptual (theory, visual design, narrative), omit P2 and say why.

**P3 — The bet** (whenever the user is present). One dated action in an active project + what evidence will count as "it worked". Format: action / project / deadline / expected evidence. If the user decides not to bet on this source, record "no bet" with their reason — the absence of a row is also a signal for the 30-day review.

### Capture — verbatim, never polished

**One fleeting note per Careo** (one per extraction, not one per question): `Fleeting Notes/Careo — {source-slug} — YYYY-MM-DD.md`. The user's answers are transcribed **verbatim**: their syntax, their verbal tics, without correcting grammar, rephrasing or summarizing. Polishing kills the voice and the thinking. Claude may only add wikilinks in a `[!claude] Context` callout at the end of the note — never inside the user's text.

```yaml
---
type: fleeting
origin: careo
source: "[[Source Title]]"
lns_touched:
  - "[[LN cited in P1]]"
project: "[[Project of the bet]]"   # omit if there was no bet
created: YYYY-MM-DD
---

## P1 — The clash
> [the question exactly as formulated, with its wikilinks]

[the user's answer, verbatim]

## P2 — The steal
> [question / nominated candidates — or "omitted: source has no processes/metrics"]

[the user's answer, verbatim — choice or rejection with reason]

## P3 — The bet
> [question]

[the user's answer, verbatim — or "no bet: {reason}"]

> [!claude] Context
> - Connects with [[X]] / [[Y]] (wikilinks + one line only, outside the user's text)
```

**Propagation to `Your extension`**: if a verdict clearly extends a specific LN, copy the text verbatim (prefixed with the date) into its `## Your extension` section and set `voice_state: extended-by-owner`. This unlocks promotion to PN — the Careo is now the main path through which that gate opens. If in doubt about which LN it belongs to, leave only the fleeting note — don't force the mapping.

**"Your extension" is an island — wired, not just mentioned.** In the same step in which text is written into an LN's `## Your extension` (by Careo propagation, above), ALSO create `Fleeting Notes/Island — {LN-slug} — extension — YYYY-MM-DD.md`:

```yaml
---
type: fleeting
island: true
origin: extension
lns_touched:
  - "[[Extended LN]]"
created: YYYY-MM-DD
---
```

Body: the same verbatim text copied into `Your extension`, without the date prefix or any callout. Before creating it, check there isn't already a Fleeting with `origin: extension` and that same LN in `lns_touched` (avoids duplicates if the Careo touches the same LN again). This is the write path for extensions filled DURING a Careo. Extensions the user fills directly in Obsidian, outside any skill, don't go through here — for those there is `$OPEN_BRAIN_ENGINES/engine/extension_islands.py`, which periodically sweeps LNs with a real `Your extension` (not the placeholder comment) and no island Fleeting yet, and creates them in the same format. Both paths write the same kind of Fleeting; there is no third version to maintain.

**Bets ledger**: if P3 produced a bet, append (never rewrite) one line to `Resources/Careo/apuestas.jsonl`:

```json
{"date": "YYYY-MM-DD", "source": "source-slug", "project": "Project", "action": "...", "deadline": "YYYY-MM-DD", "evidence": "...", "lns": ["LN-XX"], "status": "open"}
```

Create the file (and the `Resources/Careo/` folder) if it doesn't exist.

### Orphan islands — the Careo also produces writing material

Any answer from the user to P1, P2 or P3 longer than **~80 words** is ALSO saved as its own Fleeting: `Fleeting Notes/Island — {source-slug} — YYYY-MM-DD.md`.

```yaml
---
type: fleeting
island: true
origin: careo
source: "[[Source Title]]"
lns_touched:
  - "[[LN cited in the answer]]"
created: YYYY-MM-DD
---
```

Body: the user's text, verbatim, without the question and without any `[!claude]` callout — it is island material for `open-brain-escribir`, not a Careo record. The threshold is not forced: a short answer (most of them) stays only in the Careo fleeting. If more than one answer in the same Careo exceeds the threshold, each is its own island.

**`Resources/Chat Sessions/`** — if the user's reasoning in this extraction's conversation (outside the three Careo answers: discussion of the clash, doubts about the steal, context for the bet) adds up to more than ~150 of their words, save the full exchange verbatim in `Resources/Chat Sessions/{source-slug} — YYYY-MM-DD.md` before closing. It is the longest source of islands, which P1–P3 don't capture because the Careo condenses everything into three closed questions.

**What this does NOT do yet (on purpose — same pattern as `source_hash`)**: this is only the write side. The read side — a 30-day check that flags overdue `open` bets and dead extractions (a batch 30+ days old with 0 retrievals, 0 outputs and an empty `Your extension` in all its LNs) — **is not implemented yet**. That is where the condition for redesigning the workflow lives: not asked per extraction, but measured per batch against `times_retrieved`, any output ledger you keep and this bets ledger. Until it exists, the ledger accumulates without anything reading it; that is correct, not a bug.

### Closing — thermometer before handoff

Before offering any handoff, count the **open** entries in `Resources/Review Queue.md` — those without a closing mark (`RESOLVED`, `APPLIED`, `DEFERRED`, `VERDICT`, `OWNER ONLY`).

- **20 or fewer open**: if P1 produced a juicy verdict, close with ONE line — *"This is a post — shall I send it to `open-brain-escribir`?"*. Never chain automatically (same principle as convergences, G7). A verdict turned into output is the cheapest way to close the judgment → output loop.
- **More than 20 open**: **don't offer to queue anything.** State how many there are and the date of the oldest unresolved one, and offer the only thing that moves the needle: *"N open in the Review Queue, the oldest from {date} — shall we clear it before adding?"*.

**Why**: a queue that only ever receives and is rarely emptied turns every "shall I queue this?" into a formality, and the user ends up giving the same answer every time. The threshold turns the step into a measurement rather than a ritual.

### Unattended mode (batch, scheduled, user absent or not answering)

The Careo is NEVER answered alone and NEVER skipped silently. If the user is not present or doesn't answer:

1. Write `Resources/Careo/Pendiente — {source-slug}.md` with the 3 questions already loaded (wikilinks, steal candidates, everything ready to answer cold) and frontmatter `{type: careo-pendiente, source, created}`.
2. Report it at closing: "Careo queued — awaiting answers".
3. If your agent reads a session-start file such as `Resources/Hot Cache.md`, add a line to its pending-threads block pointing at the queued Careo (source + date + path to the Pendiente file) — that is what guarantees the queued Careo is seen, since nothing else reads `Resources/Careo/Pendiente — *.md` on its own. Otherwise report the queued Careo only at closing. Once answered, the capture is processed exactly the same way (fleeting note, Your extension, ledger), the Pendiente file is marked `resolved: YYYY-MM-DD` and, if you added one, that line is removed from the session-start file.

---
