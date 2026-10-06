# Step 6.7 — LN Lint

> The full lint step: command, the `features` exception and rule L07, how to treat BLOCK/WARN/INFO, and the complete L01–L17 rules table with severities. Read it when running the linter and when interpreting a violation.

---

## Step 6.7: LN Lint (mandatory, after writing each batch)

After writing all LNs for a source and completing the wiring (Step 6.5), run the deterministic linter to catch mechanical errors before they enter the vault.

**Tool**: `$OPEN_BRAIN_ENGINES/engine/ln_lint.py` (requires `pyyaml`). Install once: `pip install pyyaml --break-system-packages`.

**Procedure**:

```bash
python3 "$OPEN_BRAIN_ENGINES/engine/ln_lint.py" check-batch "Literature Notes/" --prefix XX --format summary --history
```

Where `XX` is the prefix used for this source's LNs. `--history` appends the batch aggregate to `Resources/Vault Health/ln_lint_history.jsonl`, so the lint trend accumulates without anyone having to run it separately.

**On `features` and the L07 rule**: `features` is not worth blocking on. It has no strong consumer — interactive retrieval measured *worse* with it — and its strict labeling precision is modest. Treat an L07 finding about `features` as INFO: fix it if the value is illegal, don't stall a batch over a missing label. The labels you get from the Step 7 enumeration are cleaner than anything a separate tagging pass produces. Every other lint rule keeps its severity.

**How to handle results:**

- **BLOCK violations** (L01–L04, L06–L07, L09, L17): Fix immediately. The LN is structurally broken — missing frontmatter, invalid features, no source/mentor wikilink, no Your extension section, no description. These are non-negotiable.
- **WARN violations** (L05, L08, L10–L11, L13–L14, L16): Fix in this pass if possible. If not fixable (e.g., source genuinely has no page numbers for L13), accept and report to the user.
- **INFO violations** (L12, L15): Report only. No literal quote or no connector callout is acceptable for some notes.

**Lint rules reference:**

| ID | What it checks | Severity |
|----|----------------|----------|
| L01 | Frontmatter YAML is parseable | BLOCK |
| L02 | `type: literature` present | BLOCK |
| L03 | `source:` contains `[[wikilink]]` | BLOCK |
| L04 | `mentor:` contains `[[wikilink]]` | BLOCK |
| L05 | `search_terms:` has ≥ 4 items written (extraction target 4–6; the enrichment floor is separate: ≥3 specific, resolvable terms — hubs and terms without a page don't count) | WARN |
| L06 | `domains:` has ≥ 1 item | BLOCK |
| L07 | `features:` is a list, each value in {factual, conceptual, application, decision, diagnosis, code-artifact} | BLOCK |
| L08 | `voice_state:` is a valid value | WARN |
| L09 | `## Your extension` section exists | BLOCK |
| L10 | `## Your extension` is empty (not pre-filled) | WARN |
| L11 | Body has no voice leak ("I think", "Claude suggests") | WARN |
| L12 | At least one literal quote in body | INFO |
| L13 | `source_ref:` is not empty | WARN |
| L14 | File ≤ 3000 chars (multi-insight signal) | WARN |
| L15 | `[!claude]` callout present | INFO |
| L16 | `created:` in YYYY-MM-DD format | WARN |
| L17 | `description:` present and non-empty (a claim, not a topic) | BLOCK |

`search_context` coverage (one entry per search_term) is required by the template but is not a separate lint rule.

**If any LN has BLOCK status after fixing**: do NOT write it to the vault. Report it as a failed extraction for that insight in Step 10.

**Include the lint summary in the Step 10 report.**

**Skip conditions**: `ln_lint.py` not available, or source produced zero LNs. If skipped, note "Lint: skipped (engine unavailable)" in the report.

---
