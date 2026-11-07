# Open Brain — A Knowledge Management Framework

**Open Brain** is an opinionated framework for building and maintaining personal knowledge vaults that stay useful as they scale. It addresses the core problem most PKM systems ignore: **notes don't just need to be captured — they need to be found, connected, kept alive, tested, and turned into output.**

**[MemoryBrain](https://memorybrain.ai) is built on Open Brain.** Open Brain defines how a brain is built; MemoryBrain is where it lives inside your AIs (ChatGPT and Claude, through a remote MCP connector). The skills are listed at [memorybrain.ai/openbrain/skills](https://memorybrain.ai/openbrain/skills/).

Most knowledge management systems work well at 50 notes. At 500, search gets noisy. At 2,000+, the vault becomes a graveyard of ideas you know you wrote down but can't surface when you need them. And at every scale, without active recall and deliberate output, the knowledge never becomes skill.

Open Brain addresses this with a structured approach across eight modules — from first capture through to written thinking and system automation. The repo has two parts:

- **`docs/`** — 46 problem/solution docs that explain the framework. They are tool-agnostic.
- **`skills/`** — 23 [Claude Code](https://claude.com/claude-code) skills that implement it on a Markdown vault (see [Skills](#skills)).
- **`engines/`** — the Python scripts those skills call for the deterministic work: graph, retrieval log, health checks, lint, course build.

Some parts of the framework are practices you run by hand rather than features a skill runs for you — publishing, measuring how much your vault improves an output, and mining your own sessions for automation. The docs say so where it applies.

---

## Try it in two minutes

[`example-vault/`](example-vault/) is a small vault: 33 notes built from two invented books. Everything in it is fictional. It contains six deliberately seeded defects, so you can see what the engines catch and what they miss. You don't need a vault of your own or Claude Code: only Python 3.9+.

```bash
git clone https://github.com/Memory-brain/open-brain.git
cd open-brain
pip install pyyaml          # optional; without it one informational check reports 0
python3 engines/health-engine/health_check.py self-test
bash example-vault/run-demo.sh
```

`run-demo.sh` copies the vault to a temporary directory, runs five engines there and deletes the copy afterwards, so nothing is written into the repo. The five engines are autolink (typed graph), the health check, the enrich scan, a one-hop graph retrieval and the eval. The excerpt below is real output from 2026-10-14, trimmed: `…` marks a cut, and checks that reported 0 are left out of the summary.

```text
== 1. Autolink: index the vault and build the typed graph ==
✅ Indexed 33 notes → entities.json
✅ Wrote 130 edges → graph.jsonl
…
🔖 Index edges (frontmatter): 97
🎯 Signal/noise ratio: 54.5% (18/33 non-trivial claim edges)

== 2. Health check (deterministic checks) ==
  "summary": {
    "Orphan Notes": 1,
    "Unprocessed Inbox (>30d)": 1,
    "Contradiction Scan": 1,
    "skill_sequence Adoption & Signal": 3,
    "PN Provenance (resolved sources:)": 1,
    "Description as Claim, Not Label": 2,
    …
-- details of the checks that fired --
[1] Orphan Notes: count=1
     items: ["Small teams beat large teams on ambiguous work"]
[5] Unprocessed Inbox (>30d): count=1
     items: [{"note": "The Quiet Standup", "days": 63, "rating": 3}]
[12] Contradiction Scan: count=1
     items: [{"a": "A new routine sticks when it is small enough to run on a bad day", "b": "Judge a practice by its weekly review, not by its daily streak", "type": "contradice", …}]
[16] Search Term Crowding: count=0
     yellow_top: [{"term": "Habit Formation", "tag_count": 12, "tier": "flat", "threshold": 20, …}]
[36] PN Provenance (resolved sources:): count=1
     single_author_items: [{"pn": "Small teams beat large teams on ambiguous work", "author": "dov hartigan", "sources": 2}]
[46] Description as Claim, Not Label: count=2
     topic_not_claim: {"total": 1, "sample": ["Literature Notes/TF - A fixed weekly rhythm makes a small team pred"]}

== 3. Enrich scan (notes under 3 specific, resolvable search terms) ==
  "under_threshold": [
    {
      "note": "SL - A broken streak predicts dropout more than a missed day",
      "specific_resolvable": 2,
…
== 4. Retrieval: one-hop graph expansion from a seed note ==
 Score  Edge Type         Dir  Seed                                      Neighbor
   5.0  contradice          →  Judge a practice by its weekly review, n  A new routine sticks when it is small enough to ru
   1.0  refuerza            →  Judge a practice by its weekly review, n  Team rituals need an owner and a cue, not just a c
   1.0  refuerza            ←  Judge a practice by its weekly review, n  Restarting an evening reading habit after a broken

== 5. Eval (L1 metrics across six dimensions) ==
    "integrity": {
      "frontmatter_compliance_pct": 100.0,
      …
      "broken_links": 0,
      "orphan_pns": 1,
    …
    "graph": {
      "total_edges": 130,
      "total_entities": 33,
      "edges_per_entity": 3.94,
      "signal_noise_ratio_pct": 54.5,
    …
    "pipeline": {
      "inbox_total": 3,
      "inbox_stale_30d": 1,
```

Of the six seeded defects, four are caught and one is caught only in part:

- **Caught:** the stale Inbox item, the orphan Permanent Note, the topic-style description and the Literature Note with only two search terms.
- **Caught in part:** the crowded term `Habit Formation`. It shows up in the yellow band (12 notes), but the check's count stays 0 because a flat term only counts as red above 20 notes.
- **Missed:** a broken wikilink inside a Literature Note. Broken-link checks only scan Permanent Notes.

[`example-vault/README.md`](example-vault/README.md) lists each defect, where it is and which check is expected to catch it. Edge types in the graph keep their original Spanish identifiers: `contradice` = contradicts, `refuerza` = reinforces, `extiende` = extends.

---

## The Eight Modules

### Module 1: Knowledge Enrichment

The foundation. Addresses the three failures that compound as a vault grows: notes becoming unfindable, search terms losing discriminative power, and knowledge connections carrying no semantic meaning.

**Problems:**
- [Retrieval Decay](docs/retrieval-decay.md) — Notes become progressively harder to find as your vocabulary evolves
- [Term Saturation](docs/term-saturation.md) — When a search term accumulates so many notes it loses discriminative power
- [Knowledge Graph Signal vs. Noise](docs/knowledge-graph-signal-noise.md) — Why generic "mentions" links make the graph useless

**Solution:**
- [The Enrichment Pattern](docs/enrichment-pattern.md) — Evidence-driven search term repair, term splitting, and typed connections between Permanent Notes

---

### Module 2: Knowledge Extraction

How raw sources — books, articles, PDFs, web content — become atomic, structured notes. The quality of extraction determines the quality of everything downstream. Includes both passive extraction (from sources you read) and active research (filling gaps you identify).

**Problems:**
- [Source Overwhelm](docs/source-overwhelm.md) — The unprocessed inbox: capture without extraction is organized procrastination
- [Atomic Note Decomposition](docs/atomic-note-decomposition.md) — Getting the granularity right when converting a book to notes
- [The Re-reading Trap](docs/re-reading-trap.md) — When your notes fail as references and you keep returning to the original
- [Reactive Knowledge Accumulation](docs/reactive-knowledge-accumulation.md) — When the vault only reflects what you happened to read, not what you need to know
- [The Seven Extraction Layers](docs/seven-extraction-layers.md) — What a source contains, why slotting notes into layers was retired from extraction, and where layers survive (the `layer` field on Permanent Notes)

**Solutions:**
- [The Extraction Pipeline](docs/extraction-pipeline.md) — Ingest → Extract → Index, with an admission gate before extraction
- [The Autonomous Research Loop](docs/autonomous-research-loop.md) — Filling knowledge gaps through targeted multi-round web research (a practice)

---

### Module 3: Knowledge Maturation

How captured notes become your own ideas. The promotion process that separates storage from understanding.

**Problems:**
- [The Literature Note Graveyard](docs/literature-note-graveyard.md) — 500 notes from 20 books, but no original positions
- [Premature Synthesis](docs/premature-synthesis.md) — Building theses on thin evidence before sufficient convergence
- [Domain Blindness](docs/domain-blindness.md) — Not knowing what you know or what you're missing in a field
- [Convergence Detection](docs/convergence-detection.md) — Why two independent sources confirming an idea beat ten that merely mention it
- [The Endorsement Gap](docs/endorsement-gap.md) — The difference between a note that exists in your vault and one you have explicitly approved

**Solutions:**
- [The Maturation Ladder](docs/maturation-ladder.md) — Literature Note → Your Extension → Convergence → Permanent Note → Domain Synthesis, with maturity (seed → growing → evergreen) derived from use afterwards
- [Convergence Promotion](docs/convergence-promotion.md) — The 4-part convergence test, the per-cluster extension gate, and the state machine from draft to endorsed (plus visual pattern promotion)

---

### Module 4: Active Recall & Practice

How knowledge becomes skill. The practice layer that closes the gap between understanding and doing.

**Problems:**
- [The Collector's Fallacy](docs/collectors-fallacy.md) — When saving notes feels like learning but produces no retention
- [Skill Stagnation](docs/skill-stagnation.md) — The gap between understanding a concept and actually doing it well
- [Invisible Progress](docs/invisible-progress.md) — Learning without a feedback loop: you don't know if you're improving
- [Course Gate Design](docs/course-gate-design.md) — Why linear reading produces recognition but not generation or transfer
- [Context-Absent Output](docs/context-absent-output.md) — When AI generates answers without grounding in your actual knowledge
- [The Judgment Gap](docs/judgment-gap.md) — The distance between knowing about X and having developed judgment on X
- [Empty Prompting](docs/empty-prompting.md) — Using AI as a content dispenser without building judgment: outputs accumulate, capability stays flat

**Solutions:**
- [The AI-Driven Creation Loop](docs/practice-loop.md) — Delegate → Elevate → Challenge as a practice you run by hand, and the loop the skills run: practice log → gaps and friction → promotion review → next course
- [The Specificity Delta](docs/specificity-delta.md) — Comparing an output made without your vault against one made with it (a manual comparison)
- [The Learning Science of Courses](docs/learning-science-of-courses.md) — The research behind the course design
- [Three-Gate Progression](docs/three-gate-progression.md) — Vocabulary → Production → Transfer, scored after the course by a separate evaluation step

---

### Module 5: Knowledge Retrieval

How to access what you know — in multiple modes, for different purposes, from any context.

**Problems:**
- [The Search Box Bottleneck](docs/search-box-bottleneck.md) — Why text search degrades as the primary retrieval method for complex knowledge
- [Isolated Retrieval](docs/isolated-retrieval.md) — Finding individual notes without following the reasoning thread connecting them
- [Knowledge Portability](docs/knowledge-portability.md) — When your vault is stranded on your laptop and inaccessible everywhere else

**Solution:**
- [Multi-Modal Retrieval](docs/multi-modal-retrieval.md) — Six intents (including a visual track), a query-expansion gate, one-hop graph traversal, and remote access as a read-only search-and-read pattern

---

### Module 6: Vault Health & Maintenance

How to keep a large vault reliable. The immune system that prevents structural decay.

**Problems:**
- [Structural Debt](docs/structural-debt.md) — The compounding pathologies of orphan notes, broken links, and maturity drift
- [The Unmeasured Vault](docs/unmeasured-vault.md) — Running blind: no metrics, no signal of health or decay
- [The Manual Maintenance Ceiling](docs/manual-maintenance-ceiling.md) — Why one-by-one review stops scaling at 500+ notes
- [The Flat Graph Problem](docs/uniform-graph-traversal.md) — Why all-equal edge weights make graph retrieval less useful as the vault grows

**Solutions:**
- [The Vault Immune System](docs/immune-system-pattern.md) — Automated health checks, a 3-layer eval with a weekly trend, continuous graph maintenance, and a weekly review
- [Graph Myelination](docs/myelination-pattern.md) — Traversal-reinforced edge weights that make the graph self-organize around how you actually think

---

### Module 7: Knowledge Output

How a full vault becomes written thinking. The output layer that closes the loop.

**Problems:**
- [The Blank Page Problem with a Full Vault](docs/blank-page-full-vault.md) — 1,000 notes and still can't write a paragraph
- [Writing Without Evidence](docs/writing-without-evidence.md) — Opinions disconnected from the knowledge you actually built
- [Single-Perspective Blindness](docs/single-perspective-blindness.md) — The structural limit of evaluating your own work

**Solution:**
- [Knowledge-Grounded Output](docs/knowledge-grounded-output.md) — You write first and your text is kept verbatim → grounding against the one note that contradicts it → a claim emerges across several fragments → multi-perspective review

---

### Module 8: System Automation

How to discover and eliminate manual repetition in your own workflow. The meta-layer that makes the system improve itself over time.

**Problem:**
- [Manual Repetition Overhead](docs/manual-repetition-overhead.md) — The cost of doing the same multi-step tasks repeatedly without recognizing the pattern

**Solution:**
- [The Automation Discovery Pattern](docs/automation-discovery-pattern.md) — Mining your own session history to surface what should be automated (a practice)

---

### Framework Context

How Open Brain relates to the traditions it draws from — and where it diverges.

- [Where Open Brain Fits in the PKM Landscape](docs/pkm-genealogy.md) — What it takes from Forte (CODE/PARA), Zettelkasten, and Deliberate Practice — and the four things none of them have

---

## Skills

`skills/` contains 23 Claude Code skills. `open-brain` is the router: it reads your request and hands it to the right skill.

| Module | Skills |
|---|---|
| 1 · Enrichment | `open-brain-enrich`, `open-brain-autolink`, `open-brain-graph` |
| 2 · Extraction | `open-brain-ingest`, `open-brain-extract`, `open-brain-index`, `open-brain-analyze` |
| 3 · Maturation | `open-brain-promote`, `open-brain-synthesize` |
| 4 · Practice | `open-brain-flashcards`, `open-brain-course`, `open-brain-course-evaluate`, `open-brain-practice-log`, `open-brain-learn-session`, `open-brain-execute`, `open-brain-improve` |
| 5 · Retrieval | `open-brain-retrieve` |
| 6 · Health | `open-brain-health`, `open-brain-eval`, `open-brain-review` |
| 7 · Output | `open-brain-escribir` (island-first writing), `open-brain-panel` (multi-perspective review) |

### Install

```bash
# 1. Skills
cp -R skills/* ~/.claude/skills/

# 2. Engines: copy them into the root of your vault
export OPEN_BRAIN_VAULT="/path/to/your/vault"
cp -R engines/* "$OPEN_BRAIN_VAULT"/
export OPEN_BRAIN_ENGINES="$OPEN_BRAIN_VAULT"
```

- **`OPEN_BRAIN_VAULT`** — the root of your Markdown vault. The skills use the folder conventions described in `skills/open-brain/references/shared/vault-spec.md` (`Literature Notes/`, `Permanent Notes/`, `Sources/`, …).
- **`OPEN_BRAIN_ENGINES`** — where the Python engines live. The skills call them as `$OPEN_BRAIN_ENGINES/<engine>/<script>.py`. Keeping them in the vault root (as above) is the expected layout.
- **Engines** (`engines/`): Python 3.9+. Most scripts use only the standard library. `pip install pyyaml` is recommended (stricter frontmatter parsing; required by two health reports). `numpy` and `scipy` are needed only for the optional LSA/embedding channels in `retrieval-eval/`, which are off by default. The engines create their own data files (graph, traversal log, retrieval log) on first run; none are shipped.

| Engine | Used by |
|---|---|
| `autolink/` | Graph indexing, typed links, one-hop traversal, myelination, co-usage — autolink, graph, retrieve, enrich, ingest |
| `retrieval-eval/` | Retrieval Log and retrieval evaluation — retrieve, extract |
| `enrich-engine/` | Search-term scan, crowding, splits — enrich, extract |
| `health-engine/` | Health checks and log compression — health, promote, extract |
| `eval-engine/` | Scorecard and weekly trend — eval |
| `vault-scan/` | Shared vault scanner imported by other engines |
| `course-engine/` | Course build and outcome recording — course, course-evaluate |
| `engine/` | Lint, islands, practice log, output ledger, project routing, synthesis scan — extract, escribir, practice-log, promote, synthesize, ingest |

---

## Design Principles

**Content is sacred; metadata is the lever.** Enrichment and maintenance operations don't change what a note claims. They improve the metadata, connections, and structure that make notes findable and usable. Compressing a note's wording is an explicit, reviewable operation — never a side effect of maintenance.

**Additive only.** The framework adds search terms, connections, and structure. It never silently removes existing content: rejected sources and notes are moved and logged, not deleted.

**Human in the loop for meaning; automation for bookkeeping.** Changes to what a note says — new Permanent Notes, endorsements, splits, merges, new domains — need your approval. Derived bookkeeping (usage counters, maturity, graph edges and weights) is recalculated automatically, because it is computed from the vault rather than declared.

**Diagnosis before treatment.** Every maintenance operation starts with a scan. Fix what the data says is broken, not what you assume.

**Active recall over passive review.** Reading notes is not learning. Testing recall, producing answers, and applying knowledge to new cases is learning.

**Output closes the loop.** Knowledge that never becomes output — writing, decisions, conversations — hasn't been integrated. The vault exists to make you better at thinking, not to make you better at storing.

---

## Who This Is For

Open Brain is built for knowledge workers who:

- Use Obsidian, Logseq, or any linked-note tool and have outgrown basic tagging
- Have 500+ notes and notice that search is getting worse, not better
- Want their vault to function as a retrieval system, not just a storage system
- Care about the *structure* of knowledge, not just the *volume*
- Want to close the loop from reading → notes → synthesis → skill → output

The docs apply to any linked-note tool. The skills assume Claude Code and a folder of Markdown notes with YAML frontmatter.

---

## Repository Structure

```
docs/
├── retrieval-decay.md                  # Module 1: Why notes become unfindable
├── term-saturation.md                  # Module 1: When search terms lose power
├── knowledge-graph-signal-noise.md     # Module 1: Why generic links degrade graph value
├── enrichment-pattern.md               # Module 1: The systematic solution (solution doc)
│
├── source-overwhelm.md                 # Module 2: The unprocessed inbox problem
├── atomic-note-decomposition.md        # Module 2: Getting granularity right
├── re-reading-trap.md                  # Module 2: When notes fail as references
├── reactive-knowledge-accumulation.md  # Module 2: Vault mirrors reading history, not knowledge gaps
├── seven-extraction-layers.md          # Module 2: What a source contains; layers retired as extraction slots
├── extraction-pipeline.md              # Module 2: Ingest → Extract → Index (solution doc)
├── autonomous-research-loop.md         # Module 2: Filling gaps via targeted multi-round research (solution doc)
│
├── literature-note-graveyard.md        # Module 3: Notes that never become ideas
├── premature-synthesis.md              # Module 3: Building on thin evidence
├── domain-blindness.md                 # Module 3: Not knowing what you know
├── convergence-detection.md            # Module 3: Why two confirming sources beat ten mentioning ones
├── endorsement-gap.md                  # Module 3: Notes that exist vs. notes you have approved
├── maturation-ladder.md                # Module 3: From captured to owned (solution doc)
├── convergence-promotion.md            # Module 3: Convergence test, extension gate, draft → endorsed (solution doc)
│
├── collectors-fallacy.md               # Module 4: Saving ≠ learning
├── skill-stagnation.md                 # Module 4: Understanding ≠ doing
├── invisible-progress.md               # Module 4: Learning without feedback
├── course-gate-design.md               # Module 4: Why linear study produces recognition, not transfer
├── context-absent-output.md            # Module 4: AI output without your knowledge context
├── judgment-gap.md                     # Module 4: Knowing about X vs. having judgment on X
├── empty-prompting.md                  # Module 4: Using AI without building judgment
├── practice-loop.md                    # Module 4: Manual creation loop + the loop the skills run (solution doc)
├── specificity-delta.md                # Module 4: Manually comparing output with and without your vault (solution doc)
├── learning-science-of-courses.md      # Module 4: Learning science foundations for course design
├── three-gate-progression.md           # Module 4: Vocabulary → Production → Transfer gate model
│
├── search-box-bottleneck.md            # Module 5: Why text search degrades
├── isolated-retrieval.md               # Module 5: Notes without their context
├── knowledge-portability.md            # Module 5: Vault stranded on one device
├── multi-modal-retrieval.md            # Module 5: Six retrieval intents incl. visual (solution doc)
│
├── structural-debt.md                  # Module 6: Compounding vault pathologies
├── unmeasured-vault.md                 # Module 6: No metrics, no signal
├── manual-maintenance-ceiling.md       # Module 6: Manual review doesn't scale
├── uniform-graph-traversal.md          # Module 6: Why all-equal edge weights flatten the graph
├── immune-system-pattern.md            # Module 6: Automated health, human judgment (solution doc)
├── myelination-pattern.md              # Module 6: Traversal-reinforced graph self-organization (solution doc)
│
├── blank-page-full-vault.md            # Module 7: Full vault, blank page
├── writing-without-evidence.md         # Module 7: Opinions without vault evidence
├── single-perspective-blindness.md     # Module 7: The limit of self-review
├── knowledge-grounded-output.md        # Module 7: Island → contradicting note → claim → review (solution doc)
│
├── manual-repetition-overhead.md       # Module 8: Cost of tasks without recognized patterns
├── automation-discovery-pattern.md     # Module 8: Mining session history for automation candidates (solution doc)
│
└── pkm-genealogy.md                    # Framework Context: How Open Brain extends Forte, Zettelkasten, and Deliberate Practice

skills/
├── open-brain/                         # Router + shared vault spec
└── open-brain-*/                       # 22 skills (see Skills above)

engines/                                # Python engines the skills call (copy into your vault root)

example-vault/                          # Fictional 33-note vault + run-demo.sh (see "Try it in two minutes")
```

---

## Further Reading

- Ahrens, S. (2017). *How to Take Smart Notes.* — The Zettelkasten foundation that Open Brain extends.
- Matuschak, A. *Evergreen Notes.* — The concept of notes that develop over time, which enrichment operationalizes.
- Bush, V. (1945). *As We May Think.* — The original vision of associative trails that typed connections implement.
- Roediger, H.L. & Karpicke, J.D. (2006). *Test-Enhanced Learning.* — The science behind active recall over passive review.
- Wozniak, P. (1990). *Optimization of Learning.* — The spaced repetition foundation for SM-2 scheduling.

---

## License

MIT — Use it, adapt it, extend it. If it helps you think better, that's the point.
