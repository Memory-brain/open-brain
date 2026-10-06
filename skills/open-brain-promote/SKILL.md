---
name: open-brain-promote
description: 'Promotes Literature Notes to Permanent Notes, and Design References to Visual Pattern Notes. This is where the shared ritual lives, along with the convergence gate (≥2 independent sources — different author, and neither citing the other — plus ONE extension written by you, the vault owner, per cluster, not per note) and the endorsement state machine. The long specs live in reference/text-promote.md and reference/visual-promote.md, loaded by mode. It never promotes on its own: the vault owner confirms what becomes permanent. Triggers: promote, convergences, open-brain-promote, promote with the web UI, visual promote, promote patterns, visual patterns.'
metadata:
  version: "9.10.0"
  triggers: promote to permanent · level up · convergences · open-brain-promote · endorse this PN ·
    reject this PN · open brain promote · visual promote · promote patterns · visual convergence ·
    PAT notes · visual patterns
  status: canonical
  requires_engine:
  - name: maturity_migrate.py
    version: unpinned
  - name: output_ledger.py
    version: unpinned
  - name: update_graph.py
    version: unpinned
  consumes:
  - A request to promote convergent Literature Notes to a Permanent Note, or convergent Design References
    to a Visual Pattern Note
  - The vault owner's explicit endorse/reject decision and, per cluster, a one-paragraph extension of what
    the convergence means to them
  produces:
  - A Promotion Brief with candidates, draft note, convergence-test result, and evaluation questions
  - A new provisional PN or PAT note with full traceability frontmatter, or a note moved to Rejected/
    with rejection metadata
  - A silent update to the typed knowledge graph via update_graph.py
  handoffs:
  - skill: open-brain-extract
    when: the task actually requires creating Literature Notes, which Promote does not do
    requires_approval: true
  - skill: open-brain-ingest
    when: the task actually requires creating Inbox notes
    requires_approval: true
  - skill: open-brain-synthesize
    when: the task actually requires updating Domain Indexes
    requires_approval: true
---

> **Global constraints**: if your vault has a `Resources/Skill Constraints.md` note, this skill inherits it. Any exception is declared explicitly below.

# Open Brain — Promote (v9.10.0)

Vault Promote is the synthesis layer of the knowledge system. **Two pipelines, one ritual:**

1. **Text promote** — convergences between Literature Notes from different authors → Permanent Notes (PNs).
2. **Visual promote** — convergences between Design References from different products → Visual Pattern Notes (PATs).

Both share the same logic: **detect convergence → test quality → generate a brief → the vault owner endorses → write the note.**
What changes is the input (LNs vs REFs), the output (PNs vs PATs), and the convergence test (textual 4-part vs visual 4-gate). The detailed mechanics of each pipeline live in a reference file — see "Routing" below.

Two principles underpin everything here:

- **Human confirmation**: nothing becomes permanent without the vault owner. The system can propose; only the owner endorses.
- **Source independence**: two sources count as two only if they have different authors and neither cites the other. Two works by the same author are one reinforced source.

---

## Changelog

- **v9.10.0** — Approval leaves a trace, and the template is no longer duplicated. (1) `endorsed_at` / `endorsed_via` / `status: draft` — an `endorsement_state` that almost every PN shares (`provisional`) cannot distinguish "the owner approved it and nobody recorded it" from "never reviewed". (2) `generated_by` on every new PN, so that a fix to a skill or engine can be turned into the query "which notes were born with this defect". (3) An append-only **`## Historial`** (history) block with four events and only four. And a hygiene fix: `reference/text-promote.md` **no longer duplicates** the PN frontmatter and points to your PN template instead — two diverging schemas for the same object are a second version of the truth waiting to be confused with the first.
- **v9.9.1** — `reference/text-promote.md` and `reference/visual-promote.md` are rebuilt and shipped; an explicit fallback is added in case they go missing again.
- **v9.9** — The extension gate is a **checkable field**, not a feeling: if `cluster_extension` is empty, `gate_passed` is `false`. Reason: a global "do it all" approval otherwise lets clusters through with `cluster_extension: null`.
- **v9.7** — The extension is requested once **per cluster**, not per note. Per-note extensions put the friction on the most expensive step, and in practice the gate was never reached.
- **v9.4** — PN template to the endorsed standard. **v9.3** — visual pipeline (PAT). **v9.2** — sub-commands and endorsement state machine.

## Routing — read this first, then load the matching reference

**The mode is decided FIRST** — before any scan or analysis. Detect mode, then load the corresponding reference file and follow it end to end. Do NOT load the reference for the mode you are not running.

| Mode | Triggers | Then load |
|------|----------|-----------|
| **chat** (default) | "promote", "convergences", "open-brain-promote" | `reference/text-promote.md` |
| **ui** | "promote with the web UI", "open the promote web page", "with the UI", "start the promote UI" | `reference/text-promote.md` (UI Mode section) |
| **visual** | "visual promote", "promote patterns", "visual convergence", "PAT notes", "visual patterns" | `reference/visual-promote.md` |

Text-side sub-commands (`--by-application`, `--review-friction`, `--endorse`, `--reject`) are specified in `reference/text-promote.md`.
Visual atomic commands (`--visual-endorse`, `--visual-reject`) are specified in `reference/visual-promote.md`.

If genuinely ambiguous between chat and UI, ask once: *"Do you want the ritual here in chat (default) or in the promote web UI?"*

### If a reference file is missing (fallback — v9.9)

**This package includes both** (`reference/text-promote.md` and `reference/visual-promote.md`). Still, check that the file exists before loading it.

If it is missing, **do not abort and do not make it up**: run the ritual with what is in this SKILL.md, which is self-sufficient for the main path (convergence gate → per-cluster extension gate → endorsement state machine → writing the PN → graph → `skill_sequence`), and **say so in the first line of the brief**: *"`reference/text-promote.md` is not installed; running the base ritual without sub-commands."*

What is lost without the reference, and therefore what you must NOT pretend to support:

- Text sub-commands: `--by-application`, `--review-friction`, `--endorse`, `--reject`.
- Visual commands: `--visual-endorse`, `--visual-reject`, and the full PAT pipeline.
- The UI Mode section with the server contract.

If the user asks for one of those, the honest answer is that the reference is not installed — do not improvise an approximate version of the sub-command.


**HARD RULE (UI)**: If the user asked for UI mode, **the server ALWAYS starts**, even if the scan finds no promotable clusters. If nothing can be promoted, say so INSIDE the queue passed to the server (`gate_passed: false`), not in chat without the UI.

---

## The shared ritual (applies to both pipelines)

1. **Convergence scan** — find candidate clusters.
2. **Apply the convergence test** — textual 4-part (text) or visual 4-gate (visual). See the reference.
3. **Generate a Promotion Brief** — show the vault owner ALL candidates, a draft note, the test result, and the evaluation questions. **Present and STOP.**
4. **Wait for the vault owner's evaluation.** Blocking. Do NOT write the note until they answer.
5. **Write the note** — with full traceability frontmatter.
6. **Link back** to sources and **update the typed graph** (silent, see below).
7. **Report.**

The note is ALWAYS born `provisional`. Endorsement is a separate, explicit second step.

---

## The extension gate lives at the cluster, not at the note (v9.7)

The obvious failure mode of a human gate is rubber-stamping. The less obvious one — and the one that per-note extensions produce — is that the gate is **never reached**. Friction placed on the most expensive step — write your own paragraph on every candidate note — produces a queue, not judgment. Friction is worth its cost only where there is something to judge, and what deserves judgment is the *convergence*, not each note that feeds it.

**So the gate is:**

1. `≥2 sources that are genuinely independent` — different author, and neither citing the other. Two works by the same author count as one reinforced source, not two. Check this explicitly; no script enforces it, so if you don't check it nobody does.
2. **One extension written by you (the vault owner) per cluster** — a single paragraph about what the convergence means to you — recorded on the cluster, not on each LN:
   ```yaml
   cluster_extension: "<the vault owner's own words>"
   extended_by: owner
   extended_at: <YYYY-MM-DD>
   ```
3. Present **at most 3 clusters per session**, ordered by `convergence_strength` and then by how many notes in the cluster have `times_retrieved > 0`. Real use is a better priority signal than cluster size.

What does **not** change: the human-confirmation principle stands. Nothing becomes permanent without the vault owner. The confirmation moves, it does not disappear.

**The extension gate is a field, not a vibe (v9.9).** A global approval can let clusters cross the gate and get written as PNs with `cluster_extension: null` — the friction moves from the expensive place to the valuable place, and is then skipped.

So: **if `cluster_extension` is empty, the gate is NOT passed.** Write it in the queue as `gate_passed: false` with the reason, and ask for the extension — once, per cluster, in the vault owner's words. A global approval (*"do it all"*, *"go ahead"*, *"promote"*) is **not** a cluster extension and does not fill that field. If the owner wants to promote anyway, go ahead — but the PN is written with `cluster_extension: "(promoted without extension — global approval YYYY-MM-DD)"`, so the record does not claim judgment where there was none.

A useful acceptance check for this gate: within a few weeks of use, at least one cluster should cross the full gate with a real extension. If none does, the gate is still not being reached.

**Do not ask for a per-note extension anymore.** If a candidate LN still carries placeholder text saying its empty extension blocks promotion, that text is stale — ignore it, and say so in the brief.

---

## Endorsement state machine (shared philosophy)

Every promoted note carries an endorsement field. **Note the field name differs by pipeline** — PNs use `endorsement_state`, PATs use `endorsement_status` — but the *philosophy* is identical and lives here:

**Four states:**
- `provisional` (PNs) / `pending` (PATs) — the note exists but has not passed explicit criteria from the vault owner. **Default for ALL new notes.**
- `endorsed` — the vault owner explicitly approved it via any promote mode. Set `endorsed_at` + `endorsed_via` (see below).
- `rejected` — the vault owner rejected it. The note moves to a `Rejected/` subfolder with frontmatter intact + `rejected_at` and `rejected_reason`. It is **NOT deleted.**
- `unendorsed` (PNs) — the vault owner reviewed the note and explicitly withdrew a previous endorsement (or declined to endorse it) without rejecting it: the note stays in `Permanent Notes/` but no longer counts as approved judgment. Use it when an endorsed PN stops holding up but still has value as a record; use `rejected` when it does not survive at all.

**Rejected-note policy (both pipelines):**
1. Move file into the pipeline's `Rejected/` subfolder (`Permanent Notes/Rejected/` for PNs, `Design References/Rejected/` for PATs).
2. Add `rejected_at: <ISO>` and `rejected_reason: <free text>` to frontmatter.
3. Do NOT delete — a rejected note is auditable historical debt.
4. Do NOT remove inbound wikilinks / back-references. **A broken link is the correct signal.**

**Passive migration**: existing notes without the endorsement field get labeled `provisional`/`pending` the first time they enter ANY flow (course, practice-log, promote). No mass migration sprint.

The controlled list of `endorsed_via` values and the exact frontmatter blocks live in each reference file.

---

## Approval is an event, not an adjective (v9.10)

When nearly every PN carries `endorsement_state: provisional`, the field separates nothing: it does not distinguish "the owner approved it in a session and nobody recorded it" from "never looked at it", which is exactly the difference the human-confirmation principle exists to mark.

The PN is born with these three fields, **in addition to** the `endorsement_state` field it already wrote — they do not replace it: `check_22` validates that enum and `--endorse` keeps working the same way.

```yaml
endorsed_at:            # EMPTY unless the vault owner approves IN THIS session, explicitly
endorsed_via:           # promote | promote-by-application | promote-atomic-endorse | sesion | careo | review-queue
status: draft           # while endorsed_at is empty
```

The `endorsed_via` values are identifiers and stay as written: `promote` (this ritual; you may record the specific mode as `promote-by-application` or `promote-atomic-endorse`), `sesion` (approved during a regular working session), `careo` (approved during a challenge/cross-examination session, the same value other skills use as `origin: careo`), `review-queue` (approved while processing a review queue).

**Do not write `endorsed_at` yourself.** It is only filled when the vault owner explicitly approves in the conversation, and then `endorsed_via: promote`. An inferred approval date is the opposite of what the human-confirmation principle asks for: the system certifying that the owner approved something. If the session is unattended, the PN is born `draft`, full stop — draft PNs should be surfaced again at the start of a later session (for example in your session-start context or the health report), which is the only place where approval can actually happen.

`check_41` (Endorsement as Event) requires `endorsed_at` or `status: draft` on every PN created **on or after the check's cutoff date**. Older PNs are reported as `legacy_backlog` and do not count.

### `generated_by` — what produced this note

On every new PN or PAT:

```yaml
generated_by: "open-brain-promote <version of this skill> · engine-stamp <date from $OPEN_BRAIN_ENGINES/health-engine/engine-stamp.json>"
```

Without this field a fix to this skill applies only going forward and the notes already written with the defect stay invisible: there is no way to list them. Do not invent it — if you cannot read `engine-stamp.json`, write only the skill version.

### `## Historial` — append-only, four events

At the end of the PN body, after `Connections` (the heading is kept as `## Historial` because health checks parse it; it is the note's history log):

```markdown
## Historial

2026-09-18 — approved — domain review of <Domain>
2026-10-02 — downgraded to confidence: medium — the second source turned out to be by the same author
```

**Four events and only four**: approval, `confidence` downgrade, merge with another note, and a source added after the fact. Not one line per edit — that is what git is for, and nobody reads it.

**Never rewrite an existing line.** If an entry was wrong, add another one saying so. The block's value is that the change cannot be made without leaving a trace, and rewriting it destroys exactly that. Approval is the first event on the timeline: a PN with `endorsed_at` and no history line is a violation that `check_41` counts.

## Update the typed knowledge graph (silent, shared)

After writing a note and linking back, update the typed graph. Fire-and-forget — silent on success, silent on failure, never blocks the report. If the autolink engine is not installed, the hook stays quiet.

```bash
GRAPH_SCRIPT="$OPEN_BRAIN_ENGINES/autolink/update_graph.py"
if [ -f "$GRAPH_SCRIPT" ]; then
  python3 "$GRAPH_SCRIPT" "<absolute path to the note just written>" --quiet 2>/dev/null || true
fi
```

---

## Trace propagation — `skill_sequence` (v9.8)

This is **additive**: an instruction applied on top of whatever frontmatter the reference already defines, not a rewrite of that template.

When writing the note in Step 5 of the shared ritual: if the cluster's source LNs or REFs carry `skill_sequence:` in their frontmatter, copy it to the new PN/PAT — if several sources in the cluster have different sequences, use the one from the source with the highest `times_retrieved` (the one that weighed most in the decision) and append:

```yaml
skill_sequence:
  - skill: open-brain-promote
    at: "YYYY-MM-DDTHH:MM"
```

If no source in the cluster has `skill_sequence` (older notes), start the list here with only the promote entry — do not invent earlier steps that did not happen.

---

## Gotchas

G1 — **Auto-write without evaluation** → The agent generates the PN and writes it without waiting for the vault owner to answer the evaluation questions. → The ritual is BLOCKING at Step 4. Present brief → STOP → wait for the owner → THEN write.

G2 — **Provisional skipped** → The PN is created with `endorsement_state: endorsed` directly. → Every note is born `provisional`. Endorsement is an explicit, separate act (`--endorse`).

G3 — **Rejected = deleted** → The agent deletes the rejected note instead of moving it to Rejected/. → Move to `Permanent Notes/Rejected/` with frontmatter intact + `rejected_at` + `rejected_reason`. Never delete.

G4 — **Mode leak** → Both reference files (text + visual) are loaded in the same session. Unnecessary context and risk of cross-contamination. → Detect mode FIRST, load ONLY the matching reference. One mode per run.

G5 — **Convergence test skipped** → The agent sees two LNs on the same topic and promotes without applying the formal 4-part test. "Same topic" ≠ real convergence. → Always apply the 4-part test (text) or 4-gate test (visual). No test, no brief.

G6 — **Maturity written by hand** → `maturity` is assigned at creation (or "promoted" by editing the field). → **`maturity` is a derived field**: vault-scan's `maturity()` computes it from `times_retrieved`, `external_outputs` (published) and `internal_outputs` (delivered), and health `check_6` fails if the declared value does not match. A new PN comes out `seed` because its counters are 0, not because you write it. Thresholds: seed → growing (≥2 retrievals **or** ≥1 output of any kind) → evergreen (≥5 retrievals **and** ≥1 **published** output). Canonical name of the intermediate state: `growing` (`budding` is a dead alias). To repair, run `python3 "$OPEN_BRAIN_ENGINES/engine/maturity_migrate.py" --apply`.

G7 — **Output counter by hand** → `external_outputs` is incremented because "this PN fed a document". → Counters are derived from your output ledger, if you keep one (e.g. `Resources/Output Ledger/ledger.jsonl`, maintained with `$OPEN_BRAIN_ENGINES/engine/output_ledger.py`): `python3 "$OPEN_BRAIN_ENGINES/engine/output_ledger.py" counters --apply`. Declared outputs without a ledger entry are untraceable. If the note fed something real, what is missing is the artifact's entry in the ledger — add it there, then rerun the counters. If you keep no ledger, leave the counters alone.

G8 — **Broken endorsement enum** → `provisionall` or another variant is written and no query sees it. → The legal values are `provisional`, `endorsed`, `unendorsed`, `rejected`. `check_22` validates the enum.

---

## What Not To Do (both pipelines)

- **Do NOT write a PN or PAT before the vault owner has answered the evaluation questions.** Auto-generated notes without evaluation are not learning, they are archiving.
- Do NOT create Literature Notes (use `open-brain-extract`).
- Do NOT create Inbox notes (use `open-brain-ingest`).
- Do NOT update Domain Indexes (use `open-brain-synthesize`).
- Do NOT write `maturity` at all — it is derived (see G6). Same for `external_outputs` / `internal_outputs` (see G7).
- Do NOT ask the vault owner for an extension on every candidate LN. One extension per cluster (see the gate section).
- Do NOT write `endorsed_at` unless the vault owner approved in this very session. An inferred approval date is the system certifying the owner's judgment for them — the exact failure the human-confirmation principle exists to prevent. Unattended session → the PN is born `draft`.
- Do NOT rewrite an existing `## Historial` line. Append a correcting line instead; rewriting destroys the only property the block has.
- Do NOT auto-endorse PNs or PATs without explicit action from the vault owner. Promotion creates a provisional note; endorsement is a separate second step.
- Do NOT delete rejected PNs or PATs. Move to the respective `Rejected/` folder.
- Do NOT skip the convergence test (text 4-part) or the visual convergence test (4-gate).
- Do NOT write to `gaps.md` — Promote does not produce skill gaps.
- Do NOT write to `promote-feedback.md` — those blocks are written by `open-brain-practice-log` and `open-brain-course`. Promote CONSUMES them (in `--review-friction`).
- Do NOT load the reference for a mode you are not running.

---

## Reference index

- `reference/text-promote.md` — full text pipeline: scan, 4-part convergence test, Promotion Brief, PN frontmatter additions + body order + per-section quality rules, Ideas/ hook, link-back, UI Mode (`promote-queue.json` contract + server launch), and modes `--by-application`, `--review-friction`, `--endorse`, `--reject`.
- `reference/visual-promote.md` — full visual pipeline: visual convergence scan, 4-gate test, Visual Promotion Brief, PAT frontmatter + body structure, link-back, and atomic commands `--visual-endorse`, `--visual-reject`.
