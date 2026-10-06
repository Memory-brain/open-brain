# Route card: extract

> **This is a routing card, not the skill.** The full, current rules live in the `open-brain-extract` skill. Once you have routed here, load `open-brain-extract` and follow its `SKILL.md` (and the references it names) end to end. Do not execute from this card.

## Route here when

- Extract notes / create Literature Notes / process this PDF, article, book, repo or transcript.

## What the skill does

Turns one source into atomic, linked Literature Notes. It starts with an admission gate that scores the source before extracting anything; a source scoring 4/12 or less is logged as rejected and extraction stops. Then: feature detection, free extraction, multi-label post-tagging, visual embedding, lint, mentor-to-LN wiring, an epistemic delta, and a short three-question review with you (clash / steal / bet). PDFs are pre-processed to text first.

## Route elsewhere when

- Archiving a source without extracting from it: route to **ingest**.
- Permanent Notes or Source Outlines: route to **promote** or **index**.

## Usual next step

- **index**, if the book is rated TOP (or INTERESTING).
- **promote**, if convergences with existing notes were detected.
- **escribir**, if the review surfaced something worth writing about.
- **autolink** runs silently afterwards.
