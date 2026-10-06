---
name: "open-brain-retrieve"
description: 'Retrieves notes from the vault to answer knowledge questions, find related notes, discover cross-domain connections and pull visual design references. Two tracks that can run at once: text (what you know about an idea) and visual (what form or pattern can represent it). Logs every invocation in the Retrieval Log, increments usage counters and reinforces the graph through myelination. Triggers: what do I know about, search my vault, what notes do I have, find notes, retrieve notes, act as a designer and retrieve, open-brain retrieve.'
metadata:
  description_long: 'Navigates an Open Brain vault of Permanent Notes and Literature Notes in six modes — Operative, Exploratory, Critical, Expressive, Serendipity, Visual — and reinforces the paths it uses (myelination). Part of the Open Brain knowledge OS.'
  version: "9.23.0"
  status: canonical
  changelog: references/CHANGELOG.md
  requires_engine:
  - log_entry.py
  - eval_retrieval.py
  - myelinate.py
  - graph_hop.py
  - health_check.py
  - output_ledger.py
  - query.py
  consumes:
  - "A question about knowledge, connections, provenance, a domain, staleness, serendipity or visual design against the vault"
  - "The current state of the Hot Cache and the Retrieval/Session Log"
  produces:
  - "A synthesized, cited answer (notes or guidance mode) over PN/LN/PAT/REF"
  - "A mandatory Retrieval Log entry and its myelination traversals"
  - "Updated times_retrieved/last_retrieved counters on the notes used"
---

# Open Brain — Retrieve

Navigates the vault to answer knowledge questions, trace where an idea came from and discover cross-domain connections. You always enter through an indexed entry point, never by browsing folders, and every invocation ends with an entry in the Retrieval Log. **Two tracks**: text (what the vault knows about an idea) and visual (what form can represent it); they share the entry flow — Hot Cache → intent → log — and diverge in scope, rerank and output.

**Paths.** Vault paths are relative to `$OPEN_BRAIN_VAULT`. Engine scripts live under `$OPEN_BRAIN_ENGINES` (e.g. `$OPEN_BRAIN_ENGINES/retrieval-eval/log_entry.py`). **Identifiers.** The Retrieval Log field names (`Expansión`, `Notas devueltas`, `Notas usadas sustantivamente`, `Motor determinista`, `Términos que matchearon`, `Gaps detectados`, `Tarea`, `Juicio que no estaba en el vault`, `Artefacto producido`…), the engine's CLI flags and enum values such as `ninguno` ("none") are parsed by the engines and are kept verbatim; English glosses are given in `references/retrieval-log.md`.

**References in `references/` are loaded when a step asks for them, not before.** `entry-steps.md` if a step 0–0.9 is unclear, the Hot Cache is missing, or you need the numbers · `query-types.md` if the Query Type is not 1 · `visual.md` whenever rule 6 fires · `attempt-first.md` with Query Type 9 · `reconstruction-loop.md` if the first pass returns little · `engine-and-sidecar.md` if the engine fails · `counters.md` if in doubt about what to increment · `guidance.md` if the consumer is another skill · **`retrieval-log.md` always, before Step 10** · `myelination.md` for which pairs get recorded · `CHANGELOG.md` for the historical why.

---

## Core Principle: Navigate, Don't Browse

In a vault with thousands of Literature Notes, browsing folders is too slow. Enter through an index: **concept** `Search Terms/[[X]].md` → backlinks · **domain** `Domains/[[X]].md` → competency map → PNs · **source** `Resources/Source Index.md` → `ln_prefix` → `ls "Literature Notes/" | grep "^PREFIX"` · **author** `Mentors/[[X]].md` → backlinks · **manuscript** `Manuscripts/Active Manuscripts.md` → feeder PNs · **visual pattern** `Design References/` by `pattern_family`, `visual_goal`, `output_targets`, `linked_pns`.

> `processed: true` on an Inbox note is NOT a coverage signal. The signal is `vault_coverage` in the Source Index.

---

## Step 0 — Hot Cache (mandatory)

Read `Resources/Hot Cache.md` and `Resources/Hot Cache - Active Context.md` before classifying. Pull out five things: **last session focus** · **changes in the last 72 h** (surface them, they match more often) · **active threads** (if the query resolves one, say so) · **`[!stale]` callouts** (warn before the user acts on outdated knowledge) · **the session's random note**, if your Hot Cache generator writes one (mention it once, briefly, without forcing it: it is offered serendipity, not an obligation to use it).

**The Hot Cache is a hint, not a boundary.** Always run at least one probe *outside* what it shows: it ranks by availability, not relevance. If the best note is one the user has never used, the Hot Cache is exactly where it will not be.

If the file does not exist, create it with the template in `references/entry-steps.md` and continue — never halt. Retrieve is READ-ONLY except for counters: it only appends to "Active threads" in Critical or Expressive mode, and only if the output changes the user's decision state.

## Step 0.1 — Open the log entry (mandatory, BEFORE searching anything)

```bash
python3 "$OPEN_BRAIN_ENGINES/retrieval-eval/log_entry.py" open --query "<the user's literal query>" --origen "<client>"
```

It returns an `id`: keep it, Step 10 needs it. If the command fails, continue the retrieval and note it under `Gaps detectados` — never halt for this.

**Why it goes here and not at the end.** A log written only *after* answering depends on someone remembering to write it, and in practice newly mandated log fields stayed empty for weeks. A record written at the end measures the memory of whoever answered, not what was asked. This line is the only trace of the query if the session is abandoned before Step 10: the entry stays **open**, dashboards can show it at its own level, and the difference between open and closed entries becomes a measured gap instead of an assumed one.

## Step 0.3 / 0.5 — Logs (conditional)

**Session Log** — if the query is scoped to one domain, read the last 3 entries of `Resources/Session Log.md` that mention it; cross-domain, skip. **Retrieval Log** — if it exists, scan the last 10 entries: same-day reformulation · **same query failed ≥2 times in 14 days** (say so: it is usually a content gap, not an indexing gap) · recent successes as a boost, never as a forced match · **a note named in `missing:` 2+ times** (say so before answering; nothing else reads that field). If it does not exist, skip silently.

## Step 0.7 — Probe discipline

Quality is set by how you search, not by how you rank afterwards. **The first good hit is a lead, not an answer.**

**Minimum**: the concept in every language your vault uses, one synonym, and one negative or failure phrasing. A multilingual vault often files the same idea in the other language. Stop when new probes stop bringing new notes, not when the first ones bring something usable.

| If the query wants… | Grep `description:` for |
|---|---|
| cautions, what breaks, what to avoid | `fail`, `anti-pattern`, `destroys`, `doesn't work`, `erodes`, `trap`, `mistake` |
| a trade-off or a choice | `vs`, `trade-off`, `when`, `criterion`, `beats`, `instead of` |
| how to do something | `how`, `method`, `step`, `protocol`, `technique`, `checklist` |
| evidence or numbers | `%`, `study`, `experiment`, `data`, `measured` |

Add the equivalents in any other language your notes are written in.

**Do not filter or rank by `features`**: measured three times, for a capable reader the tag subtracts precision. It stays in the frontmatter for batch consumers; interactive retrieval ignores it.

## Step 0.8 — Query expansion (mandatory; it is a gate, wait for the answer)

**Before searching anything, ask the user for the vault's vocabulary for this task.** Write the draft yourself — domain vocabulary you already know is in the vault, the `search_terms` and `description` of what you have seen this session, the literal claim of any PN you can name —: 8–15 terms, nouns and claim-phrases, no instruction verbs or boilerplate. Show it and **wait**.

```
I'm going to search with: judgment capture, tacit knowledge, decision log, provenance,
desirable friction, note-making, learning artifact, expert blind spot, self-written memory.
Are these the terms you would use, or do you want to change/add any?
```

Whatever comes back goes into the `Expansión` field of the log and into **every** search, tagged `(confirmed as is)` or `(user's terms)`. **Non-interactive fallback** (scheduled task): use your draft without waiting, tagged `(unconfirmed — non-interactive session)`. **Scope**: explicit invocation only — an implicit, always-on retrieve configured in your agent instructions stays silent by design.

It is the heaviest step of all and the only one whose measured improvement does not cross zero. Tables, CIs and discarded alternatives: `references/entry-steps.md`.

## Step 0.9 — Show the anchor (mandatory; NOT a gate, do not wait)

After the expansion and the first pass, and **before reading any note body**, print the 3–5 candidates you are going to build on — one line each, title plus the hook that surfaced it — and **continue without waiting**. If the user corrects you, the correction becomes the `Expansión` and the retrieval is redone.

```
Anchoring on:
  1. [[<full title of note 1>]]   (bm25, lsa)
  2. [[<full title of note 2>]]   (hop)
  3. [[<full title of note 3>]]   (meta)
If you're heading somewhere else, tell me where and I'll redo it.
```

Showing instead of asking is a measured decision: the anchor saturates at a single note, works even when it is the wrong one, and **no observable signal predicts when it is needed** — so a conditional question cannot be implemented. 0.8 asks and 0.9 does not **for different reasons**: do not cite them as the same finding. Numbers: `references/entry-steps.md`.

---

## Intent classification (always declare it: *"(Mode: operative)"*)

| Intent | Fires on | Priority order |
|---|---|---|
| **Expressive** | "publish", "post", "evergreen", "what am I writing", "what have I published" | Ideas/ → evergreen PN → growing |
| **Critical** | "contradictions", "tension", "what doesn't fit", "where do they disagree", "challenge" | All LNs on the topic (by mentor) + all PNs |
| **Exploratory** | "authors", "experts", "mentors", "original", "nuances" | LN (by mentor) → PN (contrast) → Cases |
| **Serendipity** | "odd connections", "serendipity", "what am I not seeing", "cross-domain" | Under-used LNs + orphan PNs + cross-domain bridges |
| **Visual** | stem "design", "slide", "carousel", "visual", "pattern", "visual reference", "doesn't look powerful", "form for", "asset", "interface", "UI" | Design References (PAT → REF by rerank) → linked PNs → source LNs → `Resources/Images/` |
| **Operative** | "what do I know about", "give me the key points of", "summarize" — and anything not matched above | Active manuscript → evergreen PN → growing → seed → LN (only if no PN) |

They are evaluated in that order and Operative is the default. If it is genuinely ambiguous, ask.

**Rule 6 is independent, not a fallback**: it is evaluated against every query regardless of what happened with rules 2–5, and if it matches, Visual runs as an **additional** track next to the primary intent — two separate sections, both modes declared (*"(Mode: critical + visual)"*). A Critical/Expressive/Exploratory match never suppresses it. Worked examples: `references/query-types.md`.

**Before any intent**: read `Manuscripts/Active Manuscripts.md`. If an active manuscript overlaps the topic, put it at the very top and then apply the intent's priority.

---

## The canonical flow (Query Type 1 — "what do I know about X?")

The other six text Query Types are in `references/query-types.md`, the visual one in `references/visual.md` and 9 — attempt first, opt-in — in `references/attempt-first.md`; they all share this spine.

1. Classify and declare the intent. Check active manuscripts.
2. Read `Search Terms/[X].md` if it exists — definition, aliases, related terms.
3. Gather candidates: notes with `[[X]]` in `search_terms` or in the body, plus the aliases.
4. **Graph hop** (cheap, optional): `python3 "$OPEN_BRAIN_ENGINES/autolink/graph_hop.py" --seeds "title" … --max 5 --json`. If it fails, continue.
5. **Deterministic engine (Step 4.7 — mandatory)**, before the pre-filter:
   ```bash
   python3 "$OPEN_BRAIN_ENGINES/retrieval-eval/eval_retrieval.py" retrieve "<literal query>" --expand "<the 0.8 expansion, literal>" --k 20 --json --log-id <id from Step 0.1>
   ```
   Three rules that get broken without meaning to: **pass your expansion in `--expand`** (without it the engine does RM3, which is a floor, not a substitute) · **its output is candidates, not an answer** — triage and ranking are still yours, and never cite a note whose body you did not read · **if it fails, do not halt**: `no disponible: <reason>` ("not available") in the `Motor determinista` field, note it in Gaps and continue with grep + hop. Skip it only if the user asks for speed, or in Visual mode. The rest: `references/engine-and-sidecar.md`.
6. **Sidecar (Step 4.8)**: written by the 4.7 engine when it answers (since 9.22.0). Nothing to do except pass `--log-id`. Schema: `references/engine-and-sidecar.md`.
7. **Frontmatter pre-filter (L0)**: over the union grep + hop + engine, read **only the frontmatter** (~50 tok) of each candidate, rank by relevance of `description` to the query, and read the full body **only of the top K** (4–6 typical, up to 8 in broad Critical/Exploratory). Record `Candidates pre-filtered: N → K (+ H hop, + E motor)`.
8. Order within the intent's tier: `confidence` (high→low) → `maturity` (evergreen→seed) → `times_retrieved` desc (inverted in Serendipity).
9. **Maturity is a signal, not a filter**: never hide an LN because a PN on the topic exists. Show both with their maturity and counters, and mark LNs "not yet incorporated" — they are candidates to update the PN.
10. **Synthesize, don't list**: what the vault knows and how confident it is, cited with `[[wikilinks]]`, with layer gaps flagged.
11. Increment `times_retrieved` and `last_retrieved` on every note used substantively — PN **and** LN, never in Serendipity. What counts: `references/counters.md`. **Exception**: if the query is about the system itself (challenge, audit, health, skill design), increment nothing and close the log with `--origen_uso auditoría` ("audit"); the engine records the read in `audit_retrievals`. Otherwise, `--origen_uso tarea` ("task").

If the first pass returns little, or the user asks to reconstruct where an idea came from, the three-pass iterative loop in `references/reconstruction-loop.md` applies. If the consumer is another skill, or the user asks for "guidance for", the output mode is not `notes` but `guidance`: `references/guidance.md`.

---

## Step 10 — Retrieval Log (mandatory, no exceptions)

One invocation, one entry in `Resources/Retrieval Log.md` — in Serendipity too, and even if the retrieval fails. The entry **already exists** since Step 0.1: here it is closed, not written from scratch.

```bash
python3 "$OPEN_BRAIN_ENGINES/retrieval-eval/log_entry.py" close --id <id from Step 0.1> --json <file with the fields>
```

`--json` avoids fighting the quoting of twenty wikilinks; each field also has its own flag (`--returned`, `--used`, `--expansion`, …). `close` fills only `Gaps detectados`, `Juicio que no estaba en el vault` and `Artefacto producido` with `ninguno` when they are not passed — they are mandatory with an escape value, and omitting them is how they used to disappear — and lists at the end the ones that were not recorded. If you have no `id` because Step 0.1 failed, write the entry by hand with the template in `references/retrieval-log.md`. **Read `references/retrieval-log.md` before closing it**: it has the field-by-field template, the flag names and the self-healing header.

Fields: `Query` · `Expansión` · `Dominio detectado` · `Track` · `Notas devueltas` · `Design References devueltas` (if visual) · `Notas usadas sustantivamente` · `Output mode` · `Candidates pre-filtered` · `Motor determinista` · `Términos que matchearon` · `Tokens served (est.)` · `Outcome` · `Reformulation?` · `Gaps detectados` · `Tarea` · `Juicio que no estaba en el vault` · `Artefacto producido`.

The four rules most often broken:

- **Full title in every wikilink.** The complete title inside the brackets, byte for byte the file name; you shorten the gloss after the dash, never what is inside. A wikilink with `…`, `...` or a trailing dash is malformed — and a truncated title is an entry that can no longer be read back.
- **`Términos que matchearon`** (terms that matched): name the hook of every returned note. `ninguno (hop)`, `ninguno (título)`, `ninguno (motor)` and `description: "fragment"` are valid values; an unattributed hit is not.
- **`Tarea` / `Juicio` / `Artefacto producido`**: `Tarea` (task) is what the retrieval was for, not how it searched (closed vocabulary; `otro` — "other" — exists for that). `Juicio` (judgment not in the vault) is what the user decided that no note said — never the assistant's reasoning. In all three, `ninguno` is a valid value; omitting the field is not.
- **Outcome Level B**, only in Critical and Expressive: close with *"Retrieval balance: I used [[X]], [[Y]]. Anything missing? (enter = ok)"*. The answer overrides the automatic inference and fills `missing:`.

## Step 11 — Myelination (automatic since 9.22.0)

`log_entry.py close` records it in Step 10 from the `Notas usadas sustantivamente` field: every pair of notes used together is a traversal — in every mode, Serendipity included; audit-origin queries (`--origen_uso auditoría`) are not myelinated. Your only job is to **list there every note you used**. When this was a manual step, traversals simply went unrecorded. Retrieve never runs `myelinate.py apply`. If the close warns that myelination failed, note it in Gaps and continue. Detail: `references/myelination.md`.

## Closing — manuscript ritual (Phase 12)

If PNs were used substantively, before finishing: read `Manuscripts/Active Manuscripts.md` and ask *"You used the PNs [list]. Does any of them feed a post idea in Ideas/?"*. If 3 PNs from the same cluster accumulate `times_retrieved ≥ 3`, propose opening a manuscript. Forced Promotion and the dormancy signal: `references/counters.md`.

---

## Formatting

Declare the intent at the start · lead with synthesis, not lists · cite with `[[wikilinks]]` · mention confidence, maturity and counters of the key notes · show LNs next to PNs · in visual results always include the embed, the reusable rule and a concrete application · flag gaps · close with the manuscript hook.

## What NOT To Do

- **Do not write anything to the vault** except the retrieval-loop counters. No new notes, no edits, no moves.
- **Do not touch `external_outputs`, `internal_outputs` or `maturity` by hand**: they are derived. If a retrieval fed a deliverable, what's needed is to get the deliverable into the output ledger (if you keep one).
- **Do not increment `times_retrieved`** in Serendipity, or on PNs that only came out through Visual `linked_pns` without being cited in the synthesis.
- **Do not skip** intent classification · Step 4.7 in a substantive retrieval (nor treat its rows as an answer) · 4.8 when 4.7 went well · Step 10 · Step 11 · the Forced Promotion reminder · the Level B line in Critical/Expressive. If the log cannot be written, say so out loud instead of skipping it silently.
- **Do not halt** on a failure of the engine or the myelination script: `no disponible: <reason>`, Gaps, and continue.
- **Do not browse folders at random**, do not present raw lists without synthesis, do not hide an LN because a PN on the topic exists.
- **Do not return visual results** without at least one image embed or an explicit `visual_status: needs_assets`.
- **Do not propose** moving anything to `Permanent Notes/Dormant/` or `Literature Notes/Archived/`: neither exists as a convention. And do not trust `processed: true` as a coverage signal.
