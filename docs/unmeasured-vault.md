---
module: module-6-health
related_skills:
  - open-brain-eval
  - open-brain-health
  - open-brain-retrieve
last_updated: 2026-10-06
---

# The Unmeasured Vault: Running Blind on Your Own Knowledge

## The Problem

Most knowledge vaults have no metrics. You don't know how many notes you have, how many have been synthesized into durable principles, what percentage are well-connected, how often notes are actually retrieved during real work, or whether the vault has improved or degraded over the past three months.

Without measurement, you can't distinguish a healthy vault from a sick one. You have an intuition — "feels pretty good," or "getting a bit cluttered" — but intuition about complex systems is unreliable. It's biased toward recent activity (you just added a great set of notes, so the vault feels alive) and toward visible content (the notes you wrote about things you find interesting, not the ones that have silently become orphans).

The result is that most PKM practitioners spend months or years building a knowledge system without knowing whether it's working. They can't answer basic questions: Is the vault more connected than it was six months ago? Has the inbox backlog grown or shrunk? Are notes being retrieved in practice, or just captured and forgotten? These questions have answers — but only if someone is tracking them.

Without measurement, you also can't improve deliberately. Improvement requires a baseline. If you don't know where you started, you can't know whether you've moved.

---

## Why It Happens

### Obsidian and similar tools are file systems, not knowledge databases

The standard PKM tools — Obsidian, Logseq, Notion — are designed around file management and editing. They're excellent at storing and displaying content. They are not designed to compute aggregate metrics across a collection of files.

There's no built-in dashboard that tells you your orphan rate, your average inbound link count, your synthesis funnel conversion, or your inbox backlog size. Getting those numbers requires either manual counting (impractical at scale) or scripts that process the files and compute the metrics. Since the tools don't offer this natively, most users never set it up — and the vault remains unmeasured.

### No baseline was established

Measurement requires a starting point. If you never recorded what your vault looked like at 100 notes — orphan rate, graph density, backlog size, note count by maturity level — then you have nothing to compare against at 500 notes. You can compute current state, but you can't track change over time.

Most practitioners don't establish a baseline because measurement doesn't feel like the point. The vault is for thinking and learning, not for tracking. This is a reasonable intuition that leads to a significant blind spot: you can't tell whether the habits you're building are making the vault better or just keeping it busy.

### Measurement feels like overhead

There's a common perception that measuring a knowledge vault is bureaucratic overhead — the kind of thing corporations do to feel like they're managing things, not what a practitioner does to actually use their knowledge. This perception conflates two different things: measuring for compliance (pointless overhead) and measuring to detect problems early (the only way to maintain a complex system).

A vault with 2,000 notes is a complex system. Complex systems degrade in ways that aren't visible without instrumentation. The measurement overhead is not the cost of bureaucracy — it's the cost of actually knowing whether your system works.

---

## How to Detect It

Without looking anything up, answer these questions about your vault right now:

| Metric | Can you answer? |
|---|---|
| Total note count | Yes / No / Approximately |
| Broken link count | Yes / No |
| Orphan rate (% of notes with no inbound links) | Yes / No |
| Average inbound links per note | Yes / No |
| Inbox backlog (unprocessed sources) | Yes / No |
| Notes added in the last 30 days | Yes / No |
| Notes that have been retrieved at least once in real work | Yes / No |

If you can't answer most of these, the vault is unmeasured. The inability to answer isn't a problem with your memory — it's evidence that the metrics aren't being tracked.

---

## How to Fix It

**Step 1: Establish a baseline**

Run a one-time analysis that records:

- Total note count
- Notes by maturity level
- Orphan rate
- Broken link count
- Inbox backlog size
- Average inbound links per note (proxy for graph connectedness)

Record this as a snapshot with a date. This is your starting point. Without it, future measurements are absolute values with no context.

**Step 2: Run regular evaluations**

Compute the same metrics on a schedule and compare against the baseline and the previous period. It helps to split evaluation into three layers by cost: a **mechanical layer** that runs every time (a script, no tokens), a **judgment layer** where an LLM scores a sample of notes against a rubric (only on demand, when you want a deep eval), and a **trend layer** that compares the last several runs — reviewed weekly.

What you're looking for: trends, not perfection. An orphan rate that's declining month over month is a healthy vault even if the absolute number is still high. An orphan rate that's climbing month over month is a structural problem even if the number seems small.

**Step 3: Use a scorecard with 6 dimensions**

A single metric will mislead you. A vault can have high note count (looks healthy) but low graph connectedness (structurally weak). Use a multi-dimensional scorecard:

| Dimension | What it measures | Key metrics |
|---|---|---|
| Integrity | Structural soundness | Frontmatter compliance, broken links, orphan permanent notes, count drift |
| Graph | Connectedness and link semantics | Signal/noise ratio (edges that aren't bare mentions), edge-type distribution, generative share, myelination |
| Pipeline | Capture-to-synthesis flow | Stale inbox, source coverage, endorsement states, owner extension rate (notes where you added your own thinking, not only the assistant's) |
| Practice | Whether knowledge is being exercised | Spaced-repetition accuracy per domain, weak cards, practice logs |
| Funnel | Notes advancing from capture to use | Source → literature note → permanent note conversion, `times_retrieved`, external outputs |
| Output | Knowledge becoming external artifacts | Ideas, published pieces, manuscripts, rejected permanent notes |

Each scorecard metric gets a 🟢🟡🔴 status from fixed thresholds — for example, graph signal/noise ≥ 20% is green, literature-to-permanent conversion ≥ 10% is green, at least 30% of permanent notes ever retrieved is green. Four of the metrics are north stars: funnel conversion, owner extension rate, external outputs and graph signal/noise. The rest are diagnostic. The scorecard gives you a systemic view in one pass.

**Step 4: Measure retrieval separately**

The scorecard tells you whether notes are being retrieved; it doesn't tell you whether retrieval finds the right ones. For that, log every retrieval: open an entry before searching and close it afterwards with the query, the notes returned, the notes actually used, and the outcome. Two numbers come out of it. **Log coverage** — opened versus closed entries — shows how much retrieval goes unrecorded. **Pooled recall** on a set of judged queries (`$OPEN_BRAIN_ENGINES/retrieval-eval/`) shows how much of what was relevant got found. Judge a change to retrieval by its paired delta against the previous setup on the same queries, not by the absolute level.

The health check adds a few measurements of the pipeline itself — for example, how much extraction expands a source into notes. They are reported as info, as descriptions rather than verdicts.

**Step 5: Decide what to do when a metric stalls**

A plateau or a regression doesn't say what to do next. Find the last deliberate intervention that touched the metric. If the metric moved the right way, keep the type of intervention and adjust only its magnitude. If it didn't move, change the type of intervention instead of stacking another of the same kind. Two rounds of the same type without movement means you've hit a design ceiling: record it as one, with the evidence, rather than trying a third time.

---

## Related

- [Structural Debt](structural-debt.md) — what the metrics will reveal when you first measure a vault that's never been audited
- [The Manual Maintenance Ceiling](manual-maintenance-ceiling.md) — why manual measurement doesn't scale and automation is required
- [The Vault Immune System](immune-system-pattern.md) — the complete maintenance system that includes measurement as a core layer
