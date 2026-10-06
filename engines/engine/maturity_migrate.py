"""
maturity_migrate.py — writes the DERIVED maturity into the frontmatter.

`maturity` is no longer an editable field: `vaultscan.maturity()` computes it from
`times_retrieved`, `external_outputs` and `internal_outputs`. This script is the
initial migration and the repair tool if someone writes the field by hand again
(health's check_6 detects the divergence; this fixes it).

  python3 engine/maturity_migrate.py            # dry-run
  python3 engine/maturity_migrate.py --apply

Vault location: OPEN_BRAIN_VAULT (or VAULT_ROOT) when set; otherwise the parent
of this script's folder (engines installed at the vault root).
"""
import argparse, os, re, sys
from collections import Counter
from pathlib import Path

_ENGINES = Path(__file__).resolve().parent.parent
VAULT = Path(os.environ.get("OPEN_BRAIN_VAULT") or os.environ.get("VAULT_ROOT") or _ENGINES)
# vault-scan reads VAULT_ROOT: make it agree with this script's vault.
os.environ["VAULT_ROOT"] = str(VAULT)
for _cand in (_ENGINES / "vault-scan", VAULT / "vault-scan"):
    if (_cand / "vaultscan.py").exists():
        sys.path.insert(0, str(_cand))
        break
else:
    raise SystemExit("ERROR: cannot find vault-scan/vaultscan.py next to engine/. "
                     "Install the vault-scan engine.")
import vaultscan as vs  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Write the derived maturity into each Permanent Note.")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry-run)")
    a = ap.parse_args()
    pn_dir = VAULT / "Permanent Notes"
    if not pn_dir.is_dir():
        raise SystemExit(f"ERROR: {pn_dir} not found. Set OPEN_BRAIN_VAULT to your vault root.")
    changed, dist = [], Counter()
    for p in sorted(pn_dir.rglob("*.md")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        m = re.match(r"(---\n)(.*?)(\n---)", raw, re.S)
        if not m:
            continue
        fmtxt = m.group(2)
        fm = vs.parse_fm(raw)
        derived = vs.maturity_of(fm)
        dist[derived] += 1
        declared = str(fm.get("maturity") or "").strip().lower()
        if declared == derived:
            continue
        changed.append((p.stem, declared or "(empty)", derived))
        if not a.apply:
            continue
        if re.search(r"^maturity:.*$", fmtxt, re.M):
            new = re.sub(r"^maturity:.*$", f"maturity: {derived}", fmtxt, flags=re.M)
        else:
            new = fmtxt + f"\nmaturity: {derived}"
        # traceability: the previous state is not deleted, it is noted once
        if declared and declared not in vs.MATURITY_STATES and \
           not re.search(r"^maturity_legacy:", new, re.M):
            new += f"\nmaturity_legacy: {declared}   # previous schema, not defined in the contract"
        p.write_text(m.group(1) + new + m.group(3) + raw[m.end():], encoding="utf-8")
    print("derived distribution:", dict(dist))
    print(f"PNs with divergence: {len(changed)}")
    for s in changed[:10]:
        print("   ", s[1], "→", s[2], "|", s[0][:60])
    print("(dry-run)" if not a.apply else f"wrote {len(changed)} files")


if __name__ == "__main__":
    main()
