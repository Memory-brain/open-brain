---
module: module-7-output
related_skills:
  - open-brain-escribir
  - open-brain-retrieve
last_updated: 2026-10-06
---

# Writing Without Evidence: Opinions Disconnected from Your Own Knowledge

## The Problem

You've spent three months building a vault around sleep science. You've read six books, taken detailed notes, synthesized principles, connected ideas across domains. Now you sit down to write a piece on the topic. An hour later, you have a 600-word draft.

You read it back. It's fine. It's coherent. But a competent person who had never opened your vault could have written the same thing. The specific principles you've worked out, the counterintuitive connections you've noticed, the cases that refined or contradicted your initial understanding — none of that is in the draft. It's a competent essay written from general impressions of the topic.

This is not because your vault is bad. It's because your writing process didn't include a step where the vault contributed. You wrote from memory — from the vague impressions left by your reading — rather than from the specific, tested claims you actually built. The vault exists, the knowledge is there, but the pipeline between vault and draft has a gap.

This failure is common and invisible. It feels like using your knowledge, because you're writing about something you studied. But general impressions are not knowledge — they're the starting point that knowledge management is supposed to improve upon. If your writing after six months of PKM is indistinguishable from your writing before, the system isn't working.

---

## Why It Happens

### The retrieval step is skipped

A typical writing session goes: open document, think about the topic, write what comes to mind, clean it up. The vault is never opened. The notes are never consulted. The writing comes entirely from working memory, which stores vague impressions and the most recent things you read — not the carefully synthesized principles you built over months.

This isn't laziness. It's the default behavior when there's no explicit step in the workflow that says "before writing, retrieve." Writing and note-taking feel like different activities that happen in different sessions. Without a ritual that connects them, retrieval gets skipped.

### Note-to-writing gap

Notes live in one mental context (the vault, Obsidian, the knowledge management tool) and writing lives in another (the blank document, the writing application). These contexts don't naturally communicate. A note about the conditions under which discovery research helps versus hurts exists in the vault — but unless you've specifically designed a workflow that surfaces it during writing sessions, it stays there.

This gap is structural, not attentional. You're not failing to remember that the note exists — you're working in a context where it wouldn't occur to you to check. The vault is for "learning sessions," not for "writing sessions." This mental partition is the problem.

### No provenance tracking

When you make a claim in writing, you typically don't mark where it comes from. "Most teams do discovery too early" goes in the draft without a tag indicating whether it comes from a specific tested principle in your vault, a book you half-remember, or something you made up during the writing session.

Without provenance tracking, you can't audit your own claims. You can't distinguish the things you've actually worked out from the things you're asserting from vague impression. The draft looks equally confident throughout, even though some claims are vault-grounded and others aren't.

---

## How to Detect It

**The source trace test:** Pick a piece you recently wrote on something you have vault notes about. For each specific claim you made, try to find the note it came from. Not a note that's related — the specific note that contains the evidence or reasoning behind that exact claim.

Run this audit:

| Claim in draft | Vault note that supports it | Source quality |
|---|---|---|
| [Your claim 1] | Found / Not found | Tested principle / Casual note / None |
| [Your claim 2] | Found / Not found | Tested principle / Casual note / None |
| [Your claim 3] | Found / Not found | Tested principle / Casual note / None |

If most cells in the "vault note" column are empty, the draft was written without evidence from your own knowledge base.

**The uniqueness test:** Read the piece again and ask: could a smart person who hadn't read what you've read have written this? If yes, your specific knowledge didn't contribute. The piece is generic — competent, perhaps, but not grounded in your particular evidence and reasoning.

**The claim specificity test:** How many specific, non-obvious claims does the piece contain — claims that would surprise a casual reader of the topic and that you can directly trace to a specific piece of evidence? If the answer is "zero or one," you wrote from impressions.

---

## How to Fix It

**Retrieval at two scales**

The vault should contribute at two different moments, and the amount of retrieval differs at each.

*While you are still writing fragments*, keep it to one note. After you save a piece of your own text, look for the single note in your vault that clearly contradicts it — not five that agree. That one note sharpens your position without burying your own words under sources. `open-brain-escribir` works this way: it saves what you wrote verbatim, then grounds it against at most one contradicting note, never before the text exists.

*Once a claim has emerged and you are assembling a piece*, retrieve against the claim itself, not the topic. For example: if you are about to argue "sleep after learning matters more for memory than sleep before it," search for notes about:
- Timing of sleep relative to learning
- Cases where sleep loss hurt recall vs. made no difference
- Principles about memory consolidation
- Counterarguments you've encountered

Keep the candidate set small (`open-brain-retrieve` pre-filters by frontmatter and reads the full body of only the top handful, up to about eight), then hop along graph links from the strongest hits — favoring contradiction and cross-domain links where your vault types them — so the set isn't made only of notes that already agree with each other. Read them with the claim in mind. Mark which ones support, which contradict, and which add nuance. This takes 10-15 minutes and changes what you write.

**Vault citation during writing**

As you make claims in your draft, keep a link to the vault note they come from — a wikilink or a brief inline marker such as "(← PN: sleep-timing-principle)". It doesn't need to be publication-ready; it's for your own audit.

This practice forces precision. When you can't find a vault source for a claim, you're explicitly signaling to yourself that this claim is asserted, not evidenced. You can then decide: is this claim worth defending? Should I find evidence for it? Or should I soften the language to match its actual epistemic status?

It also makes provenance measurable without self-report. If deliverables keep their links to the notes they used, a script can later scan them and count which ones cite a real vault note. That is worth doing because the gap is usually larger than it feels.

**The evidence audit**

After finishing a draft, review it once specifically for evidence. For each substantive claim:

1. Can you trace it to a specific note or case in your vault?
2. If not, is it a reasonable inference from traced claims, or is it asserted from impression?
3. For all asserted claims: either find a source, soften the language, or cut the claim.

This audit is not about footnoting everything. It's about knowing which parts of your thinking are grounded and which are floating.

---

## Related

- [The Blank Page Problem with a Full Vault](blank-page-full-vault.md) — the upstream failure: not knowing what to say even with a full vault
- [Single-Perspective Blindness](single-perspective-blindness.md) — the next failure after a draft exists: evaluating it from only one perspective
- [Knowledge-Grounded Output](knowledge-grounded-output.md) — the systematic approach that prevents this failure by design
