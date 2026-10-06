# Step 0 and Step 0.4 — Scope check and Admission Gate

> The full scope check and admission gate: criteria table, consequence per band, REJECT procedure, why the gate exists, its kill criterion and what the gate is NOT. Read it when unsure about the threshold, the kill criterion, or what to do with a rejected source.

---

## Step 0: Scope Check — Is This Source Ready?

Classify the source:
- ✅ **Ready** — Inbox note with substance, OR raw text/PDF in conversation, OR highlights
- ⚠️ **Empty shell** — Inbox metadata stub, no actual content yet
- ❓ **Unclear** — Partial content, needs clarification

`Ready` answers *can I extract this*. Step 0.4 answers *should I* — and it runs before a single note is written.

## Step 0.4: Admission Gate (MANDATORY, all sources, before extracting)

Score the source on four criteria **before extraction, on any source type** — not only books. Judge from the abstract, table of contents, section headings and a skim; you do not need the full read to score.

| Criterion | Score | What distinguishes each level |
|----------|-----------|--------------------------|
| **Originality** | X/3 | 1 = restates what is already known · 2 = synthesis with a perspective · 3 = new framework |
| **Density** | X/3 | 1 = diluted · 2 = balanced · 3 = high density of actionable insights |
| **Contribution** | X/3 | 1 = the vault already says it (≥3 notes in the engine's top-10 assert the same) · 2 = qualifies, extends or adds new evidence to what the vault already has · 3 = contradicts a vault note or opens an axis no note covers |
| **Evidence** | X/3 | 1 = opinion · 2 = mixed · 3 = empirical, or cases with data |
| **TOTAL** | X/12 | |

**How Contribution is scored.** Before giving the number, run the engine on the source's central claim and look at the `description`s of the top-10:

```bash
python3 "$OPEN_BRAIN_ENGINES/retrieval-eval/eval_retrieval.py" retrieve "<central claim of the source, one sentence>" --k 10 --json --no-sidecar
```

Count how many assert the same as the source, **not counting notes from the source itself** (on a second pass or a re-extraction the engine returns the source's own LNs and contribution would come out falsely low). **≥3 → Contribution = 1**, even if the topic is central to the vault. The error this step can make is the opposite one: if the engine doesn't find the similar notes, Contribution comes out high and the source gets in. That's the cheap error; the expensive one — admitting redundancy by design — is the one this fixes. The criterion it replaces, *Convergence*, counted points of contact with the vault, and that rewards redundancy: a deliberately mediocre baseline article that restated well-known PKM methods scored 2 on Convergence **precisely because the vault already had it**, and that point pushed it to 5/12 and admitted it. Convergence still exists, but where it is useful: in Step 6, when writing each note, as a promotion signal. Not at the door.

**Redundancy veto.** Originality = 1 **and** Contribution = 1 → REJECT, whatever the total. A source that neither says anything new nor adds anything to the vault is not saved by being well written or by bringing data about what you already know.

**Consequence:**

- **≥9 — TOP.** Extract. When done, invoke `open-brain-index` directly for the exhaustive Source Outline.
- **5–8 — INTERESTING.** Extract. Minimal `open-brain-index` only if the user asks.
- **≤4 — REJECT. Do not extract.** This cuts: no notes are written.

**When the result is REJECT:**

1. **Do not write a single LN.** Not partial, not "the best three".
2. Append one line to `Resources/Rejected Sources.jsonl` (create it if missing), one source per line. Keys are kept as the engines parse them:
   ```json
   {"fuente": "<title or URL>", "fecha": "YYYY-MM-DD", "tipo": "paper|articulo|libro|transcript|repo", "score": {"originalidad": N, "densidad": N, "aporte": N, "evidencia": N, "total": N}, "veto_redundancia": true|false, "razon": "<one sentence: which criterion sank it and why>", "decidido_por": "claude|user"}
   ```
   (`fuente` = source, `fecha` = date, `tipo` = type, with `articulo|libro` = (article|book), `originalidad/densidad/aporte/evidencia` = originality/density/contribution/evidence, `veto_redundancia` = redundancy veto, `razon` = reason, `decidido_por` = decided by.)
3. If an Inbox note exists, **keep it** with `vault_coverage: rejected`. Nothing is deleted — same doctrine as `open-brain-promote`: what is rejected is moved and annotated.
4. Report the score to the user in one line. **The user can override the verdict in either direction** — if they do, the JSONL line carries `"decidido_por": "user"` and the reason they give.

**Why this gate exists.** A vault without recorded rejections has **zero negative examples**: without rejections there is nothing to calibrate the threshold against, so the JSONL matters as much as the cut. And admission is the **only** control point the system has left: a note already written is not retired for disuse — the vault's doctrine is that what an agent writes into its own memory does not expire through age or disuse. What doesn't get in is the only thing you don't have to maintain afterwards.

**Kill criterion for this gate.** If in **10 sources in a row none scores below 5**, the threshold isn't discriminating: either it goes up, or you admit the real filter is the user choosing what to paste into the chat. **Trigger**: before scoring this source, count how many of the last 9 decisions recorded in `Resources/Rejected Sources.jsonl` + `Resources/Source Index.md` scored ≥5 — if all 9 did and this one does too, say so in this same extraction's Step 10 report ("⚠️ Admission Gate: 10 sources in a row ≥5 — the threshold may not be discriminating"). Nobody else checks this; this step is the only moment when the data to do it is already in context.

**What this gate is NOT**: it is not an a-priori quality rubric. It is a **prediction** of expected value, and it can only be scored after the fact — per batch and per source type. That scorekeeper is `$OPEN_BRAIN_ENGINES/engine/batch_scorecard.py`, not this step.
