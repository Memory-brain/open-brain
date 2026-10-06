---
name: open-brain-course-evaluate
description: >
  Evaluates and closes a v3 course by reading practice-export.md (downloaded from course.html into the course
  folder) directly from the vault. Evaluates vocabulary, written production and transfer scenarios. No API. Triggers: course-evaluate, evaluate this course,
  close the course, evaluate the <Skill> course.
metadata:
  version: 3.0.0
  status: canonical
  consumes:
  - practice-export.md (schema practice-export/1) downloaded from course.html into the course folder
  - course-content.json with canonical answers, evaluation_criteria and expert_reference
  produces:
  - course-evaluation.md with vocabulary score, result per exercise/scenario and an overall diagnosis
  - next-course-brief.md if the next_move requires generating a follow-up course
---

# open-brain-course-evaluate (v3)

Closes a generated course by reading the learner's exported answers from the vault.

## Before you run it

In `course.html` the learner clicks **Download practice-export.md** (or **Copy markdown** and pastes it
into a new file) and saves it as `Skills/<Domain>/<Skill>/practice-export.md`, next to `course.html`.
Only if you run your own sync endpoint, the course's optional "Sync to the vault" button writes the same
file. Then: `course-evaluate`.

## When to use

The user says:

- `course-evaluate`
- `evaluate this course`
- `close the course`
- `evaluate the <Skill> course`
- `evaluate my course answers`

## Flow

1. **Identify the course.** Find the Skill by name or scan `Skills/` for the most recent
   `practice-export.md`.
2. **Read from the vault:**
   - `Skills/<Domain>/<Skill>/practice-export.md` (exported answers — format below)
   - `Skills/<Domain>/<Skill>/course-content.json` (canonical answers + scenarios)
3. **Evaluate** each exercise and scenario with the rules below.
4. **Write** the results to the vault.
5. **Record the outcome** in the mastery graph, if the course engine is available:
   `python3 "$OPEN_BRAIN_ENGINES/course-engine/course_build.py" record-outcome …` (check the engine's
   usage for the exact arguments). This is what updates `Skills/skill_mastery_state.yaml`.

## practice-export.md format (schema `practice-export/1`)

Written by the course page (template `course.html.template`, `buildPracticeExport`). Every learner answer
is a Markdown blockquote (`> …`); an empty answer is `> _(empty)_`.

```markdown
---
type: practice-export
schema: practice-export/1
domain: "<Domain>"
skill: "<Skill>"
exported_at: <ISO timestamp>
confidence_wager: alta | media | baja | not recorded     # high | medium | low bet before practice
vocab_score: "<correct>/<total>"
practice_done: "<attempted>/<total>"
scenarios_done: "<answered>/<total>"
---

# Practice export — <Skill>

## Vocabulary
Score: X/Y (Z%)
| # | term | selected | correct |          # one row per concept quiz; "_(not answered)_" if skipped

## Modules
### M<n> — <module title>
- effort_check: it was hard | normal | it came easily | not recorded
**Comprehension:** <question>
> <answer>
**Teaching:** <prompt>
> <answer>

## Exercises
### E<n> — <module> · <concept>
- state: answered | i_dont_know | quiz_passed | quiz_failed | revealed | pending
- revealed: yes | no
- quiz_score: 1/2 | 0/2 | none
**Prompt:** <flashcard front>
> <answer>

## Scenarios
### S<n> — <scenario title>
- state: answered | draft | pending        # draft = text typed but "Save answer" not pressed
- effort_check: …
**Deliverable:** <deliverable>
> <answer>
```

Map `E<n>` to the n-th flashcard across `modules[].flashcards` and `S<n>` to `scenarios[n-1]` in
`course-content.json` to get the canonical `back`, `evaluation_criteria` and `expert_reference`
(the export deliberately omits them).

## Rules

1. The free-text answer weighs more than the quiz.
2. `revealed` is not mastery.
3. `i_dont_know` is a useful signal for the next course.
4. Mastery = explains in their own words + applies it to an example.
5. **Scenarios are the strongest transfer signal.** Vocabulary + production
   without transfer = recognition, not mastery.
6. Use `evaluation_criteria` and `expert_reference` from course-content.json to evaluate
   scenarios (the learner never saw the expert reference).
7. Cross each module's/scenario's `effort_check` against its real score: "came easily" + low score
   is a false positive (illusion of learning). Never score from `effort_check` alone.

## Output

```markdown
## Vocabulary Score
X/Y (Z%)

## Result per exercise
| exercise | state | verdict | score 0-2 | what's missing | micro-action |

## Result per scenario
| scenario | criteria met | score 0-3 | what it shows | what's missing |

## Overall diagnosis
- Level: insufficient / basic / functional / solid
- Transfer: yes/no

## Mastered concepts
## Gaps to repair
## False positives

## Next Move
repair_vocabulary | practice_real_cases | repair_course | advanced_course

## Next Course Brief (if applicable)

## Machine-readable YAML
```

## Effects

Writes:
- `Skills/<Domain>/<Skill>/course-evaluation.md`
- `Skills/<Domain>/<Skill>/next-course-brief.md` (if next_move requires a course)

## Backward compatibility

If `practice-export.md` doesn't exist, accept the markdown pasted in the chat (the course's "Copy markdown" or "Copy prompt + answers" output, same format) and suggest saving it as `practice-export.md` next time. Older exports without the `schema` field: read them best-effort with the same rules.
