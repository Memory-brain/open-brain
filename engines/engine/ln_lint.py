#!/usr/bin/env python3
"""
ln_lint.py — quality gate for open-brain-extract Literature Notes (v9.5).

Validates each LN against deterministic rules BEFORE it is written to the vault.
Catches mechanical errors the LLM makes systematically, without needing AI
judgment.

The AI keeps the judgment: deciding whether a WARN is acceptable, enriching
search_terms, improving the content. This script only detects mechanical
violations.

Commands:
  check <file.md>                         → lint one LN
  check-batch <folder/> --prefix XX       → lint every LN with that prefix
  check-batch <folder/> --since YYYY-MM-DD → lint LNs created since a date
  check-batch <folder/> --history          → also append the batch aggregate
  history [--limit N] [--scope X]          → pass-rate trend per batch

Severities:
  BLOCK — structurally broken, do not write to the vault
  WARN  — deficient but functional, report to the user
  INFO  — improvement suggestion, report only

Vault root: OPEN_BRAIN_VAULT (or VAULT_ROOT) if set, otherwise the nearest
ancestor of this file that looks like a vault.

Dependencies: pyyaml (pip install pyyaml --break-system-packages)
"""

# `dict | None` in annotations is 3.10+. On Python 3.9 a module-level variable
# annotation is evaluated at import time and crashes; with this future import
# annotations are lazy and the gate runs on 3.9 too.
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# --- safe import of yaml ---
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ---------------------------------------------------------------------------
# Frontmatter parsing (works with or without pyyaml)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Search Terms registry (for L05). Fail-open: if the vault cannot be found,
# L05 falls back to the old raw count and says so. This script is a PRE-write
# gate in the extract pipeline: it must not break because a folder is missing.
# ---------------------------------------------------------------------------

_REGISTRY: dict | None = None


def _load_term_registry() -> dict:
    """{'terms': set, 'hubs': set, 'found': bool}. Cached per process."""
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY
    base = None
    envs = [os.environ.get(k) for k in ("OPEN_BRAIN_VAULT", "VAULT_ROOT")]
    cands = [Path(e) for e in envs if e] + list(Path(__file__).resolve().parents)
    for c in cands:
        if (c / "Search Terms").is_dir():
            base = c
            break
    if base is None:
        _REGISTRY = {"terms": set(), "hubs": set(), "found": False}
        return _REGISTRY
    terms = {p.stem for p in (base / "Search Terms").rglob("*.md")}
    domains = {p.stem for p in (base / "Domains").rglob("*.md")} if (base / "Domains").is_dir() else set()
    hubs = {t for t in terms
            if any(o.startswith(t + " — ") or o.startswith(t + " - ") for o in terms)}
    _REGISTRY = {"terms": terms, "hubs": hubs | domains, "found": True}
    return _REGISTRY


def _extract_frontmatter(content: str) -> tuple[dict | None, str]:
    """
    Extract YAML frontmatter and body from a markdown file.
    Returns (frontmatter_dict, body_text). If no frontmatter, returns (None, content).
    """
    if not content.startswith("---"):
        return None, content

    # Find closing ---
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return None, content

    yaml_str = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3:]

    if HAS_YAML:
        try:
            fm = yaml.safe_load(yaml_str)
            return fm if isinstance(fm, dict) else None, body
        except yaml.YAMLError:
            return None, content
    else:
        # Fallback: regex-based extraction for critical fields
        fm = {}
        for line in yaml_str.strip().split("\n"):
            m = re.match(r'^(\w[\w_]*)\s*:\s*(.+)$', line.strip())
            if m:
                key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
                fm[key] = val
        # Handle search_terms as list
        terms = re.findall(r'- "?\[\[([^\]]+)\]\]"?', yaml_str)
        if terms:
            fm["search_terms"] = terms
        domains = []
        in_domains = False
        for line in yaml_str.split("\n"):
            if line.strip().startswith("domains:"):
                in_domains = True
                continue
            if in_domains:
                dm = re.match(r'\s+-\s+"?\[\[([^\]]+)\]\]"?', line)
                if dm:
                    domains.append(dm.group(1))
                elif not line.strip().startswith("-"):
                    in_domains = False
        if domains:
            fm["domains"] = domains
        return fm, body


# ---------------------------------------------------------------------------
# Lint rules
# ---------------------------------------------------------------------------

VALID_FEATURES = {
    "factual", "conceptual", "application",
    "decision", "diagnosis", "code-artifact"
}

# Legacy support — still accept old layer values during migration
VALID_LAYERS = {
    "knowledge", "compression", "mental-model",
    "application", "artifact", "decision", "diagnosis"
}

VALID_VOICE_STATES = {
    "author-only", "with-claude-connectors", "extended-by-owner",
}
# Legacy vaults used "extended-by-<name>"; any value with this prefix is
# accepted when reading.
LEGACY_VOICE_PREFIX = "extended-by-"

VOICE_LEAK_PATTERNS = [
    r"\bI think\b",
    r"\bIn my opinion\b",
    r"\bClaude suggests\b",
    r"\bClaude recommends\b",
    r"\bAs an AI\b",
    r"\bI believe\b",
    r"\bI would say\b",
]


class Violation:
    def __init__(self, rule_id: str, severity: str, message: str):
        self.rule_id = rule_id
        self.severity = severity  # BLOCK, WARN, INFO
        self.message = message

    def to_dict(self):
        return {
            "rule": self.rule_id,
            "severity": self.severity,
            "message": self.message,
        }

    def __str__(self):
        icon = {"BLOCK": "🚫", "WARN": "⚠️", "INFO": "ℹ️"}.get(self.severity, "?")
        return f"{icon} [{self.rule_id}] {self.message}"


def lint_file(filepath: Path) -> dict:
    """
    Lint a single Literature Note file.
    Returns a result dict with file, status, and violations.
    """
    content = filepath.read_text(encoding="utf-8", errors="replace")
    violations: list[Violation] = []

    # --- L01: YAML parseable ---
    fm, body = _extract_frontmatter(content)
    if fm is None:
        violations.append(Violation(
            "L01", "BLOCK", "Frontmatter YAML is missing or unparseable"
        ))
        # Can't check further rules without frontmatter
        return _result(filepath, violations)

    # --- L02: type: literature ---
    note_type = fm.get("type", "")
    if note_type != "literature":
        violations.append(Violation(
            "L02", "BLOCK", f"type should be 'literature', got '{note_type}'"
        ))

    # --- L03: source not empty, contains [[ ---
    source = str(fm.get("source", ""))
    if not source or "[[" not in source:
        violations.append(Violation(
            "L03", "BLOCK",
            f"source is missing or not a wikilink: '{source[:60]}'"
        ))

    # --- L04: mentor not empty, contains [[ ---
    mentor = str(fm.get("mentor", ""))
    if not mentor or "[[" not in mentor:
        violations.append(Violation(
            "L04", "BLOCK",
            f"mentor is missing or not a wikilink: '{mentor[:60]}'"
        ))

    # --- L05: >=3 SPECIFIC, RESOLVABLE search_terms ---------------------
    # This rule used to be `len(terms) >= 4`, counting strings. Almost every LN
    # passed it, so it measured nothing — and worse, it created the pressure that
    # produced the problem it meant to prevent. Any string satisfies a quota, so
    # it got met with the cheapest hub term that vaguely fit, or with an invented
    # term that resolves to no existing Search Term. Pure Goodhart: the quota is
    # met with whatever is cheapest, and the cheapest thing was noise.
    #
    # Now we count what actually retrieves: terms that EXIST in the registry and
    # are NOT hubs (a hub does not discriminate — it is the top of the tree, not
    # a signal). That way the cheapest way to meet the minimum becomes finding a
    # real specific term, which is exactly the behaviour we want.
    #
    # Expect a large share of a legacy vault to fail this at first; that is
    # backlog the old contract could not see, not a regression. The threshold
    # drops from 4 to 3 on purpose — three terms that resolve retrieve better
    # than six that do not. Without a registry (fail-open) the old raw count of
    # 4 is applied instead.
    terms = fm.get("search_terms", [])
    if not isinstance(terms, list):
        terms = []
    reg = _load_term_registry()
    names = [str(t).replace("[[", "").replace("]]", "").split("|")[0].strip()
             for t in terms]
    if not reg["found"]:
        # fail-open: without a registry resolvability cannot be judged
        if len(terms) < 4:
            violations.append(Violation(
                "L05", "WARN",
                f"search_terms has {len(terms)} items, minimum is 4 "
                f"(Search Terms registry not found: resolvability could not be "
                f"checked — set OPEN_BRAIN_VAULT)"
            ))
    else:
        unresolved = [n for n in names if n not in reg["terms"]]
        specific = [n for n in names if n in reg["terms"] and n not in reg["hubs"]]
        if len(specific) < 3:
            detail = f"{len(specific)} specific resolvable of {len(names)}"
            if unresolved:
                detail += f"; unresolved: {', '.join(unresolved[:4])}"
                if len(unresolved) > 4:
                    detail += f" (+{len(unresolved) - 4})"
            violations.append(Violation(
                "L05", "WARN",
                f"search_terms: {detail} — minimum 3 that exist in Search Terms/ "
                f"and are not hubs. A term that does not resolve leads to no hub; "
                f"a hub does not discriminate."
            ))

    # --- L06: domains >= 1 ---
    domains = fm.get("domains", [])
    if not isinstance(domains, list):
        domains = []
    if len(domains) < 1:
        violations.append(Violation(
            "L06", "BLOCK", "domains is empty, at least 1 required"
        ))

    # --- L07: features is valid (v10) or legacy layer is valid ---
    features = fm.get("features", None)
    layer = fm.get("layer", None)
    if features is not None:
        # v10 hybrid model: features is a list
        if not isinstance(features, list):
            violations.append(Violation(
                "L07", "BLOCK",
                f"features must be a list, got {type(features).__name__}"
            ))
        else:
            for f in features:
                if str(f).strip() not in VALID_FEATURES:
                    violations.append(Violation(
                        "L07", "BLOCK",
                        f"feature '{f}' not in valid set: {sorted(VALID_FEATURES)}"
                    ))
    elif layer is not None:
        # Legacy: single layer field (pre-v10 notes)
        if str(layer).strip() not in VALID_LAYERS:
            violations.append(Violation(
                "L07", "BLOCK",
                f"layer '{layer}' not in valid set: {sorted(VALID_LAYERS)}"
            ))
    else:
        violations.append(Violation(
            "L07", "BLOCK",
            "neither 'features' (v10) nor 'layer' (legacy) found in frontmatter"
        ))

    # --- L08: voice_state is valid ---
    voice = str(fm.get("voice_state", "")).strip()
    if voice and voice not in VALID_VOICE_STATES \
            and not voice.startswith(LEGACY_VOICE_PREFIX):
        violations.append(Violation(
            "L08", "WARN",
            f"voice_state '{voice}' not in valid set: {sorted(VALID_VOICE_STATES)}"
        ))

    # --- L09: ## Your extension section exists ---
    # (legacy heading "## Tu extensión" is still accepted)
    if not re.search(r"## (Your extension|Tu extensi[oó]n)", content):
        violations.append(Violation(
            "L09", "BLOCK", "'## Your extension' section is missing"
        ))

    # --- L10: Your extension is empty ---
    tu_ext_match = re.search(
        r"## (?:Your extension|Tu extensi[oó]n)\s*\n(.*?)(?=\n## |\Z)",
        content, re.DOTALL
    )
    if tu_ext_match:
        tu_ext_content = tu_ext_match.group(1).strip()
        # Remove HTML comments
        cleaned = re.sub(r"<!--.*?-->", "", tu_ext_content, flags=re.DOTALL).strip()
        if cleaned:
            violations.append(Violation(
                "L10", "WARN",
                "'Your extension' is pre-filled — should be empty on creation"
            ))

    # --- L11: Voice leak in body ---
    # Only check body (not frontmatter, not callouts)
    body_without_callouts = re.sub(
        r"> \[!claude\].*?(?=\n[^>]|\Z)", "", body, flags=re.DOTALL
    )
    for pattern in VOICE_LEAK_PATTERNS:
        if re.search(pattern, body_without_callouts, re.IGNORECASE):
            violations.append(Violation(
                "L11", "WARN",
                f"Possible voice leak in body: pattern '{pattern}' detected"
            ))
            break  # one warning is enough

    # --- L12: At least one literal quote ---
    has_quote = bool(re.search(r'>\s*"[^"]{10,}', body))
    if not has_quote:
        violations.append(Violation(
            "L12", "INFO", "No literal quote found (> \"...) — consider adding one"
        ))

    # --- L13: source_ref not empty ---
    source_ref = str(fm.get("source_ref", "")).strip()
    if not source_ref:
        violations.append(Violation(
            "L13", "WARN", "source_ref is empty — page/chapter reference missing"
        ))

    # --- L14: File not too long (multi-insight signal) ---
    if len(content) > 3000:
        violations.append(Violation(
            "L14", "WARN",
            f"File is {len(content)} chars (>3000) — may contain multiple insights"
        ))

    # --- L15: [!claude] callout present ---
    if "[!claude]" not in content:
        violations.append(Violation(
            "L15", "INFO", "No [!claude] connector callout found"
        ))

    # --- L16: created date format ---
    created = str(fm.get("created", "")).strip()
    if created:
        try:
            datetime.strptime(created, "%Y-%m-%d")
        except ValueError:
            violations.append(Violation(
                "L16", "WARN",
                f"created date '{created}' is not YYYY-MM-DD format"
            ))
    else:
        violations.append(Violation(
            "L16", "WARN", "created date is missing"
        ))

    # --- L17: description present and non-empty -------------------------
    # BLOCK class, the same status as L01 (unreadable frontmatter), and for the
    # same reason: an LN without `description` is not deficient, it is mute.
    # It is the field the template calls the dominant retrieval signal (above
    # the structured tags in A/B tests) and the one the careo gate requires
    # reading in order to cite what the note claims.
    #
    # Before this rule, LNs without the field passed the linter green: none of
    # the other 16 rules looked at it. The root cause was the template, not the
    # writer's judgment; the YAML block that gets copied literally now carries
    # `description: ""`. This rule is the dam that keeps the gap from refilling.
    description = str(fm.get("description", "") or "").strip()
    if not description:
        violations.append(Violation(
            "L17", "BLOCK",
            "description is missing or empty — it is the dominant retrieval "
            "signal: write a claim, not a topic"
        ))
    elif description.lower().startswith(("sobre ", "about ")):
        violations.append(Violation(
            "L17", "WARN",
            f"description looks like a label, not a claim: '{description[:60]}'"
        ))

    return _result(filepath, violations)


def _result(filepath: Path, violations: list[Violation]) -> dict:
    """Build a result dict from violations."""
    blocks = [v for v in violations if v.severity == "BLOCK"]
    warns = [v for v in violations if v.severity == "WARN"]

    if blocks:
        status = "BLOCK"
    elif warns:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "file": filepath.name,
        "path": str(filepath),
        "status": status,
        "violation_count": len(violations),
        "block_count": len(blocks),
        "warn_count": len(warns),
        "violations": [v.to_dict() for v in violations],
    }


# ---------------------------------------------------------------------------
# Batch lint
# ---------------------------------------------------------------------------

def lint_batch(folder: Path, prefix: str | None = None,
               since: str | None = None) -> dict:
    """Lint all .md files in a folder matching optional filters."""
    results = []
    files = sorted(folder.glob("*.md"))

    for f in files:
        # Filter by prefix
        if prefix and not f.name.startswith(prefix):
            # Also check for "XX - " pattern
            if not f.name.startswith(f"{prefix} -") and \
               not f.name.startswith(f"{prefix}-"):
                continue

        # Filter by creation date (from frontmatter)
        if since:
            content = f.read_text(encoding="utf-8", errors="replace")
            fm, _ = _extract_frontmatter(content)
            if fm and fm.get("created"):
                try:
                    created = datetime.strptime(str(fm["created"]), "%Y-%m-%d").date()
                    if created < datetime.strptime(since, "%Y-%m-%d").date():
                        continue
                except ValueError:
                    pass  # can't parse date, include it

        results.append(lint_file(f))

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    blocked = sum(1 for r in results if r["status"] == "BLOCK")

    return {
        "folder": str(folder),
        "prefix": prefix,
        "since": since,
        "total": total,
        "passed": passed,
        "warned": warned,
        "blocked": blocked,
        "results": results,
    }


# ---------------------------------------------------------------------------
# Aggregated history
#
# Without it each extraction is audited on its own, in a separate .md under
# `Resources/Vault Health/Extraction Audits/`. A one-off WARN and a worsening
# trend are then indistinguishable: there is no series to compare against.
# This ledger creates one — one JSON line per linted batch, with the pass-rate
# and the breakdown by rule.
#
# The linter's own hash is recorded too: a pass-rate is only comparable with
# another measured by the same instrument, and this file changes (adding a
# rule shifts the historical pass-rate at once).
# ---------------------------------------------------------------------------

HISTORY_PATH = "Resources/Vault Health/ln_lint_history.jsonl"


def lint_sha() -> str:
    """Short hash of the linter that produced the measurement."""
    import hashlib
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    except OSError:
        return "unknown"


def rule_counts(batch_result: dict) -> dict:
    """How many notes each rule fires on (a note counts once per rule)."""
    counts: dict[str, int] = {}
    for res in batch_result["results"]:
        seen = set()
        for v in res["violations"]:
            key = f"{v['rule']}:{v['severity']}"
            if key in seen:
                continue
            seen.add(key)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def history_row(batch_result: dict, scope: str, backfill: bool = False) -> dict:
    total = batch_result["total"] or 1
    return {
        "at": datetime.now().isoformat(timespec="seconds"),
        "scope": scope,
        "total": batch_result["total"],
        "pass": batch_result["passed"],
        "warn": batch_result["warned"],
        "block": batch_result["blocked"],
        "pass_rate": round(batch_result["passed"] / total, 4),
        "block_rate": round(batch_result["blocked"] / total, 4),
        "rules": rule_counts(batch_result),
        "lint_sha": lint_sha(),
        "backfill": backfill,
    }


def history_file(vault: Path | None = None) -> Path:
    root = vault or _vault_root()
    return (root / HISTORY_PATH) if root else Path(HISTORY_PATH)


def append_history(row: dict, vault: Path | None = None) -> Path:
    path = history_file(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def _vault_root() -> Path | None:
    for k in ("OPEN_BRAIN_VAULT", "VAULT_ROOT"):
        if os.environ.get(k):
            return Path(os.environ[k])
    here = Path(__file__).resolve()
    for anc in [here.parent, *here.parents]:
        if (anc / "Literature Notes").is_dir() and (anc / "Permanent Notes").is_dir():
            return anc
    return None


def print_history(limit: int = 20, scope: str | None = None) -> None:
    path = history_file()
    if not path.exists():
        print(f"No history yet ({path}). Run check-batch --history.")
        return
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if scope and scope not in r.get("scope", ""):
            continue
        rows.append(r)
    if not rows:
        print("No rows for that filter.")
        return
    print(f"\n📈 ln_lint — aggregated history ({len(rows)} batches, last {limit})\n")
    print(f"{'scope':<28} {'n':>6} {'pass':>7} {'block':>7}  top rule")
    prev = None
    for r in rows[-limit:]:
        top = max(r["rules"].items(), key=lambda kv: kv[1])[0] if r["rules"] else "—"
        delta = ""
        if prev is not None:
            d = r["pass_rate"] - prev
            delta = f" ({d:+.1%})"
        prev = r["pass_rate"]
        print(f"{r['scope'][:28]:<28} {r['total']:>6} "
              f"{r['pass_rate']:>6.1%} {r['block_rate']:>6.1%}  {top}{delta}")
    shas = {r["lint_sha"] for r in rows[-limit:]}
    if len(shas) > 1:
        print("\n⚠️  Rows measured with different linter versions "
              f"({len(shas)} hashes): a pass-rate jump may be the "
              "instrument, not the batch.")
    print()


def print_summary(batch_result: dict) -> None:
    """Print a human-readable lint summary."""
    r = batch_result
    print(f"\n📋 LN Lint — {r['total']} files checked")
    if r.get("prefix"):
        print(f"   Prefix filter: {r['prefix']}")
    print(f"   ✅ Pass: {r['passed']}  ⚠️ Warn: {r['warned']}  🚫 Block: {r['blocked']}")
    print()

    for res in r["results"]:
        if res["status"] == "PASS":
            continue
        icon = "🚫" if res["status"] == "BLOCK" else "⚠️"
        print(f"{icon} {res['file']}")
        for v in res["violations"]:
            if v["severity"] == "INFO":
                continue
            sev_icon = {"BLOCK": "  🚫", "WARN": "  ⚠️"}.get(v["severity"], "  ℹ️")
            print(f"{sev_icon} [{v['rule']}] {v['message']}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="LN quality gate for open-brain-extract"
    )
    sub = parser.add_subparsers(dest="command")

    # check single file
    p_check = sub.add_parser("check", help="Lint a single Literature Note")
    p_check.add_argument("file", help="Path to the .md file")
    p_check.add_argument("--json", action="store_true", help="Output as JSON")

    # check batch
    p_batch = sub.add_parser("check-batch", help="Lint all LNs in a folder")
    p_batch.add_argument("folder", help="Path to Literature Notes folder")
    p_batch.add_argument("--prefix", default=None,
                         help="Filter by LN prefix (e.g. 'AB')")
    p_batch.add_argument("--since", default=None,
                         help="Filter by created date (YYYY-MM-DD)")
    p_batch.add_argument("--format", choices=["summary", "json", "full"],
                         default="summary", help="Output format")
    p_batch.add_argument("--history", action="store_true",
                         help="Append this batch's aggregate to "
                              "Resources/Vault Health/ln_lint_history.jsonl")
    p_batch.add_argument("--scope", default=None,
                         help="Batch label in the history "
                              "(default: prefix/since/folder)")

    # history
    p_hist = sub.add_parser("history",
                            help="Pass-rate trend per batch")
    p_hist.add_argument("--limit", type=int, default=20)
    p_hist.add_argument("--scope", default=None, help="Filter by scope")

    args = parser.parse_args()

    if args.command == "check":
        result = lint_file(Path(args.file))
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            icon = {"PASS": "✅", "WARN": "⚠️", "BLOCK": "🚫"}[result["status"]]
            print(f"{icon} {result['file']} — {result['status']}")
            for v in result["violations"]:
                print(f"  {Violation(v['rule'], v['severity'], v['message'])}")
        sys.exit(1 if result["status"] == "BLOCK" else 0)

    elif args.command == "check-batch":
        batch = lint_batch(
            Path(args.folder),
            prefix=args.prefix,
            since=args.since,
        )
        if args.format == "json":
            print(json.dumps(batch, indent=2, ensure_ascii=False))
        elif args.format == "full":
            print(json.dumps(batch, indent=2, ensure_ascii=False))
        else:
            print_summary(batch)

        if args.history:
            scope = args.scope or args.prefix or (
                f"since:{args.since}" if args.since else Path(args.folder).name
            )
            path = append_history(history_row(batch, scope))
            print(f"📈 Aggregate appended to {path}")

        sys.exit(1 if batch["blocked"] > 0 else 0)

    elif args.command == "history":
        print_history(limit=args.limit, scope=args.scope)
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
