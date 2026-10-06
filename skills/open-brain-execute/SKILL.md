---
name: open-brain-execute
description: 'Action and execution. Transforms knowledge into practical guides, templates, checklists,
  decision frameworks. Phase 2 of the learn system. Triggers: how do I apply this, create a template, practical
  guide, checklist, decision framework, open-brain execute'
metadata:
  folded_from_top_level:
    version: 9.0.0
  version: 9.0.0
  status: canonical
  consumes:
  - Structured knowledge produced by open-brain-analyze (Knowledge, Compression, Mental Models)
  - Raw content, if that output does not exist yet
  produces:
  - Application guide (Quick-Start + detailed workflows)
  - Behavior system (cues, friction audit, identity, fallback)
  - Reusable artifacts with a filled-in example
  - Decision map with trade-offs and principles
---

# Open Brain — Execute

Phase 2 of a 3-phase learning system. Transform structured knowledge into things people can actually use — guides that direct action, artifacts that capture knowledge in reusable form, and decision frameworks that improve judgment. Produces 3 layers: Application, Artifacts, and Decision.

Works with output from open-brain-analyze (Knowledge, Compression, Mental Models) as primary input. If that doesn't exist, extract what's needed from raw content — but stay focused on the DO phase, not the UNDERSTAND phase.

---

## Process

### Step 1: Identify the Action Surface

Map what someone could actually DO:
- What tasks does this knowledge enable?
- What workflows does it improve?
- What decisions does it inform?
- What artifacts could capture this for reuse?

### Step 2: Prioritize by Impact

Rank by Frequency × Impact × Difficulty. Focus on high-frequency, high-impact, high-difficulty applications. Skip what people can figure out alone.

### Step 3: Produce the 3 Layers

---

## Layer 4a: Application

**Purpose**: "I understand the concepts, now what do I actually DO?"

```
## 4. Application — [Topic Name]

### Quick-Start Guide
[Minimum viable application. 5-7 steps max for 30 minutes. Include expected output of each step.]

### Detailed Workflows
[For each major application area:]

#### [Workflow Name]
**When to use**: [Specific trigger situation]
**Prerequisites**: [What you need before starting]
**Steps**:
1. [Action] → [Expected result]
2. [Action] → [Expected result]
**Decision points**: [Where you choose, with guidance]
**Common mistakes**: [What goes wrong, how to avoid]
**Output**: [What you should have when done]

### Guiding Questions
[Questions to ask at each stage — thinking scaffolds that force active engagement rather than mechanical step-following.]

### Adaptation Guide
[How to modify for different contexts. Use matrix: team size, industry, maturity, time, resources.]

### Real-World Examples
[2-3 concrete examples. Show: situation, what was done, why, result. Include one good and one mediocre execution with specific differences highlighted.]
```

**Quality check**: Every step produces visible output. Decision points have guidance. Workflows say WHEN to use them, not just HOW. Examples show good vs. mediocre.

---

## Layer 4b: Behavior System

**Purpose**: Plans fail not because people lack intention — they fail because conditions don't support the behavior. This layer designs the environment and triggers so the Application guide actually gets used.

```
## 4b. Behavior System — [Topic Name]

### Cue Design
[What will reliably trigger each key behavior? Cues must be specific — "when I feel ready" is not a cue, "when I open my notes app" is.]
- **Behavior**: [What should be done]
- **Cue**: [Specific situation, time, place, or preceding action]
- **Implementation intention**: "When [cue], I will [behavior] in [context]"

### Friction Audit
[For each desired behavior, what makes it hard and how to remove it:]
| Behavior | Current friction | How to remove it |
|----------|-----------------|-----------------|
| [Action] | [What blocks it] | [Specific fix] |

### Identity Frame
[Connect behaviors to who the learner is becoming. One strong identity frame is more durable than ten action items.]
- "A [type of person] does [behavior] because [value/identity it represents]"
- What vote does each practice cast for the kind of person the learner is becoming?

### Fallback Protocol
[What happens after a miss? This is where most behavior change systems collapse.]
- Re-entry trigger: [The next specific opportunity to try again]
- Minimum viable version: [The smallest possible version of the behavior when conditions are hard]
- Normalization: missing once is data, not failure — the question is what happens next
```

**Quality check**: Cues are specific and automatic. Identity frame is genuine (not "be a better PM" but connects to a value the person actually holds). Fallback protocol exists — without it, one miss kills the behavior permanently.

---

## Layer 5: Artifacts

**Purpose**: Reusable tools, documents, templates. Makes knowledge tangible and shareable.

```
## 5. Artifacts — [Topic Name]

### Artifact Map
[Table: name, type, purpose, when to create, complexity level]

### Core Artifacts
[For each high-priority artifact:]

#### [Artifact Name]
**Type**: [template/document/scorecard/checklist/dashboard/etc.]
**Purpose**: [What it does and why]
**When to create**: [Trigger or cadence]
**Structure**: [Exact template with sections, fields, format]
**Example** (filled): [Completed example with realistic content — critical for usability]
**Quality signals**: [How to know it's good]
**Common failure modes**: [What bad looks like and why]

### Artifact Dependencies
[Which feed into which. Creation order. What updates when.]

### Artifact Maintenance
[Review cadence. Revision triggers. What goes stale.]
```

**Quality check**: Every artifact has structure AND filled example. Specific enough to create directly. Dependencies explicit. Quality signals and failure modes included.

---

## Layer 6: Decision

**Purpose**: Map decisions this knowledge improves. Better decisions = highest-leverage outcome.

```
## 6. Decision — [Topic Name]

### Decision Map
[Table: decision, frequency, stakes (low/med/high), reversibility (easy/hard/irreversible)]

### Key Decisions
[For each high-stakes decision:]

#### [Decision Name]
**Context**: [When this arises]
**What you're actually deciding**: [The real choice underneath the surface question]
**Options**: [Realistic options including "do nothing"]
**Trade-offs**:
| Option | Advantages | Disadvantages | Best when... |
|--------|-----------|---------------|-------------|
**Information you need**: [Essential vs nice-to-have data/signals]
**Red flags**: [Signals to NOT proceed]
**What an expert would do**: [Specific, not generic]
**Common traps**: [How people get this wrong]

### Decision Principles
[Meta-rules for judgment across many decisions in this domain.]

### Decision Sequences
[How decisions chain — one constrains/enables others. Map cascading effects.]
```

**Quality check**: Trade-off tables are honest (every option has real pros AND cons). Expert behavior is specific. Decision sequences show cascading effects. Red flags are observable.

---

## Key Principles

**Action first, explanation second.** Every section leads with what to DO. If someone reads the output and doesn't know what to do differently tomorrow, the output has failed.

**Concreteness fading.** Start with a concrete example, then generalize. Never start with a principle and illustrate it — start with the situation and extract the principle.

**Trade-offs, not answers.** For decisions, make trade-offs visible so people choose well given THEIR context. If an option has no disadvantages, you haven't thought hard enough.

**Templates need examples.** An empty template is nearly useless. Template + filled example = teaching (d=0.77). Always include both.

**Decisions are the premium output.** Better decisions outvalue better templates. Invest extra in the Decision layer.

**Plans without systems don't survive contact with reality.** Layer 4a tells people what to do. Layer 4b designs the conditions that make doing it likely. Both are necessary — a workflow without a cue is a wish.

---

## Output Format

Produce all layers in order: Application (4a) → Behavior System (4b) → Artifacts (5) → Decision (6). Use topic name consistently. For large topics, organize by domain area but always produce complete layers.
