# Changelog

*The git history was condensed into a single commit on 2026-10-06, when the framework was separated from a private vault. The dated entries below are the version history.*

## 2026-10-14

**Runnable example.** `example-vault/` is a fictional 33-note vault built from two invented books, plus `run-demo.sh`, which runs autolink, the health check, the enrich scan, one-hop graph retrieval and the eval on a temporary copy. The vault contains six seeded defects, each listed in `example-vault/README.md` with the result the engines are expected to give. Four are caught, one is caught in part (a crowded term shows in the yellow band but not in the red count) and one is missed (a broken link inside a Literature Note). The README has a new "Try it in two minutes" section with real output.

**CI.** `.github/workflows/ci.yml` runs the health-check self-test and the example-vault demo on Python 3.11. It also checks that the demo still catches the seeded defects.

**Engine fixes** found while running the example:

- `health_check.py self-test` no longer exits with "vault not found" when no vault is configured. The self-test builds its own fixture vaults.
- `health_check.py run` no longer aborts without PyYAML. Checks 34 and 35 load modules that exit when PyYAML is missing; that exit now skips those two checks instead of killing the whole run.
- `eval_engine.py`: integrity no longer requires `layer` on Literature Notes, which carry `features` instead. Before, every Literature Note that followed the template counted as non-compliant.
- `eval_engine.py`: `inbox_stale_30d` counts only Inbox notes that are still `processed: false`, the same rule as health check 5. Before, extracted sources counted as stale.
- `eval_engine.py`: the graph signal/noise ratio now leaves out the frontmatter index edges, as `autolink.py` already did. Counting them as signal pushed the ratio close to 100% on any indexed vault. Earlier eval results for this metric are therefore not comparable with new ones.
- `eval_engine.py`: `total_entities` counts distinct notes. `entities.json` keys every note twice, so the count was doubled and `edges_per_entity` halved.

## 2026-10-06

**Skills added.** `skills/` now ships 23 Claude Code skills that implement the framework: the `open-brain` router plus ingest, extract, index, analyze, enrich, autolink, graph, retrieve, promote, synthesize, health, eval, review, improve, execute, flashcards, course, course-evaluate, learn-session, practice-log, escribir and panel. See the README for install and the module → skill map.

**Engines added.** `engines/` ships the Python engines the skills call (autolink, retrieval-eval, enrich-engine, health-engine, eval-engine, vault-scan, course-engine, engine). Python 3.9+, mostly standard library (PyYAML recommended; numpy/scipy only for optional retrieval channels). No data files are shipped.

**Docs brought in line with how the system works today.** All 46 docs were checked against the current skills. The biggest changes:

- **Extraction** — the pipeline order is Ingest → Extract → Index. Ingest triage (how much raw text to keep) and the extraction admission gate (whether to extract at all, scored /12) are separate gates. The seven extraction layers were retired as slots for notes, because slotting produced filler notes; they survive as the `layer` field on Permanent Notes.
- **Enrichment** — the minimum is 3 specific, resolvable search terms; crowding bands are ≤10 / 11–20 / >20 (150 for hubs); failed queries are triaged before they are treated as retrieval decay.
- **Maturation** — the 4-part convergence test, the independence check and the per-cluster extension written by you. Endorsement is explicit approval, separate from `maturity`, which is derived from use.
- **Practice** — the Delegate → Elevate → Challenge loop and the specificity delta are documented as practices you run by hand. Course gates match the course skill (Gate 1 blocks at 70%; Gates 2–3 are scored afterwards by course-evaluate).
- **Retrieval** — six intents including a visual track, the query-expansion gate, one-hop traversal on every retrieval, embeddings off by default. Remote access is described as a generic read-only pattern.
- **Health** — current scorecard, 3-layer eval with a weekly trend. Myelination values corrected (×1.10 reinforce, 1.25 strong, 2.0 cap; decay only on edges traversed at least once).
- **Output** — writing is island-first: you write, your text is kept verbatim, and grounding happens afterwards against the one note that contradicts it.

**README** — module summaries updated; two Module 4 docs that were unlinked are now linked; the duplicate Module 8 entry is removed; design principles restated to match what the system automates; new Skills section.

**Removed** `_config.yml`: no site was built from it.

## 2026-06-19

Initial publication: 46 framework docs across eight modules.
