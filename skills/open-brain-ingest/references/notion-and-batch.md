# Notion migration and batch ingestion

> Mapping from Notion properties to Obsidian fields, and the two-pass procedure for migrating a whole database without duplicating support notes. Read it only when the source is Notion or a batch is being ingested.

---

## Notion Migration: Property Mapping

| Notion Property | Obsidian Field | Notes |
|----------------|----------------|-------|
| Type / Category | `source_type` | Map to: article, book, video, podcast, course, tool, tweet, conversation, research-report, other |
| Rating / Review | `rating` | 1-5 scale |
| Link / URL | `link` | Direct URL |
| Tags / Searchable terms | `search_terms` | Create `[[wikilinks]]` |
| Author / Mentor | `mentor` | Create `[[wikilink]]` |
| Areas | `areas` | Create `[[wikilinks]]` |
| AI summary / Notes | body content | Raw capture in body |

### Batch ingestion

When migrating a full database:
1. First pass: identify ALL unique mentors, search terms, books, and areas across all pages
2. Create all supporting notes first (prevents duplicates)
3. Second pass: create Inbox notes, linking to already-created supporting notes
4. Report totals and any issues

---
