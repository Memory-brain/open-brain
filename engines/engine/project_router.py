#!/usr/bin/env python3
"""
project_router.py — Deterministic project routing for Open Brain vault.

Shared engine that any skill calls BEFORE writing an output file.
Discovers projects generically: every folder under Projects/Active/ is a project
(no project names are hardcoded). Builds a keyword index from each project's
README.md (frontmatter tags/area + the start of the body), its folder name and
its file names,
and returns the best-matching project path (or "zettelkasten" if the file
belongs to the global knowledge base rather than a specific project).

Usage:
    python3 engine/project_router.py --vault /path/to/vault --query "Acme onboarding presentation"
    python3 engine/project_router.py --vault /path/to/vault --query "literature note about mental models"
    python3 engine/project_router.py --list        # vault from OPEN_BRAIN_VAULT

Output (JSON):
    {"match": "Acme", "path": "Projects/Active/Acme", "confidence": "high", "reason": "..."}
    {"match": null, "path": "zettelkasten", "confidence": "high", "reason": "Pure knowledge note — not project-scoped"}

Exit codes:
    0 = match found or explicit zettelkasten routing
    1 = error (bad args, vault not found)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ── Zettelkasten folders: files here are NEVER project-routed ──────────────
ZETTELKASTEN_FOLDERS = {
    "literature notes", "permanent notes", "search terms", "fleeting notes",
    "mentors", "dossiers", "sources", "archive", "domains",
}

# ── Stop words (Spanish + English): ignored during keyword matching ────────
STOP_WORDS = {
    "para", "de", "la", "el", "un", "una", "los", "las", "del", "al",
    "con", "por", "que", "en", "es", "se", "no", "lo", "como", "más",
    "pero", "sus", "le", "ya", "sin", "sobre", "este", "entre", "cuando",
    "muy", "también", "fue", "ser", "tiene", "esto", "desde", "todo",
    "esta", "son", "uno", "hay", "aquí", "the", "and", "for", "with",
    "from", "that", "this", "are", "not", "can", "has", "was", "but",
    "all", "its", "into", "than", "then", "them", "been", "have", "will",
    "each", "which", "their", "said", "about", "would", "make", "like",
}

# ── Keywords that signal a file is an output/deliverable (project-routable) ─
OUTPUT_SIGNALS = [
    "plan", "roadmap", "audit", "design", "prototype", "spec", "prd",
    "one-pager", "presentation", "deck", "proposal", "handoff", "brief",
    "report", "talk", "course", "post", "article", "doc", "demo", "prompt",
    "rewrite", "migration", "refactor", "v2", "v3", "v4", "draft",
    "mini-roadmap", "metrics", "ui", "ux", "onboarding",
]


def load_projects(vault_root: Path) -> list[dict]:
    """Scan Projects/Active/ and build a keyword index per project."""
    projects_dir = vault_root / "Projects" / "Active"
    if not projects_dir.is_dir():
        return []

    projects = []
    for entry in sorted(projects_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        project = {
            "name": entry.name,
            "path": f"Projects/Active/{entry.name}",
            "keywords": set(),
            "tags": set(),
        }

        # Keywords from folder name
        for token in re.split(r"[\s\-_]+", entry.name.lower()):
            if len(token) > 2 and token not in STOP_WORDS:
                project["keywords"].add(token)

        # Keywords from README.md frontmatter tags + body
        readme = entry / "README.md"
        if readme.is_file():
            text = readme.read_text(encoding="utf-8", errors="replace")

            # Extract tags from frontmatter
            fm_match = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if fm_match:
                fm = fm_match.group(1)
                tag_match = re.search(r"tags:\s*\[([^\]]+)\]", fm)
                if tag_match:
                    for tag in tag_match.group(1).split(","):
                        tag = tag.strip().strip("'\"").lower()
                        project["tags"].add(tag)
                        for t in re.split(r"[\s\-_]+", tag):
                            if len(t) > 2:
                                project["keywords"].add(t)

                # Extract area
                area_match = re.search(r"area:\s*(\S+)", fm)
                if area_match:
                    project["keywords"].add(area_match.group(1).lower())

            # Keywords from first 500 chars of body (after frontmatter)
            body = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", text, count=1, flags=re.DOTALL)
            for token in re.split(r"[^a-záéíóúñü\w]+", body[:500].lower()):
                if len(token) > 3 and token not in STOP_WORDS:
                    project["keywords"].add(token)

        # Keywords from all filenames in the project
        for f in entry.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".html", ".docx", ".pptx"):
                for token in re.split(r"[\s\-_\.]+", f.stem.lower()):
                    if len(token) > 3 and token not in STOP_WORDS:
                        project["keywords"].add(token)

        projects.append(project)

    return projects


def is_zettelkasten_note(query: str) -> bool:
    """Check if the query describes a pure knowledge note (not project-scoped)."""
    q = query.lower()
    zettelkasten_signals = [
        "literature note", "permanent note", "search term", "fleeting note",
        "mentor", "dossier", "source note", "ln -", "pn -", "extract from",
        "book note", "concept:", "principle:", "mental model",
    ]
    return any(signal in q for signal in zettelkasten_signals)


def score_project(project: dict, query_tokens: set[str], query_lower: str) -> tuple[int, str]:
    """Score how well a project matches the query. Returns (score, reason)."""
    score = 0
    reasons = []

    # Direct name match (strongest signal)
    name_lower = project["name"].lower()
    if name_lower in query_lower or any(
        t in query_lower for t in re.split(r"[\s\-_]+", name_lower) if len(t) > 3
    ):
        score += 10
        reasons.append(f"project name '{project['name']}' matches query")

    # Tag match
    tag_hits = project["tags"] & query_tokens
    if tag_hits:
        score += 5 * len(tag_hits)
        reasons.append(f"tags match: {', '.join(tag_hits)}")

    # Keyword overlap
    kw_hits = project["keywords"] & query_tokens
    if kw_hits:
        score += 2 * len(kw_hits)
        reasons.append(f"keywords match: {', '.join(sorted(kw_hits)[:5])}")

    return score, "; ".join(reasons) if reasons else "no match"


def route(vault_root: Path, query: str) -> dict:
    """Main routing logic. Returns a routing decision as dict."""

    # Step 1: Check if it's a pure Zettelkasten note
    if is_zettelkasten_note(query):
        return {
            "match": None,
            "path": "zettelkasten",
            "confidence": "high",
            "reason": "Pure knowledge note — route to standard Zettelkasten folder",
        }

    # Step 2: Check for output signals
    q_lower = query.lower()
    has_output_signal = any(s in q_lower for s in OUTPUT_SIGNALS)

    # Step 3: Load and score projects
    projects = load_projects(vault_root)
    if not projects:
        return {
            "match": None,
            "path": "zettelkasten",
            "confidence": "low",
            "reason": "No active projects found in vault",
        }

    query_tokens = set()
    for token in re.split(r"[^a-záéíóúñü\w]+", q_lower):
        if len(token) > 2 and token not in STOP_WORDS:
            query_tokens.add(token)

    scored = []
    for p in projects:
        s, reason = score_project(p, query_tokens, q_lower)
        scored.append((s, p, reason))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_project, best_reason = scored[0]

    # Step 4: Decision thresholds
    if best_score >= 10:
        confidence = "high"
    elif best_score >= 5 and has_output_signal:
        confidence = "medium"
    elif best_score >= 3 and has_output_signal:
        confidence = "low"
    else:
        # No strong match — check if it has output signals (might need a new project)
        if has_output_signal:
            return {
                "match": None,
                "path": "ask_user",
                "confidence": "none",
                "reason": "File looks like a project output but no project matched. "
                         "Ask user which project this belongs to, or create a new one.",
                "candidates": [p["name"] for _, p, _ in scored[:3]],
            }
        return {
            "match": None,
            "path": "zettelkasten",
            "confidence": "medium",
            "reason": "No project match and no output signals — likely a knowledge note",
        }

    return {
        "match": best_project["name"],
        "path": best_project["path"],
        "confidence": confidence,
        "reason": best_reason,
    }


def list_projects(vault_root: Path) -> list[dict]:
    """List all active projects with their keywords."""
    projects = load_projects(vault_root)
    return [
        {
            "name": p["name"],
            "path": p["path"],
            "tags": sorted(p["tags"]),
            "keyword_count": len(p["keywords"]),
        }
        for p in projects
    ]


def main():
    parser = argparse.ArgumentParser(description="Route files to vault projects")
    parser.add_argument("--vault", default=os.environ.get("OPEN_BRAIN_VAULT"),
                        help="Path to the vault root (default: $OPEN_BRAIN_VAULT)")
    parser.add_argument("--query", help="Description of file to route")
    parser.add_argument("--list", action="store_true", help="List active projects")
    args = parser.parse_args()

    if not args.vault:
        print(json.dumps({"error": "No vault given: pass --vault or set OPEN_BRAIN_VAULT"}), file=sys.stderr)
        sys.exit(1)
    vault_root = Path(args.vault)
    if not vault_root.is_dir():
        print(json.dumps({"error": f"Vault not found: {vault_root}"}), file=sys.stderr)
        sys.exit(1)

    if args.list:
        result = list_projects(vault_root)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.query:
        result = route(vault_root, args.query)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
