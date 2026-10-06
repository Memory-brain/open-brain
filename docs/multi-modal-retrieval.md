---
module: module-5-retrieval
related_skills:
  - open-brain-retrieve
  - open-brain-graph
  - open-brain-autolink
last_updated: 2026-10-06
---

# Multi-Modal Retrieval: Four Ways to Access What You Know

## What It Is

Multi-modal retrieval is the practice of using different retrieval methods — each optimized for a distinct type of question and a distinct type of cognitive task — rather than routing all knowledge access through a single search interface.

The central insight is that "I need to access my vault" actually describes several qualitatively different intentions. Finding what you know about a topic is not the same operation as exploring connections across a domain, which is not the same as surfacing contradictions before a decision, which is not the same as collecting material to write with. Collapsing these into one operation — typing keywords into a search box — produces mediocre results for most of them and excellent results for almost none.

Multi-modal retrieval assigns each query intent to the method most appropriate for it. The result is not just faster retrieval — it's qualitatively different access to knowledge. Questions you couldn't answer with keyword search become answerable. Connections you'd never have found by browsing get surfaced automatically. Knowledge you built two years ago becomes as accessible as knowledge you built last week.

---

## Mode 1: Intent-Based Search

### What it is

Before running any query, classify what you're trying to do. The classification determines which entry point to use.

### The six retrieval intents

| Intent | The question you're asking | Priority order |
|---|---|---|
| **Operative** (default) | What do I know about X? | Active manuscript → most mature permanent notes → less mature ones → literature notes (only if no permanent note covers it) |
| **Exploratory** | What do the authors and experts I've read say about X? | Literature notes by author → your permanent notes as contrast → cases |
| **Critical** | Where do my sources and my own notes disagree about X? | Every literature note on the topic (grouped by author) + every permanent note on it, side by side |
| **Expressive** | What material can I draw on to write about X? | Ideas/drafts → mature permanent notes → growing ones |
| **Serendipity** | What am I not seeing? | Under-used literature notes + orphan permanent notes + cross-domain bridges, least-retrieved first |
| **Visual** | What shape or pattern could represent X? | Design references (patterns → references) → linked permanent notes → source notes → images |

Visual is a separate **track**, not an alternative: whenever a query asks for something visual, it runs alongside whichever text intent applies and returns design references rather than notes, in its own section.

Recent context is not an intent. Every retrieval starts by reading a hot cache of recent work — last session's focus, recent changes, open threads, stale-knowledge warnings — and treats it as a hint, not a boundary: at least one probe always goes outside what the hot cache shows, because it ranks by availability, not relevance.

### How to use it

Before querying, ask: "What am I trying to do with the result?" If you can't answer, default to Operative intent and be prepared to switch modes when the initial results suggest a different framing is needed.

Intent decides the priority order, but it is not the step that moves recall most. In the reference vault that was **query expansion**: before searching, the assistant drafts 8–15 terms the vault actually uses for this task (nouns and claim phrases, not instructions), shows them, and waits for you to confirm or correct them — a gate, not a suggestion. Then, before reading any note body, it shows the 3–5 candidate notes it is about to anchor on and keeps going; if you redirect it, your correction becomes the new expansion. Every probe covers the concept in each language the vault is written in, a synonym, and a negative or failure phrasing.

Candidates come from two pools: the assistant's own grep and graph hop, and a deterministic engine (`$OPEN_BRAIN_ENGINES/retrieval-eval/eval_retrieval.py`) that fuses BM25, metadata match, graph hop, LSA and bridge channels over the whole vault. The engine's output is a candidate list; triage and synthesis stay with the assistant. Semantic embedding matching is optional and off by default — the confirmed expansion is what bridges the vocabulary gap.

---

## Mode 2: Conversational Q&A

### What it is

A multi-turn session that maintains context across questions and synthesizes answers as prose rather than returning individual notes. Unlike a single query that produces a list, a conversational session follows a thread — each answer can trigger a follow-up question, and the system maintains awareness of what's already been covered.

### When to use it

- When you're exploring a domain you haven't visited in a while
- When you want to think through a question by testing your knowledge against your vault
- When a single query isn't enough — you need to navigate to an answer through multiple steps
- When you want a synthesized understanding, not a collection of note fragments

### Example session structure

```
Query:     What do I know about decision-making under uncertainty?
Response:  [Synthesized answer from relevant notes]

Follow-up: What contradicts the main framework in that answer?
Response:  [Contradictions and qualifications from other notes]

Follow-up: What real cases from my own experience relate to this?
Response:  [Connected case notes]
```

### What it produces

A conversational session generates a transcript — a record of the questions asked and answers synthesized. This transcript is itself a reusable reference: a curated synthesis of what you know about a topic, produced through a structured exploration, stored for future use.

---

## Mode 3: Graph Traversal

### What it is

A structural query over the typed knowledge graph — the network of relationships between notes, where each connection carries a semantic type (contradicts, extends, exemplifies, validated_by, etc.).

Graph traversal doesn't search for notes that mention a keyword. It searches for notes that stand in a specific relationship to each other or to a given note. This enables queries that are structurally impossible with text search.

### The four core graph queries

| Query type | What it finds | When to use it |
|---|---|---|
| **Contradiction scan** | Pairs of notes that contradict each other within a domain | Before a consequential decision in that domain |
| **Fertile node query** | Notes with the highest number of incoming connections | When you want to identify your most load-bearing ideas |
| **Case-theory query** | Theoretical notes with no connected case examples | To find theories that need grounding in real experience |
| **Cross-domain bridge** | Connections between notes from different domains | When looking for transferable insights or unexpected analogies |

### The compounding effect of myelination

Graph traversal is not just retrieval — it feeds reinforcement. When a retrieval closes, every pair of notes you used together is recorded as a traversal. Weights only change later, when the myelination cycle runs (`myelinate.py apply`): traversed edges are reinforced, and edges that were used once and then abandoned slowly decay. Retrieval's graph hop doesn't rank by weight; it ranks neighbours by edge type plus a capped bonus for how many times the pair has been used together — so the paths you actually use do surface earlier in future queries.

This mirrors the neurological process of myelination — the insulation of frequently-fired neural pathways that makes them faster and more reliable. In a knowledge vault, myelination means that the reasoning structures you actually use compound over time: the more you traverse a connection, the more visible and accessible it becomes in subsequent retrievals.

The practical implication: a vault that has been actively used for retrieval over years is qualitatively more valuable than a vault that has only been used for authoring. The retrieval history is structural knowledge that makes future retrieval better.

---

## Mode 4: Remote Access

### What it is

Retrieval via a queryable endpoint rather than the local application — enabling vault access from mobile devices, different computers, AI assistant conversations, and any other context where the primary authoring application isn't available.

### When to use it

- Mobile: You're away from your desk and need to retrieve or reference vault knowledge
- AI integration: You want an AI assistant to have access to your specific knowledge during a conversation
- Cross-tool: You're working in a different application and need vault access without switching contexts
- Collaboration: You want to share or discuss specific vault content with someone else

### The architecture

No shipped Open Brain skill provides remote access; it is a pattern you implement. The simplest version that works is a small read-only MCP server over the vault with three tools:

| Tool | What it does |
|---|---|
| `search` | Keyword query (a few terms work better than a sentence) → ranked notes with title, path and snippet |
| `read` | Note path → full note content |
| `list` | Folder → the notes in it, for orientation |

Requests carry a bearer token. If you want to capture from elsewhere, add write tools behind a **separate** write token — the read token doesn't lack a permission check, it lacks the permission — and have writes land in a server-side inbox you review and pull into the vault, never directly in it.

Once this exists, the vault travels with you: any MCP-capable assistant — on another computer or on your phone — can search, read and synthesize from your notes. Keep expectations honest: remote search is lexical, the client assistant does the synthesis, and intent routing, query expansion, graph queries and myelination stay local. Remote retrievals don't write to the Retrieval Log or feed myelination unless you build that in.

---

## When to Use Which Mode

| Situation | Recommended mode |
|---|---|
| Quick factual lookup | Intent-based search (Operative) |
| Pre-decision research | Graph traversal (contradiction scan) + Conversational Q&A |
| Writing preparation | Intent-based search (Expressive) + Conversational Q&A |
| Domain review after time away | Conversational Q&A |
| Finding structural patterns in knowledge | Graph traversal (fertile nodes, cross-domain bridges) |
| Access from mobile or another machine | Remote access (keyword search + read) |
| Deep exploration of a new connection | Conversational Q&A starting from a graph finding |

There is no hierarchy among the modes — they are complementary, not competing. A single retrieval session often uses multiple modes in sequence: a conversational session might begin with an intent-based query, follow a contradiction found via graph traversal, and later reread a specific note through the remote layer.

---

## What It Is Not

**Not full-text search.** Multi-modal retrieval builds on top of search but is not reducible to it. Keyword search is one input among several. Graph traversal follows typed structure, conversational sessions carry context across turns, and intent routing decides what to read first. Remote access is the exception: it is keyword search plus reading, with the client assistant doing the synthesis.

**Not folder browsing.** Organizing notes into folders is an authoring concern. Retrieval should not depend on having organized correctly at the time of capture. Multi-modal retrieval is index-based and graph-based, not folder-based.

**Not just keyword matching.** The most important queries a knowledge worker needs to answer — "what contradicts my current view?", "what's connected across domains?", "what do I know that's relevant to this decision?" — are not answerable by matching words. They require semantic understanding of note relationships.

**Not a one-time configuration.** The graph traversal and myelination modes become more powerful the more the vault is used for retrieval. The value compounds over time with use — which means delaying adoption has a genuine cost.

---

## Measuring Impact

| Metric | Baseline (search-only) | With multi-modal retrieval |
|---|---|---|
| Pooled recall on judged queries | Measure once as the baseline | Accept a change only if its paired delta is positive |
| Time to useful answer | Multiple attempts + phrasing variants | Single intent-classified query |
| Contradictions surfaced before decisions | Near zero | Systematic (graph query) |
| Cross-domain connections discovered | Accidental | Queryable |
| Vault access frequency | Limited to desk + app | Any device, any context |

Make the measurement instrumental rather than self-reported. Every retrieve opens an entry in a Retrieval Log before it searches and closes it at the end — query, expansion, notes returned, notes used substantively, outcome, gaps, what the retrieval was for. The gap between opened and closed entries is itself a measurement. From the logged queries, build a golden set of judged queries and compute pooled recall with `$OPEN_BRAIN_ENGINES/retrieval-eval/`. Judge changes to the retrieval method by the **paired delta** against the previous configuration on the same queries, with a confidence interval — not by the absolute level, which depends on how hard your queries are.

---

## Related

- [The Search Box Bottleneck: Why Text Search Fails Knowledge Vaults](search-box-bottleneck.md)
- [Isolated Retrieval: Finding Notes Without Following the Thread](isolated-retrieval.md)
- [Knowledge Portability: When Your Vault Is Stranded on Your Laptop](knowledge-portability.md)
- [The Practice Loop: From Passive Notes to Active Skills](practice-loop.md)
