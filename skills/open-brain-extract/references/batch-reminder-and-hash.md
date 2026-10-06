# Steps 6.1 and 6.2 — Periodic reminder in long batches and `source_hash`

> The criterion reminder every ~6 LNs and the `source_hash` computation, with the rationale for each and what they deliberately don't do yet. Read it in a long batch or when the source has a text cache.

---

## Step 6.1: Periodic reminder in long batches

**Why it exists**: in a long batch (a TOP source usually yields 8–15 LNs), the admission criterion for an LN — one idea only, the three voices separate, `search_context` with the real relation and not a generic label — holds firmly for the first 2–3 notes and dilutes towards the end. It is the same mechanism by which a long-context safety monitor misses actions buried in the middle of a long transcript (Martin & Roger, 2026, arXiv:2605.12366, §4.6). The cheapest mitigation the paper measures is not more reasoning or a longer prompt — it is repeating the criterion at the moment, not just once at the start.

**What to do**: every ~6 LNs written in the same batch, or when crossing into a different section/chapter of the source (whichever comes first), re-read the admission criterion in one sentence before continuing: is this note one idea, not two? does the `[!claude]` callout contain only wikilinks + one line, not a paragraph of new analysis? does each `search_context` explain the real relation, or is it a generic label ("related", "relevant")? It is not a formal check and creates no artifact — a one-sentence pause, as cheap as the reminder the paper measures (<3 % overhead).

**What it does NOT do**: it doesn't replace the Step 6.7 LN Lint (that one is mechanical, runs once at the end of the batch); this is the reminder *during* writing, not the verification *after*. Nor is it a gate — if on re-reading the criterion a note already written fails it, fix it on the spot; don't block the rest of the batch.

---

## Step 6.2: `source_hash` — Freshness by Content, Not Just by Date

**Why it exists**: the staleness checks in `$OPEN_BRAIN_ENGINES/health-engine/health_check.py` only compare `last_validated`/`claim_date` against today — purely temporal. If the user re-extracts a re-edited source, nothing detects that the text under an already-extracted LN changed; the clock is the only signal, and a source can be re-edited without enough time passing to trigger the temporal check.

**What to do**: if a text cache exists for this source in `Resources/Extracted Text/{source-slug}.md` (created in Step 0.5), compute its sha256 and store the first 16 hex characters as `source_hash: "sha256:<16-hex>"` on every LN born from that source. If the source has no cache (web article, video, text pasted directly) — omit the field entirely; don't write an invented value.

```bash
python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()[:16])" "Resources/Extracted Text/{source-slug}.md"
```

**What it does NOT do yet (on purpose)**: this is only the write side. A check that compares `source_hash` against the real cache on every health pass (a "source drift" check) **is not implemented yet** — it needs real LNs with `source_hash` to validate the LN→cache mapping before writing the read side without guessing. Until then, this field accumulates without anything reading it; that is correct, not a bug.

**The literal quote remains the anchor, not the hash**: if the hash changes because the source was re-edited, the real question is whether the LN's quote still appears in the new text — that is judgment, not something this mechanical step decides.

---
