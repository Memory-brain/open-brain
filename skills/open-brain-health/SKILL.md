---
name: open-brain-health
description: >
  The vault's immune system. The mechanical checks (orphans, stale, inbox, maturity,
  frontmatter, broken links, count drift, ghosts, crowding, stale claims, connector
  verb diversity, log bloat, pipeline compression, skill_sequence adoption) are run by
  health-engine/health_check.py — no LLM. The AI prioritizes, writes the report and resolves
  the judgment checks.
  Triggers: health check, review my vault, orphan notes, duplicates, open-brain health
metadata:
  version: "2.5.0"

---

# Open Brain — Health (v2, deterministic engine)

The checks are split: most are mechanical scans of the filesystem/frontmatter
and are run by `$OPEN_BRAIN_ENGINES/health-engine/health_check.py`. Your job as the AI:
**prioritize the findings, write the report, and resolve the 4-5 judgment checks**.

Model: **the assistant orchestrates · the script executes · any UI you use consumes findings.json.**

## Phase 1 — run the engine (script, no thinking needed)

```bash
python3 "$OPEN_BRAIN_ENGINES/health-engine/health_check.py" run
```

Runs the mechanical checks over the whole vault (a few seconds for a few thousand notes) and writes
`Resources/Vault Health/findings.json`. Accepts `--check 1,3,6` for a subset,
`--json` to dump the raw JSON, and `--stdout-only` to print the JSON without rewriting
`findings.json`. `python3 "$OPEN_BRAIN_ENGINES/health-engine/health_check.py" self-test`
runs the engine against a deliberately broken and a clean fixture vault (checks 36-42).
The engine needs the `vault-scan` engine installed next to it. It autodetects the vault; if that
fails, set `OPEN_BRAIN_VAULT` (or `VAULT_ROOT`) to the vault root.

Checks the engine runs (the registry is `CHECKS` in `health_check.py`; it is the source of truth):

| Group | Checks |
|---|---|
| Notes | 1 orphan PNs · 3 stale knowledge · 5 unprocessed inbox · 6 maturity drift · 7 frontmatter · 8 broken links (PNs) · 9 low-confidence pillars · 17 stale claims · 22 frontmatter YAML integrity · 23 vault-wide orphans · 30 source drift (LN vs cache) |
| Graph & vocabulary | 4 function coverage by domain · 12 contradiction scan (declared tensions from `autolink/graph.jsonl`) · 16 search-term crowding · 21 connector verb diversity · 24 search terms without wikilink · 28 term over-application · 42 vocabulary drift |
| Sources & mentors | 11 count drift (Dossiers) · 31 LNs without mentor · 32 undistilled mentors · 36 PN provenance (resolved `sources:`) · 37 third-party names · 39 batch link audit · 41 endorsement as event |
| Structure & surface | 13 ghosts & archive back-links · 25 taxonomy adherence · 26 instruction surface (count + drift) · 29 engine stamp drift · 40 instruction cost by layer · 43 declared figures vs filesystem · 44 rule recurrence · 45 skill invocation payload · 46 description as claim · 47 Careo pointers |
| Pipeline (info) | 27 dormancy candidates · 33 log bloat · 34 pipeline compression benchmark · 35 skill_sequence adoption & signal · 38 prune witness log |

Each finding carries a `severity` (critical|important|maintenance|info|judgment); checks 36-42
also carry `status` (`ok` | `findings` | `not_run`) and `failure_origin`, so a `not_run` is never
read as a clean zero.

**Check 6 (maturity drift).** `maturity` is a derived field. The engine computes each PN's
maturity from its counters — `seed` (unused), `growing` (≥2 retrievals or ≥1 output),
`evergreen` (≥5 retrievals AND ≥1 published output) — and reports every PN whose declared
`maturity` differs from the derived value. It should always be 0; a non-zero count means someone
wrote the field by hand. The repair (with the vault owner's confirmation) is
`python3 "$OPEN_BRAIN_ENGINES/engine/maturity_migrate.py"` (dry-run) and then `--apply`.

**Checks that skip gracefully.** Some checks depend on files or engines a vault may not have.
They never crash the run; they report a zero with `skipped: true`, `status: not_run` or an
explanatory `detail`/`note`. Say in the report which ones were skipped — a skipped check is
not a clean one:
- 12 needs `autolink/graph.jsonl` (run `open-brain-autolink` first).
- 29 needs a baseline `health-engine/engine-stamp.json` you generate yourself.
- 31 (dangling-mentor part) and 32 need an optional `mentor-engine/mentor_metrics.py`, which is
  not shipped with Open Brain.
- 37 needs `Meta/third-party-names.txt` (one name per line; `!Full Name` lines are exceptions).
- 43 needs `OPEN_BRAIN_BINDING_RULES` pointing to a rules document whose figures it audits.
- 44 needs `Meta/Instruction Surface Log.md` and `Resources/Session Log.md`.
- 45 needs skill sources inside the vault (`.claude/skills/`).
- 47 needs `Resources/Careo/`.

Optional configuration (environment variables): `OPEN_BRAIN_INSTRUCTION_SURFACES` (extra
instruction files for check 26), `OPEN_BRAIN_ON_DEMAND_SURFACES` (on-demand files for check 40),
`OPEN_BRAIN_NON_TAXONOMY` (extra root folders check 25 treats as machinery),
`OPEN_BRAIN_ENDORSEMENT_CUTOFF` or `run --endorsement-cutoff YYYY-MM-DD` (check 41 treats PNs
created before that date as legacy backlog instead of violations; unset, it applies to every
dated PN). Lists are `;`-separated paths relative to the vault.

## Your agent instruction file — the only region this skill may touch, and what it must check

If your vault's agent instruction file (the file at the vault root that tells the assistant
how to work in this vault) delimits a regenerable region between
`<!-- BEGIN:AUTOGEN estado-derivado -->` and `<!-- END:AUTOGEN estado-derivado -->`
(`estado-derivado` = "derived state"; it is an identifier, keep it as written),
that region holds counts derived from the filesystem and nothing else.

- **Do not write to the instruction file outside those markers.** Not one line, not even to
  correct a fact you know is wrong: that is proposed to the vault owner, who decides.
  An automated rewrite outside the block is a failure, not an improvement.
- **Check the block's counts against the filesystem** when you run. If they diverge by
  more than 10%, propose updating the block — and only the block.
- `check_26` reports `claude_autogen` with the instructions inside and outside the block.
  Growth outside the block is the signal to watch; the absence of the block is a
  finding in itself. Neither authorizes deleting anything: pruning is by
  falsification and the vault owner decides it (log it in `Meta/Instruction Surface Log.md`
  if you keep one).

## Phase 2 — YOU prioritize and write (judgment)

1. Read `findings.json` (structured — do NOT scan the vault yourself).
2. Read `Resources/Hot Cache.md`: do NOT re-flag what the user just resolved; if a
   recent session was a large extraction, frame inbox/layer gaps as "post-extraction
   hygiene", not as a structural problem.
3. Compose the report grouped by severity: **Critical (now)** → low-confidence
   pillars, stale + heavily used. **Important (soon)** → orphans, maturity drift,
   red crowding, ghosts, connector verb diversity (if weak_ratio>0.6). **Maintenance**
   → inbox, frontmatter, broken links, count drift. **Skipped** → list the checks that did not
   run (see above) in one line. **Info** → 33/34/35: never
   present them as alarms; they measure the pipeline itself, not note integrity.
4. Give 3-5 concrete prioritized actions at the end (which skill to run for each gap).
5. If any finding is HIGH and actionable today, add it to the Hot Cache "Active threads".

### How to read 34 and 35 (severity: info — not a verdict)

They come from a simple idea: if public benchmarks exist for how much an external
agent-trajectory format compresses, the Open Brain pipeline deserves the same kind of
honest measurement — without assuming that "more structured" means "more token-efficient".

- **34 (Pipeline Compression Benchmark)**: compares characters/4 of each source's raw
  text (`raw_strategy: full`) against the total of the Literature Notes it produced.
  An `avg_ratio` > 1.0x means the LNs weigh MORE than the raw source — this is the
  EXPECTED result (each LN adds frontmatter, `search_context`, connectors and
  provenance per atomic insight), not an alarm. `skipped_count` are sources without a
  comparable full raw — they never silently drop out of the average.
  It does NOT decide whether the pipeline should be optimized for tokens — that is the
  vault owner's call.
- **35 (skill_sequence Adoption & Signal)**: `skill_sequence` is a relatively new field.
  If `adoption_pct` is low or `signal` shows no clear pattern across sequences,
  **that is not a failure** — not enough real time has passed for
  `times_retrieved`/outputs to accumulate. Never turn an isolated number into a verdict
  about which skill sequence "works better" — with a single session of data the only
  valid reading is descriptive.

## Phase 2b — judgment checks (the engine does NOT do these)

### Before any judgment check: quote before verdict (CCR, v2.5.0)

For the checks in this phase (12, 14, 15c, 18, 19, 20, 21 — all ask for an AI judgment, not a mechanical scan): before marking a finding, quote verbatim the exact fragment in question — the self-contradicting sentence in check 12, the literal text of the weak connector in 21, the name of the mentor without a photo in 14 — and only then decide whether it is a real finding. Asking directly "is anything wrong here?" produces more false negatives than first asking for the literal quote and judging on it (Martin & Roger, 2026, arXiv:2605.12366, §4.3): a model that fails to detect a problem when asked whether it exists can instead quote it verbatim when asked to copy it first. The token cost is minimal — it does not change the report format, only the internal order of the judgment.

- **12 Contradiction Scan**: the engine already lists the *declared* tensions — PN pairs joined by a
  `contradice`/`refuta` (contradicts/refutes) edge in `autolink/graph.jsonl` that share a search_term
  or domain. Your judgment has two jobs: (a) verify that each listed pair is a real contradiction at
  the decision level (check `domain_only` pairs first — weaker evidence), and (b) look for *undeclared*
  contradictions among PNs (maturity growing|evergreen, confidence medium|high) that share a
  search_term and do not cite each other, using semantic signals (negation, opposite modals). Do NOT
  flag internal tensions within a single PN or cross-domain pairs with no shared search_term. If
  `graph_age_days` > 7 or `graph_missing`, say so before trusting the count.
- **14 Mentor Photos**: interactive — list photo-pending / nobg-missing / broken-embed and
  ask the user. Do not auto-generate images.
- **15c Design Ref frontmatter**: review missing visual fields; do not autocomplete them.
- **18 Myelination**: run `python3 "$OPEN_BRAIN_ENGINES/autolink/myelinate.py" report` and interpret;
  if there are >50 pending traversals, suggest `myelinate.py apply`.
- **21 Connector Verb Diversity** (inspired by Chen/Zhao/Cohan 2026):
  the engine counts how many `[!claude] Connectors` callouts use ONLY weak verbs
  ("related to", "connects to") without any verb that differentiates the type of
  relation (contradicts, extends, depends on, applies to, operationalizes...). It is a
  lexical proxy, not a semantic one — the paper's finding is that LLMs converge on
  "integrate/relate" far more than humans do (34.2% vs 2.35%), and assistant-written
  connectors are likely to suffer the same bias. If `weak_ratio > 0.6`, report it
  as **Important**: *"N connectors (X%) only say 'related to' without
  differentiating the type of connection — consider reviewing the listed items and
  rewriting them with a more specific verb."* Do NOT rewrite the connectors
  yourself in this pass — the check is diagnostic, the fix is a separate session
  (or part of a future `open-brain-enrich` pass).
- **19 Demanded Concepts** (what to write): run `python3 "$OPEN_BRAIN_ENGINES/autolink/demand.py" --json`.
  The `concept` bucket lists concepts referenced many times but without a note — it is the writing
  backlog the graph dictates. Report the top 5 (refs ≥ 4) as an **Important** action:
  *"You cite [[X]] N times without a note — candidate for a Search Term + PN"*. The `source` bucket (high refs)
  → route to `open-brain-ingest`/`open-brain-index` to create the Dossier. Do NOT confuse with Check 8
  (broken links counts the total; this ranks and classifies the actionable value). Do not create notes
  automatically — only prioritize.
- **20 Validation Gap** (what to validate): run `python3 "$OPEN_BRAIN_ENGINES/autolink/validation_gap.py" --json`.
  Measures how many PNs are validated by a Case. Report as **Important**: (a) the
  `validation_queue` — top 5 PNs with the highest `times_retrieved`+`in_degree` WITHOUT a Case (claims that carry
  weight without being tested); (b) `orphan_cases` — real Cases without `principles_validated` (the
  cheapest win: link them); (c) `broken_links` — `principles_validated` pointing to a non-existent PN.
  NEVER fabricate Cases (they are the vault owner's real experiences); only prioritize and propose links.

## Fix modes

The engine is **report-only**. Mechanical fixes (downgrade maturity, count reconcile)
are applied separately and ALWAYS with confirmation: never delete notes, merge search terms,
create domains or change a note's body without the vault owner's approval.

- **33 Log Bloat**: if `count > 0`, the finding carries a `fix` with the exact command —
  `python3 "$OPEN_BRAIN_ENGINES/health-engine/compress_logs.py" --apply`. The script archives (never deletes)
  `Hot Cache.md` entries older than 14 days from the "Recent changes" section into
  `Resources/Hot Cache — Cambios Archive.md` ("Cambios" = changes; the file name is kept as is), and closed months of `Session Log.md` into
  `Resources/Session Logs/{YYYY-MM}.md`. Run it with `--dry-run` first to see what
  would be archived before `--apply`. This MAY be run without asking for extra
  confirmation per entry (it is non-destructive archiving, not a merge or deletion), but
  always report what was moved.
- **34 and 35 have no fix** — they are pure, read-only measurement (`$OPEN_BRAIN_ENGINES/engine/compression_benchmark.py`
  and `$OPEN_BRAIN_ENGINES/engine/skill_sequence_report.py`, both reusable standalone). There is no mechanical action to apply; the output is input for the vault owner's
  judgment, not a problem to solve.

## What this skill NO LONGER contains (it lives in the engine)

All the scanning logic of the mechanical checks → `$OPEN_BRAIN_ENGINES/health-engine/health_check.py`.
If a threshold or a path is wrong, fix it in the script — NOT in this prompt. If the engine
is not installed (`$OPEN_BRAIN_ENGINES/health-engine/health_check.py` and `vault-scan/` missing),
the skill says so and stops: it does not fall back to scanning the vault by hand.

## Final report (format)

```
## Vault Health Report — <date>
### Summary — <totals by type> · overall health: <Good|Needs attention|Critical>
### Critical (fix now) — ...
### Important (fix soon) — ...
### Maintenance — ...
### Pipeline (info, 34/35) — 1-2 descriptive sentences, no forced conclusion
### Suggested Actions (prioritized) — 1... 2... 3...
```
