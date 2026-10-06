---
name: open-brain-improve
description: 'Improvement and practice. Diagnostic rubrics, coaching plans, practice exercises. Phase
  3 of the learn system. Triggers: how do I improve, what am I doing wrong, rubric, coaching, practice exercises,
  open-brain improve'
metadata:
  folded_from_top_level:
    version: 9.0.0
  version: 9.0.0
  status: canonical
  consumes:
  - Output of open-brain-analyze
  - Output of open-brain-execute
  - A specific capability or skill to diagnose and improve
  produces:
  - Diagnostic rubrics with red/green flags
  - Coaching map by level (novice → expert)
  - Practice exercises with success criteria and real-world experiments
  handoffs:
  - skill: open-brain-analyze
    when: when the cycle closes, the output of the Practice phase feeds the next analysis cycle
    requires_approval: true
---

# Open Brain — Improve

Phase 3 of the learn system closes the learning loop: evaluate whether knowledge is being applied correctly, identify gaps, and build deliberate practice. Works with output from open-brain-analyze and open-brain-execute; if those don't exist, extract what's needed but stay focused on the improve phase. Produces three layers: Diagnosis, Coaching, and Practice — grounded in cognitive science (self-testing d=0.57, self-explaining d=0.61, teaching d=0.77).

---

## Process

### Step 1: Define the Capability
- Observable differences: beginner vs intermediate vs advanced
- Critical sub-skills
- Most costly mistakes

### Step 2: Build Diagnostic System
Rubrics and criteria for self-assessment and external review.

### Step 3: Design Improvement Path
Progression from novice to expert with specific coaching at each transition.

### Step 4: Create Practice Activities
Exercises targeting specific sub-skills with built-in feedback.

---

## Layer 7: Diagnosis

**Purpose**: Accurate self-assessment and external review. Identify exactly where work is strong, weak, and why.

```
## 7. Diagnosis — [Topic Name]

### Quality Criteria
[For each key output/behavior:]

#### [Output/Behavior Name]
**Excellent**: [Specific, observable — not "good communication" but "key message in first 30 seconds, ≤3 data points, explicit call to action"]
**Adequate**: [Minimum acceptable standard]
**Poor**: [Failure patterns with WHY they fail]

### Diagnostic Rubric
| Dimension | Novice | Developing | Competent | Expert |
|-----------|--------|------------|-----------|--------|
| [Dim 1] | [Observable behavior] | ... | ... | ... |

### Red Flags
[Observable signals something is wrong. Each: what you see, what it means, what to fix.]

### Green Flags
[Signals things are on track. Prevents over-correction.]

### Expert Review Questions
[Questions an expert would ask reviewing work. Ordered by importance.]

### Self-Assessment Protocol
[Step-by-step self-evaluation process. Designed to catch common blind spots.]
```

**Quality check**: Every criterion is observable and specific (behavioral anchors, not comparative language). Red flags are early warnings. Self-assessment accounts for known blind spots.

---

## Layer 8: Coaching

**Purpose**: Guide from current level to next level. Specific recommendations based on where someone is.

```
## 8. Coaching — [Topic Name]

### Skill Progression Map
[For each transition:]

#### From [Level N] to [Level N+1]
**You're at this level when**: [Observable indicators]
**The key shift**: [Fundamental change — not "learn more" but "stop optimizing parts and start optimizing the system"]
**Focus on**: [2-3 specific practice areas]
**Stop doing**: [Behaviors that were fine before but now hold you back]
**Start doing**: [New behaviors marking the transition]
**Typical timeline**: [Realistic with conditions]
**Signs you've made it**: [How to know you leveled up]

### Common Plateaus
[Where stuck, why, and what breaks through.]

### Expert Habits
[Specific practices experts maintain — not "practice regularly" but "review every failed cycle within 48h and write 3 hypotheses before looking at data".]

### Mistakes by Level
[Novice mistakes ≠ intermediate mistakes. Map each level's typical errors and fixes.]

### Learning Accelerators
[What disproportionately speeds up improvement: exposure types, relationships, mindset shifts, tools.]

### What NOT to Do
[Anti-patterns in the improvement process itself. How people try to improve but actually build bad habits.]
```

**Quality check**: Stages based on behavioral shifts, not time. Each transition has start/stop behaviors. Plateaus include breakthroughs. Expert habits are specific and actionable.

---

## Layer 9: Practice

**Purpose**: Deliberate practice that builds real capability.

```
## 9. Practice — [Topic Name]

### Practice Architecture
[Sub-skills trained, exercise sequence, recommended spacing.]

### Exercises
[For each:]

#### [Exercise Name]
**Targets**: [Specific sub-skill]
**Level**: [Beginner/Intermediate/Advanced]
**Format**: [roleplay/case analysis/writing/decision simulation/quiz/teaching]
**Time**: [Realistic estimate]
**Setup**: [Materials, context, scenario]
**Instructions**: [Clear steps]
**Success criteria**: [How to know you did it well — measurable]
**Debrief questions**: [Reflection questions driving Kolb's RO stage]
**Variations**: [Context/difficulty modifications]

### Retrieval Practice Sets
[Free-recall and cued-recall questions (NOT multiple choice). Answers in separate section.]

### Scenario Bank
[Realistic scenarios for case analysis. Each: situation, info available, constraints, ambiguity. Include expert analysis.]

### Practice Schedule
[4-week plan with spacing. Week 1: exercises A,B. Week 2: exercise C + review A. Build in spaced repetition.]

### Teaching Exercises
[Require explaining/teaching to others. Leverage d=0.77 strategy. Include: what to teach, to whom, format, how to evaluate effectiveness.]

### Real-World Experiments
[Simulated practice builds confidence; real-world experiments build the actual skill. For each key behavior from open-brain-execute, design a testable assignment:]

#### [Experiment Name]
**Hypothesis**: "I believe that if I [do X], then [result Y] will happen, because [reason Z]"
**Task**: [One concrete action to take in the next 48-72 hours. Specific enough to do today.]
**Debrief questions** (answer after the experiment):
1. What actually happened vs. what I predicted?
2. What did I do differently from what I planned?
3. What does this tell me about the underlying principle?
**Diagnosis**: Did the principle hold? Where did it break? What would I adjust?
**Next experiment**: [Escalate to a bigger test, or revise the hypothesis]

[The experiment loop is: Hypothesis → Real action → Debrief → Diagnosis → Next attempt. This is what converts understanding into capability.]

### Recommendation Hooks
[Learning that stays private has limited value. For each key insight, design the version that travels:]
- **One-sentence hook**: [The takeaway that survives a casual conversation — specific enough to be memorable, short enough to repeat]
- **Retellable story**: [The anecdote from the source or from practice that illustrates the principle — character, tension, outcome, lesson]
- **Visible win**: [What evidence would a learner show after applying this? "I tried this and..." format]
- **Status signal**: [How does sharing this make the sharer look thoughtful or expert?]

[Ask: "What sentence will the learner repeat to a colleague tomorrow?" Design for that sentence.]
```

**Quality check**: Every exercise has explicit success criteria. Uses high-effect strategies (self-testing, teaching, self-explaining). Scenarios are ambiguous enough for judgment. Practice schedule implements spacing. Real-World Experiments connect learning to actual behavior change. Recommendation Hooks are specific enough to be memorable.

---

## Key Principles

**Formative, not summative.** Rubrics = roadmaps, not report cards. The question: "what should I work on next?" not "what score did I get?"

**Observable behaviors, not vague qualities.** "Good strategic thinking" is not diagnostic. "Identifies 3+ alternative hypotheses before committing" is.

**Practice needs feedback loops.** An exercise without success criteria is just activity.

**Spacing is non-negotiable.** Distributed practice produces durable skill. It feels harder — that IS the point.

**Retrieval > re-reading.** Force recall, not recognition. Free-recall beats multiple choice.

**Teaching is the strongest test.** Design exercises requiring the learner to teach (d=0.77).

**Different levels need different practice.** Novice = basic skills. Intermediate = complexity + edge cases. Expert = judgment in ambiguity.

---

## Output Format

Produce all 3 layers in order: Diagnosis → Coaching → Practice. Use topic name consistently. The output feeds back into open-brain-analyze for deeper understanding in the next cycle.
