# Step 10 — full Retrieval Log schema

> The entry template field by field, the self-healing header, and the rules that govern it: full title in every wikilink, Tarea/Juicio/Artefacto, Level A and Level B outcome inference, term attribution, tokens served and reformulation detection. Read BEFORE writing the entry, always.
>
> **Field names are identifiers.** The log's field names and several values are Spanish because `log_entry.py` and the log parser read them verbatim; keep them exactly as written. Glosses: `Expansión` = expansion · `Dominio detectado` = detected domain · `Notas devueltas` = notes returned · `Design References devueltas` = design references returned · `Notas usadas sustantivamente` = notes used substantively · `Motor determinista` = deterministic engine · `Términos que matchearon` = terms that matched · `Gaps detectados` = gaps detected · `Tarea` = task · `Juicio que no estaba en el vault` = judgment that was not in the vault · `Artefacto producido` = artifact produced · `Estado: abierta` = status: open · `ninguno` = none · `no disponible` = not available · `título` = title · `motor` = engine.

---

## How it is written: open at the start, close at the end

The entry **is not typed**: `log_entry.py` opens it in Step 0.1, before searching, and it is closed here. The schema below is still the contract — what changes is who writes the characters and when.

```bash
# Step 0.1, before searching anything. Returns an id.
python3 "$OPEN_BRAIN_ENGINES/retrieval-eval/log_entry.py" open --query "<literal query>" --origen "<client>"

# Step 10, at the end. Same id.
python3 "$OPEN_BRAIN_ENGINES/retrieval-eval/log_entry.py" close --id <id> --json fields.json
```

The 17 schema fields, with their flag: `--expansion` Expansión · `--dominio` Dominio detectado · `--track` Track · `--returned` Notas devueltas · `--refs` Design References devueltas · `--used` Notas usadas sustantivamente · `--modo` Output mode · `--prefiltro` Candidates pre-filtered · `--motor` Motor determinista · `--terminos` Términos que matchearon · `--tokens` Tokens served (est.) · `--outcome` Outcome · `--reform` Reformulation? · `--gaps` Gaps detectados · `--tarea` Tarea · `--juicio` Juicio que no estaba en el vault · `--artefacto` Artefacto producido. The same name works as the key in `--json`. `--intent` corrects the header's intent, which Step 0.1 leaves as `pending`.

Three things the command does that were forgotten by hand: it counts the wikilinks in the three lists and writes the `(N)`, fills `Gaps` / `Juicio` / `Artefacto producido` with `ninguno` when they are not passed, and adds a `Campos no registrados` ("fields not recorded") line with whatever is missing — `Design References devueltas` does not count as missing if the track is not visual. An entry that is opened and never closed **stays in the log** marked `**Estado**: abierta`: it is the only proof of a retrieval that started and was not recorded. `python3 "$OPEN_BRAIN_ENGINES/retrieval-eval/log_entry.py" coverage --days 30` reports open vs closed.

Writing the entry by hand is valid **only** if `open` failed and there is no `id`. In that case, this is the template.

---

## Step 10: Write to Retrieval Log (mandatory)

Before closing the response, append one entry to `Resources/Retrieval Log.md`. This is non-negotiable — every invocation produces exactly one log entry, even in Serendipity mode, even if retrieval failed.

Self-healing fallback: if `Resources/Retrieval Log.md` does not exist, create it with the header below and then append the first entry.

```markdown
---
type: meta
title: Retrieval Log
purpose: "Append-only log of open-brain-retrieve invocations."
created: YYYY-MM-DD
policy: "Append-only. Prune to Retrieval Log - YYYY.md after 180 days. Never delete."
schema_version: "5.3"
---

# Retrieval Log
---
```

### Entry schema

```markdown
## YYYY-MM-DD HH:MM — [intent: Operative|Exploratory|Critical|Expressive|Serendipity|Visual|implicit]

**Query**: "literal query text"
**Expansión**: term term term ...  <!-- mandatory: 8-15 words of the vault's vocabulary, passed to --expand in Step 4.7; NOT `Términos que matchearon`, which is attribution afterwards. If the user corrected the anchor in step 0.9, the correction goes here tagged `(user correction)`. Step 0.8 always asks before searching — tag `(confirmed as is)`, `(user's terms)`, or `(unconfirmed — non-interactive session)` if the fallback applied -->
**Dominio detectado**: [Domain name | cross-domain | none]
**Track**: text | visual | text+visual
**Notas devueltas** (N): [[full note title]], [[full note title]], ...  <!-- full title, byte for byte the file name without `.md`; never abbreviated or with «…» -->
**Design References devueltas** (N): [[full REF/PAT title]], ... (only if Track includes visual)
**Notas usadas sustantivamente** (M): [[full note title]] — one-line gloss · [[full note title]] — gloss  <!-- full title here too; what gets shortened is the gloss after the dash, never what is inside the brackets. Myelination pairs are derived from this list -->
**Output mode**: notes | guidance
**Candidates pre-filtered**: N → K (+ H hop, + E motor)  <!-- grep candidates → notes whose full body was read; H added by graph hop, E by the deterministic engine -->
**Motor determinista**: E candidatas nuevas / N devueltas · índice de X días | no disponible: <reason>  <!-- Step 4.7: "E new candidates / N returned · index X days old". "no disponible" is a valid value, omitting the field is not -->
**Términos que matchearon**: term → [[note]], description: "fragment" → [[note]], ninguno (hop) → [[note]], ninguno (motor) → [[note]]  <!-- which hook produced each hit: literal term, description probe, title, hop or deterministic engine; never unattributed -->
**Tokens served (est.)**: ~N  <!-- sum of characters of note bodies loaded into context / 4; in guidance mode, tokens of the guidance served -->
**Outcome**: success | partial | failure
**Reformulation?**: no | yes → links to prior failed query in same session
**Gaps detectados**: [brief description, or "ninguno"]
**Tarea**: challenge | eval | plan-decisión | estimación | explicar | escribir | otro  <!-- one value; the task the retrieval serves, not the retrieval mode in the header. Glosses: plan-decisión = plan/decision, estimación = estimate, explicar = explain, escribir = write, otro = other -->
**Juicio que no estaba en el vault**: [1-2 lines with what the user decided or asserted that no returned note said | "ninguno"]
**Artefacto producido**: [[path or title]] | ninguno  <!-- mandatory; "ninguno" is a valid value, omitting it is not -->

---
```

### Full title in every wikilink (mandatory)

Every wikilink written into the Retrieval Log carries the note's **complete title**, exactly as the filename reads without `.md`. No abbreviation, no ellipsis, no leading fragment. This applies to `Notas devueltas`, `Notas usadas sustantivamente`, `Design References devueltas`, `Términos que matchearon`, `Artefacto producido` and `Gaps detectados` alike — every field, not only the first one where the note appears.

Why the rule exists. In a measured log, roughly a quarter of the wikilinks resolved to no note in the vault, and dozens were truncated with «…» or `...`. The truncation was not a transcription slip — it was systematic: the schema said `[[link]]`, so the same note was written in full under `Notas devueltas` and shortened under `Notas usadas sustantivamente`, where the gloss made the long title feel redundant. The log is the only index of what the vault served; a truncated title is an entry that cannot be read back. It breaks the `times_retrieved` audit, the reformulation scan, the missing-note check of Step 0.5 and every retrospective count of what was actually used.

Rules that keep it honest:

- **The gloss is where you compress, the brackets are not.** Write `[[<the complete, long note title exactly as the file is named>]] (tr 4→5) — the threshold rule`, never `[[<the first words of the title>…]]`. The cost is tokens in one field; the alternative is an unreadable row forever.
- **Never invent or reconstruct a title from memory.** Copy it from the filename or the frontmatter `title` of the note actually read in this retrieval. A plausible title that does not exist as a file is the same defect as a truncated one, and harder to spot.
- **A wikilink containing `…`, `...`, or a trailing `—` is malformed.** Before appending the entry, scan it for those three and fix them; if a title genuinely ends in an ellipsis, use the piped form `[[real title|alias]]` so the identifier stays whole.
- **A note whose title changed since a previous entry is not retro-edited.** The log is append-only. Write the current title in the new entry and, if the old entry matters, name both in `Gaps detectados`.

Falsifiable prediction: with this rule in force, the count of truncated log wikilinks stops growing. Measure it with `grep -ocE '\[\[[^]]*(…|\.\.\.)[^]]*\]\]' "Resources/Retrieval Log.md"` (a pattern matching only `…` misses the three-dot variant). If a new one appears in the next 30 entries, the rule is being skipped and the fix is a pre-append lint, not more prose here.

### Task, new judgment and artifact (mandatory)

Three fields close three gaps:

- **`Tarea`** takes one value from the closed list. It is not the intent of the header (Operative, Critical…): that is *how* the vault was searched; this is *what for*. Closed vocabulary because per-task analysis otherwise has to infer the task from query keywords. Do not invent values; `otro` exists for that.
- **`Juicio que no estaba en el vault`** is the one line that turns the log from a record of what came out into a record of what should go back in. Write what the user decided, ruled out or asserted in this session that no returned note said. If the vault already said it all, write `ninguno` — that is also information. Never fill it with the assistant's own reasoning: if the judgment is not the user's, it does not go here. `open-brain-review` and the Case pipeline read this field first.
- **`Artefacto producido`** names the output the retrieval fed (a document, a decision recorded elsewhere, a message, a Case, a skill patch) or says `ninguno`. Mandatory so the log can be joined with the output ledger (`engine/output_ledger.py`); a retrieval that produced nothing is a valid row, an entry without the field is not.

### Inferring outcome

- **Level A (automatic, all modes)**: **`success`**: ≥1 note from `Notas devueltas` was cited substantively in the response. For the visual track: ≥1 design reference surfaced with image or application. **`partial`**: ≥1 note cited BUT supplemented with content not in the returned notes. For the visual track: design references found but no image anchor available. **`failure`**: NO notes from `Notas devueltas` were cited in the final response. Inference is auto-applied silently — the user is not asked to confirm this level.

- **Level B (Critical and Expressive modes only)**: at the end of the response, append: *"Retrieval balance: I used [[X]], [[Y]]. Anything missing? (enter = ok)"*. The user's reply overrides the Level A outcome and populates a `missing:` field in the log entry if they name a note that should have surfaced. An empty reply or "ok" confirms Level A's inference. Scoped to Critical/Expressive only (the retrievals that feed a decision or a manuscript) — Operative/Exploratory/Serendipity/Visual keep Level A only, per the same precision-over-recall principle applied to guidance mode.

### Registering which term produced each hit (mandatory)

For every note in `Notas devueltas`, name the hook that surfaced it: the `search_term` that matched, the title match, the `description` probe, the graph hop or the engine. One entry per note, in the `Términos que matchearon` field, using the term's literal string and the note's wikilink.

Why this field exists, and why it is not optional. Vaults accumulate many distinct search terms; most have no page in `Search Terms/` and appear in exactly one note. They were written as recall hooks — the odd angle from which someone might ask for that one note. Whether they work cannot be checked from usage counters alone: notes with and without such free singletons can retrieve at the same rate. That is not evidence the hooks are useless; it is evidence the instrument is missing. A log that records which notes came back but never what made them come back makes both "prune the singletons" and "keep them, they're the rare recall" unfalsifiable.

Rules that keep the field honest:

- **A note whose hit came from the hop, the title or the deterministic engine gets `ninguno (hop)` / `ninguno (título)` / `ninguno (motor)`; a hit from the intent probe over `description:` gets `description: "fragment that matched"`.** An unattributed hit filed under a term is worse than no data: it credits the vocabulary layer with recall it did not produce.
- **The term is written as it appears in the frontmatter**, not normalized — the whole point is to tell `cognitive load` from `Cognitive Load` (or a term from its translation).
- **If two terms matched the same note, both are listed.** This is what will eventually say whether the free term added anything the hub did not.

At 30 days this field answers one question with data: how many hits each free term produced versus each hub. At 60 days with zero hits, the singletons stop being a design decision and become a measured cost.

### Estimating tokens served

`Tokens served` makes the serve-everything liability visible (retrieval cost is the cost that scales with the store). Estimate: total characters of note bodies actually loaded into context during this retrieval ÷ 4. In guidance mode, count the synthesized guidance instead — that is what the consumer paid for. No precision needed; the trend over time is the signal. `open-brain-eval` reads this field to chart cost per query.

### Detecting reformulation

Before writing, scan the last 5 entries filtered by today's date. If any has a semantically similar query AND outcome `failure` or `partial`, mark: `**Reformulation?**: yes → see entry [HH:MM] above`

---
