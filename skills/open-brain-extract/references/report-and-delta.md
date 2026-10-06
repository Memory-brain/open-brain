# Steps 8, 9, 10 and 10.5 — Tier consequence, metadata, report and epistemic delta

> The indexing consequence per tier, the metadata that gets updated, the full report template with the Epistemic Delta block and its nine types, and the deterministic side-effects after the report. Read it every time you assemble Step 10.

---

## Step 8: Tier Consequence (scoring happens in Step 0.4)

Scoring already happened in **Step 0.4**, before writing anything, and on any source type. Here only its indexing consequence runs:

- **TOP (≥9)** → `open-brain-index` is invoked directly, while the source is still in context, for the exhaustive Source Outline.
- **INTERESTING (5–8)** → recommend a minimal `open-brain-index` whenever the user wants it.
- **REJECT (≤4)** → never reaches here: extraction stopped at Step 0.4.

Don't re-score. If after reading the full source the Step 0.4 score looks wrong, **say so in the report with the corrected score** and let the user decide — don't change it silently, because the rejections JSONL is calibrated against scores as they were emitted.

---

## Step 9: Update Metadata

**Inbox note frontmatter** (if source came from Inbox):
```yaml
processed: true
vault_coverage: complete   # or partial / partial-features
ln_prefix: XX
literature_notes_created: N
updated: YYYY-MM-DD
```

**`Resources/Source Index.md`**: update the row (or add if missing) with LN count and coverage.

**Supporting notes**: if Literature Notes reference Search Terms or Mentors that don't yet exist as notes, create them as stubs.

---

## Step 10: Report to the user

```
## ✅ Extraction complete — [Source]

**N Literature Notes** created in `Literature Notes/` with prefix `[XX]`.

**Lint**: N LNs checked — X pass, Y warn, Z block
[If any BLOCK]: ⚠️ N LNs blocked by lint — see details below.
[If any WARN]: Pending warnings: [list top 3 rule IDs]

**Feature coverage:**
| Source Feature | Detected? | Notes with feature |
|---------------|-----------|-------------------|
| code-artifact | ✓/✗ | N |
| diagnosis | ✓/✗ | N |
| application | ✓/✗ | N |
| decision | ✓/✗ | N |
| factual | ✓/✗ | N |
| conceptual | ✓/✗ | N |

⚠️ **Gap detected**: [feature] detected in source but not captured — [justification or "needs second pass"]

**Evidence bundle** (if applicable):
- Figures in PDF: N (N referenced in LNs, N unreferenced)
- Tables detected: N
- Scanned pages: N
- [Any bundle warning]

**Book Tier** (if applicable): [TOP/INTERESTING/REJECT] ([X/12])
→ [If TOP]: open-brain-index invoked now while the source is in context.

**Detected convergences** (Permanent Note candidates):
- **[Theme in one sentence]**. [Author of the new source] says [claim of the new LN]; [author of the other source] says [claim of the existing LN or PN]. [If there are ≥2 independent sources, say so.]

Each note is named by what it asserts and who asserts it, never by its code (`ABC-37`, `XYZ-08`): people don't retain codes. If the link is needed, use the alias `[[filename|claim]]`.

**Epistemic Delta** — what changes in the state of the vault:

For each affected claim (or a single `no_delta_identified` entry if this extraction touches no live claim):

- **Affected claim**: [what the note asserts, in one sentence, and whose it is] `[[filename|claim]]`, never the bare code
- **Type**: reinforces_claim | weakens_claim | qualifies_claim | contradicts_claim | adds_benchmark | adds_evidence | connects_threads | creates_question | no_delta_identified
- **What changes**: [one line in natural language — how the claim reads differently after this source]
- **Portable benchmark / evidence**: [something measurable or citable the user can reuse, if applicable]
- **Natural next use**: no_immediate_output | future PN | stress test | skill patch | post | decision | research thread
- **[If Type ∈ {weakens_claim, qualifies_claim, contradicts_claim}]** → queued in `Resources/Review Queue.md` for your own review

No numeric confidence scale — free text. "More precise", "more measurable", "now conditional on X" are all valid. If there's no affected claim: **Type: no_delta_identified** with one line explaining what the source adds even though nothing live changes. Silence is not valid; neither is inventing.

**Careo (Step 11)** — next: [3 questions live | queued in `Resources/Careo/Pendiente — {slug}.md`]

**Next steps (pick one):**
- `open-brain-promote` for the convergences
- `open-brain-index` for the Source Outline (if TOP/INTERESTING)
- A new source
```

**The report does NOT close the extraction.** Step 11 (Careo) always comes after — answered live if the user is there, queued if not. An extraction without a Careo (neither live nor queued) is an incomplete extraction.

---

## Step 10.5: Post-report side-effects (deterministic, no prompt)

After showing the report and before starting the Careo, apply these mechanical side-effects:

1. **Retrieval counter**: for each delta with `Affected claim ≠ no_delta_identified`, increment `times_retrieved` on the cited note and update `last_retrieved: YYYY-MM-DD`. A new source moving a vault claim IS a retrieval — the note was used to think, not just read.

2. **Review queue append**: for each delta with `Type ∈ {weakens_claim, qualifies_claim, contradicts_claim}`, append (never rewrite) one line to `Resources/Review Queue.md` (create if missing):

   ```
   - YYYY-MM-DD · [[Affected claim]] · [type] · source: [source-slug] · delta: "what changes (one line)"
   ```

3. **Deltas ledger**: append (never rewrite) one line to `Resources/Careo/deltas.jsonl` per extraction, **whatever the delta type** — including `no_delta_identified`:

   ```json
   {"date": "YYYY-MM-DD", "source": "source-slug", "type": "reinforces_claim", "claim": "[[Affected claim]] | null", "delta": "what changes (one line)", "lns": ["LN-XX"]}
   ```

   All nine types are persisted. If only the three that open a Review Queue entry reached disk, the other six would be shown in the report and die with the session, and `no_delta_identified` would never be recorded — even though silence is not a valid outcome. Without the ledger, the feature's own success criterion can't be checked. Create the file if missing.

4. **Reindex and check the engine** (always, at the end of the batch): `python3 "$OPEN_BRAIN_ENGINES/retrieval-eval/eval_retrieval.py" index`, then `python3 "$OPEN_BRAIN_ENGINES/retrieval-eval/check_alignment.py"`. A non-zero exit is reported in bold at the top of the report and the extraction is not considered closed.

These side-effects are deterministic — they don't ask the user. The review queue still only receives `weakens_claim`, `qualifies_claim` and `contradicts_claim`: **the ledger is measurement, the queue is pending work**. Neither is automatic execution (same principle as G7).

---
