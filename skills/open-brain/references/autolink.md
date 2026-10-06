# Route card: autolink

> **This is a routing card, not the skill.** The full, current rules live in the `open-brain-autolink` skill. Once you have routed here, load `open-brain-autolink` and follow its `SKILL.md` (and the references it names) end to end. Do not execute from this card.

## Route here when

- Regenerate the graph / update autolink.
- Silently, after any operation that creates or modifies notes.

## What the skill does

Rebuilds the typed knowledge graph (`autolink/graph.jsonl`) plus its entity index, n-ary hyperedges and myelination traversals, and provides the SurpriseFilter novelty check used by ingest.

## Route elsewhere when

- Answering relational questions: **graph** consumes the rebuilt graph.

## Usual next step

- None; it is the silent tail of the note-creating chains.
