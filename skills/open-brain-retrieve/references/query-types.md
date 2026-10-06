# Query Types 1–7, manuscript precedence and source prefixes

> Full text of Manuscripts Take Precedence, Maturity as Signal, Navigating by Source and the seven text Query Types. `SKILL.md` carries the canonical flow (QT1); the full procedure for each type is here.

---

## Manuscripts Take Precedence on Topic Match

Regardless of intent, always check Active Manuscripts first. Read `Manuscripts/Active Manuscripts.md`. If any active manuscript overlaps with the query topic:
1. Surface the manuscript at the top: *"This touches an active manuscript. Here is the related material."*
2. Then apply the intent-based priority for the rest.
3. At the end, ask (Phase 12 ritual): *"Does any of these PNs feed a post idea in Ideas/?"*

---

## Maturity as Signal, Not Filter

Never hide an LN because a PN exists on the same topic. Show both, labeled with maturity, retrieval count, and output count. Example (**illustrative — placeholder titles; check `Permanent Notes/` for the real wikilink before citing it**):

```
PN evergreen: [[<a real PN title from your vault>]] (retrieved: 7, outputs: 2)
  ↳ fed by 3 LN: [[LN 1]], [[LN 2]], [[LN 3]]
  ↳ 2 related LN NOT yet incorporated: [[LN 4]], [[LN 5]]
```

"Not yet incorporated" LNs are candidates for updating the PN. Do not hide them.

---

## Navigating by Source (the prefix system)

1. Read `Resources/Source Index.md` — find the row for the source.
2. Check `vault_coverage`.
3. Get the `ln_prefix`.
4. Run: `ls "Literature Notes/" | grep "^PREFIX"` to get all notes instantly.

---

## Query Type 1: "What Do I Know About [X]?"

1. Classify intent. Declare it.
2. Check Active Manuscripts for topic overlap. Surface any match first.
3. Find `Search Terms/[X].md`. If it exists, read it — get definition, aliases, and related terms.
4. Gather all notes where `search_terms` includes `[[X]]` or body contains `[[X]]`. Also search for aliases.
5. **Frontmatter pre-filter (L0)** — before reading any full note body, read ONLY the frontmatter (YAML block) of each candidate (~50 tokens per note). Extract `description` and `search_terms`. Rank candidates by relevance of `description` text to the query (semantic match, not just keyword). Read the full body (L2) only of the **top K** candidates (K = 4–6 for typical queries; up to 8 for Critical/Exploratory with broad scope). Log: `**Candidates pre-filtered**: N → K (+ H hop, + E motor)` in the Retrieval Log entry. This step exists because loading the full body of every grep match costs ~10K tokens per query, while frontmatter alone (~50 tokens) is enough to rank and discard ~60 % of candidates. **Widen the pool before ranking it**: Step 4.7 adds the deterministic engine's 20 candidates to the grep+hop pool, and the L0 ranking runs over the union — the engine buys width, this step keeps the cost down.
6. Apply intent-based ordering on the top-K notes whose full body was loaded. Within each tier, sort by: `confidence` (high → medium → low), then `maturity` (evergreen → growing → seed), then `times_retrieved` descending (invert for Serendipity).
7. Show maturity as signal, not filter.
8. Synthesize a response — don't just list notes. Tell the user what they know and how confident the vault is. Cite specific notes using `[[wikilinks]]`.
9. Increment `times_retrieved` on every note (PN or LN) used substantively. Do NOT increment in Serendipity mode.
10. Surface gaps: if coverage is weak in certain layers, mention it.
11. Manuscript hook: ask whether any used PN feeds an active manuscript.

---

## Query Type 2: "Find Connections Between [A] and [B]"

1. Gather all notes tagged with concept A and all notes tagged with concept B.
2. Find **direct connections**: notes that reference both A and B.
3. Find **bridge notes**: notes in A that link to notes in B.
4. Find **shared dimensions**: notes in A and B that share the same `layer`, `domain`, or `search_terms`.
5. Synthesize the connection and explain WHY these ideas relate.

**Serendipity Mode**: when the user is working in a domain and doesn't explicitly ask for connections, proactively scan for PNs in the current domain that link to other domains, notes with 2+ domains in frontmatter, and pairs in different domains sharing 2+ search terms. Surface only the most non-obvious connections.

---

## Query Type 3: Knowledge Provenance — "Where Did This Idea Come From?"

1. Start at the Permanent Note.
2. Read its `sources` field → the Literature Notes it was synthesized from.
3. For each Literature Note, read its `source` field → the Inbox note or Book.
4. For the Inbox/Book, check `Resources/Source Index.md` for full source context.
5. Read `mentor` field → original author.
6. If the PN feeds any Active Manuscript, include it in the chain.

Present the chain: **Original Source → Inbox/Book → Literature Notes → Permanent Note → (Active Manuscript, if any)**

---

## Query Type 4: Domain Exploration — "Show Me Domain [X]"

1. Read `Domains/[X].md`.
2. Present: description and status, competency map, layer coverage (count per layer), sources processed (cross-reference with Source Index), progression path, cross-domain connections, Active Manuscripts tagged with this domain.
3. Highlight strongest areas and gaps.
4. Suggest next actions.

---

## Query Type 5: "What's Been Processed From [Book]?"

1. Read `Resources/Source Index.md` → find source row → get `ln_prefix` and `vault_coverage`.
2. Run: `ls "Literature Notes/" | grep "^PREFIX"`.
3. Group by layer.
4. Report coverage status; suggest missing layers if `vault_coverage` is not `complete`.

Never use the Inbox note's `processed: true` field to determine this.

---

## Query Type 6: Stale Knowledge — "What Needs Review?"

Find Permanent Notes where `last_validated` is older than 6 months AND `confidence` is `medium` or `low`. Sort by `times_retrieved` descending.

**Caveat**: this 6-month threshold assumes a vault old enough to have notes that age. In a young vault this query will structurally return 0 results, and 0 then means "too young to tell," not "nothing is stale." Don't report 0 as a clean bill of health without saying so.

Also surface:
- PN with `times_retrieved ≥ 3` and `external_outputs = 0` → Forced Promotion reminder: *"Are you using it in a post idea (Ideas/), or shall we demote it to an LN?"*
- PN with `times_retrieved ≥ 5` and `external_outputs = 0` → the reminder repeats each time it is cited; citing is not blocked (see `counters.md`).
- PN > 90 days without retrieval: surface it as a candidate via `python3 "$OPEN_BRAIN_ENGINES/health-engine/health_check.py" run --check 27` (Dormancy Candidates, age × importance) and let the user decide what to do with it. Never propose a folder move or a tag — there is no vault convention for either.

---

## Query Type 7: Serendipity (first-class mode)

Invert normal heuristics:
1. Find LNs with low `times_retrieved` that share search_terms with recently used PNs.
2. Find PNs with `times_retrieved = 0` connected to active domains.
3. Find pairs of notes in different domains sharing 2+ search_terms.
4. Surface only the most interesting connections — non-obvious links.
5. Never increment `times_retrieved` — serendipity retrieval is exploratory. (Myelination traversals are still recorded; see `myelination.md`.)
6. Ask at the end: *"Does any of these connections open a new line for you? If so, I can propose a synthesis PN."*

---
