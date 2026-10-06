# Route card: graph

> **This is a routing card, not the skill.** The full, current rules live in the `open-brain-graph` skill. Once you have routed here, load `open-brain-graph` and follow its `SKILL.md` (and the references it names) end to end. Do not execute from this card.

## Route here when

- Contradictions / tensions between notes / fertile PNs / cross-domain PNs / sandwiches (Cases connecting PNs).
- Orphans, demanded concepts, validation gaps (claims with no Case).

## What the skill does

Typed queries over the knowledge graph (`autolink/graph.jsonl`). The determinism lives in the query scripts; this skill orchestrates them, frames the result with judgment (never raw output) and offers a single concrete next step. It checks graph freshness first.

## Route elsewhere when

- "What do I know about X": **retrieve**.
- "Promote this LN": **promote**.
- "Audit my vault": **health**.

## Usual next step

- **autolink**, if the graph has not been generated yet.
- **ingest** / **index**, when referenced sources have no Dossier.
