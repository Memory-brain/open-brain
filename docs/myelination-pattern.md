---
module: module-6-health
related_skills:
  - open-brain-autolink
  - open-brain-retrieve
  - open-brain-health
last_updated: 2026-10-06
---

# Graph Myelination

A knowledge graph that never updates its edge weights doesn't get more useful with use — it just gets bigger. The myelination pattern fixes this by treating usage as data: connections you rely on repeatedly get stronger; connections you once relied on and then abandoned gradually weaken. The graph structure that emerges over months reflects how you actually think, not how you expected to think when you first linked two notes.

---

## What It Is

Graph myelination is an edge-weighting mechanism for knowledge vaults. Every connection between notes starts with a base weight — not a perfectly uniform one: in Open Brain the base is derived from how strongly the link was classified, so most edges start at 1.0 and some a little below. As you use the vault — running retrievals, following reasoning threads, working through a problem — usage is recorded as traversals. A myelination cycle processes those records: traversed edges are reinforced, and edges that were used once but not since receive a small decay. Over time, the graph develops topology.

The name comes from neuroscience. Myelin is the substance that wraps around frequently-used neural axons, making signal transmission faster and more reliable. Neural pathways that are used more become faster; unused pathways atrophy. The brain doesn't maintain all connections equally — it invests in the paths that matter.

Graph myelination applies the same principle to a knowledge vault.

---

## The Biological Analogy

In the nervous system, myelination isn't a deliberate decision — it's an emergent property of use. The axons you fire repeatedly get wrapped in myelin. The axons you don't use gradually lose it. The structure of your neural connectivity is, in part, a record of what you've thought about.

The analogy to a knowledge graph is direct. When you use two connected notes together to answer a question — a note about "feedback mechanisms" and a connected note about "activation thresholds", because that pair is part of how you reason about this domain — that is equivalent to firing a neural pathway. The myelination cycle reinforces it. The connection that proves productive over many sessions becomes a strong edge in the graph.

The connections you added speculatively — "these two might relate" — but never used are the unmyelinated axons. The system doesn't delete them, and it doesn't punish them either: an edge that has never been used simply stays at its base weight.

---

## How the Myelination Cycle Works

**Step 1: Traversal recording.** A traversal is not "an edge the system walked". It is a **pair of notes you used together substantively** in one retrieval. When a retrieval closes its log entry, every pair among the notes listed as used is written automatically as a traversal record: `from` and `to` (note titles), timestamp, the query, and the intent. Recording is automatic on purpose — when traversals depended on someone remembering to log them by hand, they stopped being logged.

**Step 2: Reinforcement.** When the cycle runs (`myelinate.py apply`), it processes all traversals recorded since the last run. For each pair that has an edge in the graph, the edge's weight is multiplied by the reinforce factor — once per traversal — and its traversal counter goes up. Pairs with no edge between them are skipped by apply; usage-derived co-usage edges can be generated from the retrieval log so that pairs you keep using together but never linked still get an edge to learn on.

**Step 3: Decay.** After reinforcement, decay is applied **only to edges that have been traversed at least once**. Never-traversed edges are exempt. Decay used to be global, and on a large graph that destroyed more signal than it created: each pass eroded thousands of never-used edges to reinforce a handful, pulling the whole graph's mean weight down without telling you anything new. Limiting decay to edges with a usage history keeps its meaning — "this was useful once and hasn't been since" — and leaves the rest of the graph alone. A `--decay-all` flag keeps the old behaviour for simulations only.

**Step 4: Threshold classification.** After weights are updated, edges are classified:

- Edges at or above the strong threshold are reported as myelinated.
- Edges below the prune threshold are flagged as decay candidates for review. They stay in the graph.

---

## Reinforcement and Decay

| Parameter | Value | Effect |
|---|---|---|
| Reinforce factor | ×1.10 per traversal | Each traversal adds 10% weight |
| Decay factor | ×0.98 per cycle | Applied only to edges traversed at least once |
| Strong threshold | 1.25 | Reported as "myelinated" |
| Prune threshold | 0.3 | Decay candidate — review before pruning |
| Weight cap | 2.0 | Hard maximum |
| Weight floor | 0.1 | Hard minimum — weight never reaches 0 |

The math: starting from 1.0, an edge needs three traversals to cross the strong threshold (1.10³ ≈ 1.33). Reinforcement compounds, so weights would grow without bound if nothing stopped them — the cap at 2.0 is what stops them, and roughly eight traversals with little decay in between are enough to reach it. An edge that was used and then abandoned loses 2% per cycle; it takes dozens of idle cycles to fall back toward its base weight, and many more to reach the prune threshold. An edge that has never been traversed never moves.

The strong threshold was lowered from an earlier 1.5 because 1.5 turned out to be unreachable in practice: it needed more traversals on a single edge than real usage produced. Pick thresholds against the traversal counts your vault actually generates, not against what feels like "strong".

---

## What You Can Observe (The Report)

The myelination report (`myelinate.py report`, or `query.py myelinated`) surfaces three things.

**Myelinated edges by connection type.** Which relationship types appear among your strongest edges? Open Brain uses typed connections — "extends," "contradicts," "applies to," "feeds," "cross-domain." The types that dominate among strong edges hint at how you reason: comparative and critical, application-focused, or boundary-crossing. Read this as a hypothesis, not a verdict — early on, very few edges will cross the strong threshold, and in practice most traversed edges tend to be usage-derived co-usage edges rather than the typed links you wrote.

**Top myelinated pairs.** The specific note pairs with the strongest connections — the concept adjacencies your thinking returns to most often. They can surface non-obvious structure: two notes you'd never consciously have named as central, but which your usage reveals as a core link. A useful sanity check is to look at the first few strong pairs without context and ask whether you recognise them as genuinely central; if you don't, the recording rule is capturing noise.

**Decay candidates.** Edges that have fallen below the prune threshold. These were used at some point and then abandoned for a long time. They warrant a brief audit: was the connection real? If it still seems meaningful, keep it. If it looks like a historical artifact, pruning it cleans the graph.

---

## The Effect on Retrieval

Be precise about what myelination changes. The retrieval graph hop does **not** read edge weights. It ranks a seed note's neighbours by **edge type priority** plus a capped bonus for the edge's **traversal count** — how many times that pair has actually been used together. The deterministic retrieval engine's hop channel ranks by how many seed notes point at a neighbour. So:

- Usage does shape retrieval: a pair you have used together many times surfaces earlier from either end, through its traversal count.
- Weight and decay do not shape retrieval ranking. Weight feeds the fertility ranking (`query.py fertile`, count × average weight) and the myelination report.

The practical effect: when you retrieve on a topic you work in daily, pairs you have repeatedly used together come up first. On a topic you haven't touched in a year, the hop falls back to edge type alone — the structure is less settled, which is an accurate reflection of a dormant domain.

---

## Cadence

No shipped skill runs the cycle on a timer. Apply is triggered:

- after the graph is regenerated (`autolink --write-graph`), and
- by the health check's myelination check, which runs the report and suggests `apply` when more than 50 traversals are pending.

You can also run it yourself whenever enough traversals have accumulated. Nothing is lost if it runs late: the traversal log accumulates continuously and one apply processes everything pending in a single pass. What *is* lost is visibility — until apply runs, recorded usage hasn't touched any weight, so check the pending count rather than assuming the graph is current.

**Persistence.** Weights and traversal counts are stored as edge metadata and survive graph regeneration: they are carried over by matching each edge on (from, to, type). Renaming a note is the exception — edges are keyed by note title, so a rename drops the myelination learned on that note's edges unless you migrate it. Keep the learned weights of edges that disappear in a separate file, so they can be restored if the edge comes back.

---

## Related

- [The Flat Graph Problem](uniform-graph-traversal.md) — Why all-equal edge weights make graph retrieval progressively less useful at scale
- [Knowledge Graph Signal vs. Noise](knowledge-graph-signal-noise.md) — The prerequisite: typed connections give myelination something meaningful to reinforce
- [The Enrichment Pattern](enrichment-pattern.md) — How connections are typed and created, which is the input that myelination operates on
- [The Vault Immune System](immune-system-pattern.md) — The broader maintenance system that myelination plugs into, alongside structural debt detection and health scoring
- [Multi-Modal Retrieval](multi-modal-retrieval.md) — How graph traversal fits into the retrieval modes and when to use it
