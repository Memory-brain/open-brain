---
name: open-brain-flashcards
description: 'Spaced repetition flashcard sessions. Pre-session brief, launches a local flashcard viewer if you have one,
  post-session coaching on missed cards and recurring patterns. Triggers: flashcards, review flashcards, quiz me,
  flashcard session, open-brain flashcards

  '
metadata:
  version: 1.0.0
  description_long: 'Open Brain Flashcards runs spaced-repetition sessions (SM-2) over the Permanent Notes of
    your vault, domain by domain: a pre-session brief, an Anki-style viewer (your own local viewer, or the chat
    as fallback), and post-session coaching on missed cards and recurring patterns. Part of the Open Brain
    skill set for Markdown/Obsidian vaults.

    '
  status: canonical
  consumes:
  - An existing domain of Permanent Notes in the vault
  - The generated deck (cards-<DOMAIN>.json) or willingness to regenerate it
  - Log history from previous sessions (SM-2 state)
  produces:
  - A spaced-repetition review session served locally (Anki-style viewer) or run in chat
  - A pre-session brief with due/new cards and historical trend
  - An append-only markdown log of the session and post-session coaching
---

# Open Brain — Flashcards

Orchestrates the full spaced-repetition ritual over your Permanent Notes, domain by domain. It uses SM-2 spacing. The job is to ritualize sessions: nobody should open the viewer cold, and nobody should close the tab without a 60-second conversation about what failed.

---

## System structure

### The flashcard viewer (optional)

This skill does not ship a viewer. **If you have a local flashcard viewer** (a deck builder plus a small local server with an Anki-style page), point the skill at its folder with the env var `OPEN_BRAIN_FLASHCARDS_DIR`. The skill expects this shape:

```
$OPEN_BRAIN_FLASHCARDS_DIR/
├── build.js                          # generates cards-<SLUG>.json from the domain's PNs
├── server.js                         # multi-domain, simplified SM-2, port 8000
├── index.html                        # Anki-style viewer
├── cards-<SLUG>.json                 # one deck per domain
├── state-<SLUG>.json                 # SM-2 state per domain
├── session-<SLUG>.json               # only exists while a session is open
└── ...
```

**If you don't have a viewer**, run the session in chat: build the deck from the domain's PNs (front = the PN title as a question, back = its core claim), show one front at a time, wait for the user's answer, reveal the back, ask "good or bad?", and append the result to the log below in the same format the server would use. Skip the server-specific steps (start/kill server, endpoints, `open http://…`).

### Logs (in the vault)

```
$OPEN_BRAIN_VAULT/Resources/Flashcards Logs/
├── <Domain A>.md        # human append-only log, 1 block per session
└── <Domain B>.md
```

Each domain = one deck, one state, one session at a time, one independent markdown log. They coexist without collision.

### Server endpoints (if you use a viewer)

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/state`        | Today's deck + stats + current session |
| POST | `/api/review`       | `{id, result: 'good'|'bad'}` — writes SM-2 + appends a line to the log instantly |
| POST | `/api/end`          | Closes the session block and rewrites the header with a summary |
| GET  | `/api/log-summary`  | **For this skill**: stats + recentSessions + weakCards + strongCards + dueSoon |

Without a viewer, compute the same summary by reading the domain's log file.

---

## Step 0: Resolve the domain

The user says `flashcards`, `flashcards Organic Chemistry`, `flashcards Music Theory`, etc.

- If **no domain is specified** → ask once: *"Which domain?"* (suggest the domain with the most PNs as default). If the recent conversation mentions a clear domain, use it without asking.
- If a domain is specified → use it as given, respecting capitalization and spaces. The server converts it to a slug (`Organic Chemistry` → `Organic-Chemistry`).
- **Do not invent domains.** If the user requests a domain not found in any PN's `domain:` or `domains:` field, say: *"I don't have PNs tagged with that domain. Do you want me to list the available domains?"*

From here: `<DOMAIN>` = original string (with spaces), `<SLUG>` = slug form.

---

## Step 1: Verify the deck

Before starting the server, check that `$OPEN_BRAIN_FLASHCARDS_DIR/cards-<SLUG>.json` exists.

- **Does not exist** → run `cd "$OPEN_BRAIN_FLASHCARDS_DIR" && DOMAIN="<DOMAIN>" node build.js`. Wait for the output and tell the user how many cards were generated.
- **Exists but old** (>14 days, check `generatedAt`) → warn: *"Your <DOMAIN> deck is X days old. Regenerate before starting?"*. If yes, run build.js.
- **Recent** → continue.

**Critical**: never start the server with a nonexistent deck.

---

## Step 2: Pre-session brief

Start the server in the background (default port 8000). While it starts, call `GET http://localhost:8000/api/log-summary` and build a **4-line brief** before the user opens the browser.

```bash
cd "$OPEN_BRAIN_FLASHCARDS_DIR"
PORT=8000 DOMAIN="<DOMAIN>" node server.js &
sleep 1
curl -s http://localhost:8000/api/log-summary
```

Brief format (adapt to the real content, not a rigid template):

> **<DOMAIN> session** · X cards due · Y new
>
> 📊 History: Z sessions, W% overall accuracy, last 5 trajectory: [70 → 60 → 75 → 65 → 80%]
>
> ⚠️ Coming up: 3 cards you keep stumbling on:
> - [[Card A]] — 3 misses in recent sessions
> - [[Card B]] — 33% historical accuracy
> - [[Card C]] — you missed it last time
>
> 🌱 And N new cards you've never seen.
>
> Open http://localhost:8000

If it is the **first session for the domain** (totalSessions = 0):
> **<DOMAIN> session** · X cards total · this is your first session.
> Open http://localhost:8000.

Wait for the user to confirm they've finished, then go to Step 3.

---

## Step 3: Post-session coaching

When the user says "done" / "finished" / "closed the tab" / "ready", call `/api/log-summary` again. Compare with the Step 2 snapshot to detect what happened this session.

1. **Read the last log entry** (`Resources/Flashcards Logs/<DOMAIN>.md`) — the block `## YYYY-MM-DD HH:MM — N cards · X% correct`. This tells you exactly what failed and what was correct.

2. **Give coaching in 3 pieces**:
   - **Net result**: `Today X% (vs. Y% historical average)` — state whether it went up or down, without drama.
   - **Patterns**: is there a thematic cluster in the failures? E.g., *"Today's 3 misses are all about reaction mechanisms. There's a note you're avoiding."* Read the failed PNs and look for overlaps in their tags/connections.
   - **One concrete next action**: single, specific. E.g., *"Before the next session, open [[<the PN you missed most>]] and rewrite the first paragraph in your own words. 5 minutes."*

3. If the user has failed the same card in ≥3 consecutive sessions → **that is the main coaching point**: the note is poorly written; it isn't being memorized because something in its phrasing doesn't stick. Suggest rewriting it, not studying it more.

---

## Step 4 (optional): Auxiliary commands

### `flashcards gaps <DOMAIN>`
Brief only, without starting a session.
- Call `/api/log-summary` (start the server temporarily if needed, kill it afterwards).
- Return a fuller report: top 10 weakCards with accuracy, top 5 strongCards (candidates for "I already know these, remove them"), full trajectory of the last 10 sessions.
- Does not open the browser.

### `flashcards regenerate <DOMAIN>`
Run `DOMAIN="<DOMAIN>" node build.js` and report the delta: *"Before 45 cards, now 52 (+7 new PNs detected)"*. If the server is running, remind the user to reload the tab.

### `flashcards wipe <DOMAIN>`
Nuclear operation: deletes `state-<SLUG>.json` and `session-<SLUG>.json`. Requires explicit confirmation: *"This deletes all your SM-2 progress in <DOMAIN> (X cards with history). The markdown log in the vault is NOT touched. Confirm?"*. Only proceed if the user says "yes" or an unambiguous equivalent.

---

## Always do

- Start the server with `DOMAIN="<DOMAIN>"` exported; do not assume the default.
- Kill old processes on the port before starting: `lsof -ti :8000 | xargs kill -9 2>/dev/null || true`
- Offer to open the browser (on macOS: `open http://localhost:8000`) after the brief.
- After coaching, leave the server running unless the user asked to close it (they may want another round).

## Never do

- **Do not interpret cards for the user during the brief.** The brief shows what's coming, not the answers.
- **Do not regenerate the deck mid-session.** build.js overwrites `cards-<SLUG>.json` and breaks the session in progress.
- **Do not touch `state-<SLUG>.json` manually.** That is the SM-2 ground truth; any change breaks the intervals.
- **Do not edit past entries of the vault's markdown log.** It is append-only by design. If information is needed, read; only append new session blocks.
- **Do not coach on cards that don't appear in today's log.** Coaching is about the just-closed session, not all-time history.
