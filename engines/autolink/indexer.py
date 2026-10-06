#!/usr/bin/env python3
"""
Open Brain — Autolink Indexer
Reads all vault notes and builds entities.json: slug → {type, domains, title, aliases}.
Run from autolink/ directory: python3 indexer.py
"""
import os, re, json, pathlib, unicodedata

# Vault root: $OPEN_BRAIN_VAULT if set, otherwise the parent of this autolink/ folder.
VAULT = pathlib.Path(os.environ.get("OPEN_BRAIN_VAULT") or pathlib.Path(__file__).resolve().parent.parent)
# Directories whose notes are graph entities (and edge sources).
# Conceptual source of truth: vaultscan.KNOWLEDGE_DIRS + CAPTURE_DIRS, plus
# "Search Terms".
#
# "Search Terms", "Domains", "Playbooks", "Sources", "Ideas" and "Fleeting Notes"
# must stay in this list: autolink.py drops every link whose target is not in
# entities.json, so a missing directory turns all links into it into "broken"
# links that never reach the graph.
# The TERMINAL_DIRS (Projects, Manuscripts, Published, Research) are left out on
# purpose: they add almost no edges and are outputs, not knowledge.
NOTE_DIRS = [
    "Permanent Notes",
    "Literature Notes",
    "Cases",
    "Dossiers",
    "Domains",
    "Mentors",
    "Playbooks",
    "Areas",
    "Sources",
    "Inbox",
    "Ideas",
    "Fleeting Notes",
    "Search Terms",
]
OUT = pathlib.Path(__file__).parent / "entities.json"

LAYER_RE = re.compile(r"^layer:\s*(.+)$", re.MULTILINE)
DOMAIN_RE = re.compile(r'\[\[([^\]]+)\]\]')
TYPE_RE = re.compile(r"^type:\s*(.+)$", re.MULTILINE)
ALIAS_RE = re.compile(r"^aliases?:\s*\[?([^\]\n]+)\]?", re.MULTILINE)

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

def parse_note(path: pathlib.Path):
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    # Extract frontmatter
    fm = ""
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            fm = raw[3:end]

    note_type = "unknown"
    tm = TYPE_RE.search(fm)
    if tm:
        note_type = tm.group(1).strip().strip('"')

    # Infer type from directory if not in frontmatter
    parts = path.parts
    if "Permanent Notes" in parts:
        note_type = "permanent"
    elif "Literature Notes" in parts:
        note_type = "literature"
    elif "Cases" in parts:
        note_type = "case"
    elif "Mentors" in parts:
        note_type = "mentor"
    elif "Inbox" in parts:
        note_type = "inbox"
    elif "Dossiers" in parts:
        note_type = "dossier"

    # Domains
    domains_raw = re.search(r"^domains:(.*?)(?=^\w|\Z)", fm, re.MULTILINE | re.DOTALL)
    domains = []
    if domains_raw:
        domains = [m.strip().strip('"') for m in DOMAIN_RE.findall(domains_raw.group(1))]

    # Aliases
    aliases = []
    am = ALIAS_RE.search(fm)
    if am:
        aliases = [a.strip().strip('"') for a in am.group(1).split(",") if a.strip()]

    title = path.stem
    slug = slugify(title)

    return {
        "slug": slug,
        "title": title,
        "type": note_type,
        "domains": domains,
        "aliases": aliases,
        "path": str(path.relative_to(VAULT)),
    }

def main():
    if not VAULT.is_dir():
        raise SystemExit(f"Vault not found: {VAULT} (set OPEN_BRAIN_VAULT)")
    entities = {}
    total = 0
    for d in NOTE_DIRS:
        folder = VAULT / d
        if not folder.exists():
            continue
        for md in folder.rglob("*.md"):
            entity = parse_note(md)
            if entity:
                entities[entity["slug"]] = entity
                # Also index by title directly (for wikilink matching)
                entities[entity["title"]] = entity
                total += 1

    OUT.write_text(json.dumps(entities, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Indexed {total} notes → entities.json")

if __name__ == "__main__":
    main()
