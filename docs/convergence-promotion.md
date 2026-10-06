---
module: module-3-maturation
related_skills:
  - open-brain-promote
  - open-brain-synthesize
last_updated: 2026-10-06
---

# Convergence-Based Promotion

## What It Is

Convergence-based promotion is the mechanism that moves ideas from Literature Notes — records of what sources said — to Permanent Notes — records of what you believe, supported by evidence. It is the central act of knowledge synthesis. Everything before it is preparation; everything after it is application.

Most PKM systems treat this transition as informal: you read enough, you feel confident enough, you write a synthesis. The problem is that "confident enough" is not a reliable signal. You can feel confident after one persuasive book. You can feel perpetually uncertain after twenty books that never quite align. Informal synthesis leaves the decision to intuition, which is biased toward both premature confidence and indefinite procrastination.

Convergence-based promotion replaces that intuition with a test. The question is not "do I feel ready to synthesize?" but "have two or more independent sources made the same structural claim?" If yes, the test is passed. If no, the note stays in the queue. The threshold is explicit — but a written threshold only holds where something checks it. The independence rule is not enforced in code, so the promotion ritual checks it by hand every time, and the own-voice gate is recorded as a field that can be audited rather than a judgment nobody can verify afterwards. In the reference vault, clusters approved with a blanket "do it all" were written with that field empty, which is why an empty field now means the gate failed.

---

## The Convergence Test

Before promoting any cluster of Literature Notes into a Permanent Note, `open-brain-promote` applies a four-part test. All four must pass.

**1. Different source prefixes: do the notes come from at least two different sources?**

Convergence within one source is supporting evidence, not synthesis. A chapter that repeats its own thesis three times is still one source.

**2. Different vocabulary or framing: do the sources describe the idea differently enough that the agreement is non-trivial?**

Two notes that use the same words for the same idea are often the same idea copied, not two derivations of it. Agreement reached from different starting vocabularies is what makes convergence informative.

**3. Specific enough to be actionable: could the claim guide a real decision?**

"Learning requires feedback" fails: nobody decides anything differently after reading it. "The right difficulty is just above current ability — too easy builds nothing, too hard triggers overload" passes. A claim that can't change a decision is a definition, not a position.

**4. Counterfactual: if this note didn't exist, which concrete decision or output would be harder?**

Answer with a specific example from your own work or vault. An abstract answer fails the cluster. This question lives in the brief as a gate; it is not stored in the note.

Two gates sit on top of the test.

**The independence check.** The sources must have different authors, and neither may cite the other. Two works by the same author count as one reinforced source, not two; a book and its popularization don't qualify; two sources that both trace their claim to the same study are amplifying one signal. The entire epistemological value of convergence rests on this, which is why the skill asks for it explicitly.

**One extension per cluster.** A single paragraph, in your words, on what the convergence means to you, recorded on the cluster as `cluster_extension`. If it is empty, the queue marks the cluster `gate_passed: false` and asks for it once. A general approval ("go ahead", "promote it") does not fill the field. If you promote anyway, the note records that it was promoted without an extension, so the record doesn't claim judgment where there was none.

Clusters that fail stay on the brief as weak signals. Two sources that address the same topic but propose different mechanisms are not converging — they're contrasting, and a tension with evidence on both sides can be worth recording on its own.

---

## The Promotion Process

Passing the convergence test tells you that promotion is warranted. The ritual in `open-brain-promote` runs in this order, for at most three clusters per session.

### Step 1: Scan for candidate clusters

A cluster is a group of two or more Literature Notes, from different independent sources, that appear to be making the same structural claim. The skill scans for them and orders them by convergence strength and then by how many of their notes have actually been retrieved. You may also bring one you noticed while reading. Either way, the starting point is a set of existing Literature Notes, not a blank page.

### Step 2: Run the convergence test

Apply the four parts and the two gates. If any of them fails, the notes are not ready for promotion. The right response is to continue reading, looking for sources that strengthen the cluster — or to conclude that what appeared to be alignment is a coincidence of topic.

### Step 3: Present the Promotion Brief, and stop

The brief lists every adjacent Literature Note the scan found (you decide which ones the synthesis really rests on), the test results, a draft of the note with its boundary conditions, and three questions:

1. Is this real synthesis, or just an intersection of authors saying the same thing?
2. What decision or output changes if this note doesn't exist?
3. What do you add that no source says?

The skill writes nothing until you answer. If the answer to the third question is "nothing yet", the note is not promoted; if you insist, it is written with `confidence: low, awaiting-extension`.

### Step 4: Write the Permanent Note

A Permanent Note has a fixed structure, ordered action first, justification second:

- **A title that is a falsifiable claim**, identical to the file name: not "thoughts on feedback" but "Feedback only improves performance when the recipient has the agency to act on it."
- **One paragraph of judgment**: three to six sentences that assert rather than report what sources said.
- **Operating rule**: what to do, starting with a verb, and it must change a real decision.
- **Test**: how to tell, at the moment of decision and in under a minute, whether the rule applies.
- **Boundary conditions**: mandatory. A concrete case where the claim stops working or inverts, not "it depends".
- **Why it matters**: the default belief the note replaces.
- **Evidence**: named sources with at least one verifiable data point, and how many independent sources converge.
- **Your extension**: mandatory. What you have lived or judged beyond the sources, which someone who read the same books could not have written.
- **Connections**: only those that pass a five-part quality bar (a real wikilink, a specific reason anchored in both notes, not a reason that would fit half the vault, no catch-all phrasing, and a decision, tension or tool gained). Zero connections is valid; filler is not.
- **`## Historial`** (history log): an append-only timeline that starts with the note's first event.

### Step 5: Link back and update the graph

The source Literature Notes get links back to the new note, the typed graph is updated, and the session ends with a report. The note is born `provisional` and `status: draft`. Endorsement is a separate, explicit step that comes later.

---

## The Endorsement State Machine

Every promoted note carries `endorsement_state`, with four legal values: `provisional`, `endorsed`, `unendorsed` and `rejected`. The enum is checked by `open-brain-health`.

```
provisional (+ status: draft) → endorsed   (you approve it explicitly)
provisional                   → rejected   (you reject it, with a reason)
```

`unendorsed` marks a note whose endorsement was withdrawn, or never given, after a review; it is set only by you, like `endorsed`.

There is no automatic progression. Neither time nor use advances a provisional note to endorsed; only your explicit approval does.

**Provisional**: The note passed the convergence test and was written up as a Permanent Note. It has evidence but no approval and, at birth, no use history. It should be retrieved and used, but with the awareness that it hasn't been tested in practice yet.

**Endorsed**: You explicitly approved the note — in a promote session, a working session, the confrontation step (careo) of an extraction, or a review of the queue. The approval is recorded as an event: `endorsed_at` with the date, `endorsed_via` with the route, and a first line in `## Historial`. The agent never fills these on its own, and a note with `endorsed_at` but no Historial line is flagged by health checks. Use is the best evidence for your approval, but it is tracked separately as the derived `maturity` (`seed` → `growing` → `evergreen`, computed from retrievals and the output ledger). A heavily used note is mature, not endorsed, until you say so.

**Rejected**: You used this note in practice and it failed. Or your thinking has evolved past the position it expresses, and you no longer hold it. Or new evidence contradicts the convergence it was built on. Rejection is not deletion. The note moves to `Permanent Notes/Rejected/` with its frontmatter intact and two additions, `rejected_at` and `rejected_reason`; links pointing to it are left broken on purpose.

The rejection reason is the most valuable field in the system. "Doesn't generalize past early-stage companies — the mechanism breaks when organizational complexity exceeds a threshold" tells you more than the original note did. It shows you where the principle's boundary conditions actually lie — not where you guessed they lay when you wrote it, but where you discovered them through use.

Practice feeds this machine without driving it. `promote --by-application [Skill]` walks the provisional notes behind a skill you have trained and asks for one decision per note (endorse, reject, keep provisional, reformulate, skip), and `promote --review-friction` does the same for notes that didn't fit when you applied them in a practice session.

---

## Promotion Quality Tests

Beyond the primary convergence test, three secondary tests assess the quality of a promotion decision.

**The stranger test**: Could someone unfamiliar with either source read your Permanent Note and recognize the underlying pattern in a completely different domain? If the note can only be understood by someone who's read the same books you read, it may still be too source-dependent.

**The prediction test**: Does the permanent note generate a testable prediction? "Small structural advantages compound faster than most people expect" implies that in any domain you examine, early advantages should be disproportionately durable. A principle that makes no predictions is difficult to use — and difficult to falsify, which means you'll never know whether it was right.

**The connection test**: How many existing notes in your vault does the new Permanent Note link to, extend, or partially contradict? A note that connects to nothing may be expressing a genuinely isolated insight — or it may be using vocabulary that doesn't map onto how you've indexed related concepts. Either way, a note without connections is harder to retrieve and harder to compound with other knowledge.

---

## Why Endorsement State Matters When You Use the Notes

When you pull knowledge as context — for writing, for reasoning, for AI-assisted production — the quality of the output depends on the quality of the context you inject. Not all notes contribute equally.

An endorsed note is a position you've tested in practice and confirmed. You used it under real conditions, it worked, and you explicitly approved it. When you inject it as context, you're injecting a stable, tested belief.

A provisional note is a position with good evidence but no use history. It might be equally valuable — or it might be a synthesis that looked compelling in the library and fails in practice. When you inject it as context, you're injecting a hypothesis.

Treating endorsed and provisional notes as equivalent is like treating a hypothesis and a replicated result as equivalent — they're both part of the knowledge system, but they're not the same kind of evidence.

Where Open Brain acts on this today: `open-brain-practice-log` lists endorsed notes first when it gathers the notes you'll draw on for a session, and marks provisional ones with a warning; visual retrieval of pattern notes has an endorsement tier. Text retrieval in `open-brain-retrieve` does not rank by endorsement — it orders results by `confidence`, then `maturity`, then `times_retrieved` — so when you pull notes as context for output, check their endorsement state yourself.

---

## What This Is Not

**Not accumulation**: The number of Permanent Notes in your vault is not a health metric. A vault with 30 endorsed notes that you've tested and trust is more valuable than a vault with 300 provisional notes that you've never used. Promotion is a quality gate, not a volume operation.

**Not a one-time process**: A note you promoted two years ago based on the best evidence available then may need to be revised if new evidence contradicts it, or if the context where it applies has changed. When extraction finds a source that weakens, qualifies or contradicts a permanent note, it queues that epistemic delta for review. Confidence downgrades, merges and added sources are appended to the note's `## Historial`; existing lines are never rewritten, so the record shows how your assessment changed. If the note no longer holds at all, rejection is the exit.

**Not text-only**: The same ritual has a visual pipeline. Convergent Design References can be promoted to Visual Pattern Notes (PAT) through a visual four-gate test, with their own `--visual-endorse` / `--visual-reject` commands and a `Design References/Rejected/` folder; PAT notes start `endorsement_status: pending`. The skill can also build its queue for a local browser view (UI mode) instead of running in chat.

**Not confidence theater**: The convergence test exists to prevent a specific failure mode — promoting notes because you feel confident, rather than because the evidence warrants confidence. The test is not a bureaucratic formality. It is the mechanism by which the feeling of confidence becomes grounded in evidence rather than enthusiasm.

---

## Measuring Impact

| Metric | Formula | Target |
|---|---|---|
| Promotion rate | Permanent Notes / Literature Notes | ≥ 10% green, 5–10% amber |
| Endorsement rate | Endorsed PNs / Total PNs | > 30% for vaults > 6 months old |
| Rejection ratio | Rejected PNs / Total promoted over 12 months | 5–15% is healthy; near-zero suggests insufficient testing |
| Extension rate | Promoted clusters with a real `cluster_extension` / Total promoted | Close to 100%; promotions without an extension are intersections of authors |
| Time to first endorsement | Avg. days from promotion to first endorsement | < 90 days; longer suggests notes aren't being used in output |

---

## Related

- [Why Two Sources Are Worth More Than Ten](convergence-detection.md)
- [The Endorsement Gap](endorsement-gap.md)
- [The Maturation Ladder: From Captured to Owned](maturation-ladder.md)
- [Premature Synthesis: Building on Thin Evidence](premature-synthesis.md)
- [The Literature Note Graveyard](literature-note-graveyard.md)
- [The Practice Loop: From Passive Notes to Active Skills](practice-loop.md)
