---
name: open-brain-graph
description: 'Queries over the vault''s typed graph (contradictions, fertile PNs, cross-domain,
  sandwiches). The deterministic part lives in autolink/query.py — this skill only orchestrates and applies judgment
  to the result. Triggers: contradictions, fertile PNs, cross-domain, sandwich, open-brain graph'
metadata:
  version: 2.1.0
  status: canonical
  requires_engine:
  - name: autolink.py
    version: unpinned
  - name: demand.py
    version: unpinned
  - name: indexer.py
    version: unpinned
  - name: query.py
    version: unpinned
  - name: update_graph.py
    version: unpinned
  - name: validation_gap.py
    version: unpinned
  consumes:
  - A typed graph already generated in autolink/graph.jsonl (not stale)
  - A structural query type requested by the user (contradictions, fertile, cross-domain, sandwiches,
    demand, validation gap)
  produces:
  - A filtered result framed with judgment (never raw output)
  - A single concrete next step offered to the user
  handoffs:
  - skill: open-brain-autolink
    when: if autolink/query.py does not exist yet (the graph has not been generated)
    requires_approval: true
  - skill: open-brain-ingest
    when: when demand.py detects referenced sources (source bucket) without a Dossier
    requires_approval: true
  - skill: open-brain-index
    when: when demand.py detects sources without a Dossier, to create the Source Outline
    requires_approval: true
---

# Open Brain — Graph (v2.1, orchestrates autolink/query.py)

Structural search (not semantic — that is `open-brain-retrieve`). All the mechanics are already
deterministic in `autolink/query.py`. Your job: pick the right query, run it, and
**filter + frame** the result with judgment. Do not paraphrase or paste raw output.

## Resolving paths — MANDATORY, read this before doing ANYTHING

- `$OPEN_BRAIN_VAULT` = the root of your Markdown vault.
- `$OPEN_BRAIN_ENGINES` = the directory holding the engine scripts. The graph and its scripts live in `$OPEN_BRAIN_ENGINES/autolink/`.

If your agent runs file tools and shell in different environments (e.g. a sandbox that mounts the
directories under another path), resolve each variable separately for each context.

**Checking that the graph exists (Step 0, before any query):**

1. Try to `Read` `$OPEN_BRAIN_ENGINES/autolink/graph.jsonl`.
   If it returns content → the graph exists. Continue.
2. ONLY if Read fails, try in the shell: `ls "$OPEN_BRAIN_ENGINES/autolink/graph.jsonl"`
3. If both fail → the graph does not exist. Suggest running `open-brain autolink`.

**NEVER declare that autolink does not exist without having tried the COMPLETE and CORRECT path.**
The most common mistake is running `ls autolink/` without the full path, or using the file-tools
path in the shell (or vice versa). Each context has its own path.

## Graph freshness

The graph lives in `$OPEN_BRAIN_ENGINES/autolink/graph.jsonl`. If it is empty or stale (>7 days — compare
the file's modification date with today), regenerate it first with:

```bash
cd "$OPEN_BRAIN_ENGINES/autolink"
python3 indexer.py && python3 autolink.py --all --write-graph --quiet
```

## Trigger → command table

Run from `$OPEN_BRAIN_ENGINES/autolink/`:

| The user says | Command |
|---|---|
| contradictions / tensions / which PNs clash | `python3 query.py contradictions --limit 10 --type permanent` |
| fertile PNs / root PNs | `python3 query.py fertile --type permanent --limit 10` |
| cross-domain / PNs that cross domains | `python3 query.py cross-domain --limit 15` |
| sandwiches / Cases connecting PNs | `python3 query.py sandwich --limit 5` |
| which cases apply this PN | `python3 query.py cases-of "<exact title>"` |
| orphan PNs | `python3 query.py orphans --limit 20` |
| what to write / demanded concepts / ranked broken links | `python3 demand.py --limit 20` |
| what to validate / claims without a Case / validation queue | `python3 validation_gap.py --limit 20` |
| regenerate the graph | `python3 indexer.py && python3 autolink.py --all --write-graph --quiet` |
| update the graph for [note] | `python3 update_graph.py "<path>"` |

Add `--json` if you need to parse; otherwise read the normal output.

Do NOT use graph for "what do I know about X" (that is `open-brain-retrieve`), "promote this LN"
(`open-brain-promote`) or "audit my vault" (`open-brain-health`).

## The only thing you add (judgment on the output)

- **contradictions**: pick the 1–3 most interesting (prioritize `refuta` (refutes) > `contradice` (contradicts), and
  PN↔PN > LN↔LN). Frame them: *"Tension between [axis A] and [axis B] — material if you write about Y."*
- **fertile**: if they ask for a domain, keep the top 5 of that domain.
- **cross-domain**: group by domain pair and say how many connections each pair has.
  Concentrations of 3+ in the same pair are Article candidates.
- **sandwich**: say which PNs each Case connects and ask whether that intersection interests them.
- **validation_gap**: PNs that carry weight (high `times_retrieved` + graph in-degree) but that NO Case validates. It is untested theory. Top 3–5 = claims worth grounding in a real experience. Do NOT fabricate Cases (they are the user's real experiences). Also look at `ORPHAN CASES` (experiences already captured without `principles_validated` — the cheapest win is linking them) and `BROKEN LINKS` (re-point to the renamed PN). Frame it: *"You cite [[X]] without any Case — is there a real decision/experience that validates it?"*
- **demand**: concepts referenced many times that do NOT have a note — the graph tells you what to write. Keep the `concept` bucket (ignore `source`/`archive`). The top 3–5 by reference count are direct candidates to create as Search Term + PN. Frame it: *"You cite [[X]] N times without having a note — shall we create it?"*. For sources use `--all-buckets` and hand off to `open-brain-ingest`/`open-brain-index`.
- Do not try to explain relations the script marked `menciona` (mentions, no verb) — admit it and move on.

## After the query: a single next step

Offer ONE concrete step, not a menu:
- contradiction → *"Shall I open [PN-A] and [PN-B] so you can see the exact tension?"*
- cross-domain concentration → *"There are 3 links between domain A and domain B. Shall I open an `open-brain-escribir` session on that thesis?"*
- sandwich → *"This Case connects 2 PNs. Shall I open an `open-brain-escribir` session on that thesis?"*

The query is the means; the piece the user writes is the end.

## Note

This skill does NOT bundle scripts: it depends on the autolink engine being installed in
`$OPEN_BRAIN_ENGINES/autolink/` (created/maintained via `open-brain-autolink`). If `query.py` is missing, run `open-brain-autolink` first.
If a relation is misclassified, fix it in `autolink/patterns.py`, not in this prompt.
