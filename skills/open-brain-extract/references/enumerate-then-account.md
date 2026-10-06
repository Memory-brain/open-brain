# Step 7 — Enumerate-then-account

> The full step: what changed from the binary audit and why, re-reading Skill Constraints from disk, the four moves of the accounting, the feature coverage table as a secondary cross-check, and the filler-notes precedent. Read it every time before reporting.

---

## Step 7: Enumerate-then-account (MANDATORY, before reporting)

**What changed and why.** Earlier versions ran this step as a binary audit: "does each detected feature appear in at least one note?" Measured against a hand-built ground truth during this skill's development, that check added almost nothing. What did work — **roughly 40 % more cautionary insights captured** — was forcing an explicit enumeration first. The reason is mechanical: warnings and gotchas are rarely lost because the scanner failed to see them, they are lost because the note budget ran out and nobody noticed. A checkbox per feature can be satisfied by one note while five other warnings quietly disappear; a numbered list cannot.

**Before starting, re-read `Resources/Skill Constraints.md` from disk (if your vault has it).** Don't assume it survived intact in context: extraction is the longest pipeline in the system and by now the context has been compacting for a while, so the global constraints you read in the preamble are now a memory, not a reading. If a constraint you thought was in force isn't in the file, or says something different, the file wins. It costs one read and avoids closing an entire extraction against a rule that no longer exists.

**Do this, in order:**

1. **Enumerate.** Before looking at the notes you wrote, list every distinct cautionary or practical insight the source actually contains — anti-patterns, failure modes, "don't do X", thresholds where something breaks, conditions where the advice inverts. Number them. Aim for exhaustiveness, not for elegance: a list of 14 is a better input than a list of 5.
2. **Account for each one.** Walk your list and mark each item either **captured** (name the note) or **dropped** (say why in one clause: redundant with #3, too thin to stand alone, out of scope for this vault).
3. **Report the accounting**, not just a coverage table. `12 of 14 captured · 2 dropped (one redundant with the note that state is modeled as a finite machine, one too thin)` tells the user something. A row of ✅ does not.
4. Nothing may be silently dropped. An insight you decide not to keep is a decision with a reason; an insight nobody listed is a leak.

The features table below still helps as a *secondary* cross-check — and the tags fall out of the enumeration for free, which is why they come out cleaner this way than when assigned as an afterthought:

| Source Feature | Detected in Source? | Captured in Notes? | Status |
|---------------|--------------------|--------------------|--------|
| code-artifact | ✓/✗ | N notes | ✅ / ⚠️ |
| diagnosis | ✓/✗ | N notes | ✅ / ⚠️ |
| application | ✓/✗ | N notes | ✅ / ⚠️ |
| decision | ✓/✗ | N notes | ✅ / ⚠️ |
| factual | ✓/✗ | N notes | ✅ / ⚠️ |
| conceptual | ✓/✗ | N notes | ✅ / ⚠️ |

**Secondary cross-checks** (after the accounting, not instead of it):
1. Source has code blocks but no note tagged `code-artifact` → look again.
2. Source has negation/warning language but no note tagged `diagnosis` → look again; this is where the enumeration usually pays.
3. Source has step-by-step procedures but no note tagged `application` → look again.
4. Every note in the same domain → ask whether there are cross-domain implications; if yes, at least one cross-domain note.

**Never create a note to fill a slot.** The known failure: a coverage report that drives a batch of filler notes into empty categories produces notes that are never retrieved afterwards. A gap in the table is information about the source, not a task. Flag it and let the user decide.

---
