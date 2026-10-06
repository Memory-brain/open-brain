---
name: open-brain-analyze
description: 'Analysis and compression. Transforms raw content into structured knowledge, compressed principles,
  and mental models. Phase 1 of the learning system. Triggers: analyze this, pull out the concepts, compress it,
  mental models, open-brain analyze'
metadata:
  folded_from_top_level:
    version: 9.0.0
  version: 9.0.0
  status: canonical
  status_note: 'Looks like it overlaps with open-brain-extract; verified that it does not — analyze produces a study document, extract writes Literature Notes.'
  consumes:
  - Raw unstructured content (books, articles, PDFs, transcripts, documentation)
  produces:
  - 'Three layers: Knowledge, Compression and Mental Models'
  - A conditional Practical Extraction Appendix (narratives, cases, techniques, anti-patterns, decisions)
  - Extraction Manifest — a list of proto-notes ready for direct consumption
  - Book Tier Assessment (for books) and a closing Activation Prompt
  handoffs:
  - skill: open-brain-extract
    when: after producing the Extraction Manifest, to create the Literature Notes without re-parsing
    requires_approval: true
  - skill: open-brain-index
    when: if the Book Tier Assessment is TOP or INTERESTING, to generate an Outline of the book
    requires_approval: true
  - skill: open-brain-execute
    when: the application phase depends on the quality of this output
    requires_approval: true
  - skill: open-brain-improve
    when: the improvement phase depends on the quality of this output
    requires_approval: true
---

# Open Brain — Analyze

Phase 1 of a 3-phase learning system. Transform raw, unstructured content (books, articles, PDFs, transcriptions, documentation) into structured knowledge a person can understand, remember, and think with. Produces 3 layers: Knowledge, Compression, and Mental Models. `open-brain-execute` and `open-brain-improve` depend on this output quality. This skill writes nothing to the vault; `open-brain-extract` is the skill that writes Literature Notes, and can use this manifest as its starting list.

---

## Process

### Step 1: Scan and Scope

Read the full content. Before extracting, answer internally:
- What domain? (business, technical, creative, scientific)
- What type? (theory, methodology, case study, research, how-to)
- What is the author's core argument?
- Who is the intended audience?

### Step 2: Extract Raw Elements

Pull out: concepts, frameworks, processes, principles, examples, data, relationships between ideas, contradictions, and what the author assumes readers already know.

**Also scan specifically for these commonly-overlooked elements:**
- **Named case studies** (companies, projects, experiments) — raw material for notes tagged `application` downstream. Tag them clearly.
- **Operational techniques** — interview scripts, observation protocols, scoring systems, workshop formats, decision matrices.
- **Negative/inverse patterns** — what the author says to AVOID. The inverse of a framework often reveals insights the positive framing misses.
- **Cross-domain implications** — if the source is about one domain but has insights about another, flag those explicitly.
- **Narrative moments** — stories, anecdotes, transformation examples, failure cases. A principle without a story decays; a story without a principle is incomplete.
- **Identity moments** — passages where the author connects behavior change to who someone becomes ("I became the kind of person who…"). These signal where behavior design lives in the material.

### Step 3: Produce the 3 Layers

---

## Layer 1: Knowledge

**Purpose**: Complete, structured understanding. The reference layer.

```
## 1. Knowledge — [Topic Name]

### Core Concepts
[For each: name, plain-language definition, why it matters, one concrete example. Group related concepts.]

### Frameworks & Models
[For each: name, components, how they relate, when to use. Use matrix/table format when comparing multiple items across dimensions.]

### Key Processes
[Step-by-step sequences. Numbered. Include decision points and conditions.]

### Important Relationships
[What depends on what. What enables what. What contradicts what. What amplifies what.]

### Context & Boundaries
[Where does this apply? Where NOT? What assumptions? What prior knowledge needed?]
```

**Quality check**: Every concept has a concrete example. Frameworks described verbally AND spatially (tables). Dependencies explicit. Jargon defined on first use.

---

## Layer 2: Compression

**Purpose**: The 20% that captures 80% of value. What should survive if everything else is forgotten.

```
## 2. Compression — [Topic Name]

### Core Principles
[3-7 one-sentence principles someone could repeat from memory. Each followed by "which means..." explanation.]

### Key Rules & Heuristics
[If X then Y. When in doubt, do Z. Condensed expert wisdom.]

### Critical Distinctions
[What beginners confuse that experts never do. What looks similar but is fundamentally different.]

### Anti-Patterns
[What NOT to do. Each with WHY it fails.]

### The Cheat Sheet
[Everything above in a single-page reference. Dense, scannable, table format. Must stand alone.]
```

**Quality check**: Principles are memorable (short enough to recall without notes). Heuristics guide real decisions. Anti-patterns explain WHY. Cheat sheet works independently.

---

## Layer 3: Mental Models

**Purpose**: How this knowledge changes the way you think. The most transformative layer.

```
## 3. Mental Models — [Topic Name]

### How Experts Think About This
[What do they notice first? What questions do they ask? How do they frame problems? How is this different from a novice?]

### Thinking Frameworks
[Reusable reasoning structures. Each: name, when to apply, steps/questions, example in action.]

### Problem-Structuring Patterns
[How to break down problems in this domain. Standard decompositions. Which approach fits which situation.]

### Evaluation Lenses
[How to assess ideas/proposals in this domain. What signals quality? Risk? How to prioritize?]

### Mental Shifts
[Frame as "Before this, you might think X. After, you realize Y." Each shift should feel genuinely useful, not obvious.]
```

**Quality check**: Mental models described through behavior change, not just statements. Thinking frameworks are reusable. Each mental shift creates genuine reframing.

---

## Practical Extraction Appendix

After producing the 3 main layers, append this section. It provides raw material that `open-brain-execute` and `open-brain-extract` need for notes tagged `application`, `code-artifact`, `decision` and `diagnosis`.

**Conditional sections**: only include sections where the source actually has that type of content. Omit sections that genuinely don't exist. Exception: if a section is expected for a source type (e.g., case studies in a business book) but none were found, include the header with: `*None found — source is primarily theoretical.*`

```
## Practical Extraction — [Topic Name]

### Narrative Extraction
[Include ONLY if source contains named stories or transformation examples with identifiable protagonists and stakes.]
- **[Story name / protagonist]**:
  - *Situation*: [context]
  - *Tension*: [decision point]
  - *Decision*: [what they did and why]
  - *Outcome*: [what happened]
  - *Principle*: [what this illustrates]

### Case Studies
[Include ONLY if source contains named real-world examples — companies, projects, experiments.]
- **[Company/Project/Person]**: Context → what they did → result → lesson

### Identity Moments
[Include ONLY if source explicitly connects behavior to identity — "become the kind of person who…"]
- **[Quote or paraphrase]**: What identity does this construct?

### Operational Techniques
[Include ONLY if source contains concrete how-to methods: scripts, protocols, checklists, workshop formats.]
- **[Technique name]**: When to use → steps → expected output

### Anti-Patterns & Failure Modes
[Include ONLY if author explicitly names failure modes and explains WHY they fail.]
- **[Anti-pattern name]**: What it looks like → why it fails → what to do instead

### Decision Signals
[Include ONLY if source contains trade-off frameworks or "when to use X vs Y" guidance.]
- **[Decision/Trade-off]**: Options → criteria → recommended approach

### Cross-Domain Connections
[Include ONLY if source contains insights that clearly apply to domains beyond its primary one.]
- **[Insight]** → applies to [other domain] because [reason]
```

---

## Extraction Manifest

After the Practical Extraction Appendix, always produce this section. It is a pre-structured list of every proto-note identified, ready for `open-brain-extract` to consume directly — no re-parsing required.

The manifest is the contract between `open-brain-analyze` and `open-brain-extract`. When the manifest is in context, extract can work from it, referring back to the 3 layers only for additional context — this avoids extracting twice. Extract still applies its own admission gate, templates and lint; the manifest is input, not a substitute for them.

```
## Extraction Manifest — [Topic Name]

[One entry per distinct insight worth creating as a Literature Note.]

### Note [N]: [Proposed note title — self-contained, specific]
- **features**:
  - [factual|conceptual|application|decision|diagnosis|code-artifact]
- **Maturity**: seed
- **Domain**: [primary domain from Domains/ folder]
- **Search terms**: [[Term1]], [[Term2]], [[Term3]], [[Term4]], [[Term5]]
- **Core insight** (1-2 sentences, faithful to the author): [the insight itself]
- **Evidence**: [specific data, example, or argument from source]
- **Source pointer**: [page, chapter or timestamp]
- **Suggested connections**: [[Possible existing note or concept]] because [reason]
```

**Critical: search terms are the most important field in the manifest.** Include:
- The primary concept name
- Synonyms and adjacent concepts
- Domains where this idea applies
- The problem it solves (not just the solution name)

Aim for 4–6 terms per note. A note about "spreading practice over days beats cramming" should have: `[[Spaced Repetition]]`, `[[Desirable Difficulties]]`, `[[Forgetting Curve]]`, `[[Study Planning]]`, `[[Long-Term Retention]]` — not just `[[Spaced Repetition]]`.

**Other manifest principles:**
- One entry per distinct idea — if there are 15 notes to create, list all 15.
- Titles should be self-contained: "The Data Fallacy — more data ≠ better understanding" beats "Data and understanding".
- The manifest doesn't replace the 3 layers — it adds structure. Layers give depth; the manifest gives `open-brain-extract` its work queue.

---

## Key Principles

**Compress, don't summarize.** A summary preserves structure and reduces length. Compression finds load-bearing ideas and discards the rest. Ask: "If someone could only remember 5 things, which 5 make them most capable?"

**Concrete beats abstract.** The brain encodes "the company that tried X and failed because Y" far better than "avoid doing X."

**Structure reveals meaning.** How you organize knowledge IS knowledge. Relationships between concepts often matter more than the concepts themselves.

**Expert thinking is the prize.** The most valuable extraction is not facts — it's the mental model that makes an expert effective.

**Use matrix organizers.** When comparing multiple items across dimensions, use tables (d=1.07 — highest effect size of any mapping strategy).

---

## Book Tier Assessment

After the Extraction Manifest, always produce this section for books and long-form content. Skip for articles, videos, or short content.

```
## Book Tier Assessment — [Title]

| Criterion | Score | Justification |
|----------|-----------|---------------|
| **Originality** | X/3 | Does it introduce its own frameworks or concepts, or restate what is already known? |
| **Density** | X/3 | Ratio of actionable insights per page |
| **Convergence** | X/3 | How many points of contact with domains already present in the vault? |
| **Evidence** | X/3 | Are claims backed by research/cases, or mostly the author's opinion? |
| **TOTAL** | X/12 | |

**Tier: [TOP / INTERESTING / SKIP]**

→ [If TOP]: open-brain-index will generate an exhaustive Outline (chapter by chapter, concept map, claims with evidence).
→ [If INTERESTING]: open-brain-index will generate a minimal Outline (central thesis, one-line chapters, 5-8 key concepts).
→ [If SKIP]: Not worth indexing. The relevant insights are already in the Extraction Manifest.
```

**Scoring criteria:**
- **Originality**: 1 = restates the known | 2 = synthesis with its own perspective | 3 = genuinely new framework
- **Density**: 1 = diluted, lots of filler | 2 = balanced | 3 = high density, every chapter contributes
- **Convergence**: 1 = isolated domain | 2 = 3-5 connections with the vault | 3 = 6+ cross-domain connections
- **Evidence**: 1 = unsupported opinion | 2 = mixed | 3 = empirical research or concrete cases with data

This is a reading-time estimate only. The binding admission score is `open-brain-extract` Step 0.4, which replaces Convergence with **Contribution** (what the source adds that the vault doesn't already say) and adds a redundancy veto; if the two disagree, extract's score wins.

**Thresholds**: ≥9 → TOP | 5-8 → INTERESTING | ≤4 → SKIP

The user can override the tier at any time by stating it explicitly.

---

## Activation Prompt

After the Extraction Manifest, always close with this section. Its purpose is the bridge between reading and learning — forcing the integration step that actually creates knowledge.

```
---

## Activation Prompt — Before You Archive This

Knowledge that isn't activated decays. Before sending these notes to the vault, spend 5 minutes with these questions:

**1. What did you already know?**
Which ideas in this analysis were genuinely new vs. confirmed what you already believed?
(This reveals your actual learning delta, not just what you read.)

**2. What creates resistance?**
Is there a mental shift or principle here that feels wrong or counterintuitive to you?
(Resistance is where the real learning is. Either the author is wrong — and you should be able to explain why — or your mental model needs updating.)

**3. Where would you apply this first?**
Name one specific situation in the next 30 days where one of these ideas would change what you do.
(If you can't name one, the knowledge has no activation trigger and will stay theoretical.)

Respond to any of these here, or tell me to proceed directly to open-brain-extract.
```

If the user responds to any of these, continue the conversation before proceeding to the vault. Their responses reveal their prior knowledge, resistance points, and activation triggers — all of which should inform how `open-brain-extract` writes the notes (especially the `[!claude] Connectors` callout and what the user later adds in `## Your extension`).

---

## Output Format

Produce all sections in order: Knowledge → Compression → Mental Models → Practical Extraction Appendix (conditional sections) → Extraction Manifest → Book Tier Assessment (books only) → Activation Prompt.

Use the topic name from the content as header throughout.

For very large content (full book), process section by section, then produce a synthesis across all sections and a single unified Extraction Manifest at the end. The Activation Prompt appears only once, after the final unified Manifest.
