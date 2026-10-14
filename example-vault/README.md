# Example vault (fictional)

A small Open Brain vault you can run the engines against without having a vault of your own.

**Everything in it is invented.** The two books (*The Small Loop*, 2019, and *Teams of Five*, 2021), their authors (Mara Ellwood, Dov Hartigan), the essayist (Ilse Brannock), every quote, study and figure, and the vault owner's cases are fictional. They are not summaries of any real book.

Run it from the repo root:

```bash
bash example-vault/run-demo.sh
```

The script copies this folder and the autolink engine into a temporary directory, runs the engines there and deletes the directory on exit, so nothing is written into the repo. You need Python 3.9 or later. PyYAML is optional; without it, one informational check (35) reports 0.

## What is in it (33 notes)

| Folder | Notes | Content |
|---|---|---|
| `Inbox/` | 3 | the two books (`processed: true`) and one essay that was never extracted |
| `Literature Notes/` | 10 | five per book, prefixes `SL` and `TF` |
| `Permanent Notes/` | 5 | four endorsed, each built on two independent sources; one draft |
| `Search Terms/` | 8 | Habit Formation, Cue Anchoring, Minimum Viable Repetition, Environment Design, Feedback Loops, Team Size, Decision Rights, Meeting Cadence |
| `Domains/` | 2 | Behavior Change, Team Leadership |
| `Cases/` | 2 | one that confirms a Permanent Note and one that challenges another |
| `Mentors/` | 3 | the three fictional authors |

## Seeded defects

These defects were added on purpose, so you can check what the engines catch. The table also shows what they miss.

| # | Defect | Where | Expected result |
|---|---|---|---|
| 1 | Unprocessed Inbox item older than 30 days | `Inbox/The Quiet Standup.md` | **Caught.** Health check 5 (`Unprocessed Inbox (>30d)`: 1), eval `inbox_stale_30d: 1` |
| 2 | Literature Note with too few search terms (2, minimum 3) | `Literature Notes/SL - A broken streak predicts dropout more than a missed day.md` | **Caught** by `enrich_engine.py scan` (`under_threshold`). No health check counts terms per note. |
| 3 | Orphan Permanent Note, with no links in the body. Both its sources come from one author. | `Permanent Notes/Small teams beat large teams on ambiguous work.md` | **Caught.** Health check 1 (`Orphan Notes`: 1), eval `orphan_pns: 1`. Health check 36 also flags it as `single_author`. |
| 4 | Crowded search term: `Habit Formation` is tagged on 12 notes, including notes where it adds nothing | 8 Literature Notes + 4 Permanent Notes | **Partly caught.** Health check 16 lists it in `yellow_top` (tag_count 12, yellow band >10), but the check's `count` stays 0, because a flat term only counts as red above 20 notes. A vault this small cannot reach that band. |
| 5 | `description` states a topic instead of a claim (`"About meeting rhythm."`) | `Literature Notes/TF - A fixed weekly rhythm makes a small team predictable.md` | **Caught.** Health check 46 (count 2: the description starts with "about" and has fewer than 8 words) |
| 6 | Broken wikilink in a Literature Note's connector, pointing to a note that was never written | `Literature Notes/TF - Five is the largest team where everyone can track everyone's work.md` → `[[TF - Decisions stall when nobody knows who can say no]]` | **Missed.** Health check 8 and eval `broken_links` scan only Permanent Note bodies. Check 39 audits only batches created in the last 45 days. Autolink drops the edge without reporting it. |

The vault also contains one deliberate tension that is not a defect. *A new routine sticks when it is small enough to run on a bad day* contrasts with *Judge a practice by its weekly review, not by its daily streak*. Health check 12 surfaces that pair as a contradiction candidate for you to judge.

Numbers that depend on today's date, such as the Inbox item's age in days, change with the date you run the demo.
