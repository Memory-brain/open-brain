# open-brain-ingest changelog

> Version history. Read it when you need to understand why a step is the way it is, or when preparing a new version — never to run the flow.

---

## Changelog

- **v1.9.0** — **Progressive-disclosure refactor.** The SKILL.md shrank by roughly 60 %. Moved to `references/`: the changelog, one file per note type (Inbox, Case, Design Reference), the support notes (Mentor/Search Term/Book and the photo protocol), the SurpriseFilter, project routing, `skill_sequence`, Notion migration and batch import, and the embedded Vault Spec. What stays inline is what runs on every invocation: the full triage tree, the source tier, the commands with their band and confidence tables, bidirectional wiring, File Naming and the "What Not To Do" list. No new instructions.
- **v1.8.3** — **Periodic reminder in batch ingestion (Step 0.7).** Every ~15 items of a long batch, re-read the triage criterion in one sentence instead of holding it only from the start of the batch. Based on the finding that criteria applied over a long context dilute towards the middle and end (Martin & Roger, 2026, arXiv:2605.12366). +1 paragraph.
- **v1.8.2** — Two changes, neither touches the flow. (1) **Boundary with `open-brain-extract` in the `description`**: "It archives and catalogs the source; it does NOT pull notes out of it." This mirrors the matching sentence in `open-brain-extract`, so a request like "I have this article open and don't want to lose it, process it as usual" is routed by the user's verb (*archive* vs *extract*) rather than by guesswork. (2) **The changelog moved out of the `description`**, which is loaded on every request and should contain routing information only.
- **v1.8.1** — Fixed an obsolete handoff name (now `open-brain-extract`).
- **v1.8** — `skill_sequence`: trace field on Inbox/Case/REF/PAT notes recording which skill(s) produced the note. Starts collecting the data needed to later measure which skill sequences produce notes that get used.
