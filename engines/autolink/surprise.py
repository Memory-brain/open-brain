"""
surprise.py — SurpriseFilter for open-brain-ingest.

Inspired by neuron's SurpriseFilter (Z-Sigma): evaluates novelty of
incoming content BEFORE creating a vault note. Uses discrete vault
signals instead of vector embeddings — deterministic, no LLM.

THREE BANDS (like neuron):
  1. Novel    (score ≥ 0.6)  → proceed with ingestion
  2. Confirm  (0.3 ≤ score < 0.6) → content reinforces existing knowledge;
                                      suggest linking instead of new note
  3. Duplicate (score < 0.3) → near-duplicate exists; ask the user before creating

THREE SIGNALS:
  1. search_terms overlap — how many proposed terms already tag existing notes
  2. title similarity   — trigram overlap with existing note titles
  3. mentor saturation  — diminishing returns for overrepresented mentors

Usage:
  python3 surprise.py evaluate \\
      --title "How to Build a Second Brain with Obsidian" \\
      --terms "PKM,Second Brain,Obsidian,Note-taking" \\
      --mentor "Tiago Forte" \\
      --type inbox

  python3 surprise.py evaluate \\
      --title "My experience redesigning the onboarding flow" \\
      --terms "Onboarding,UX,Conversion" \\
      --type case

  python3 surprise.py stats       # show vault coverage stats
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Vault root: $OPEN_BRAIN_VAULT if set, otherwise the parent of this autolink/ folder.
VAULT_ROOT = Path(os.environ.get("OPEN_BRAIN_VAULT") or SCRIPT_DIR.parent)
VAULT_INNER = VAULT_ROOT
ENTITIES_FILE = SCRIPT_DIR / "entities.json"


def load_entities() -> dict:
    """Load entities.json (built by indexer.py); clear error if missing."""
    if not ENTITIES_FILE.exists():
        raise SystemExit(f"entities.json not found at {ENTITIES_FILE} — run indexer.py first")
    return json.loads(ENTITIES_FILE.read_text(encoding="utf-8"))

# ============================================================
# BAND THRESHOLDS
# ============================================================

NOVEL_THRESHOLD = 0.6       # score ≥ this → novel
CONFIRM_THRESHOLD = 0.3     # score ≥ this but < NOVEL → confirmation band
# score < CONFIRM → duplicate

# Signal weights (sum to 1.0)
W_TERMS = 0.50    # search_terms overlap is strongest signal
W_TITLE = 0.35    # title trigram similarity
W_MENTOR = 0.15   # mentor saturation


# ============================================================
# SIGNAL 1: Search Terms Overlap
# ============================================================

def load_search_terms_index() -> dict[str, set[str]]:
    """Build index: search_term → set of note slugs that reference it.

    Reads frontmatter of all notes to find search_terms fields.
    Also reads Search Terms/ folder to find all known terms.
    """
    term_to_notes: dict[str, set[str]] = {}

    # Scan all markdown files for search_terms in frontmatter
    for md_file in VAULT_INNER.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Quick frontmatter extraction
        if not content.startswith("---"):
            continue
        end = content.find("\n---", 3)
        if end == -1:
            continue
        fm = content[3:end]

        slug = md_file.stem
        # Find search_terms entries
        in_terms = False
        for line in fm.split("\n"):
            stripped = line.strip()
            if stripped.startswith("search_terms:"):
                in_terms = True
                continue
            if in_terms:
                if stripped.startswith("- "):
                    # Extract term from [[wikilink]] or plain text
                    m = re.search(r'\[\[([^\]]+)\]\]', stripped)
                    if m:
                        term = m.group(1).lower().strip()
                    else:
                        term = stripped[2:].strip().strip('"\'').lower()
                    if term:
                        term_to_notes.setdefault(term, set()).add(slug)
                elif not stripped.startswith("#") and stripped and not stripped.startswith("-"):
                    in_terms = False

    return term_to_notes


def score_terms_overlap(
    proposed_terms: list[str],
    term_index: dict[str, set[str]],
) -> tuple[float, list[dict]]:
    """Score how much the proposed terms overlap with existing vault coverage.

    Returns (novelty_score, details).
    novelty_score: 1.0 = all terms are new; 0.0 = all terms already heavily covered.
    """
    if not proposed_terms:
        return 1.0, [{"term": "(none)", "status": "no terms provided"}]

    details = []
    total_novelty = 0.0

    for term in proposed_terms:
        term_lower = term.lower().strip()
        notes = term_index.get(term_lower, set())
        count = len(notes)

        if count == 0:
            # Completely new term — maximum novelty
            novelty = 1.0
            status = "new"
        elif count <= 3:
            # Lightly covered — still novel
            novelty = 0.8
            status = "light"
        elif count <= 10:
            # Moderately covered — some novelty
            novelty = 0.5
            status = "moderate"
        elif count <= 20:
            # Well covered — low novelty
            novelty = 0.25
            status = "saturated"
        else:
            # Heavily covered — very low novelty
            novelty = 0.1
            status = "oversaturated"

        details.append({
            "term": term,
            "existing_notes": count,
            "status": status,
            "novelty": novelty,
        })
        total_novelty += novelty

    avg_novelty = total_novelty / len(proposed_terms)
    return avg_novelty, details


# ============================================================
# SIGNAL 2: Title Similarity (trigram overlap)
# ============================================================

def trigrams(text: str) -> set[str]:
    """Generate character trigrams from normalized text."""
    t = text.lower().strip()
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t)
    if len(t) < 3:
        return {t}
    return {t[i:i+3] for i in range(len(t) - 2)}


def score_title_similarity(
    proposed_title: str,
    entities: dict[str, dict],
    note_types: set[str] | None = None,
) -> tuple[float, list[dict]]:
    """Find the most similar existing titles using trigram overlap.

    Returns (novelty_score, top_matches).
    novelty_score: 1.0 = no similar title exists; 0.0 = exact duplicate.
    """
    proposed_tri = trigrams(proposed_title)
    if not proposed_tri:
        return 1.0, []

    similarities = []
    seen_slugs: set[str] = set()
    # entities is a dict keyed by both slug and title, each pointing to the
    # same record dict — iterate .values() (not the dict itself, which
    # would iterate keys/strings) and dedupe by slug since a record is
    # reachable through two keys.
    for ent in entities.values():
        if note_types and ent.get("type") not in note_types:
            continue
        slug = ent["slug"]
        if slug in seen_slugs:
            continue
        slug_tri = trigrams(slug)
        if not slug_tri:
            continue

        # Jaccard similarity
        intersection = proposed_tri & slug_tri
        union = proposed_tri | slug_tri
        sim = len(intersection) / len(union) if union else 0.0

        if sim > 0.15:  # Only track meaningful similarities
            seen_slugs.add(slug)
            similarities.append({
                "slug": slug,
                "type": ent.get("type", "?"),
                "similarity": round(sim, 3),
            })

    similarities.sort(key=lambda x: -x["similarity"])
    top = similarities[:5]

    if not top:
        return 1.0, []

    max_sim = top[0]["similarity"]
    # Convert similarity to novelty: novelty = 1 - max_similarity
    novelty = max(0.0, 1.0 - max_sim)
    return novelty, top


# ============================================================
# SIGNAL 3: Mentor Saturation
# ============================================================

def load_mentor_counts() -> dict[str, int]:
    """Count Literature Notes per mentor."""
    mentor_counts: dict[str, int] = Counter()

    ln_dir = VAULT_INNER / "Literature Notes"
    if not ln_dir.exists():
        return dict(mentor_counts)

    for md_file in ln_dir.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not content.startswith("---"):
            continue
        end = content.find("\n---", 3)
        if end == -1:
            continue
        fm = content[3:end]

        for line in fm.split("\n"):
            stripped = line.strip()
            if stripped.startswith("mentor:"):
                m = re.search(r'\[\[([^\]]+)\]\]', stripped)
                if m:
                    mentor_counts[m.group(1).lower()] += 1
                break

    return dict(mentor_counts)


def score_mentor_saturation(
    mentor: str | None,
    mentor_counts: dict[str, int],
) -> tuple[float, dict]:
    """Score how saturated a mentor is in the vault.

    Returns (novelty_score, details).
    More LNs from this mentor = lower novelty (diminishing returns).
    """
    if not mentor:
        return 0.8, {"mentor": "(none)", "ln_count": 0, "status": "no mentor specified"}

    mentor_lower = mentor.lower().strip()
    count = mentor_counts.get(mentor_lower, 0)

    if count == 0:
        novelty = 1.0
        status = "new mentor"
    elif count <= 5:
        novelty = 0.8
        status = "lightly covered"
    elif count <= 15:
        novelty = 0.6
        status = "moderately covered"
    elif count <= 30:
        novelty = 0.4
        status = "well covered"
    else:
        novelty = 0.2
        status = "heavily covered"

    return novelty, {
        "mentor": mentor,
        "ln_count": count,
        "status": status,
        "novelty": novelty,
    }


# ============================================================
# COMPOSITE EVALUATION
# ============================================================

def evaluate(
    title: str,
    terms: list[str],
    mentor: str | None = None,
    note_type: str = "inbox",
) -> dict:
    """Run full SurpriseFilter evaluation.

    Returns a dict with:
      - novelty_score (0.0-1.0)
      - band: "novel" | "confirmation" | "duplicate"
      - recommendation: what to do
      - signals: breakdown of each signal
    """
    # Load data
    entities = load_entities()
    term_index = load_search_terms_index()
    mentor_counts = load_mentor_counts()

    # Score each signal
    terms_score, terms_details = score_terms_overlap(terms, term_index)

    # For title similarity, compare against relevant note types
    relevant_types = {"inbox", "literature", "permanent", "case", "fleeting"}
    title_score, title_matches = score_title_similarity(
        title, entities, relevant_types
    )

    mentor_score, mentor_details = score_mentor_saturation(mentor, mentor_counts)

    # Weighted composite
    composite = (
        W_TERMS * terms_score +
        W_TITLE * title_score +
        W_MENTOR * mentor_score
    )
    composite = round(composite, 3)

    # Classify band
    if composite >= NOVEL_THRESHOLD:
        band = "novel"
        recommendation = "Proceed with ingestion — this content brings new knowledge to the vault."
    elif composite >= CONFIRM_THRESHOLD:
        band = "confirmation"
        # Find what it reinforces
        existing_refs = []
        for td in terms_details:
            if td["status"] in ("moderate", "saturated", "oversaturated"):
                existing_refs.append(td["term"])
        for tm in title_matches[:2]:
            existing_refs.append(tm["slug"])

        recommendation = (
            f"This content overlaps with existing vault knowledge. "
            f"Consider linking to existing notes instead of creating a new one. "
            f"Overlaps with: {', '.join(existing_refs[:5])}"
        )
    else:
        band = "duplicate"
        closest = title_matches[0]["slug"] if title_matches else "(unknown)"
        recommendation = (
            f"Near-duplicate detected. Most similar: '{closest}'. "
            f"Ask the user before creating — this may already be captured."
        )

    return {
        "novelty_score": composite,
        "band": band,
        "recommendation": recommendation,
        "thresholds": {
            "novel": NOVEL_THRESHOLD,
            "confirmation": CONFIRM_THRESHOLD,
        },
        "signals": {
            "terms": {
                "score": round(terms_score, 3),
                "weight": W_TERMS,
                "weighted": round(W_TERMS * terms_score, 3),
                "details": terms_details,
            },
            "title": {
                "score": round(title_score, 3),
                "weight": W_TITLE,
                "weighted": round(W_TITLE * title_score, 3),
                "top_matches": title_matches,
            },
            "mentor": {
                "score": round(mentor_score, 3),
                "weight": W_MENTOR,
                "weighted": round(W_MENTOR * mentor_score, 3),
                "details": mentor_details,
            },
        },
    }


# ============================================================
# STATS command
# ============================================================

def cmd_stats() -> None:
    """Show vault coverage stats relevant to surprise evaluation."""
    term_index = load_search_terms_index()
    mentor_counts = load_mentor_counts()
    entities = load_entities()
    # entities.json maps both slug and title to the same record: iterate the
    # values and dedupe by slug (iterating the dict itself yields key strings).
    unique = {e["slug"]: e for e in entities.values() if isinstance(e, dict) and "slug" in e}

    type_counts = Counter(e.get("type", "?") for e in unique.values())

    print(f"\nVault SurpriseFilter Stats")
    print("=" * 60)
    print(f"  Total entities:     {len(unique)}")
    print(f"  Unique terms:       {len(term_index)}")
    print(f"  Unique mentors:     {len(mentor_counts)}")

    print(f"\n  Note types:")
    for t, n in type_counts.most_common(10):
        print(f"    {t:20s} {n:>5}")

    # Term coverage histogram
    term_sizes = [len(notes) for notes in term_index.values()]
    if term_sizes:
        bins = {"1 note": 0, "2-5": 0, "6-10": 0, "11-20": 0, "20+": 0}
        for s in term_sizes:
            if s == 1: bins["1 note"] += 1
            elif s <= 5: bins["2-5"] += 1
            elif s <= 10: bins["6-10"] += 1
            elif s <= 20: bins["11-20"] += 1
            else: bins["20+"] += 1
        print(f"\n  Term coverage distribution:")
        for label, n in bins.items():
            print(f"    {label:10s} {n:>4} terms")

    # Top mentors
    if mentor_counts:
        print(f"\n  Top 10 mentors by LN count:")
        for name, count in sorted(mentor_counts.items(), key=lambda x: -x[1])[:10]:
            sat = "🔴" if count > 30 else "🟡" if count > 15 else "🟢"
            print(f"    {sat} {name:30s} {count:>3} LNs")


# ============================================================
# CLI
# ============================================================

def cmd_evaluate(args: argparse.Namespace) -> None:
    terms = [t.strip() for t in args.terms.split(",") if t.strip()] if args.terms else []

    result = evaluate(
        title=args.title,
        terms=terms,
        mentor=args.mentor,
        note_type=args.type or "inbox",
    )

    # Colored band indicator
    band_icon = {
        "novel": "🟢 NOVEL",
        "confirmation": "🟡 CONFIRMATION",
        "duplicate": "🔴 DUPLICATE",
    }

    print(f"\n{'=' * 60}")
    print(f"SurpriseFilter Evaluation")
    print(f"{'=' * 60}")
    print(f"  Title: {args.title}")
    print(f"  Terms: {', '.join(terms) if terms else '(none)'}")
    print(f"  Mentor: {args.mentor or '(none)'}")
    print(f"\n  Novelty Score: {result['novelty_score']:.3f}")
    print(f"  Band: {band_icon.get(result['band'], result['band'])}")
    print(f"\n  {result['recommendation']}")

    print(f"\n  Signal Breakdown:")
    s = result["signals"]
    print(f"    Terms:  {s['terms']['score']:.2f} × {s['terms']['weight']} = {s['terms']['weighted']:.3f}")
    for td in s["terms"]["details"]:
        icon = "🆕" if td["status"] == "new" else "📗" if td["status"] == "light" else "📙" if td["status"] == "moderate" else "📕"
        count = td.get("existing_notes", 0)
        print(f"      {icon} {td['term']} — {td['status']} ({count} notes)")

    print(f"    Title:  {s['title']['score']:.2f} × {s['title']['weight']} = {s['title']['weighted']:.3f}")
    for tm in s["title"]["top_matches"][:3]:
        print(f"      ↔ {tm['slug'][:60]} (sim={tm['similarity']:.3f}, {tm['type']})")

    print(f"    Mentor: {s['mentor']['score']:.2f} × {s['mentor']['weight']} = {s['mentor']['weighted']:.3f}")
    md = s["mentor"]["details"]
    print(f"      {md.get('mentor', '?')} — {md.get('status', '?')} ({md.get('ln_count', 0)} LNs)")

    if args.json:
        print(f"\n--- JSON ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # evaluate
    p_eval = sub.add_parser("evaluate", help="Evaluate novelty of incoming content")
    p_eval.add_argument("--title", required=True, help="Proposed note title")
    p_eval.add_argument("--terms", default="", help="Comma-separated search terms")
    p_eval.add_argument("--mentor", default=None, help="Author/mentor name")
    p_eval.add_argument("--type", default="inbox", help="Note type: inbox, case, fleeting")
    p_eval.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # stats
    sub.add_parser("stats", help="Show vault coverage stats")

    args = parser.parse_args()

    if args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "stats":
        cmd_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
