---
name: open-brain
description: >
  Meta-skill router for the Open Brain knowledge, learning and writing system.
  Detects intent and lazy-loads the right open-brain-* skill. Triggers on: "open-brain",
  "capture", "extract", "promote", "synthesize", "enrich", "what do I know about",
  "contradictions", "health check", "I want to learn", "analyze", "panel",
  "course", "flashcards", "practice log", "index", "process", "search my vault",
  "write", "draft", "regenerate the graph", "autolink", "weekly review",
  "vault", "learn", "retrieve", "audit", "eval".
  Explicit commands: "open-brain extract/promote/retrieve/health/escribir/autolink/start/stop/harvest/etc".
metadata:
  version: "2.1.0"
---

# Open Brain — Router v2

Single entry point. Detect intent → show the stub → load the target skill.

Each route has a short card in `references/<route>.md`. The card only helps you route; the rules you execute live in the shipped skill `open-brain-<route>`.

## Routing Table

| Intent | Route → skill | What it does (stub) |
|---|---|---|
| Capture content, migrate from Notion, save to vault | **ingest** → `open-brain-ingest` | Creates Inbox/Case/Fleeting notes with bidirectional wiring |
| Extract notes from PDF/book/article, create LNs | **extract** → `open-brain-extract` | Admission gate, then atomic Literature Notes. PDFs are converted to text first |
| Index a book, create Source Outline | **index** → `open-brain-index` | Compressed book representation inside its Dossier. TOP = exhaustive, INTERESTING = minimal |
| Promote LNs to Permanent Notes, endorse, reject | **promote** → `open-brain-promote` | Synthesis layer. Modes: chat, web UI, visual (PAT notes) |
| Search vault, what do I know about X | **retrieve** → `open-brain-retrieve` | Queries the vault: notes, connections, visual patterns, provenance |
| Synthesize domain, layer coverage, gaps | **synthesize** → `open-brain-synthesize` | Builds Domain Indexes and competency maps |
| Improve search terms, aliases, connections | **enrich** → `open-brain-enrich` | Adds metadata to existing notes without changing content |
| Contradictions, fertile PNs, cross-domain, sandwiches | **graph** → `open-brain-graph` | Typed queries on `autolink/graph.jsonl` |
| Health check, orphans, duplicates, stale notes | **health** → `open-brain-health` | Vault immune system. Diagnoses and auto-fixes where safe |
| Vault metrics, scorecard, how is my vault doing | **eval** → `open-brain-eval` | Three-layer performance eval (mechanical, judgment, trend) |
| Regenerate typed graph, update autolink | **autolink** → `open-brain-autolink` | Rebuilds `graph.jsonl`. Runs silently after note-creating ops |
| Write a post, draft, article; writing session | **escribir** → `open-brain-escribir` | Saves your writing verbatim as islands and asks one question back |
| Weekly review, what did I practice | **review** → `open-brain-review` | Sessions reviewed, domains practiced, uncaptured ideas |
| Start learning session, want to learn | **learn-session** → `open-brain-learn-session` | Routes to the analyze → extract → execute → improve sequence |
| Analyze content, compress, mental models | **analyze** → `open-brain-analyze` | Phase 1: Knowledge, Compression, Mental Models |
| Apply knowledge, template, guide, checklist | **execute** → `open-brain-execute` | Phase 2: Application, Artifacts, Decision |
| Improve, practice, rubric, coaching | **improve** → `open-brain-improve` | Phase 3: Diagnosis, Coaching, Practice |
| Expert panel, roundtable, scorecard | **panel** → `open-brain-panel` | 3–6 experts review in character → consensus + roadmap |
| Generate HTML course for a vault Skill | **course** → `open-brain-course` | Three phases: Vocabulary → Production → Transfer |
| Grade and close a course | **course-evaluate** → `open-brain-course-evaluate` | Scores the synced practice export, writes the next-course brief |
| Flashcards, spaced repetition | **flashcards** → `open-brain-flashcards` | Pre-brief → local session → post-coaching on missed cards |
| Practice log open/close/harvest | **practice-log** → `open-brain-practice-log` | open: tag domain + capabilities. close: gaps + fleeting. harvest: consolidate |

## Routing Rules

1. **Explicit command wins.** "open-brain extract" → route to extract directly.
2. **Implicit intent.** "process this PDF" → infer extract.
3. **Writing priority.** "I want to write about X" → escribir, not retrieve.
4. **Ambiguity → ask.** One concise question; don't guess.
5. **Always load the full skill before executing.** The stub and the route card are for routing; `open-brain-<route>` has the actual rules. Never execute from the card.

## Chains

After a skill completes, suggest the natural next step. Autolink runs silently after note-creating ops.

| After | Suggest | Auto-run |
|---|---|---|
| ingest | extract (if substantive content) | — |
| extract | index (if TOP book) or promote (if convergences) | autolink |
| analyze | extract (to vault the insights) | — |
| promote | enrich (improve retrieval) | autolink |
| enrich | — | autolink |
| health | — | autolink |
| eval | health / enrich / promote / synthesize (per gap found) | — |
| course | course-evaluate (once answers are synced) | — |
| practice-log close | escribir (if publishable fleeting) | — |
| escribir | ingest (if new insight saved) | autolink |

## Vault Path

Root: `$OPEN_BRAIN_VAULT`. Key folders: `Inbox/`, `Literature Notes/`, `Permanent Notes/`, `Cases/`, `Evergreen/`, `Ideas/`, `Resources/`, `Skills/`, `Domains/`, `Design References/`, `Dossiers/` (graph data lives outside the vault, in `$OPEN_BRAIN_ENGINES/autolink/`). See `references/shared/vault-spec.md` for the folder → note type map and the critical rules.

## Aliases

`open-brain start` = practice-log open · `open-brain stop` = practice-log close · `open-brain harvest` = practice-log harvest
