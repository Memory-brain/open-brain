#!/usr/bin/env python3
"""
extension_islands.py — closes the "Your extension as an island" gap that
open-brain-extract v10.12 and open-brain-escribir v3 cannot cover on their own:
the user filling in `## Your extension` of a Literature Note by hand in
Obsidian, without going through a careo or the writing skill.

Sweeps `Literature Notes/*.md`, finds those whose `## Your extension` has real
content (not the `<!-- ... -->` placeholder) and, if no linked island Fleeting
exists yet for that LN, creates one:

  Fleeting Notes/Island — {LN title} — extension — YYYY-MM-DD.md
  ---
  type: fleeting
  island: true
  origin: extension
  lns_touched: ["[[LN]]"]
  created: YYYY-MM-DD
  ---
  {verbatim text of Your extension}

The legacy heading `## Tu extensión` is still read. It does not edit the LN.
It does not rewrite an island that already exists (idempotent: it checks
`lns_touched` of the `origin: extension` Fleetings already present, whatever
their filename prefix, `Island — ` or legacy `Isla — `). Meant to run weekly
alongside `archipelago.py`, or by hand when needed.

Command:
  python3 extension_islands.py [--json] [--dry-run]

--dry-run writes nothing, it only reports what it would create.
Vault root: OPEN_BRAIN_VAULT or VAULT_ROOT if set, otherwise autodetected.
"""

# `X | None` in annotations is 3.10+; on Python 3.9 the module would crash at
# import. With this future import annotations are not evaluated.
from __future__ import annotations

import os
import re
import sys
import json
import glob
import datetime
from pathlib import Path

VAULT_MARKERS = ("Permanent Notes", "Literature Notes")
EXCLUDE_SEGMENTS = ("backups-", "_to_delete", ".git", "node_modules")


def find_vault() -> Path | None:
    for k in ("OPEN_BRAIN_VAULT", "VAULT_ROOT"):
        env = os.environ.get(k)
        if env and Path(env).exists():
            return Path(env)
    here = Path(__file__).resolve()
    for ancestor in [here.parent, *here.parents]:
        if all((ancestor / m).is_dir() for m in VAULT_MARKERS):
            if not any(seg in str(ancestor) for seg in EXCLUDE_SEGMENTS):
                return ancestor
    return None


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"\[\[|\]\]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


# Marks that a line was written by an automated pass, not by the user.
# Maintenance sweeps can leave annotations (e.g. "Near-duplicate detected
# (Action 8, Second pass YYYY-MM-DD)") *below* `## Your extension`, after the
# placeholder and a `---` rule. Without this filter `archipelago.py` would group
# them as the user's own writing. Spanish forms are kept for legacy vaults.
MACHINE_MARKS = re.compile(
    r"Casi-duplicado detectado|Near-duplicate detected"
    r"|\(Acción \d+|\(Action \d+"
    r"|Segunda pasada \d{4}-\d{2}-\d{2}|Second pass \d{4}-\d{2}-\d{2}"
    r"|Sesión \d{4}-\d{2}-\d{2}|Session \d{4}-\d{2}-\d{2}",
    re.I,
)

# Heading of the user's section in an LN; legacy Spanish heading accepted.
EXTENSION_RE = re.compile(
    r"^## (?:Your extension|Tu extensión)\s*\n(.*?)(?=\n## |\Z)", re.S | re.M)


def owner_lines(body: str) -> list[str]:
    """Filters `## Your extension` down to what the user plausibly wrote.

    Dropped: the HTML placeholder, horizontal rules separating the section from
    whatever a sweep appended after it, `>` quote blocks (Claude's marked voice
    in the three-voice contract: by definition not the user) and lines carrying
    a session or action mark from an automated pass.
    """
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    keep = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            continue
        if stripped.startswith(">"):
            continue
        if MACHINE_MARKS.search(stripped):
            continue
        keep.append(line.rstrip())
    return keep


def real_extension_text(text: str) -> str | None:
    """Returns the real text of `## Your extension`, or None if it is empty, only
    has the placeholder HTML comment, or everything below it was written by an
    automated pass (see `owner_lines`)."""
    m = EXTENSION_RE.search(text)
    if not m:
        return None
    keep = owner_lines(m.group(1))
    return "\n".join(keep).strip() or None



def ln_domains(text: str) -> list[str]:
    """`domains` from the LN's frontmatter, inherited by the island.

    `archipelago.py` groups by touched LN, domain, search term or autolink edge.
    If islands were born with `lns_touched` only, one of the grouper's four
    signals would be empty by construction, not for lack of material. The
    domain is already written in the LN the island comes from.
    """
    fm = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not fm:
        return []
    block = re.search(r"^domains:\n((?:\s+-.*\n)+)", fm.group(1) + "\n", re.M)
    if not block:
        return []
    out = []
    for line in block.group(1).splitlines():
        v = line.strip()[1:].strip().strip('"\'')
        if v:
            out.append(v)
    return out


def existing_extension_lns(vault: Path) -> set[str]:
    """LNs (by wikilink, without brackets) that already have an island Fleeting
    with origin: extension."""
    covered = set()
    for path in glob.glob(str(vault / "Fleeting Notes" / "*.md")):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        fm_m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not fm_m:
            continue
        fm_raw = fm_m.group(1)
        if not re.search(r"^origin:\s*extension\s*$", fm_raw, re.M):
            continue
        block = re.search(r"^lns_touched:\n((?:\s+-.*\n)+)", fm_raw, re.M)
        if block:
            for line in block.group(1).splitlines():
                ln = line.strip("- \n").strip('"')
                ln = re.sub(r"^\[\[|\]\]$", "", ln)
                covered.add(ln)
    return covered


def main():
    as_json = "--json" in sys.argv
    dry_run = "--dry-run" in sys.argv

    vault = find_vault()
    if vault is None:
        print(json.dumps({"error": "vault not found"}) if as_json else "Vault not found — set OPEN_BRAIN_VAULT")
        sys.exit(1)

    covered = existing_extension_lns(vault)
    today = datetime.date.today().isoformat()

    created = []
    skipped_placeholder = 0
    skipped_machine_only = 0
    skipped_covered = 0

    for path in glob.glob(str(vault / "Literature Notes" / "*.md")):
        ln_title = Path(path).stem
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        ext_text = real_extension_text(text)
        if ext_text is None:
            # Distinguish "never written" from "what is there was written by an
            # automated pass": the latter is a defect that must be countable
            # from one run to the next, not background noise.
            raw = EXTENSION_RE.search(text)
            if raw and re.sub(r"<!--.*?-->", "", raw.group(1), flags=re.S).strip():
                skipped_machine_only += 1
            else:
                skipped_placeholder += 1
            continue
        if ln_title in covered:
            skipped_covered += 1
            continue

        out_name = f"Island — {ln_title} — extension — {today}.md"
        out_path = vault / "Fleeting Notes" / out_name
        domains = ln_domains(text)
        dom_block = ("domains:\n" + "".join(f'  - "{d}"\n' for d in domains)) if domains else ""
        note = (
            "---\n"
            "type: fleeting\n"
            "island: true\n"
            "origin: extension\n"
            "lns_touched:\n"
            f'  - "[[{ln_title}]]"\n'
            + dom_block +
            f"created: {today}\n"
            "---\n\n"
            f"{ext_text}\n"
        )
        created.append({"ln": ln_title, "island_path": str(out_path), "domains": domains})
        if not dry_run:
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(note)
            except PermissionError:
                os.chmod(out_path, 0o644)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(note)

    result = {
        "date": today,
        "dry_run": dry_run,
        "islands_created": len(created),
        "created": created,
        "lns_skipped_placeholder_or_empty": skipped_placeholder,
        "lns_skipped_machine_only": skipped_machine_only,
        "lns_skipped_already_covered": skipped_covered,
    }

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    verb = "Would create" if dry_run else "Created"
    print(f"# Extension islands — {today}\n")
    print(f"{verb} {len(created)} island Fleeting(s) from `Your extension`.")
    for c in created:
        print(f"- {c['ln']} → {Path(c['island_path']).name}")
    print(f"\nLNs with no real extension yet (placeholder or empty): {skipped_placeholder}.")
    print(f"LNs whose extension only has machine text (filtered by authorship): {skipped_machine_only}.")
    print(f"LNs with a real extension already covered by an earlier island: {skipped_covered}.")


if __name__ == "__main__":
    main()
