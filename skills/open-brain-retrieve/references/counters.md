# Retrieval Loop — counters, maturity, Forced Promotion and the manuscript ritual

> What counts as substantive use, what does not, which fields are derived and must not be touched by hand, the dormancy signal and the Phase 12 ritual. Read when closing a substantive retrieve if in doubt about what to increment.

---

## Tracking What You Read (Retrieval Loop)

**This applies to every note used substantively — Permanent Note *or* Literature Note.** When the increment ritual was PN-only, a large share of substantive use (LNs) went uncounted, and a counter that covers only a slice of the corpus turns every downstream signal — staleness, sleeping giants, myelination, coverage — into a measurement of the instrumented slice rather than of the vault. All LNs and Fleeting Notes carry `times_retrieved` and `last_retrieved`; treat them exactly like PNs.

Every time a note's content is used substantively:
1. Read the note's current `times_retrieved` value.
2. Increment it by 1.
3. Update `last_retrieved` to today's date.
4. Write the updated values back to the file.
5. If content is confirmed still accurate, also update `last_validated` to today.

**Do not touch `external_outputs`, `internal_outputs` or `maturity` by hand.** They are derived fields: the output counters come from your output ledger, if you keep one (e.g. `Resources/Output Ledger/ledger.jsonl`, maintained with `$OPEN_BRAIN_ENGINES/engine/output_ledger.py counters --apply`), and `maturity` is computed from them by `vaultscan.maturity()`. Hand-written counters are unauditable — in practice, most notes claiming an external output by hand had no traceable output anywhere. If you notice a note whose retrieval clearly fed a deliverable, the right move is to make sure that deliverable is in the ledger, not to bump a number.

**Counts as substantive use** (increment +1):
- Cite the PN by name as foundation of a recommendation or analysis
- The PN informs a decision suggested to the user
- Use the PN as evidence in a structured output

**Counts as an output** (do NOT increment by hand — make sure the artifact reaches the ledger, if you keep one):
- The note is cited inside a deliverable someone else receives (proposal, plan, handoff, team doc, spec) → that document belongs in the ledger as `tier: shipped`
- The note is cited in something published to the world (a blog, social media, a talk) → `tier: published`
- Run `python3 "$OPEN_BRAIN_ENGINES/engine/output_ledger.py" backfill` and the counters follow automatically

**Does NOT count**:
- PN appears in a "related notes" listing without being used
- PN read but not cited or reasoned with
- PN mentioned as metadata in vault audits
- Serendipity mode retrieval
- **PN surfaced only through Visual Retrieval `linked_pns` without being cited in the text synthesis**

**Counting is not retroactive**: it starts from the day you adopt the retrieval loop.

**Maturity is derived, not proposed**: `seed → growing` at ≥2 retrievals or ≥1 output of any tier; `growing → evergreen` at ≥5 retrievals **and** ≥1 **published** output. `vaultscan.maturity()` computes it and the health check fails if the declared value diverges, so there is nothing to propose and nothing to write — increment the retrieval counter and the state follows. The canonical name for the middle state is `growing`; `budding` is a dead alias.

**Forced Promotion (reminder, not a block)**: when `times_retrieved ≥ 3` and `external_outputs = 0`, explicitly ask: *"This PN keeps being retrieved without producing output. Are you using it in an active manuscript, or shall we demote it to an LN?"*. At `times_retrieved ≥ 5` and `external_outputs = 0`, the reminder repeats every time the PN is cited — but citing the PN is not blocked. A hard block ("do NOT cite until the user confirms an exception") produced a queue with no throughput, not careful curation, so only the reminder remains.

**Dormancy signal**: a PN >90 days without retrieval is a candidate for review, surfaced by `check_27_dormancy_candidates` in `$OPEN_BRAIN_ENGINES/health-engine/health_check.py` (age × importance, not age alone). Retrieval itself does not move, tag, or propose deleting anything — that decision lives in the health report, and only the user acts on it. There is no `Permanent Notes/Dormant/` or `Literature Notes/Archived/` convention.

---

## Manuscript Ritual (Phase 12 — mandatory)

At the end of any session where PNs were used substantively, BEFORE ending the response:
1. Read `Manuscripts/Active Manuscripts.md`.
2. Ask the user: *"You used the PNs [list]. Does any of them feed a post idea in Ideas/?"*
3. If 3 PNs from the same thematic cluster accumulate `times_retrieved ≥ 3`, propose opening a new manuscript with a tentative title.

---
