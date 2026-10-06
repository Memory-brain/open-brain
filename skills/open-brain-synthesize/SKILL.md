---
name: open-brain-synthesize
description: 'Builds and maintains knowledge domains. The scan (notes by layer, convergence and cluster→skill
  candidates, promotion backlog, feeders) is done by $OPEN_BRAIN_ENGINES/engine/synthesize_engine.py,
  which reuses vault-scan; the AI applies the convergence test, writes the synthesis PNs and evaluates
  skills. Triggers: synthesize the domain, what gaps do I have, domain index, vault-synthesize,
  open-brain synthesize.

  '
metadata:
  version: 2.1.0
  status: canonical
  requires_engine:
  - name: synthesize_engine.py
    version: unpinned
  consumes:
  - A domain name to scan within an Open Brain vault
  - vault-scan installed alongside the engines ($OPEN_BRAIN_ENGINES/vault-scan/)
  - Existing Literature Notes and Permanent Notes for that domain
  - A prior domain-report to compare against for loop-stop detection
  produces:
  - A domain-report JSON (layer coverage, convergence candidates, skill-cluster candidates, promotion
    backlog)
  - New synthesis Permanent Notes when a convergence passes the 3-part synthesize test
  - Updated Domain Index counts (note/PN/LN counts, last_synthesized)
  - Proposed skill-cluster candidates surfaced for the vault owner's approval
  handoffs:
  - skill: open-brain-ingest
    when: two consecutive domain-reports show no progress and the gap is due to lack of sources
    requires_approval: true
  - skill: open-brain-extract
    when: two consecutive domain-reports show no progress and the gap is due to lack of sources
    requires_approval: true
---
# Open Brain — Synthesize (v2, engine + vault-scan)

Domain architect: gathers a domain's notes, finds convergences between sources, creates synthesis
PNs, discovers trainable skills and updates the Domain Index. The plumbing lives in
`$OPEN_BRAIN_ENGINES/engine/synthesize_engine.py`, which **reuses vault-scan**. Your job as the AI:
the **judgment** — applying the convergence test, writing the PNs, evaluating skill candidates, and
the competency map.

Model: **the assistant orchestrates · engine + vault-scan execute · any UI you use consumes the output.**
Requires `vault-scan/` (like autolink) at `$OPEN_BRAIN_ENGINES/vault-scan/`. The engine finds it on
its own via `OPEN_BRAIN_ENGINES` (or by walking up from its own location).

## Phase 1 — the engine scans (no thinking needed)

```bash
python3 "$OPEN_BRAIN_ENGINES/engine/synthesize_engine.py" domain-report "<Domain>"
```

Returns a JSON with: PN/LN counts, **layer coverage + gaps**, **convergence_candidates**
(pairs of LNs from DIFFERENT prefixes sharing ≥2 search_terms), **skill_cluster_candidates**
(anchor terms with ≥5 PNs covering ≥3 layers from ≥2 sources), **promotion_backlog** (LNs not
referenced by any PN, by prefix), and **existing_skills_feeders** (endorsed/total audit).

## Phase 2 — YOU apply the judgment (irreducible)

1. **Convergence test** on each candidate: create a synthesis PN only if (a) the sources are different,
   (b) they use different vocabulary but reach the same point, (c) the insight is specific and actionable.
   If it passes (a)(b) but not (c) → weak signal in the report, not a PN. Tensions are worth more than
   convergences if both sides have evidence and there is a boundary condition. This is the 3-part
   synthesize test (promote adds the counterfactual as a 4th).
2. **Write the synthesis PN** (this is yours): self-contained title, 2-4 sentences without hedging,
   why-it-matters, evidence citing each source, boundary conditions, typed connections. 4-6 search_terms.
3. **Evaluate the skill_cluster_candidates** against the 5 criteria: mass (5+ PNs), spread (3+ layers),
   multi-source (2+ prefixes), not already covered, trainable in a session with a rubric. The engine already
   checked mass/spread/multi-source; you decide "not covered" and "trainable". Present proposals; do NOT
   create files or touch `Resources/Practice Capabilities.md` without the vault owner's confirmation.
4. **Cross-domain serendipity** and **competency map**: your judgment.

## Phase 3 — the engine updates the index

```bash
python3 "$OPEN_BRAIN_ENGINES/engine/synthesize_engine.py" index-update "<Domain>" --json '{"note_count":N,"pn_count":N,"ln_count":N}'
```

Updates counts + `last_synthesized`/`updated`. You write the Domain Index content (competency map,
skills table) separately.

## Loop discipline — when to stop

Synthesize is a loop, not a one-shot: run it, create a synthesis PN, and **scan again** to see
whether the gap closed. But it is a **bounded** loop:

- **Observable success gate**: the cycle succeeded if the `domain-report` shows **one convergence
  candidate fewer** or **one more coverage layer** after writing the PN — not "until the domain is
  complete".
- **No-progress stop**: if two consecutive `domain-report`s return the same number of candidates and
  the same coverage, **stop**. The domain does not need more synthesis right now; it needs more
  sources (redirect to `open-brain-ingest` / `open-brain-extract`) or more output (use what it
  already holds in real work rather than synthesizing further).
- **Anti-overfitting**: the engine's `fertility`/`convergence_score` is a work signal, NOT the judge of
  whether the PN is good. The judge is still the convergence test (a)(b)(c) plus the vault owner's
  later endorsement, which is a separate gate.
- **Terminal states**: `synthesized` (PN created and gap reduced) · `no-convergence` (nothing passes
  the test, a clean no-op) · `needs-sources` (the gap comes from missing sources, not missing
  synthesis) · `stagnated` (two runs without progress). Never report "I scanned the domain" as success.

## What lives in the engine (no longer in this prompt)

Gathering the domain's notes · layer coverage + gaps · surfacing convergence candidates ·
surfacing cluster→skill candidates (mass/spread/multi-source) · promotion backlog ·
feeder audit · updating the index counts.

## Rules (judgment / policy)

- Do NOT create a Domain Index, cross-domain PNs, or skills without the vault owner's authorization. Surface, do not create.
- Do NOT create a PN for a convergence that fails the 3-part synthesize test (promote adds the counterfactual as a 4th) — weak signal.
- Do NOT assign `confidence: high` without multiple sources or a validating Case.
- Do NOT browse whole folders — the engine already gathers by domain (via vault-scan).
- Do NOT generate course HTML — that is `open-brain-course`. Synthesize discovers and scaffolds; course generates.
- Synthesis PNs: do not write `maturity` — it is derived from the note's counters (a new PN derives to `seed`). Sources from ≥2 LNs from different sources.

## Mentor metrics (optional)

For questions like "whose ideas have I distilled most", "which mentor do I actually use" or "what
have I read but not distilled", do not count notes by hand. This step is optional: if you have
`$OPEN_BRAIN_ENGINES/mentor-engine/mentor_metrics.py`, use that deterministic engine; if not, say the
metric is unavailable rather than estimating it.

```bash
python3 "$OPEN_BRAIN_ENGINES/mentor-engine/mentor_metrics.py" run --json
```

Returns, per mentor: `lns` (readings), `pns` (Permanent Notes citing their LNs), `distilled` and
`conversion` (what percentage of their readings reached a judgment), and `sessions` (appearances in
the Retrieval Log, which is the real usage: the frontmatter `times_retrieved` counters capture only a
fraction of that signal). Also `canon`, `undistilled`, the categories that are not mentors, and
`dangling`: attributions pointing to a mentor without a note.

Sorting by reading volume and sorting by distilled judgment usually give very different lists. If
the question is "who have I learned from", sort by `pns`, not by `lns`.
