# Gotchas

> The known gotchas (G1–G16) with their symptom and fix. Read it when something looks off: feature skew, double-reading the PDF, a contaminated callout, a generic or pointer-only Careo, an invented delta, a handoff with no receiver.

---

## Gotchas

G1 — **Feature skew: only conceptual/factual** → The agent extracts facts and frameworks without looking for anti-patterns, templates, or trade-offs. Happens especially with dense sources where conceptual information is abundant. → After the first pass, compare the features detected in Step 3.5 with the features captured in the notes. If the source has diagnosis/application/decision signals and zero notes capture them, go back to the source.

G2 — **Generic search terms** → The agent puts the main concept and stops. An LN about "segmentation by Jobs To Be Done" ships with only `[[Jobs To Be Done]]`. → Apply the "what would the user type in 6 months" rule: synonyms, adjacent domains, the problem it solves. Minimum 4, target 6.

G3 — **Double-reading the PDF** → markitdown generates the cache in Extracted Text/, but the agent re-reads the binary "to verify". Wasted tokens and risk of inconsistency. → The `.md` cache is authoritative. If markitdown failed, the fallback is page images, not a double read.

G4 — **Connector callout with extended analysis** → The `[!claude]` callout turns into a paragraph of interpretation instead of just wikilinks + a one-line reason. It contaminates Voice 1 (author). → Claude only writes connectors: `Related to [[X]] because [one line]`. No paragraphs. If there's no connection: "No connection identified yet."

G5 — **Pre-filled Your extension** → The agent "helps" by filling Your extension with suggestions. It breaks the elaborative-encoding gate — the user doesn't think if it's already written. → ALWAYS empty on creation. The blank is intentional.

G6 — **Mentor stub without key_literature_notes** → The Mentor is created but its LN list isn't updated. The LNs are orphaned from the mentor. → Step 6.5 Invariant B is mandatory: read the Mentor, append the LN, save.

G7 — **Convergence reported as an action** → The agent detects convergence and chains into open-brain-promote automatically. → Convergence is a REPORT. Present it in Step 10 and stop. The user decides whether to promote.

G8 — **Bundle as a blocker** → The agent can't generate the evidence bundle (PyMuPDF missing, corrupt PDF) and stops. → The bundle is ADDITIVE, never blocking. If it fails, continue without it. Note "Evidence bundle: skipped" in the report.

G9 — **Lint skipped in a hurry** → The agent generates 15 LNs and doesn't run lint "because they're fine". → Step 6.7 is MANDATORY. Always run it after writing the batch. BLOCK violations that slip into the vault corrupt everything downstream (promote, synthesize, retrieve).

G10 — **Bundle figures unreferenced** → The bundle extracts 8 figures but no LN uses them. → After lint, cross-check: if `bundle.figure_count >= 3` and there are zero Visual References in the LNs, go back to the source and consider whether some figure deserves its own LN or a reference in Evidence.

G11 — **Claude answers the Careo** → The agent "helps" by answering P1–P3, proposing draft answers, or filling the fleeting note with its own analysis. It's G5 at scale: pre-filling the thinking cancels the only part of the pipeline where the user thinks. → Claude only formulates and loads the questions. If the user isn't there: queue in `Resources/Careo/Pendiente — {slug}.md`, never answer for them.

G12 — **Generic Careo** → The questions come out without names ("what does this change in your mental model?", "what can you apply?"). They get answered on autopilot by the third extraction and produce no judgment. → Each question cites concrete LNs/PNs/practices/projects with wikilinks. If there's no real tension or the source doesn't support P2, say so and move on — never fill the slot.

G13 — **The user's answers polished** → The agent rephrases, corrects or summarizes the answers when transcribing them into the fleeting note or into `Your extension`. It kills the voice and contaminates the three-voice contract. → Always verbatim: the user's syntax, verbal tics included. Claude's additions live only in the `[!claude] Context` callout, never inside the user's text.

G14 — **Invented Epistemic Delta** → The agent fills the delta with a vaguely related claim so as not to leave the slot empty. It's G5 at the scale of the close: forcing a conclusion where there is none. → `no_delta_identified` is a legitimate, expected answer. If the source adds material without updating a live claim, say so. The types {weakens, qualifies, contradicts} require citing the concrete note with a wikilink — without a concrete wikilink, it's no_delta.

G15 — **Careo by pointers** → The questions are full of proper names that say nothing: LN prefixes, note codes, abbreviated titles, section references. It's the twin of G12 and more deceptive, because it *looks* concrete: it cites sources, has wikilinks, and is still unreadable for whoever reads it. → Mandatory alias (`[[name|claim]]`, with the claim read from the `description` field) plus the label-resolution gate before showing the Careo. Note: while nearly every filename carries a prefix, an instruction that says "don't show it" without giving an alternative format amounts to asking you not to cite at all.

G16 — **Handoff with no receiver** → The closing offers to queue into a queue nobody empties, and the user's answer is always the same. A step that can only end one way isn't a decision, it's a formality — and formalities erode compliance with the steps that do matter. → Thermometer before handoff: above 20 open entries, the closing reports the backlog instead of offering to add.

---
