# Step 0.7 — SurpriseFilter (full text)

> The full SurpriseFilter: when it runs and when it doesn't, the command, the three bands with the literal questions to ask the user, the frontmatter it leaves, the override rule, and the batch protocol with the mid-batch criterion reminder. Read it when the band is not green, when a batch passes ~15 items, or when unsure whether a note type is evaluated.

---

## Step 0.7: SurpriseFilter — Novelty Check (mandatory for Inbox and Cases)

Before creating any note, run the SurpriseFilter to evaluate whether this content brings genuinely new knowledge to the vault. Inspired by the SurpriseFilter idea from the neuron memory architecture: only let through information that is genuinely novel; redirect confirmations to existing notes; flag duplicates.

### When to run

Run for **Inbox** and **Case** notes. Skip for:
- Fleeting Notes (too small to evaluate meaningfully)
- Design References (visual content evaluated differently)
- Mentor/Search Term/Book support notes (these are structural, not knowledge)

### How to run

```bash
cd "$OPEN_BRAIN_ENGINES/autolink"
python3 surprise.py evaluate \
    --title "<proposed note title>" \
    --terms "<comma-separated search terms>" \
    --mentor "<author name>" \
    --type inbox
```

### Three bands

| Band | Score | Action |
|------|-------|--------|
| 🟢 **Novel** (≥0.6) | Content is genuinely new | Proceed with normal ingestion |
| 🟡 **Confirmation** (0.3–0.6) | Content reinforces existing knowledge | Show the user the overlapping notes. Ask: *"This content overlaps with existing notes. Should I create the note anyway, or would you rather link this from the notes you already have?"* If the user says proceed → create the note with `novelty_band: confirmation`. If the user says link → skip note creation and suggest adding a reference in the existing notes. |
| 🔴 **Duplicate** (<0.3) | Near-duplicate exists | Show the user the most similar note. Ask: *"This looks almost identical to [[existing note]]. Should I capture it anyway, or is it already covered?"* If the user overrides → create the note with `novelty_band: duplicate-override`. |

### Frontmatter addition

Add to every Inbox and Case note created after SurpriseFilter evaluation:

```yaml
novelty_score: 0.XXX
novelty_band: novel | confirmation | duplicate-override
```

This data is consumed later by `open-brain-extract` to prioritize truly novel content.

### Override rule

The user can ALWAYS override the SurpriseFilter. The filter advises — it never blocks. When the user overrides a confirmation or duplicate band, the note is created with the override marker so the system remembers the decision.

### Batch ingestion

During a Notion migration or batch import, run the SurpriseFilter once per item but present results as a summary table instead of asking one by one:

```
SurpriseFilter Batch Results (15 items):
  🟢 Novel: 8 items — proceed
  🟡 Confirmation: 5 items — [list with overlapping notes]
  🔴 Duplicate: 2 items — [list with matching existing notes]
```

The user reviews the 🟡 and 🔴 items in bulk and decides which to include.

**Mid-batch criterion reminder.** In a long batch (a typical Notion migration has 15–50+ items), the real triage criterion — which note type each item is, whether the SurpriseFilter bands it as novel/confirmation/duplicate, whether a Case is genuinely the user's own experience (Critical Rule 7) — holds firmly for the first items and dilutes towards the end of the batch. It is the same mechanism by which a long-context monitor misses actions buried in the middle of a long transcript (Martin & Roger, 2026, arXiv:2605.12366, §4.6). Every ~15 items of the same batch, re-read the triage criterion in one sentence before continuing. It is not a formal check and produces no new artifact — it is the same cheap pause the paper measures (<3 % overhead). It does not replace the summary table above, which still runs once at the end of the whole batch.

---
