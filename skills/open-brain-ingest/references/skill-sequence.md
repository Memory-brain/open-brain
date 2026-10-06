# Step 0.9 — Trace `skill_sequence`

> The full trace step: why it exists, the YAML, how to prepend the entry of an earlier skill in the same session, and what the field does NOT do. Read it when the content arrives chained from another skill, or when unsure whether the field triggers anything.

---

## Step 0.9: Trace — `skill_sequence`

**Why it exists**: without this field, no note records which sequence of skills produced it — the step before (which skill produced the material that fed the next one) is lost when the session closes. Without that data there is no way to measure which skill sequences produce notes that actually get retrieved or published. This is the first, mechanical step towards closing that loop. It only starts accumulating data; the aggregation ("which sequence wins") is future work.

**What to do**: every note created here (Inbox, Case, REF, PAT) carries a `skill_sequence:` field with at least one entry:

```yaml
skill_sequence:
  - skill: open-brain-ingest
    at: "YYYY-MM-DDTHH:MM"
```

If the content being captured already came from another skill in the same session (e.g. a research skill handed over a finding that is now being ingested), **prepend** that entry instead of starting from scratch:

```yaml
skill_sequence:
  - skill: open-brain-retrieve
    at: "YYYY-MM-DDTHH:MM"
  - skill: open-brain-ingest
    at: "YYYY-MM-DDTHH:MM"
```

**What it does NOT do**: it triggers nothing, does not chain the next skill automatically, and is not a field the user has to maintain by hand — each skill that creates or transforms a note simply appends its own entry to the end of the list the source note already carried (if any).

---
