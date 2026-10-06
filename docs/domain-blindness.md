---
module: module-3-maturation
related_skills:
  - open-brain-synthesize
  - open-brain-health
last_updated: 2026-10-06
---

# Domain Blindness: Not Knowing What You Know

## The Problem

You've been reading and taking notes about sports nutrition for two years. You have 120 notes on the topic. Someone asks: "What's your view on how endurance athletes should approach carbohydrate intake?" You know you have notes on this. You search. You find fragments from four different books, disconnected. You can't form a coherent position, because you don't have a map of what you actually know — you have a pile.

This is **domain blindness**: not knowing what you know, or what you're missing, within a domain you've been actively building. It's the failure mode of a vault that has grown in volume without ever producing a structured view of its own coverage.

Domain blindness makes knowledge accumulation essentially random. Without knowing what you already know, you re-read things you've already captured. Without knowing what you're missing, you can't direct your reading toward actual gaps. You end up in a permanent state of learning that never consolidates into competence you can act on or communicate.

---

## Why It Happens

### Note-level thinking without domain-level structure

PKM tools are excellent at storing and linking individual notes. They are not designed to give you a bird's-eye view of a domain. When every note is equally visible — or equally buried — there's no natural way to see the shape of what you know. You can see trees but not the forest. After years of note-taking, you may have 50 notes "about strategy" that collectively cover 3 of the 8 sub-topics that constitute a working understanding of strategy, with deep over-coverage in the 3 you happened to read about most and complete absence in the other 5.

### No coverage map

A coverage map is a structured inventory of what layers and sub-topics exist in your vault for a given domain, versus what's missing. Without one, you can only assess your knowledge by browsing notes — which gives you an impression of coverage, not a measurement of it. The impression is always inflated. The gaps are invisible until you need them.

### The illusion of coverage

Having many notes about a topic feels like knowing the topic. It isn't. Coverage in your note-taking is a function of what you happened to read, not what's important to understand. A topic where you've read 4 popular books and 0 primary research papers will look well-covered in your vault and be severely biased in its coverage. Domain blindness is partly a failure of meta-cognition: you don't know what you don't know because you've never systematically asked.

---

## How to Detect It

**The articulation test**: Without looking at your vault, write a 200-word summary of what you know about a domain you've been actively studying. Then open your vault and check: are there major sub-topics in your notes that didn't appear in your summary? Are there things you wrote in your summary that aren't supported by any notes? The gap between what you can articulate and what your vault contains is a measure of domain blindness.

**The layer audit**: For any domain, inventory your notes by layer. Open Brain records the layer of each note in its `layer` frontmatter field, so the audit is a count, not a judgment call:

| Layer (`layer` value) | What it holds | Count for your domain | Gap? |
|---|---|---|---|
| `knowledge` | Core concepts and definitions | | |
| `compression` | The few principles you would carry in your head | | |
| `mental-model` | Frameworks for how to think about the domain | | |
| `application` | Cases where the idea was actually applied | | |
| `artifact` | Ready-to-use templates, checklists, tools | | |
| `decision` | Criteria for when to use what | | |
| `diagnosis` | Failure modes and how to recognize them | | |
| `coaching` | What to fix at each level of skill | | |
| `practice` | Exercises and drills | | |

You don't have to fill this table by hand: `open-brain-synthesize` runs `synthesize_engine.py domain-report "<Domain>"`, which returns layer coverage and gaps for the domain (see below).

A domain where you have 40 concept notes and 2 application notes is not a domain you can act in — you understand it abstractly but can't use it. A domain with 30 application notes and 5 concept notes is one where you can execute without understanding the principles well enough to adapt.

**The question test**: Enumerate the 8–10 questions a practitioner would need to answer to be genuinely competent in a domain. For each question, check whether your vault has a defensible answer. Questions without coverage are gaps.

---

## How to Fix It

**Build a domain synthesis map**

A domain synthesis map is a structured document (not a tag, not a search — an actual document) that captures:
- The 5–8 sub-topics that constitute competence in this domain
- Which layers you have coverage in for each sub-topic
- Which layers are missing or thin
- Which notes have been promoted to permanent claims vs. remaining as literature notes

This document doesn't need to be long — a table with sub-topics as rows and layers as columns, with a count and a quality assessment in each cell, is sufficient. The act of creating it forces you to confront what's actually there rather than what feels like it's there.

In Open Brain this map lives in the domain's Domain Index, and the work is split. The synthesize engine does the counting: layer coverage and gaps, convergence candidates (literature notes from different sources that share at least two `search_terms`), skill-cluster candidates, and the promotion backlog (literature notes no permanent note references). The AI then writes the competency map into the Domain Index, and nothing is created there without your confirmation.

**Gap-directed reading**

Once you have a coverage map, the next source you read should target a gap. Not "this book looks interesting" — "this book covers the failure modes layer in domain X, which I have almost nothing on." This is the shift from random accumulation to deliberate construction.

**Regular domain reviews**

A domain review is a short session, once per quarter, for each active domain. Run `open-brain-synthesize` on the domain and use its report:
1. Refresh the coverage map from the engine's layer coverage
2. Identify the 2–3 biggest remaining gaps
3. Pick the next source to fill the highest-priority gap
4. Take the convergence candidates and promotion backlog to `open-brain-promote` for the ones ready to be promoted

The review prevents domain blindness from reestablishing itself after you've cleared it once.

---

## Related

- [The Literature Note Graveyard](literature-note-graveyard.md) — graveyard vaults are a leading cause of domain blindness
- [Premature Synthesis: Building on Thin Evidence](premature-synthesis.md) — domain blindness enables premature synthesis (you don't know what you're missing)
- [The Maturation Ladder: From Captured to Owned](maturation-ladder.md) — domain synthesis is the final rung
- [Retrieval Decay in Knowledge Vaults](retrieval-decay.md) — domain blindness and retrieval decay compound each other
