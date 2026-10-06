---
name: open-brain-panel
description: 'Expert panel simulator. 3-6 domain experts review work in-character, then synthesis: consensus,
  tensions, scorecard, improvement roadmap. Triggers: expert panel, round table, what would X say, scorecard,
  critique, open-brain panel'
metadata:
  folded_from_top_level:
    version: 9.0.0
  version: 9.0.0
  status: canonical
  consumes:
  - A piece of work needing expert feedback (PRD, email, one-pager, post, deck, strategy memo, Case, Permanent
    Note)
  - Implicit or stated audience/goal for that work
  produces:
  - In-character reviews from 3-6 selected experts with scores and one specific change each
  - 'A synthesis: consensus, tensions, a scorecard, and a max-3-item improvement roadmap mapped to skills'
  handoffs:
  - skill: open-brain-execute
    when: an improvement-roadmap priority requires rebuilding a section
    requires_approval: true
  - skill: open-brain-improve
    when: an improvement-roadmap priority requires targeted practice
    requires_approval: true
  - skill: open-brain-extract
    when: an improvement-roadmap priority requires extracting new literature notes
    requires_approval: true
---

# Open Brain — Panel

Runs a simulated expert panel on a piece of work in a single pass — selects 3–6 domain experts, embodies each one to produce a focused in-character review, then synthesizes consensus, tensions, a scorecard, and an improvement roadmap. Replaces an older two-step chain (expert reviews, then a separate synthesis) that always ran together but cost twice the tokens. Trigger when the user wants expert feedback, a panel review, a critique, or a rubric-based evaluation of a document, email, PRD, strategy, post, or decision.

---

## Step 1: Understand the Work

Read the work carefully:
- What type is it? (PRD, email, one-pager, post, deck, strategy memo, Case, Permanent Note, etc.)
- What domain? (product, leadership, writing, data, science, design, decision-making)
- What is the author trying to achieve with it? (If unclear, ask once.)
- Who is the audience? (Internal team, leadership, peers, external readers, their future self)

Domain + type drive expert selection. Do not skip this.

---

## Step 2: Select the Panel (3–6 experts)

Rules:
- **3 minimum, 6 maximum.** Fewer than 3 produces false consensus. More than 6 produces noise.
- **Mix lenses.** Pick experts whose evaluation criteria don't fully overlap.
- **Anchor one skeptic.** At least one expert should be likely to give a lower score than the average.
- **Match the work type.** A PRD needs product + strategy + at least one communication expert. An internal email needs communication + leadership experts. A Permanent Note needs learning/retrieval experts + a domain expert.

If the user specified experts, use those. Otherwise pick from this catalog:

### Communication & Writing
| Expert | Core Work | Lens | Scores high when… |
|--------|-----------|------|-------------------|
| **William Zinsser** | On Writing Well | Clarity, clutter | Every word works. No clutter. |
| **William Strunk** | Elements of Style | Grammar, vigor | Active voice. Positive form. |
| **Steven Pinker** | The Sense of Style | Cognitive load | Reader never re-reads a sentence. |
| **Chip Heath** | Made to Stick | SUCCESs | Simple, unexpected, concrete, credible, emotional, story. |
| **Nancy Duarte** | Resonate | Narrative arc | Tension between "what is" vs "what could be." |
| **Cole Nussbaumer Knaflic** | Storytelling with Data | Data clarity | One clear story, minimal cognitive load. |
| **Erica Dhawan** | Digital Body Language | Channel fit | Message matches channel + trust level. |
| **Kerry Patterson** | Crucial Conversations | Psychological safety | Safety before hard message. |

### Product & Strategy
| Expert | Core Work | Lens | Scores high when… |
|--------|-----------|------|-------------------|
| **Marty Cagan** | Inspired / Empowered | Discovery, empowerment | Problems validated before solutions. |
| **April Dunford** | Obviously Awesome | Positioning | Clear who it's for, why different, why it matters. |
| **Teresa Torres** | Continuous Discovery | Evidence, opportunity | Assumptions surfaced and tested. |
| **Eric Ries** | The Lean Startup | Validated learning | Fastest path to learning. |
| **Alex Osterwalder** | Business Model Canvas | Business model coherence | All 9 blocks cohere. |
| **Bob Moesta** | Demand-Side Sales | JTBD | Focus on struggling moment. |
| **Josh Seiden** | Outcomes Over Output | Behavior change | Measures a real change in behavior. |

### Leadership & Management
| Expert | Core Work | Lens | Scores high when… |
|--------|-----------|------|-------------------|
| **Kim Scott** | Radical Candor | Direct + care | Feedback specific, kind, actionable. |
| **Patrick Lencioni** | Five Dysfunctions | Team trust | Addresses root, not symptom. |
| **Reed Hastings** | No Rules Rules | Freedom + responsibility | Empowers with context, not process. |
| **Jim Collins** | Good to Great | Discipline, hedgehog | Relentless focus on what you're best at. |
| **Michael Bungay Stanier** | The Coaching Habit | Coaching questions | Asks more than it tells. |

### Data & Thinking
| Expert | Core Work | Lens | Scores high when… |
|--------|-----------|------|-------------------|
| **Edward Tufte** | Beautiful Evidence | Data-ink ratio | Maximum data, minimum ink. |
| **Nate Silver** | Signal and Noise | Prediction quality | Signal from noise. Uncertainty acknowledged. |
| **Daniel Kahneman** | Thinking Fast and Slow | Biases | System 2 engaged where needed. |
| **Philip Tetlock** | Superforecasting | Calibration | Claims are falsifiable and calibrated. |
| **Adam Grant** | Think Again | Intellectual humility | Updates views on evidence. |

### Learning & Retrieval
| Expert | Core Work | Lens | Scores high when… |
|--------|-----------|------|-------------------|
| **Anders Ericsson** | Peak | Deliberate practice | Practice targets weakness with feedback. |
| **Carol Dweck** | Mindset | Growth framing | Frames challenge as growth. |
| **Peter Brown** | Make It Stick | Retrieval, spacing | Testing over re-reading. |
| **Tiago Forte** | Building a Second Brain | CODE pipeline | Idea captured, distilled, connected, expressed. |

For domains not covered (sales, design, customer success) the user can name an expert directly; embody them using best reconstruction of their published framework.

---

## Step 3: Become Each Expert — Produce a Review Each

For each expert on the panel, produce this block. **First person. Their voice. Their priorities. Their blind spots. Do not balance — bias IS the feature.**

```markdown
### [Expert Name] — Review

**Lens**: [The one dimension this expert is evaluating]
**Score**: [1–10] — [one-sentence justification in the expert's voice]

**What works**
- [2–3 specific observations. Point to exact parts of the work ("paragraph 2", "section titled X", "the closing line"). Explain WHY it works through this expert's framework.]

**What fails**
- [2–3 specific failures. Point to exact parts. Explain WHY through this expert's principle/anti-pattern. This is the most valuable section — do not soften.]

**The one change I'd make**
[Single highest-impact recommendation. Specific enough to execute in 15 minutes. Not "improve clarity" but "delete sentences 3 and 4 of paragraph 2 and merge the rest into paragraph 1."]

**Principle that applies**
> "[Real or representative principle from this expert's work]"
[1–2 sentences applying it to the work under review.]
```

**Rules for the reviews:**
- Be the expert, don't describe them. Not "Zinsser would say…" but "I see three unnecessary modifiers in paragraph 2."
- Score honestly. A panel where everyone gives 7 is useless. The spread IS the diagnosis.
- Point to specific parts of the work. Always.
- One change per expert. Fifteen-minute specificity.
- Bias is a feature. Zinsser cares about prose, not visuals. Duarte cares about narrative arc, not grammar. Don't flatten them into generic reviewers.

---

## Step 4: Synthesize — Consensus, Tensions, Scorecard

After all individual reviews, drop the expert personas and become the panel moderator.

### 4a. Panel Summary

```markdown
## Expert Panel — Synthesis

### Panel
| Expert | Lens | Score |
|--------|------|-------|
| [Name] | [dimension] | [1–10] |

### Overall score: [weighted average] / 10 — [🟢 ≥7 | 🟡 4–6 | 🔴 ≤3]
```

### 4b. Consensus and Tensions

```markdown
### Consensus
[What ALL experts agree on — both strengths and weaknesses. High-confidence findings. 2–4 bullets.]

### Tensions
[Where experts DISAGREE. This is where the real insight lives.]

For each tension:
- **[Expert A] vs [Expert B]**: A scores [dimension] at [X] because [reason]. B scores it at [Y] because [different reason].
- **What this means for the author**: [the trade-off. Not a problem to solve — a tension to navigate consciously.]
```

### 4c. Scorecard

Dimensions are extracted from what the experts actually evaluated, not a generic checklist.

```markdown
### Scorecard

| Dimension | Score | Status | Expert(s) | Key issue |
|-----------|-------|--------|-----------|-----------|
| [Dim] | [1–10] | 🟢/🟡/🔴 | [Who scored] | [One line] |
```

### 4d. Improvement Roadmap (map to skills)

Max 3 priorities. Ordered by impact. Each mapped to a specific skill.

```markdown
### Improvement priorities

**1. [Highest — fix first, worst 🔴]**
- What: [Specific problem from the reviews]
- Why first: [Impact if not fixed]
- How: [Concrete action from the expert who identified it]
- Skill: `open-brain-execute` (rebuild a section), `open-brain-improve` (targeted practice) or `open-brain-extract` (new Literature Notes) → Layer [N] where applicable
- Success: [How the author will know it's fixed]

**2. [Second priority]** … (same structure)

**3. [Third priority]** … (same structure)
```

### 4e. Re-review Trigger

```markdown
### When to re-review
[Condition for submitting again. Usually: "After tackling priorities 1 and 2, run the panel again — the next layer of issues will surface."]
```

---

## Step 5: Optional — Update Vault

If the work reviewed was a Permanent Note or Literature Note and the panel found substantive issues:
- Offer to log the panel's key finding as a comment/annotation in the note's "Review Log" section.
- Do not rewrite the note. The user decides.

If the work was an external artifact (email, PRD, post, essay) and a PN was used in its creation, and the user confirms it shipped:
- Do not hand-increment `external_outputs` — it is derived. Add an entry to your output ledger (if you keep one, e.g. `Resources/Output Ledger/ledger.jsonl`) listing the contributing PNs, and rerun `python3 "$OPEN_BRAIN_ENGINES/engine/output_ledger.py" counters`.

---

## Principles

**One skill, one pass.** Individual reviews and synthesis always ran together. v9 makes that official. Saves tokens, eliminates handoff loss, guarantees synthesis uses what just emerged.

**Tensions > consensus.** Consensus is useful but unsurprising. Disagreement between experts is where the author learns something new about trade-offs. Lean into it.

**Scores must differentiate.** A scorecard where every dimension is 6–7 is useless. Push for honest range.

**Map to skills, not just advice.** Every priority points to a specific `open-brain-*` skill. "Improve clarity" is advice. "Run `open-brain-execute` to rebuild this section using the Big Idea template, then re-submit to panel" is a plan.

**Hygiene rules in every review.** Don't name private third parties (colleagues, clients, people from the author's life) in reviews; the cited experts are fine. Don't anchor abstract or general work to the author's own company or product unless the work is about it. When summarizing, use the author's own voice and wording, not the panel's.
