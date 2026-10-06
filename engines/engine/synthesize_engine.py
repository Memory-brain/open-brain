#!/usr/bin/env python3
"""
synthesize-engine — deterministic plumbing for open-brain-synthesize.

Reuses vault-scan. The engine produces a domain-report with ALL the mechanical work:
notes by type/layer, layer coverage + gaps, convergence CANDIDATES (LNs from
different prefixes that share search_terms), cluster→skill CANDIDATES,
promotion backlog (LNs not referenced by any PN), feeder audit, stale.

The AI keeps the judgment: applying the convergence test (do they really converge on
something actionable?), writing the synthesis PNs, evaluating skill candidates, and the
competency map.

Commands:
  domain-report "<Domain>" [--min-shared 2] [--cluster-min 5]
  index-update  "<Domain>" --json '{note_count,pn_count,ln_count,...}'

vault-scan is located via OPEN_BRAIN_ENGINES, OPEN_BRAIN_VAULT or VAULT_ROOT, or by
walking up from this file. The vault root is resolved by vault-scan; set
OPEN_BRAIN_VAULT to override it.
"""

# `X | None` in annotations is 3.10+; on Python 3.9 the module would crash at
# import. With this future import annotations are not evaluated.
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


def _bootstrap_vaultscan():
    envs = [os.environ.get(k) for k in ("OPEN_BRAIN_ENGINES", "OPEN_BRAIN_VAULT", "VAULT_ROOT")]
    bases = [Path(e) for e in envs if e] + [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
    for base in bases:
        for cand in [base / "vault-scan", base]:
            if (cand / "vaultscan.py").exists():
                sys.path.insert(0, str(cand)); return
    raise SystemExit("ERROR: cannot find vault-scan/vaultscan.py. Install vault-scan or set OPEN_BRAIN_ENGINES.")


_bootstrap_vaultscan()
import vaultscan as vs  # noqa: E402

VAULT = Path(os.environ["OPEN_BRAIN_VAULT"]) if os.environ.get("OPEN_BRAIN_VAULT") else vs.VAULT
TODAY = date.today().isoformat()
PREFIX_RE = re.compile(r"^([A-Z0-9]{2,6})\s*-\s")


def out(o):
    print(json.dumps(o, ensure_ascii=False, indent=2))


def ln_prefix(stem: str) -> str | None:
    m = PREFIX_RE.match(stem)
    return m.group(1) if m else None


def _terms(fm) -> set:
    return {t.replace("[[", "").replace("]]", "").split("|")[0].strip()
            for t in vs.as_list(fm.get("search_terms"))}


def cmd_domain_report(domain, min_shared, cluster_min):
    # --- gather the domain's notes (vault-scan) ---
    pn_data, ln_data = [], []
    for p, text in vs.iter_notes("Permanent Notes"):
        fm = vs.parse_fm(text)
        if vs._domain_match(fm, domain):
            pn_data.append((p.stem, fm, vs.body_of(text)))
    for p, text in vs.iter_notes("Literature Notes"):
        fm = vs.parse_fm(text)
        if vs._domain_match(fm, domain):
            ln_data.append((p.stem, fm))

    coverage = vs.layer_coverage(domain)

    # --- convergence: LNs from DIFFERENT prefixes sharing >=min_shared terms ---
    conv = []
    for i in range(len(ln_data)):
        si, fi = ln_data[i]
        pi, ti = ln_prefix(si), _terms(fi)
        if not ti:
            continue
        for j in range(i + 1, len(ln_data)):
            sj, fj = ln_data[j]
            pj = ln_prefix(sj)
            if pi and pj and pi != pj:
                shared = ti & _terms(fj)
                if len(shared) >= min_shared:
                    conv.append({"a": si, "b": sj, "prefixes": [pi, pj],
                                 "shared_terms": sorted(shared)})
    conv.sort(key=lambda x: -len(x["shared_terms"]))

    # --- PN clusters → skill candidates ---
    term_to_pns = defaultdict(list)
    pn_layers, pn_prefix_via_sources = {}, {}
    for stem, fm, _ in pn_data:
        pn_layers[stem] = (fm.get("layer") or "").strip().lower()
        srcs = vs.as_list(fm.get("sources"))
        prefs = {ln_prefix(s.replace("[[", "").replace("]]", "").strip()) for s in srcs}
        pn_prefix_via_sources[stem] = {p for p in prefs if p}
        for t in _terms(fm):
            term_to_pns[t].append(stem)
    clusters = []
    seen_sets = []
    for term, pns in term_to_pns.items():
        if len(pns) < cluster_min:
            continue
        layers = {pn_layers.get(p) for p in pns if pn_layers.get(p)}
        prefixes = set().union(*[pn_prefix_via_sources.get(p, set()) for p in pns]) if pns else set()
        if len(layers) >= 3 and len(prefixes) >= 2:
            sig = frozenset(pns)
            if sig in seen_sets:
                continue
            seen_sets.append(sig)
            clusters.append({"anchor_term": term, "pn_count": len(pns),
                             "layers": sorted(l for l in layers if l),
                             "source_prefixes": sorted(prefixes),
                             "pns": pns[:12]})
    clusters.sort(key=lambda x: -x["pn_count"])

    # --- promotion backlog: LNs not referenced by any PN in the domain ---
    referenced = set()
    for stem, fm, body in pn_data:
        for t in vs.wikilinks(body) + [s.replace("[[", "").replace("]]", "").strip()
                                       for s in vs.as_list(fm.get("sources"))]:
            referenced.add(t)
    backlog = defaultdict(int)
    for stem, fm in ln_data:
        if stem not in referenced:
            backlog[ln_prefix(stem) or "(no prefix)"] += 1

    # --- feeder audit of existing skills ---
    skills_dir = VAULT / "Skills" / domain
    feeders = []
    if skills_dir.exists():
        for sk in skills_dir.iterdir():
            fp = sk / "feeder-pns.md"
            if fp.is_file():
                t = fp.read_text(encoding="utf-8", errors="ignore")
                e = len(re.findall(r"\[\[", t.split("## Provisional")[0])) if "## Provisional" in t else 0
                total = len(re.findall(r"\[\[", t))
                feeders.append({"skill": sk.name, "endorsed_approx": e, "total_approx": total,
                                "flag": "never practiced (0 endorsed, >12)" if e == 0 and total > 12 else ""})

    out({
        "ok": True, "domain": domain,
        "counts": {"permanent": len(pn_data), "literature": len(ln_data)},
        "layer_coverage": coverage,
        "convergence_candidates": conv[:25],
        "skill_cluster_candidates": clusters[:10],
        "promotion_backlog": dict(sorted(backlog.items(), key=lambda x: -x[1])),
        "existing_skills_feeders": feeders,
        "note": "The engine SURFACES candidates. The AI applies the convergence test (3 parts), "
                "evaluates the clusters against the 5 skill criteria, and writes the PNs.",
    })


def cmd_index_update(domain, payload, dry):
    p = VAULT / "Domains" / f"{domain}.md"
    if not p.exists():
        out({"ok": False, "error": f"Domains/{domain}.md does not exist"}); return
    text = p.read_text(encoding="utf-8")
    changed = []
    for key in ("note_count", "pn_count", "ln_count", "skills_count", "skills_with_course"):
        if key in payload:
            if re.search(rf"^{key}:", text, re.MULTILINE):
                text = re.sub(rf"^{key}:.*$", f"{key}: {payload[key]}", text, count=1, flags=re.MULTILINE)
                changed.append(key)
    for key in ("last_synthesized", "updated"):
        if re.search(rf"^{key}:", text, re.MULTILINE):
            text = re.sub(rf"^{key}:.*$", f"{key}: {TODAY}", text, count=1, flags=re.MULTILINE)
            changed.append(key)
    if not dry:
        p.write_text(text, encoding="utf-8")
    out({"ok": True, "dry_run": dry, "updated_fields": changed})


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("domain-report"); r.add_argument("domain")
    r.add_argument("--min-shared", type=int, default=2); r.add_argument("--cluster-min", type=int, default=5)
    u = sub.add_parser("index-update"); u.add_argument("domain"); u.add_argument("--json", required=True)
    u.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.cmd == "domain-report":
        cmd_domain_report(a.domain, a.min_shared, a.cluster_min)
    elif a.cmd == "index-update":
        cmd_index_update(a.domain, json.loads(a.json), a.dry_run)


if __name__ == "__main__":
    main()
