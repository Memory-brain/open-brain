# Steps 4.7 and 4.8 — deterministic engine and candidates sidecar

> Why the engine exists (on a judged pool the agent alone reached ~97 % precision but ~31 % recall, and the engine found several times more of the relevant notes), its rules, the expected failures, and the candidates-sidecar contract. `SKILL.md` carries the command and the three rules most often broken; the rest is here.

---

> **Since 9.22.0** the sidecar is written by `eval_retrieval.py retrieve` when it answers, with `--log-id` to join it to the log entry (`--no-sidecar` for evals). What follows describes the schema; it is no longer a manual step.


## Step 4.7: Deterministic engine (second candidate source — mandatory)

Grep and the graph hop are the agent's own pool: precise and narrow. The engine at `$OPEN_BRAIN_ENGINES/retrieval-eval/eval_retrieval.py` is the second source — fused BM25 + LSA + bridge channels over an index of the whole vault, deterministic, no network, ~1.4 s per query.

**When to run it**: on every substantive retrieval (Query Types 1–7), after Pass 2/Pass 3 have produced the seed titles and **before** the frontmatter pre-filter (L0) picks the top-K. Skip it only when the user explicitly asks for speed ("quick", "just give me the first thing") or in Visual mode — QT8 ranks by endorsement, not by text similarity.

```bash
python3 "$OPEN_BRAIN_ENGINES/retrieval-eval/eval_retrieval.py" retrieve "<literal query>" --expand "<the Step 0.8 expansion, literal>" --k 20 --json --log-id <id from Step 0.1>
```

Rules:

- **Pass your own expansion in `--expand`** — the one from Step 0.8, verbatim. It is the one measured as significant (+16.9 pp, CI `[+7.8, +26.5]`). Omit it and the engine builds one by pseudo-relevance feedback (RM3: +9.0 pp, CI `[−2.0, +19.9]`) — a floor for when there is no expansion at all, not a substitute for yours.
- **The output is candidates, not an answer.** Add to the pool only what was not already there, then triage it exactly like a grep hit: frontmatter first, full body for the top 2–4. The high precision is the agent's and stays the agent's; what the engine buys is the recall the agent does not reach.
- **Do not inherit the engine's ordering as a verdict.** Rank its rows by the same criteria as everything else (`description` relevance → `confidence` → `maturity` → `times_retrieved`), and never cite a note whose body was not read in this retrieval.
- **Attribute its hits honestly.** A note that only the engine surfaced is written `ninguno (motor)` ("none (engine)") in `Términos que matchearon`. Crediting it to a term the agent never matched corrupts the one measurement that will decide the fate of the vault's free search terms.
- **If it fails, continue — never halt.** The failures to expect: no index → the command returns `{"ok": false, "fix": "python3 eval_retrieval.py index"}`; an `lsa.npz` whose fingerprint no longer matches the index → `RuntimeError` naming both fingerprints, fixed by re-indexing; the script or the folder missing altogether. In every case: write `no disponible: <reason>` ("not available") in the `Motor determinista` field, note it under `Gaps detectados`, and answer with grep + hop alone. **Querying needs only numpy** (`scipy` is imported lazily inside `lsa.build()` and is required for `index`, not for `retrieve`) — so a scipy error at query time means someone moved that import back to the module header, and that is a code bug to report, not a shell to work around.
- **Check the index age it reports.** Older than 14 days → say so before answering. A stale index under-returns recent notes silently, which looks exactly like a gap in the vault.

Why this step exists: on a judged pool of 12 queries the agent retrieved at ~97 % precision and **~31 % recall**, and of the pool's relevant notes roughly four times as many were found only by the engine as only by the agent. Two instruments disagreeing that much on the same queries means the pool the agent triages is too small — not that its judgment is off. Falsifiable: if over the next 30 entries the `Motor determinista` field keeps reporting `0 candidatas nuevas` ("0 new candidates"), this step is dead weight and comes out.

---

## Step 4.8: Candidates sidecar (mandatory when Step 4.7 ran)

The Retrieval Log records **how many** candidates there were (`Candidates pre-filtered: N → K`) — never **which** ones, nor where they landed in the fused ranking. That single omission makes *width* (the agent's pool was too narrow) indistinguishable from *dominance* (a relevant note was in the pool but a channel buried it below the reading cut) — and those two failure modes have different fixes. This step closes that gap at zero extra cost: Step 4.7 already computed the full answer, this only writes it down.

**When**: immediately after Step 4.7 returns successfully — same retrieval, no extra engine call. Skip silently if Step 4.7 was skipped, failed, or returned `{"ok": false, ...}`.

**What is written**: the exact JSON Step 4.7 returned (`candidates`, already ordered by fused rank, each with its `channels`), as ONE line appended to `Resources/Retrieval Candidates.jsonl` — append-only, never rewritten:

```json
{"date": "<today, YYYY-MM-DD>", "intent": "formal|implicit", "query": "<literal query>", "expand": "<Step 0.8, literal>", "expand_source": "<the same field Step 4.7 returned>", "candidates": [{"rank": 1, "rel": "...", "title": "...", "folder": "...", "channels": ["bm25@1", "hop@2"]}, ...]}
```

Rules:

- **No recompute, no re-rank.** The `candidates` array is Step 4.7's own output, untouched — its list order IS the fused rank (`rank` = 1-indexed position).
- **One line per retrieve**, keyed so it can be joined with the Retrieval Log entry (the `--log-id`, date + intent).
- **This is not a Retrieval Log field.** It does not replace `Candidates pre-filtered` or `Motor determinista` — both still get written in Step 10. The sidecar is a separate artifact for later diagnosis, not something the user reads per retrieval.
- **If the append fails** (permissions, disk), note it under `Gaps detectados` and continue — never let this step block the answer.

---
