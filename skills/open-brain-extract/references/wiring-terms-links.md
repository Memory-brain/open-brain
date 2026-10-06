# Steps 6.5, 6.55 and 6.6 — Mentor/source wiring, term registry and link hygiene

> The two bidirectional-wiring invariants, the `resolve-terms` protocol with its buckets and the `free` rule, why declared aliases are not ground truth, and the four link defects lint doesn't see. Read it when closing each LN and whenever you set `search_terms`.

---

## Step 6.5: Bidirectional Wiring — Mentor and Source Both Know This LN Exists

Each LN created in Step 6 must satisfy two structural invariants:

**Invariant A — Double link in frontmatter (gate).** The LN MUST have both `source: [[<Dossier or Inbox source>]]` AND `mentor: [[<Author>]]`. If either is missing, STOP and resolve before continuing:
- No clear author? Use `[[Unknown]]` or the org name as proxy (`[[OpenAI]]`, `[[Stripe]]`).
- No clear source? Find or create the Dossier / Inbox parent before writing the LN.

**Invariant B — Auto-update the Mentor's `key_literature_notes`.** For each LN created, also:
1. Read `Mentors/<author>.md`.
2. Find the `key_literature_notes:` field. If it doesn't exist, add it.
3. Append `  - "[[<new LN title>]]"` to the list.
4. Save the Mentor file.

If the Mentor doesn't exist yet, create the Mentor stub now with `key_literature_notes` containing this LN, plus `key_works: [[<source>]]`. Set `photo_status: pending`.

**Mentor photo**: Never block extraction over a missing photo. If no photo: `photo_status: pending`, leave body without embed. If original but no nobg: save original in `Mentors/images/`, embed with `![[<Mentor Name>.<ext>]]`, mark `photo_status: nobg-missing`. See `open-brain-ingest` → `references/support-notes.md` § Mentor photo protocol for the full contract.

---

## Step 6.55: Term registry (before writing a `search_term`, ask whether it already exists)

`open-brain-enrich` refuses to write a term that has no page in `Search Terms/`. If this skill wrote frontmatter without that check, it would be the leak through which unregistered free terms enter the vault — and in practice it was: free-coined terms ended up coming almost entirely from Literature Notes. This step closes that leak.

**How.** With the list of candidate `search_terms` for the whole batch already written down, and before touching any frontmatter:

```bash
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" resolve-terms --json '{"terms": ["...", "..."], "domains": ["Artificial Intelligence"]}'
```

It returns each term in one bucket, and each bucket has a single action:

| Bucket | What it means | What you do |
|---|---|---|
| `exact` | has a page with that exact name | write it as is |
| `hub` | has a page, but it has children (more specific terms) | you may keep it, but it **does not count** toward L05: add one of its `children` or another specific term |
| `alias` | the same term in another form or another language (`carga cognitiva` → `Cognitive Load`, `Human-in-the-Loop` → `Human In The Loop`) | if it's a **form variant** (casing, hyphen, accent, plural), write the `canon` without thinking. If it's a **declared alias**, read it first: if it doesn't survive a read, treat it as `near` and keep the original term |
| `near` | very similar to an existing one | look at it: if it's the same concept, write the candidate; if not, treat it as `free` |
| `free` | doesn't exist under any name | see the rule below |

**The `free` rule — where the vocabulary is decided.** A free term is coined — creating its page in `Search Terms/` **in the same batch**, with `description` and `aliases` — only if **≥2 notes in the batch justify it**. If only one note carries it, it is not coined: it stays in the note's body. Body grep (weight 0.5 in retrieval scoring) already finds it, and a single-note term indexes nothing — single-note free terms are the vast majority of free terms and essentially never produce a retrieval hit.

**The failure this prevents.** Without it, one concept ends up under several labels (e.g. `cognitive load`, `carga cognitiva`, `sobrecarga cognitiva`), none of which finds the others. `resolve-terms` would have sent the last two to the first before writing them.

**Why a declared `alias` is not ground truth.** The `aliases` field on term pages was written by the same pipeline that coined the free terms. When audited, roughly a third of alias-resolved pairs did not survive a careful read. Real-world shapes: `Hierarchy → Visual Hierarchy` on a note about system hierarchies; `Workflows → Dynamic Workflows`, which is a specific feature of one product; `Heuristics → Cognitive Bias`, which erases the distinction between a shortcut that works and its systematic failure. The pattern is always the same: **a general term absorbed by a specific one that happened to be nearby in the text**. A form variant has no such risk; a declared alias does.

**What this step does NOT do**: it doesn't decide for you. `near` and `free` are settled by your judgment; the command only guarantees you don't coin blindly.

---

## Step 6.6: Link Hygiene (the four defects lint doesn't see)

These four show up in **every** ingestion and `ln_lint` detects none of them. Check them before lint, not after.

**1. Connector wikilinks without the LN prefix.** The most expensive defect: a single batch can produce dozens of broken links this way. When writing a connector to another LN, the link is `[[<PREFIX> - <Title>]]`. Verification: for each emitted wikilink, check that a file with that exact stem exists. If the target is an LN in the batch you're writing now, you know the prefix — use it.

**2. Domains in short form.** Never `[[AI]]`, `[[PKM]]`, `[[PM]]`. The real taxonomy lives in `Domains/` and uses long names: `[[Artificial Intelligence]]`, `[[Personal Knowledge Management]]`, `[[Product Management]]`. **If the domain you want doesn't exist in `Domains/`, don't invent it** — use the closest existing one and say so in the report. Creating a new Domain requires the user's approval.

**3. Casing of `search_terms`.** The file is `Human In The Loop.md`, not `Human in the Loop.md`; `Signal Vs Noise.md`, not `Signal vs Noise.md`. Obsidian resolves the link anyway because the filesystem may be case-insensitive, **and that's why this defect survives**: a `test -f` resolves it too and gives a false OK. The only valid check is an exact stem match in Python against `os.listdir` — never `test -f`, never `ls`.

**4. New Search Terms that already exist under another name.** The output invents `Institutional Memory` when you have `Organizational Memory`, or `Engineering Practices` when you have `Engineering — Practices`. This is no longer done by eye: **Step 6.55** does it with `resolve-terms`, which compares normalized, by declared alias and by fuzzy match. What remains here is the half the command can't resolve — a semantic synonym that doesn't look similar as a string (`Institutional Memory` / `Organizational Memory` don't reach the fuzzy threshold) is still yours. A duplicate stub splits the network in two and no check detects it.

**Placement of the source note** (not a link defect, but forgotten just as often): an arXiv paper goes to `Dossiers/` with `type: dossier` + `dossier_type: paper`, not to `Inbox/`. The coverage audit goes to `Resources/Vault Health/Extraction Audits/`.

---
