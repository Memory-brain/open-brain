# Key Principles

> The skill's underlying principles: one pass, feature coverage as a quality signal, the epistemic close, search terms as the retrieval contract, convergence as a report, evidence before judgment, lint as the last gate, the three voices and the Careo as the producer of judgment. Read it when two steps seem to clash or you doubt a criterion.

---

## Key Principles

**One pass, not two.** There is no manifest-then-write handoff. Reason about the extraction internally and write notes directly.

**Feature coverage is the quality signal.** A source that produces only `conceptual` and `factual` notes has been skimmed, not extracted. Sources with detected practical features (application, decision, diagnosis, code-artifact) that appear in zero notes are failed extractions.

**An extraction closes by updating the epistemic state, not just by creating notes.** Beyond LNs, feature coverage and convergences, the close must say which vault claim is now different: reinforced, weakened, qualified, better connected or more measurable. If no claim is affected, say so explicitly with `no_delta_identified` — silence is not valid, and forcing a delta where there is none isn't either.

**Search terms are the single most important field.** Notes with weak search terms are invisible. Treat them as the retrieval contract with the user's future self.

**Convergence is a report, not an action.** Detect convergences; the user decides whether to promote. Never chain into open-brain-promote without explicit consent.

**Evidence before judgment.** When a PDF source is available, run the evidence bundle first. The LLM writes better notes when it knows the figure inventory, TOC structure, and page quality upfront — not when it's guessing.

**Lint is the last gate before the vault.** Every LN batch runs through `ln_lint.py` before being written. BLOCK violations are non-negotiable. This catches the systematic mechanical errors the LLM makes (invalid feature values, missing wikilinks, voice leaks) that compound across hundreds of notes.

**Three voices, never blurred.** The body is the author's voice. Claude's voice lives only in `[!claude]` connector callouts. The user's voice lives in `Your extension`, which is left empty for them to fill.

**The Careo produces judgment; extraction produces notes.** Claude prepares the stimulus (the concrete tension, the candidates to steal); the user produces the verdict. A Careo answered by Claude is a failed extraction even if the LNs are perfect. And a generic Careo ("what did you think?") is a Careo that didn't happen.

---
