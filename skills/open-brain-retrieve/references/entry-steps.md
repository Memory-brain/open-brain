# Entry steps 0 → 0.9, with their evidence

> Full text of Step 0 (Hot Cache, with the self-healing template), 0.3 (Session Log), 0.5 (Retrieval Log), 0.7 (probe discipline), 0.8 (expansion) and 0.9 (anchoring) — including the measurement tables that justify 0.8 and 0.9. `SKILL.md` keeps the mechanics of each step; here are the why, the Hot Cache template and the numbers. Measurements were taken on the development vault (47 log queries with gold labels); treat them as design evidence, not as facts about your vault.

---

## Step 0: Read Hot Cache (mandatory)

Before classifying query intent, read `Resources/Hot Cache.md`.

1. **Last session focus**: if the query relates to the same domain/source recently worked on, prioritize notes from that context.
2. **Recent changes**: notes created/updated in last 72h are more likely to match — surface them early.
3. **Active threads**: if a thread names a note or pending question that the retrieval matches, flag it as "resolves thread X in Hot Cache."
4. **`[!stale]` callouts**: when citing a PN, check if it carries `[!stale]` — warn the user before they act on stale knowledge.
5. **Pinned reminders**: apply retrieval loop rules (`times_retrieved`, `external_outputs`, Forced Promotion) automatically.
6. **The session's random note**: `Resources/Hot Cache - Active Context.md` carries a section "Random note for this session (manufactured serendipity)" — a PN sampled with weight 1/(1+times_retrieved) over ALL active PNs, with no confidence filter (unlike sleeping giants, which only look at confidence==high). Mention that note ONCE at the start of the session, briefly, without forcing it into the answer if it does not fit the query — it is a serendipity opportunity (a sparse index of entry points produces more discovery than an exhaustive one), not an obligation to use it.

**Self-healing fallback**: if `Resources/Hot Cache.md` does not exist, create it with:

```markdown
---
type: meta
title: Hot Cache
purpose: "Session-start operative state — last focus, active threads, pinned reminders."
created: YYYY-MM-DD
---

# Hot Cache

## Last session focus
(none yet)

## Active threads
(none yet)

## Pinned reminders
(none yet)
```

Then continue. Do not halt.

**Hot Cache is a hint, not a boundary.** Always run at least one probe *outside* what the Hot Cache surfaces. The Hot Cache ranks by recency and retrieval count, which is availability — and availability is the heuristic that produces systematic errors (Tversky & Kahneman). In a typical vault most PNs have never been retrieved, so a retrieval that only walks the Hot Cache reinforces a Matthew effect instead of answering the question. If the best note for the query is one the user has never used, the Hot Cache is exactly where it will not be.

Writing to Hot Cache: retrieve is READ-ONLY by default. Only append to Hot Cache "Active threads" when the query is in Critical or Expressive mode AND produces output that changes the user's decision state.

---

## Step 0.3: Read Session Log (conditional)

If the query is clearly scoped to a specific domain, read the last 3 entries of `Resources/Session Log.md` that mention that domain before classifying intent. Skip if the query is cross-domain or domain-agnostic, or if the file doesn't exist yet. (There is one unified Session Log; there are no per-domain session log files.)

---

## Step 0.5: Read Retrieval Log (conditional)

If `Resources/Retrieval Log.md` exists, scan its last 10 entries. Four checks:

1. **Reformulation detection**: is there a same-day query that failed or returned partial? If yes, mark this as a reformulation in the log entry.
2. **Repeated failure guard**: if the same query appeared ≥2 times in the last 14 days with `outcome: failure`, tell the user explicitly: *"This query has already failed twice in the last 14 days. It's probably a content gap, not an indexing gap. Do you want to open an Inbox note, or shall we try another reformulation?"*
3. **Recent success patterns**: if a similar query recently succeeded with specific notes, treat those as ranking boosts (not forced matches).
4. **Missing-note recurrence**: Level B (Step 10) writes `missing:` when the user names a note that should have surfaced, but no other skill or engine reads that field afterwards. Close the loop here: if the same note name appears in `missing:` two or more times in these 10 entries, say so before answering: *"You've already flagged twice that [[X]] is missing from retrieval. Do its search_terms need review, or is it not indexed at all?"*

If the log does not exist (fresh system), skip silently.

---

## Step 0.7: Probe discipline (do this before answering)

Retrieval quality is set by how you search, not by how you rank afterwards. Two A/B evals found the same thing twice: the run that searched more found the caution notes, and the run that stopped early because its first hits looked good missed them — 15 probes vs 9, with the confident-early run scoring worse. So treat the first good hit as a lead, not as an answer.

**Minimum probes.** Before you answer, run several varied greps: the concept in every language your vault uses, at least one synonym, and one negative/failure phrasing of the same idea. In a multilingual vault the same idea is often filed in the other language. Stop when new probes stop returning new notes — not when the first ones return something usable.

**Intent → vocabulary.** Grep `description:` fields with the wording that matches what the user is actually asking for. This beats filtering by the `features` tag: measured, the prose of a warning is the dominant signal and the tag added nothing for a strong reader.

| If the query wants… | Grep for |
|---|---|
| cautions, what breaks, what to avoid | `fail`, `anti-pattern`, `destroys`, `doesn't work`, `erodes`, `trap`, `mistake` |
| a trade-off or a choice | `vs`, `trade-off`, `when`, `criterion`, `beats`, `instead of` |
| how to do something | `how`, `method`, `step`, `protocol`, `technique`, `checklist` |
| evidence or numbers | `%`, `study`, `experiment`, `data`, `measured` |

Add the equivalents in every other language your notes are written in.

**Do not filter or rank by `features`.** Three separate tests said the same: for a capable reader the tag subtracts precision (44/48 without it, 38/48 with it), and its strict precision was ~43 %. The field stays in the frontmatter for cheap batch consumers; interactive retrieval ignores it.

---

## Step 0.8: Query expansion (mandatory; asked, never self-generated)

**Before running any search, ask the user for the vault's vocabulary for this task — do not write it yourself and proceed.** Draft your own guess first: domain vocabulary you already know is in the vault; the `search_terms` and `description` of anything you have already seen this session (Hot Cache, Session Log); the literal claim of any Permanent Note you can already name. Between 8 and 15 terms, nouns and claim-phrases, no verbs of instruction, no boilerplate (`retrieve`, `search`, `notes`, `vault` — the engine strips those anyway). Then show the draft and ask them to confirm or correct it. **This is a gate, not a courtesy** — wait for the answer before running any search, unlike Step 0.9 below, which shows and continues.

```
I'm going to search with: judgment capture, tacit knowledge, decision log, provenance,
desirable friction, note-making, learning artifact, expert blind spot, self-written memory.
Are these the terms you would use, or do you want to change/add any?
```

Record whatever comes back in the `Expansión` field of the Retrieval Log entry, then pass it to every search you run. Tag it `(confirmed as is)` if the user accepts the draft unchanged, `(user's terms)` if they correct or replace it.

**Fallback for non-interactive sessions** (scheduled task, nobody to answer in the turn): use your own draft without waiting, and tag it `(unconfirmed — non-interactive session)` in the `Expansión` field. It is not the normal path — it is what keeps the step from blocking a run nobody will answer.

**Scope**: this question applies only to the explicit invocation of `open-brain-retrieve` (any Query Type). An implicit, always-on retrieve configured in your agent instructions stays silent by design and keeps writing its own 2–3-concept expansion without asking — this step does not touch it.

**Epistemic note**: the measurement below compares expansion vs no expansion, never who writes it. Asking the user instead of self-generating is not backed by that measurement, but it does not contradict it either — it is a design choice made because the system otherwise never asked. Contrast with the "do not ask" of Step 0.9, which does have a specific measurement against asking — the two steps ask (or don't) for different reasons and should not be cited as the same finding.

The gap this closes is the core problem of a note vault. Queries arrive as tasks in natural language — *"improve this screen, the X at the bottom looks odd"* — and notes are abstract claims — *"Button design combines affordance, hierarchy, size and copy"*. The lexical overlap between the two is close to zero: pure BM25 got 4.4 % recall@10, and not because the vault is bad. The expansion **is** the semantic step. Everything else in this skill ranks candidates; this produces them.

Measured on the 47 gold-labelled log queries, same engine, expansion on and off:

| | no expansion | with expansion |
|---|---|---|
| recall@10 | 19.2 % | **32.2 %** |
| recall@50 | 37.9 % | **54.8 %** |
| MRR | 0.356 | **0.485** |
| queries that recover no gold note | 18 | **6** |

Paired bootstrap on recall@50: **+16.9 pp, 95 % CI [+7.8, +26.5]**. It is the only measured intervention in the engine whose interval does not cross zero. (Measured with the expansion written by the agent — the lift comes from expanding at all, and nothing suggests it depends on who writes it.)

**If the user does not answer or corrects nothing**, use your own draft as written — that is the confirmed case, not a failure. **If the engine still runs without any expansion** (non-interactive session without the fallback applied, or an error), it builds one by pseudo-relevance feedback (`retrieve` without `--expand`): first pass, discriminative terms from the top 10 Permanent Notes, re-query. It is worth **+9.0 pp** with 95 % CI `[−2.0, +19.9]` — positive but not significant, and clearly below a real expansion. It is a floor for when there is none, never a reason to skip step 0.8.

**Tried and discarded**: using the vault's `Search Terms` pages as the expansion vocabulary leaves recall **below not expanding at all** (32.3 % vs 37.9 %). That layer works as a bridge inside the `bridge` channel, not as query vocabulary.

## Step 0.9: Show the anchor before spending it (mandatory)

After the expansion of Step 0.8 and the first retrieval pass, and **before reading any full note body**, print the 3–5 candidates you are about to build on — one line each, title plus the hook that surfaced it. Then continue without waiting. If the user corrects you, the correction becomes the `Expansión` and the retrieval re-runs.

```
Anchoring on:
  1. [[<full title of note 1>]]   (bm25, lsa)
  2. [[<full title of note 2>]]   (hop)
  3. [[<full title of note 3>]]   (meta)
If you're heading somewhere else, tell me where and I'll redo it.
```

**Why it exists.** Measured over the 47 gold-labelled queries: **one concrete anchor from the user** — a concept, a description, a note — takes recall@50 from 54.8 % to **77.0 %** and cuts the queries that recover nothing from 7 to 3. Paired delta **+13.8 pp, 95 % CI [+3.6, +24.4]**. It is the largest measured lever in the whole retrieval path, larger than the expansion itself, and it stacks on top of it.

| | recall@50 | failing queries |
|---|---|---|
| expansion alone (step 0.8) | 54.8 % | 7 |
| **+ 1 concept from the user** | **77.0 %** | 3 |
| + 1 named note (oracle) | 82.3 % | 1 |
| + all gold notes (maximum) | 91.3 % | 2 |

**Why it is shown and not asked.** Three properties of that measurement decide the shape:

1. **It saturates at one.** One note gives 82.3 %; all of them give 91.3 %. The first piece of grounding carries almost everything, so one exchange is enough — and a dialogue buys nothing.
2. **It does not depend on being right.** A *random* gold note gives 78.3 %; its `search_terms` 77.0 %; its `description` 76.5 %. Any real foothold works, so the candidates you show do not need to be the right ones to be useful.
3. **There is no trigger — tested and falsified.** No observable signal in the first pass predicts where the anchor helps: folder dispersion of the top-10, top-1/top-5 concentration, how many channels vote for the first hit, the intent of the query, its length. The best rule fires on 38 % of queries and captures 40 % of the available gain — **the same as firing at random** (40 % random capture 38 %). There is no cheap way to know when to ask.

Given (3), a *conditional* question is not implementable and an *unconditional* question would spend one of the user's turns on all queries to help a minority. Showing carries the same information at the cost of five lines, and costs nothing when the anchor is already right — which, measured on the first pass with expansion, is **hit@5 66 %, hit@10 74 %**: two out of three times the correct region is already on screen.

**Do not wait for an answer.** This is not a gate. Print, continue, and use the correction only if it arrives. A step that blocks on the user turns a 1-second retrieval into a round-trip, and the measurement above does not justify that in the two-thirds of cases where the anchor was already right.
