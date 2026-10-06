---
name: open-brain-eval
description: 'Evaluates the performance of an Open Brain vault in 3 layers: L1 mechanical (script), L2 judgment
  (LLM rubric on a sample), L3 outcome (weekly trend). Phase 4 adds the refinement rule (REFINE, via
  EnvHarness/EnvRigger) to decide whether to adjust magnitude or change the type of intervention when a
  metric plateaus or regresses. Phase 5 adds a Skill Health Check from practice logs (degradation, stagnation,
  abandonment). Triggers: eval vault, evaluate the vault, how is my vault doing, vault metrics, scorecard,
  open-brain eval, run the eval, deep eval'
metadata:
  version: 1.1.0
  status: canonical
  requires_engine:
  - name: eval_engine.py
    version: unpinned
  - name: skill_health.py
    version: unpinned
  consumes:
  - The current state of the vault (notes, frontmatter, graph, logs)
  - History of previous evals to compute the trend
  - Practice logs for the Skill Health Check
  produces:
  - JSON+MD report with a 6-dimension scorecard and traffic lights
  - Historical trend of the north-star metrics
  - Refinement verdict (adjust magnitude / change type / design ceiling) per metric in plateau or regression
  - Skill Health section (degradation, stagnation, abandonment)
  handoffs:
  - skill: open-brain-health
    when: to resolve integrity gaps/fixes detected in the eval
    requires_approval: true
  - skill: open-brain-enrich
    when: for detected search-term gaps
    requires_approval: true
  - skill: open-brain-promote
    when: for the backlog of PNs pending promotion
    requires_approval: true
  - skill: open-brain-synthesize
    when: for detected domain gaps
    requires_approval: true
  - skill: open-brain-improve
    when: if the Skill Health Check detects degradation, using the recurring gaps as input
    requires_approval: true
---

# Open Brain — Eval (v1.1, 3 layers + refinement)

Evaluation system for the vault. Three independent layers, each with its own cost
and depth:

- **L1 Mechanical** — deterministic script, 0 tokens, always runs.
- **L2 Judgment** — an LLM evaluates a sample of notes against a rubric. On demand only.
- **L3 Outcome** — historical trends from past evals. Weekly review.

## Phase 1 — run the engine (ALWAYS)

```bash
python3 "$OPEN_BRAIN_ENGINES/eval-engine/eval_engine.py" run
```

`$OPEN_BRAIN_VAULT` is the vault root (where Permanent Notes, Literature Notes, etc. live);
`$OPEN_BRAIN_ENGINES` is the directory that holds the engine scripts.

It writes two files to `Resources/Evals/`:
- `YYYY-MM-DD_HHMMSS.json` — raw metrics
- `YYYY-MM-DD_HHMMSS.md` — readable report with the trend vs. the previous eval

Useful flags:
- `--json` → raw JSON to stdout (for programmatic consumption)
- `--dim integrity` → a single dimension (integrity|graph|pipeline|practice|funnel|output)

The script measures 6 dimensions:

| # | Dimension | What it measures |
|---|---|---|
| 1 | `integrity` | Frontmatter compliance %, broken links, orphan PNs, count drift |
| 2 | `graph` | Signal/noise ratio, edge type distribution, generative %, myelination |
| 3 | `pipeline` | Inbox stale, source coverage, endorsement states, owner extension rate |
| 4 | `practice` | SM-2 accuracy per domain, weak cards, practice logs |
| 5 | `funnel` | Source→LN→PN conversion, times_retrieved, external_outputs |
| 6 | `output` | Ideas, published items, manuscripts, rejected PNs |

## Phase 2 — read and present the report

1. Read the generated `.md` — do NOT recompute it yourself.
2. Read `Resources/Hot Cache.md` for context (if a recent session was extraction-heavy,
   frame the inbox backlog as "normal after extraction").
3. Present the **Scorecard** first (table with 🟢🟡🔴 traffic lights).
4. Then the 6 dimensions with deltas vs. the previous eval.
5. Close with 3-5 prioritized actions: which skill to run for each gap.

### Scorecard thresholds

| Metric | 🟢 | 🟡 | 🔴 |
|---|---|---|---|
| Frontmatter compliance | ≥95% | ≥80% | <80% |
| Graph signal/noise | ≥20% | ≥10% | <10% |
| Owner extension rate | ≥5% | ≥1% | <1% |
| Inbox stale rate | ≤20% | ≤50% | >50% |
| LN → PN conversion | ≥10% | ≥5% | <5% |
| PNs ever retrieved | ≥30% | ≥15% | <15% |
| External outputs | ≥20 | ≥5 | <5 |

"Owner extension rate" is the share of notes carrying an extension written by you (the vault owner) in your own words, as opposed to text written only by the source author or the assistant. The engine may label it with its own field name; read it from the report.

## Phase 3 — L2 Judgment (only if the user says "deep eval")

If the user asks for a "deep eval", "L2", or "audit the quality":

### 3a. Note Quality Sample (10 random notes)

Pick 10 PNs at random (or the 10 most retrieved). Evaluate each against the rubric:

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| **Atomicity** | Mixes 2+ ideas | Clear main idea but noisy | 1 idea, clean |
| **Actionability** | Abstract/obvious | Clear direction without a protocol | Applicable protocol |
| **Voice contract** | Only author or only assistant | Partial separation | Author (body) + assistant (callout) + space for the owner |
| **Grounding** | No sources | 1 source | 2+ sources, cross-source |
| **Specificity** | Generic | Domain-specific | Concrete example embedded |

Score per note: 0-10. Global score: mean of the sample.

Interpretation:
- ≥8: healthy vault, prioritize output
- 6-7: acceptable quality, enrich the weak ones
- <6: stop extracting, improve what is there

### 3b. Retrieval Audit (5 queries)

Run 5 retrieve queries on topics the user has worked on recently.
For each answer evaluate:
- How many claims are grounded in real notes? (grounding %)
- Were gaps detected where knowledge should exist? (gap detection)
- Did any unexpected cross-domain connection come up? (serendipity hit)

### 3c. Promote Quality

Read the last 5 promoted PNs and check:
- Do they really pass the 4-part convergence test?
- Are the sources from different prefixes?
- Does the counterfactual hold?

## Phase 4 — L3 Trend (historical trend)

```bash
python3 "$OPEN_BRAIN_ENGINES/eval-engine/eval_engine.py" trend --last 10
```

Shows how the key metrics evolved over the last N evals. Look for:
- **Sustained improvement** → the system works, keep the cadence
- **Plateau** → change something (more extraction? more promotion? more writing?)
- **Regression** → diagnose which skill got worse

### 4a. Refinement rule — adjust magnitude or change type? (v1.1)

A Plateau or a Regression does not by itself say what to do next. Before proposing the
next action on a metric, locate the last deliberate intervention that touched it since
the previous eval — an edited skill, an extraction push, a pruning of your agent instruction
file, a threshold change — and ask whether that metric moved in the right direction:

- **It moved in the right direction** → the TYPE of intervention is right. Do not
  rewrite or abandon it — repeat the same type of change, adjusting only the magnitude (more
  extraction if "more extraction" helped; a stricter threshold if tightening it helped; etc.).
- **It did not move, or got worse** → do not stack one more intervention of the same type hoping
  the next round works. Change the type of intervention entirely — not its intensity.
- **Two consecutive rounds of the same type without moving the metric** → the ceiling is one of
  design, not effort. Report it to the user as such instead of proposing a third identical round —
  insisting on the same type of change against evidence that it does not work is the anti-pattern,
  not the discipline.

Apply this in Phase 2 (prioritized actions) whenever a proposed action continues something
that was already tried in the previous eval — not only in Phase 4.

*Origin*: the REFINE heuristic from EnvHarness/EnvRigger (Huang et al., 2026). There, the
designer of an agent's environments decides whether a mutation moves the success rate toward a
target band; if it does, it adjusts only the magnitude of the same type of change and never
rewrites it; if not, it tries a different type of intervention instead of stacking constraints.
Pruning instructions by falsification rather than by age is half of the idea; this adds the
other half — the explicit criterion for WHEN to adjust magnitude vs. when to change type.

### 4b. Citation Probe (optional, monthly — only if ≥28 days since the last probe)

Only relevant if you publish content and want to know whether AI search engines cite it.
Unmeasured discoverability work is faith. If `Resources/GEO Probe Log.md` does not exist or
its last entry is more than 28 days old, run the probe:

1. Define (once) 5 canonical queries that a reader looking for your published work would ask.
   Run them via web search (a proxy for what engines cite; for precision, run them yourself in
   the AI search engines you care about).
2. Record per query: `cited` (your site or repository appears as a source) /
   `mentioned` / `absent`.
3. Append to the log: date, query, result, engine.
4. Read it as a trend, not a snapshot: with 0 published articles the expected result is
   `absent` everywhere — that is NOT a failure, it is the absence of content.
   3+ months of `absent` WITH published content = revise the content, do not add infrastructure.

This probe feeds north-star metric #3 (External outputs): publishing without being
cited is half the loop.

## Metrics that really matter (L3)

These are the system's 4 north-star metrics. The rest are diagnostic:

1. **Funnel conversion (LN → endorsed PN)** — does the system produce real knowledge or pile up inbox?
2. **Owner extension rate** — are you activating elaborative encoding or delegating everything to the assistant?
3. **External outputs** — does the vault feed your writing, or is it an end in itself?
4. **Graph signal/noise** — is autolink classifying well, or is everything "mentions"?

## Phase 5 — Skill Health Check (practice-log bridge)

Run the skill health analysis from the Practice Logs:

```bash
python3 "$OPEN_BRAIN_ENGINES/autolink/skill_health.py" brief
```

The script reads ALL practice logs, groups them by `linked_skill` and `capabilities`, and detects:

- **Degradation** — the rolling average of rubric_score drops below 70/100 or falls >15 points from the peak
- **Stagnation** — last 5 sessions with stddev < 3.0 (no improvement)
- **Recurring abandonment** — >40% of sessions abandoned in a skill/capability

Include the brief's output in the final report, in a separate section after the Scorecard.
If it detects degradation, suggest revisiting that skill's diagnostic rubric and practice plan
(`open-brain-improve`) with the recurring gaps as input.
If there is not enough scored data (most logs have no `rubric_score` yet), report
the available signals: abandonment rate, distribution by domain, and recurring textual gaps.

For JSON output (programmatic consumption): `python3 "$OPEN_BRAIN_ENGINES/autolink/skill_health.py" brief --json`

## Rules

- NEVER modify notes during an eval — it is read-only.
- NEVER invent data if the script fails — report the error.
- If it is the first eval (no previous one), omit deltas and say "baseline established".
- The report goes to `Resources/Evals/`, not to the vault root.
- Suggest `open-brain-health` for fixes, `open-brain-enrich` for search terms,
  `open-brain-promote` for the PN backlog, `open-brain-synthesize` for domain gaps.
- The refinement rule (4a) is a decision criterion, not an excuse not to act: a "design
  ceiling" is reported with evidence (which two interventions were tried, what each one did),
  never as a default conclusion for a metric that did not move in a single cycle.
