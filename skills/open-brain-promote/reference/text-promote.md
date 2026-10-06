# reference/text-promote.md — Text pipeline (LN → PN)

> This reference was reconstructed from the v9.4 monolith of `open-brain-promote` and updated to
> the current gates. Where it and `SKILL.md` disagree, `SKILL.md` wins.

## What changed since v9.4 (read this first)

**The extension gate lives at the CLUSTER, not on each note (v9.7).** Where v9.4 required
`≥2 LNs in extended-by-owner`, the gate now requires **a single extension written by you
(the vault owner) per cluster**, recorded on the cluster in the `promote-queue`:

```yaml
cluster_extension: "<the vault owner's words about what the convergence means>"
extended_by: owner
extended_at: <YYYY-MM-DD>
```

Reason: with per-note extensions, the friction sat on the most expensive step (writing a
paragraph on every candidate note) instead of the most valuable one (judging a convergence
that has already formed). It was not a rubber stamp: **it was never reached.**

**The field has to actually exist (v9.9).** A global "do it all" approval can push clusters
through the gate and produce PNs with `cluster_extension: null`. If the field is empty,
`gate_passed` is `false`: write it that way in the queue with the reason, and ask for the
extension. A global approval does not fill that field. If the vault owner promotes anyway,
the PN is written with `cluster_extension: "(promoted without extension — global approval
YYYY-MM-DD)"`, so the record does not claim judgment where there was none.

**The ≥2 sources must be independent.** Different author, and neither citing the other.
Two works by the same author count as **one** reinforced source, not two. Check it
explicitly: no script enforces it, so if you don't check it nobody does.

**Do not ask for a per-note extension.** If a candidate LN still carries the placeholder
saying its empty extension blocks promotion, that text is stale — ignore it and say so in
the brief.

**Sub-commands of this pipeline**: `--by-application`, `--review-friction`, `--endorse`,
`--reject`. Specified below.

---

## The flow: Brief → the vault owner evaluates → Write

The flow is:
1. **Convergence scan** — find candidate clusters.
2. **Generate a Promotion Brief** — show the vault owner ALL candidate LNs, a draft PN, the convergence test, and 3 evaluation questions.
3. **Wait for the owner's answers**. Blocking. Do not write the PN until they respond.
4. **Write the PN** — with full traceability frontmatter.
5. **Hook to Ideas/** if "Your extension" is publishable.

---

## Step 1: Convergence Scan

Group candidates by the idea they express, not just the words. Useful searches:

```
# All LNs from a source:
ls "Literature Notes/" | grep "^[PREFIX]"

# LNs tagged with a specific search term:
grep -rl "[[Term]]" "Literature Notes/"

# Existing PNs in a domain:
grep -rl "[[Domain Name]]" "Permanent Notes/"
```

Do **not** filter candidates by per-note `voice_state: extended-by-owner` any more — that was the
v9.4 gate. A cluster qualifies on source independence (≥2 independent sources) and the 4-part
test below; the owner's extension is then requested **once for the cluster** in the brief. An LN's
`voice_state` is still useful context to show in the brief, not a filter.

### When nothing passes

If after scanning 0 clusters pass the gate (independence + 4-part test + cluster extension):

**In chat mode**: say so, list the closest clusters and what each one is missing (a second
independent source, a more specific claim, the owner's extension), and stop.

**In UI mode**: do NOT ask. Build the queue with ALL detected clusters, marking `gate_passed: false` and `gate_blockers` (e.g. `["cluster_extension empty"]`, `["sources not independent"]`) for those that don't pass. Start the server. The UI shows them in gray with a tooltip.

---

## Step 2: Apply the Four-Part Convergence Test

Before proposing a PN, the cluster must pass:

1. **Different source prefixes** — at least 2 LNs from different, independent sources. Same-source convergence is supporting evidence, not synthesis.
2. **Different vocabulary / framing** — sources describe the idea differently enough that the convergence is non-trivial.
3. **Specific enough to be actionable** — concrete enough to guide a real decision. "Learning requires feedback" fails. "The right difficulty level is just above current ability — too easy fails to build skill, too hard triggers overload" passes.
4. **Counterfactual passes** — answer with a concrete example from the vault owner's work or vault: "if this PN did not exist, what specific decision, manuscript, or output would be harder?" If the answer is abstract, the cluster fails. **Note**: this is a gate question, not a frontmatter field — it lives here in the brief, not in the PN file.

Clusters that fail any test → keep on the brief as "weak signals", not promoted.

---

## Step 3: Generate the Promotion Brief

Do not write the PN yet. Generate the brief and present it to the vault owner. The brief must contain ALL of the following:

```markdown
# Promotion Brief — [Cluster idea in one declarative line]

## Candidate idea
[2-3 sentences, draft of what the PN would assert.]

## Literature Notes considered (full list)
The skill found N LNs adjacent to this idea. ALL of them are listed below — you decide which ones the synthesis truly rests on.

- [[LN-1]] — `mentor: [[X]]`, `voice_state: extended-by-owner` — one-line summary
- [[LN-2]] — `mentor: [[Y]]`, `voice_state: with-claude-connectors` — one-line summary
- ...

## Source independence
[For each pair of sources: different author? does either cite the other?]

## Convergence test
| Test | Result | Note |
|------|--------|------|
| Different source prefixes | ✅ / ❌ | [...] |
| Different vocabulary | ✅ / ❌ | [...] |
| Specific & actionable | ✅ / ❌ | [...] |
| **Counterfactual** | ✅ / ❌ | If this PN didn't exist, [your specific decision/manuscript/output] would be harder because [reason]. |

## Draft PN body
[2-4 sentences in declarative voice. State it like you believe it.]
[Boundary conditions draft — when does this NOT apply?]

## Three questions for you (please answer before this is promoted)
1. **Is this real synthesis or just intersection?** Do these LNs genuinely converge, or do they only say the same thing in different words?
2. **Which decision / output / manuscript changes if this PN does not exist?** Concrete, not abstract.
3. **What do you add that is not in any source?** This becomes the cluster extension and the PN's "Your extension". If the answer is "nothing yet", the PN is NOT promoted.

After your answers, I'll write the PN to `Permanent Notes/` with full traceability.
```

Present and stop. Wait for the vault owner.

---

## Step 4: Wait for the vault owner's evaluation

Do NOT proceed without explicit answers to the three questions.

If the owner answers but their "Your extension" answer is "nothing yet", reply: "Without your extension this is just an intersection of authors. If you want to promote it anyway, say so explicitly and I'll mark it `confidence: low, awaiting-extension`."

---

## Step 5: Write the Permanent Note (only after the vault owner has evaluated)

**File**: `Permanent Notes/[Idea title].md`

The title is a declarative statement (subject + verb + predicate), not a noun phrase. It IS the claim. The filename = the H2 heading = the core judgment.

### Frontmatter — a single source of truth (v9.10)

**Do not copy a schema from here.** The canonical PN frontmatter template is your vault's PN template (e.g. `Templates/Permanent Note.md`): open it and follow it. Keeping a second copy of the schema here would create two diverging schemas for the same object — a second version of the truth waiting to be confused with the first. If your vault has no template yet, use the fields below plus the standard ones (`type`, `layer`, `domain`, `search_terms`, `sources`, `confidence`, `created`).

What this skill adds **on top of** the template, and which the template cannot know:

```yaml
# — Endorsement (enum validated by check_22; do not touch) —
endorsement_state: provisional    # provisional → endorsed | rejected | unendorsed
# — Approval as an event (v9.10) —
endorsed_at:                      # EMPTY unless the vault owner approves IN THIS session
endorsed_via: promote             # promote | sesion | careo | review-queue
status: draft                     # while endorsed_at is empty
# — Process trace (v9.10) —
generated_by: "open-brain-promote 9.10.0 · engine-stamp <date from $OPEN_BRAIN_ENGINES/health-engine/engine-stamp.json>"
# — Convergence of this cluster —
cluster_extension: "<the vault owner's words>"   # empty ⇒ gate_passed: false
extended_by: owner
extended_at: YYYY-MM-DD
# — Manuscript pipeline (optional, filled when assigned) —
active_manuscripts: []
manuscript_role: ""               # e.g. "essay-2-anchor; essay-1-feeder"
```

And three rules that survive from v9.4 because they are still true: `maturity` **is derived** (vault-scan's `maturity()` computes it; `check_6` fails if you write it by hand), `external_outputs` / `internal_outputs` are derived from the output ledger (see G7 in `SKILL.md`), and `title` is optional — the declarative claim **is** the filename.

At the end of the body, after `Connections`, goes the `## Historial` (history) block with the first line of the timeline (see `SKILL.md`, "Approval is an event"). A PN with `endorsed_at` and no history line counts against `check_41`.

**Fields retired in v9.4 that the template does not carry either** (for the record, so nobody reintroduces them): `title` (redundant with filename, optional), `counterfactual` (a promotion gate, not a permanent field), `approved_by` + `promoted_at` + `evaluation_notes` (covered by `endorsement_state` + `endorsed_at` / `endorsed_via` + `created`), `lns_evaluated` + `lns_excluded_with_reason` (they go to the provenance appendix in the body).

### Body (canonical v9.4 order: ACTION → JUSTIFICATION → EXTENSION → GRAPH)

```markdown
## [Declarative claim — identical to the filename]

[1 paragraph (3–6 sentences). The direct judgment, no hedging. It asserts; it does not summarize sources.]

**Operating rule**: [what to DO with this — an action that changes a real decision]

**Test**: [how to know, at decision time, whether the principle applies to the case at hand]

**Boundary conditions**: [when it does NOT apply or reverses — a concrete case, not "it depends"]

**Why it matters**: [which dominant frame it breaks or replaces — the delta against the default belief]

**Evidence**: [named sources + concrete data/figure; cross-domain convergence if applicable]

**Your extension**: [what you lived/judged beyond the sources — what this would NOT be if written by someone else who read the same things]

**Connections** (omit if no connector passes the quality bar):
- Related to [[PN]] because [reason ≥25 chars, specific, falsifiable]
- Contrasts with [[PN]] in that [specific tension between the two positions]
- Enables [[PN]] by [concrete mechanism]
```

**Rationale for the order**: Rule + Test + Boundary are a contiguous decision triad (what to do / when / how far). A reader retrieving the PN in order to act gets the decision core without going through the justification. Why it matters and Evidence are justification — they support the claim but are not the actionable core.

### Optional provenance appendix

Add AFTER Connections, separated by `---`, only if you want to preserve the traceability of the promotion session. **It is not retrieved for content.**

```markdown
---
## Provenance (audit — not retrieved for content)
**LNs evaluated**:
- [[LN used]]: used
- [[LN excluded]]: excluded — [reason: source-specific / redundant / does not generalize]
**Promotion session**: YYYY-MM-DD
```

---

## Step 5 — Quality Rules Per Section

### Claim (filename + H2)
1. **Declarative sentence** with subject + verb + predicate, not a noun phrase. "AI amplifies judgment" ✓ / "AI amplification" ✗.
2. **Falsifiable**: a reasonable person could disagree. If nobody could disagree, it is a definition, not a judgment — not a PN.
3. **"I hold that…" test**: prefix it with "I hold that…". If it sounds like a position, it passes. If it sounds like a glossary entry, rewrite.

### Judgment paragraph
1. **Asserts, does not report**. Zero "according to X", "several authors suggest". The judgment is yours, backed by sources, not attributed to them.
2. **Atomic**: 3–6 sentences, a single paragraph. If it needs two paragraphs to stand, the PN is not atomic — split it.
3. **No hedging**: "it seems that", "might", "in a way" are banned — unless the uncertainty IS the content, and then `confidence: hypothesis`.
4. **Hook test**: could the first sentence open a post? If it is lukewarm, the judgment is not cooked yet.

### Operating rule
1. **Starts with an actionable verb** (evaluate, remove, give, invert, run through the filter…). It says what to DO, not what is true.
2. **Changes a real decision**: after reading it, you would do something different from your default. If it confirms what you would already do, it is a truism.
3. **Default test**: does it rule out a behavior that a reasonable person would do by default? If it rules out nothing, drop or rewrite it.
4. **A single rule**. If there are three things to do, either it is a checklist (another note) or the PN is not atomic.

### Test (applicability)
1. **Answerable in the moment** of the decision, with the information available then — not in hindsight or with a study.
2. **Binary or near-binary cut**: the answer tells you applies / does not apply, not "it depends".
3. **Does not repeat the Rule**: the Rule says what to do; the Test says how to know whether it's time. If they are the same sentence, one of the two is missing.
4. **Test of the test**: can I apply it to a real case in <30 s without data I don't have? If it requires research, it is not operational.

### Boundary conditions
1. **Mandatory**. A PN without limits is a belief, not a calibrated judgment. No boundary → not promoted.
2. **A concrete case** where it does NOT apply or reverses — not "it depends on the context".
3. **Distinguishes limit from failure**: where does the principle stop biting even if everything is executed well?
4. **Own-error test**: can I name a situation in my work where following this rule would be a mistake? If not, you have not found the limit.

### Why it matters
1. **Names the frame it breaks**: the value is the delta against the default belief ("the dominant frame is productivity…"), not generic importance.
2. **Does not paraphrase the claim**. If it repeats the judgment paragraph in other words, merge or remove it.
3. **"Most people believe X" test**: does it complete "this matters because most people believe X, and X is incomplete/false"? If there is no X to push against, it is probably superfluous.

### Evidence
1. **Named sources + concrete data** (figure, experiment, number of sources). Not "several studies".
2. **Explicit convergence**: in synthesis PNs, say how many independent sources converge and from which different angles — cross-domain convergence is the strength of the claim.
3. **Data > authority**: a verifiable figure weighs more than "an expert says".
4. **Skeptic test**: could someone go and verify at least one fact here? If nothing is verifiable, it is opinion with a citation.

### Your extension
1. **Mandatory to promote**. It is what separates a PN from a Literature Note. No extension → not promoted (it is just an intersection of authors).
2. **Not in any source**: lived experience, a case, a date, an observed pattern, a consequence the authors did not draw.
3. **First person and specific**: "I saw this when our team switched to weekly releases: the first month, bug reports doubled before they halved…" ✓ / "this can be applied to oneself" ✗.
4. **Authorship test**: could it have been written by someone who read the same sources but is not you? If yes, it is not an extension, it is a summary.
5. **Ideally publishable**: if the extension could be the body of a post, flag the hook to the manuscript pipeline. It is the bridge from PN → published piece.

### Connections
**Minimum bar to include a connector** — if a connection doesn't pass all 5 tests, DO NOT include it. Zero connectors is perfectly valid; filler connectors are not:

1. **Clear wikilink** to an existing PN or LN in the vault. No wikilink, out.
2. **Specific reason of ≥25 characters** after the wikilink, anchored in the concrete content of BOTH notes.
3. **50% test**: if the reason ("share X", "both treat Y", "have in common Z") could apply to more than half the PNs in the vault, it's filler. Out.
4. **No catch-all phrases**: prohibited — `the same principle`, `share a principle`, `both deal with`, `are related`, `have in common`, `the same concept operates` (and their equivalents in any language your vault uses).
5. **Brings a decision, tension, or new tool**. If the connector only says "both are about the same topic" without saying what is gained by knowing the connection, out.

**Good example**: `Contrasts with [[Good habits beat daily discipline]] — Clear puts identity change as the primary vector; this node puts the system as the primary vector. The tension: who changes first, the self or the environment?`

---

## Step 5.5: Ideas Hook

Once the PN is written, look at "Your extension". Ask the vault owner:

> "Is this extension publishable? If so, which format — social post / service PDF / article / internal?"

If yes, create a 3-line note in `Ideas/` with:
- `idea`: the PN title
- `seed_pns`: `[[<this PN>]]`
- `format`: chosen format
- `status`: seed
- `created`: today

---

## Step 6: Link Back to Source Literature Notes

For each LN in `sources`, add to its body (under the `[!claude] Connectors` callout):
```
- Synthesized into [[<PN title>]]
```

Also update the LN frontmatter: `synthesized_in: [[<PN title>]]`.

---

## Step 6.5: Update Typed Knowledge Graph (silent)

After writing the PN and linking back, update the typed graph (`graph.jsonl`, maintained by the autolink engine):

```bash
GRAPH_SCRIPT="$OPEN_BRAIN_ENGINES/autolink/update_graph.py"
if [ -f "$GRAPH_SCRIPT" ]; then
  python3 "$GRAPH_SCRIPT" "<absolute path to the PN file just written>" --quiet 2>/dev/null || true
fi
```

This is fire-and-forget — silent on success, silent on failure. Never block Step 7. If the autolink engine is not installed, the hook stays quiet.

---

## Step 7: Report

```
## ✅ Permanent Note created: [[<PN title>]]

**Promoted at**: YYYY-MM-DD · **endorsement_state**: provisional · **status**: draft
**LNs evaluated**: N (M used, K excluded)
**Your extension recorded**: [one line]

**Editorial pipeline**: [recorded as seed with format X / not publishable]

**Next step (if applicable)**:
- open-brain-synthesize for the Domain Index of [domain] (because there are 3+ new PNs in this domain)
- pending new cluster: [...]
```

---

## Mode --by-application (v9.2)

**Trigger**: `open-brain-promote --by-application [Skill]`

When you have trained a skill (via `open-brain-practice-log` + `open-brain-course`), the feeder PNs have already passed through your judgment in context. This mode delivers the feeder PNs in `provisional` state as an epistemic decision queue.

### Steps:
1. Verify `Skills/<Domain>/<Skill>/` exists. Read `Skills/<Domain>/<Skill>/feeder-pns.md`. Extract the Provisional list.
2. Per PN, gather: the PN content, `times_retrieved`, `external_outputs`, `last_validated`, friction entries in `promote-feedback.md` that mention this PN.
3. Present each as an atomic decision — one at a time:

```
**PN**: [[<Declarative claim of the PN>]]
**Current state**: provisional · created 2026-04-13 · times_retrieved: 0
**Synthesis**: [first paragraph of the PN]

**Decision** (only one):
  [E] Endorse — the PN holds up as my applied judgment
  [R] Reject — the PN does not survive real use
  [P] Keep provisional — I need more cases before deciding
  [F] Reformulate — the PN points the right way but needs rewriting
  [S] Skip — next PN
```

4. Apply the decision per answer. For E: `endorsement_state: endorsed`, `endorsed_at: <today>`, `endorsed_via: promote-by-application`, plus the `## Historial` line. For R: move to `Permanent Notes/Rejected/`. For F: ask the vault owner for the rewrite text, apply it, state becomes `endorsed`.

---

## Mode --review-friction (v9.2)

**Trigger**: `open-brain-promote --review-friction` or `open-brain-promote --review-friction [Skill]`

Processes `promote-feedback.md` for one or all skills. Each pending block is a friction event against a specific PN when applied to a real Case; the block's `**Owner note**:` field carries the vault owner's comment.

### Steps:
1. Scan for blocks with `Status: pending-review` in the relevant `promote-feedback.md` file(s).
2. Per friction block, present the friction context (including the `**Owner note**:`) and the PN state, then ask for a decision: E/F/R/P/S.
3. Apply the decision, mark the block `Status: processed: <outcome>`.

---

## Atomic Commands --endorse and --reject (v9.2)

**--endorse [[PN]]:**
1. Find the PN in `Permanent Notes/`. Verify `endorsement_state: provisional`.
2. Update frontmatter: `endorsement_state: endorsed`, `endorsed_at: <today>`, `endorsed_via: promote-atomic-endorse`, plus the `## Historial` line.
3. For each `feeder-pns.md` that lists this PN: move the bullet from Provisional to Endorsed.

**--reject [[PN]] (reason):**
1. Find the PN. Ask for the reason if not provided.
2. Move file: `Permanent Notes/<title>.md` → `Permanent Notes/Rejected/<title>.md`.
3. Update frontmatter: `endorsement_state: rejected`, `rejected_at`, `rejected_reason`, `rejected_via: promote-atomic-reject`.
4. For each `feeder-pns.md` that lists this PN: move the bullet to Rejected.
5. Do NOT delete wikilinks — broken links are the correct signal.

---

## UI Mode — promote-queue.json Contract

UI mode requires a promote web UI (a small Node server, `server.js`), which is **not part of this package**. If you have one installed, set `$OPEN_BRAIN_PROMOTE_UI` to its directory. If you don't, tell the user UI mode is unavailable and run chat mode.

When UI mode is triggered, build this file at `$OPEN_BRAIN_PROMOTE_UI/promote-queue.json`:

```json
{
  "generated_at": "2026-05-03T15:42:00Z",
  "generated_by": "open-brain-promote skill v9.10",
  "clusters": [
    {
      "id": "cluster-slug-kebab",
      "title": "The convergent idea in one declarative sentence",
      "convergence_strength": "strong | medium | weak",
      "domains": ["Communication", "Decision Making"],
      "layer": "knowledge | ...",
      "search_terms": ["[[Term 1]]", "[[Term 2]]"],
      "sources": ["Source title 1", "Source title 2"],
      "lns_candidates": ["PREFIX - LN filename without extension.md"],
      "lns_used": [],
      "lns_excluded": {},
      "draft_pn": "2-4 sentences in declarative voice...",
      "cluster_extension": null,
      "gate_passed": false,
      "gate_blockers": ["cluster_extension empty"],
      "connections": ["Related to [[Existing PN]] because [specific reason ≥25 chars]"],
      "mentor_map": {
        "PREFIX - LN filename.md": { "name": "Mentor Full Name", "source": "PREFIX" }
      }
    }
  ]
}
```

Key invariants: `gate_passed: false` clusters are shown in the UI in gray — they are detected but cannot be approved. `gate_blockers` explains why. `id` must be a stable kebab-case slug. `lns_candidates[i]` filenames must exactly match files in `$OPEN_BRAIN_VAULT/Literature Notes/`. Do NOT write `promote-state.json` — that is the server's session state.

### Launch the server:

```bash
# Check for an existing process on port 8001
lsof -ti:8001

# Start the server (from the promote UI directory)
cd "$OPEN_BRAIN_PROMOTE_UI" && nohup node server.js > /tmp/open-brain-promote.log 2>&1 &

# Verify it started (should return 200)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/
```

---
