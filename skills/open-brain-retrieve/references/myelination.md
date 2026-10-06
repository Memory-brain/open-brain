# Step 11 — myelination traversal recording

> Which paths get recorded, the `myelinate.py record` command and its rules. Read when in doubt about which pairs to record.

---

> **Since 9.22.0** traversals are recorded by `log_entry.py close` from the pairs in `Notas usadas sustantivamente` (notes used substantively). The `record` command below is still valid for recording a single pair by hand if ever needed.


## Step 11: Record Myelination Traversals (mandatory)

After writing the Retrieval Log, traversals are recorded so the vault's myelination engine (`$OPEN_BRAIN_ENGINES/autolink/myelinate.py`) can reinforce frequently used knowledge paths. Without this step, all graph edges stay at equal weight forever and the vault never learns from its own usage.

The idea mirrors biological myelination: axons that fire together get wrapped in myelin and conduct faster. Here, edges traversed during retrieval get weight boosts, making those paths easier to find next time. Edges that were traversed at least once but then fall out of use gradually decay — surfacing knowledge that has gone stale for review. (Edges never traversed are not decayed; see the parameters in `open-brain-autolink`.)

### What to record

For each **navigation path** taken during retrieval where both endpoints were used substantively, record one traversal. Typical paths:

- **Entry point → first note found** (e.g., Domain → PN, Search Term → LN)
- **LN → PN it feeds** (when the LN's `source` or the PN's feeding LNs were both cited)
- **PN → PN** connected via shared search terms or wikilinks (when both were cited)
- **LN → LN** used together — record these too: a typical graph holds roughly ten times more LN nodes than PN nodes, yet when only PN↔PN pairs were recorded the graph learned almost exclusively from Permanent Notes
- **PAT/REF → linked PN** (in Visual mode, when both the design reference and its linked PN were cited)

Use the note title (filename without `.md` extension) as the slug — this matches how `graph.jsonl` stores edge endpoints. Non-existent edges are silently ignored when `myelinate.py apply` runs later.

### How (manual fallback)

Run one `record` call per edge traversed:

```bash
python3 "$OPEN_BRAIN_ENGINES/autolink/myelinate.py" record \
  --from "<source note title>" \
  --to "<target note title>" \
  --query "<original query text>" \
  --intent "<detected intent>"
```

### Rules

- Only record edges for notes used **substantively** (same criteria as the `times_retrieved` increment in the Retrieval Loop).
- Record **any** co-used pair that has an edge — PN↔PN, LN↔LN or mixed. Note type is irrelevant to the graph.
- In **Serendipity mode**, still record traversals. Myelination tracks actual usage patterns independently of `times_retrieved` (which skips Serendipity). The graph should learn even from exploratory retrieval.
- **Audit-origin queries** (closed with `--origen_uso auditoría`) are not myelinated.
- In **Visual mode**, record edges between surfaced PAT/REF notes and their `linked_pns` when both were cited in the response.
- Retrieve **only records** — it never runs `myelinate.py apply`. The apply step (which updates graph weights and runs decay) happens separately via `open-brain-health` or `open-brain-autolink`.
- If the script is not found or fails, log the failure in the Retrieval Log entry under **Gaps** and continue. Do not halt retrieval for a myelination error.

---
