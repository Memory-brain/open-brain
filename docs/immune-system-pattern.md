---
module: module-6-health
related_skills:
  - open-brain-health
  - open-brain-eval
  - open-brain-autolink
  - open-brain-review
last_updated: 2026-10-06
---

# The Vault Immune System: Automated Health, Human Judgment

## What It Is

The Vault Immune System is a layered approach to knowledge vault maintenance. It separates automated detection from human judgment, and continuous monitoring from periodic review — so the vault can maintain structural health at scale without requiring a proportionally growing maintenance effort.

The name comes from the analogy: a healthy immune system doesn't wait for you to feel sick and then do a manual inspection of every organ. It runs continuously, detects anomalies automatically, and escalates to conscious attention only when something requires a decision. The vault equivalent does the same: automated checks run without human attention, flag problems with severity signals, and surface only what requires a human decision.

The system has four layers. Each layer addresses a different class of problem. Together, they cover everything from broken links (mechanical) to whether your vault is improving over time (strategic).

---

## The Four Layers

### Layer 1: Automated Detection

Deterministic checks that run over the vault without requiring human attention. No AI, no judgment — pattern matching over structured data. The reference health engine runs around forty-five numbered checks in a few seconds on a vault of a few thousand notes; the core ones:

| Check | What it finds | Why it matters |
|---|---|---|
| Orphan scan | Notes with zero inbound links | Orphans are invisible to navigation and search |
| Broken link scan | References to notes that no longer exist | Broken links silently corrupt retrieval paths |
| Crowding scan | Search terms associated with too many notes | Crowded terms lose discriminative power |
| Maturity drift | Notes whose declared maturity differs from the value derived from their usage counters | Maturity is derived, so any drift is a manual write that corrupts retrieval priority; expected count is 0 |
| Stale-use scan | Notes that are heavily retrieved but not updated recently | High-use stale notes may be confidently spreading outdated thinking |
| Count drift | Significant changes in note count across domains | Unexpected changes signal processing failures or deletions |
| Structural consistency | Labels, tags, or schema used inconsistently | Inconsistency fragments search and navigation |

Output: a prioritized list of flagged notes with the specific problem, severity, and suggested action. Severities are **critical**, **important**, **maintenance** and **info** — info covers measurements of the pipeline itself and is never presented as an alarm. The human reads the list, not the vault.

Next to the mechanical scan, health has a separate **judgment phase** for the checks a script can't decide — contradiction candidates, myelination state, demanded-but-missing concepts, principles with no validating case, weak connector verbs. These run with a *cite before verdict* rule: quote the exact fragment in question first, then decide whether it is a real finding. Asking "is anything wrong here?" directly misses more problems than asking for the literal quote first.

### Layer 2: Eval Scorecard

Measurement of six vault dimensions against fixed thresholds. This layer answers the question the automated checks can't: "Is the vault getting better or worse over time?"

| Dimension | What it measures |
|---|---|
| Integrity | Frontmatter compliance, broken links, orphan permanent notes, count drift |
| Graph | Signal/noise ratio (edges that aren't bare mentions), edge-type distribution, generative share, myelination |
| Pipeline | Stale inbox, source coverage, endorsement states, owner extension rate (notes where you added your own thinking) |
| Practice | Spaced-repetition accuracy per domain, weak cards, practice logs |
| Funnel | Source → literature note → permanent note conversion, `times_retrieved`, external outputs |
| Output | Ideas, published pieces, manuscripts, rejected permanent notes |

Each scorecard metric gets a 🟢🟡🔴 status from fixed thresholds (for example: graph signal/noise ≥20% green; literature-to-permanent conversion ≥10% green; at least 30% of permanent notes ever retrieved green). Four are north-star metrics — funnel conversion, owner extension rate, external outputs and graph signal/noise; the rest are diagnostic.

The eval itself has three layers: **L1 mechanical** runs every time at zero token cost; **L2 judgment** — an LLM scoring a sample of notes against a rubric — runs on demand; **L3 trend** compares the last runs and is reviewed **weekly**. The trend reading is sustained improvement, plateau, or regression. One bad reading is noise; a plateau or regression across several runs is a pattern that requires a decision.

### Layer 3: Continuous Graph Maintenance

After every note-creating operation, the knowledge graph is updated. New connections between notes are classified by semantic type — not just "this note mentions that note," but "this note *contradicts* / *extends* / *refines* / *provides evidence for* that note."

This layer runs after every note-creating operation, not on a separate schedule. It keeps the graph current without requiring a dedicated maintenance session.

The practical effect: when you retrieve a note and explore its connections, the connection types are accurate and current. You can navigate from "this principle" to "the cases that support it" to "the principles that contradict it" — rather than following generic links that all look the same.

This is deterministic. It reads the verbs and phrases around each link to classify the relationship. No LLM required; no human attention required.

The myelination cycle belongs to this layer too: usage recorded during retrieval is applied to edge weights after the graph is regenerated, or when the health check finds more than 50 traversals pending.

### Layer 4: Periodic Review

Once per week, a review of actual vault activity (`open-brain-review`) — what was practiced, what sessions occurred, what ideas surfaced during daily work that weren't formally captured.

This layer catches what automated detection misses: signal buried in the noise of daily activity. A note that keeps appearing in different contexts might be a cornerstone idea that deserves promotion to a higher maturity level. A pattern of failed retrievals on a topic suggests a gap in coverage. An idea that appeared in three separate sessions but was never written as a note is a synthesis opportunity.

The review produces a brief: what actually happened this week vs. what you thought happened. The gap between perceived activity and real activity is often significant.

Pair it with a **weekly improvement review**: keep one running list of the changes you made to the system itself — a skill edited, a threshold changed, a cleanup pass — and record three fields for each: what changed, what you expect it to move, and when you'll check. Each week, close the entries whose check date has passed against the eval trend before opening new ones.

---

## The Process

**After each significant batch of new notes (10+):**

1. Run Layer 1 automated detection on the new notes and their affected domains
2. Run Layer 3 graph update on the new notes
3. Review the flagged items list (typically 5-15 minutes)
4. Fix critical issues immediately; add maintenance tasks to queue

**Weekly:**

1. Run Layer 4 review
2. Check the maintenance task queue; address high-priority items
3. Note any ideas surfaced in the review that should be captured as notes

**Weekly, after the review:**

1. Run Layer 2 eval and read the L3 trend
2. Run the improvement review: close expired entries against the trend
3. For any metric in plateau or regression, apply the refinement rule:
   - Find the last deliberate intervention that touched it. If the metric moved in the right direction, the *type* of intervention is right — repeat it and adjust only its magnitude.
   - If it didn't move, or got worse, don't stack another intervention of the same type. Change the type.
   - Two consecutive rounds of the same type without movement means a design ceiling, not an effort problem. Report it as such, with the evidence of what was tried, instead of proposing a third identical round.

---

## Cadence

| Trigger | Layer | Time required |
|---|---|---|
| After every note-creating operation | Layer 3 (graph regeneration) | Automated |
| After significant note addition | Layer 1 (detection) | Automated; 5-15 min human review |
| Weekly | Layer 4 (activity review) + improvement review | 15-20 min |
| Weekly | Layer 2 eval + L3 trend | Automated; 10 min human interpretation |
| On demand | L2 judgment rubric ("deep eval") | 20-30 min |
| When >50 traversals are pending | Myelination apply (suggested by the health check) | Automated |

Total human time per month: approximately 2-3 hours. This compares to 8-12 hours for a manual equivalent at 1,000+ notes.

---

## What It Is Not

**Not a reorganization system.** The Vault Immune System maintains structure; it doesn't redesign it. If your vault's fundamental organization is wrong, this system will keep it consistently wrong, not fix it. Structural redesign is a separate, deliberate project.

**Not content editing.** Automated checks can flag a note as potentially stale or thin. They can't determine whether the content is good. Content quality — the accuracy and depth of what's written — requires human judgment and is out of scope for this system.

**Not about having a "perfect" vault.** The goal is not zero orphans or zero structural issues. The goal is to know about problems early, prioritize the ones that matter, and address them incrementally. A vault under active development will always have some structural roughness. The immune system keeps that roughness from compounding into debt.

**Not a one-time setup.** The system works through cadence. Running the checks once tells you the current state. Running them weekly for a year tells you whether you're building a better knowledge system or just a bigger one.

---

## Measuring Impact

Track these metrics before and after implementing the system:

| Metric | Baseline | Target direction |
|---|---|---|
| Orphan rate | Establish at start | Declining |
| Broken link count | Establish at start | Zero or near-zero |
| Time spent on manual maintenance | Estimate current | Declining |
| Scorecard trend (3-month) | Establish at month 3 | Stable or improving across all 6 dimensions |
| Retrieval recall | Pooled recall on a judged query set, from the Retrieval Log | Improving, by paired delta between configurations |

The clearest signal that the system is working: you stop thinking about vault maintenance as a large periodic project, and it becomes background infrastructure you barely notice.

---

## Related

- [Structural Debt](structural-debt.md) — the problem this system prevents from accumulating
- [The Unmeasured Vault](unmeasured-vault.md) — Layer 2 directly addresses this failure mode
- [The Manual Maintenance Ceiling](manual-maintenance-ceiling.md) — Layer 1 and Layer 3 directly address this failure mode
- [The Enrichment Pattern](enrichment-pattern.md) — a complementary maintenance pattern focused on findability
