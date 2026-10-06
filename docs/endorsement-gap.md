---
module: module-3-maturation
related_skills:
  - open-brain-promote
  - open-brain-practice-log
last_updated: 2026-10-06
---

# The Endorsement Gap

## The Problem

Convergence detection solves one problem: it gives you a signal for when to synthesize. But the note that results from that synthesis — the Permanent Note you wrote when three independent sources agreed on a principle — is still provisional. It passed an evidence test. It hasn't passed a use test.

The endorsement gap is the space between "I wrote this note because the evidence supported it" and "I used this note in real work and it held up." Most vaults have no mechanism for crossing that gap. Promoted notes sit in a folder labeled "Permanent Notes" where they're treated as equal to each other, regardless of whether any of them have ever been tested.

This creates a quality problem you can't see. Open a vault with 150 Permanent Notes and you'll find some that have been cited in published work, refined over multiple iterations, and proven durable across different contexts. You'll also find some that were written on a Sunday afternoon after reading an interesting book, never applied to anything, and never revisited. They look identical in the folder. They are not identical in value.

---

## Why Provisional Notes Need a Different Status

A note created through convergence detection represents what multiple sources agreed on. That's meaningful evidence. It's also not enough.

Evidence from reading is one data type. Evidence from practice is another. A principle can look robust in the literature and fail immediately in application — because the authors who established it were working in different conditions, writing for different audiences, or making assumptions they didn't state. You won't know this until you try to use the principle and discover where it breaks.

The provisional status exists to name this distinction explicitly: this note passed the convergence test, which means it's a serious candidate for a stable belief. It doesn't mean it's a confirmed stable belief. Confirmation requires use.

This matters most when you use your vault as a source of context for writing, reasoning, or AI-assisted production. A set of endorsed notes — notes you've used in practice, tested against reality, and explicitly approved — is a different kind of resource than a set of notes you wrote under the excitement of an insight. Both have value. They should not be weighted the same.

---

## Why It Happens

### There's no "save → test → endorse" workflow

Standard PKM practice is linear: capture, process, store. There's no phase after store that asks you to come back, use the note in real work, and then decide whether it survived the encounter. The workflow ends at storage. The test phase never gets built.

### The creation effort substitutes for validation

Writing a Permanent Note is hard. You synthesized multiple sources. You wrote it in your own voice. You articulated boundary conditions. That effort produces a feeling of completion — the note is done, the work is done. The idea that you now need to test it in practice feels like asking you to do the work twice. So it doesn't happen.

### There's no consequence for leaving notes provisional

If all Permanent Notes are treated as equally reliable, there's no pressure to resolve the provisional ones. They don't cost you anything by sitting there unendorsed. The vault looks healthy. You have Permanent Notes. The fact that you don't know which ones you trust is invisible until you need to rely on them under pressure.

---

## How to Detect It

**The trust test**: Think of five "important" Permanent Notes in your vault. If someone asked you to stake a claim on each of them in public writing, which ones would you use without hedging? The ones you'd hedge are unendorsed — you haven't tested them enough to trust them fully.

**The retrieval test**: Pull your vault notes as context for a piece of writing. How many times do you find yourself thinking "I wrote this, but I'm not sure it's right anymore"? Each of those moments is an endorsement gap: a provisional note that was never resolved.

**The age test**: Sort your Permanent Notes by creation date. Look at the oldest ones — the notes you wrote six or twelve months ago. Have you used them in output since then? Have you revisited them to confirm they still reflect your thinking? If not, they're aging in an unresolved state.

| Symptom | What it means |
|---|---|
| "I think I have a note on this, but I'm not sure it's right" | Unendorsed provisional notes in circulation |
| 150 Permanent Notes, no sense of which 30 are strongest | No endorsement tracking; all notes appear equivalent |
| Vault knowledge gets hedged when used ("according to my notes...") | You don't trust your own synthesis — endorsement gap is active |
| Retrieved notes often feel outdated or half-formed | Notes were promoted but never tested; provisional status never resolved |

---

## How to Fix It

The fix is to add an explicit third phase to the knowledge maturation workflow: not just capture and promote, but endorse.

### Provisional is the default state for newly promoted notes

Every note that passes the convergence test and gets written up as a Permanent Note starts provisional. This is not a failure state — it's the correct state for a note that has evidence but no use history. Provisional means: well-supported enough to hold, not yet tested enough to trust fully.

In Open Brain a new Permanent Note is born with `endorsement_state: provisional`, `status: draft` and an empty `endorsed_at`. The legal values of `endorsement_state` are `provisional`, `endorsed`, `unendorsed` and `rejected`, and `open-brain-health` checks the enum. `unendorsed` marks a note whose endorsement was withdrawn, or never given, after a review; it is set only by you, like `endorsed`. Notes still in `draft` are surfaced again at the start of the next session, because that is the only place approval can happen.

### Keep two signals apart: your approval and the note's use

The system separates two things that are easy to blur:

- **Endorsement is your explicit approval**, recorded as an event. It is set only when you approve the note in the conversation: `endorsed_at` gets the date, `endorsed_via` says where it happened (`promote`, a working session, the confrontation step (careo) of extraction, or the review queue), and the first line of the note's append-only `## Historial` (history log) block records it. The agent never writes `endorsed_at` on its own; an inferred approval date would be the system certifying your judgment for you. A note that sits in your vault for a year is not endorsed — it's just old.
- **Use is tracked separately as `maturity`**, a derived field nobody writes by hand. It is computed from `times_retrieved` and the output ledger: `seed` → `growing` (at least 2 retrievals or 1 output of any kind) → `evergreen` (at least 5 retrievals and 1 published output).

Use is the best evidence for your decision, and the test is still the one above: did you use it in real output, and did it hold up? But a heavily used note you never approved is mature, not endorsed, and an approved note nobody retrieves is endorsed, not mature. Keeping them apart is what lets you see both gaps.

### Rejection is a valid and valuable outcome

When you use a provisional note in practice and it fails — the principle doesn't generalize, the claim doesn't hold in your context, your thinking has evolved past it — the right response is to reject it, not delete it. A rejected note records that you held a position and changed your mind. That's historically useful: it shows you how your thinking evolved and guards against the same premature synthesis recurring.

Rejected notes move to a separate archive with one required field: the reason for rejection. In Open Brain that archive is `Permanent Notes/Rejected/`: the file keeps its frontmatter, gains `rejected_at` and `rejected_reason`, and inbound links are deliberately left broken as a signal. "The mechanism only holds when the feedback is immediate — too slow and the compounding effect disappears" is a useful rejection note. It's more informative than the original provisional note, because it contains the boundary condition the sources didn't give you.

### The practical resolution cycle

When you sit down to work on a domain:

1. Pull the provisional notes relevant to the domain
2. For each one, ask: have I used this? Did it hold?
3. If yes: endorse it
4. If you used it and it didn't hold: reject it with a reason
5. If you haven't used it yet: leave it provisional, but now you know it needs a test

`open-brain-promote` runs this cycle as sub-commands. `--by-application [Skill]` walks the provisional feeder notes of a skill you have been practising, one at a time, and asks for one decision each: Endorse, Reject, keep Provisional, reFormulate, or Skip. `--review-friction` works from the other end: when a note didn't fit during a practice session, `open-brain-practice-log` (and the course flow) append a friction block to the skill's `promote-feedback.md` with `Status: pending-review`, and promote presents each one for the same decision. `--endorse [[note]]` and `--reject [[note]]` handle single notes. Practice never changes a note's endorsement by itself; it only records the friction you decide on.

This doesn't require a dedicated review session. It can happen naturally as a byproduct of writing and reasoning: when you use a provisional note, you're implicitly running the test. The only missing step is recording the result.

---

## Related

- [Convergence-Based Promotion](convergence-promotion.md)
- [Why Two Sources Are Worth More Than Ten](convergence-detection.md)
- [The Maturation Ladder: From Captured to Owned](maturation-ladder.md)
- [The Collector's Fallacy: When Saving Feels Like Learning](collectors-fallacy.md)
