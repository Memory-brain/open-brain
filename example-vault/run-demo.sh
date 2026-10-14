#!/usr/bin/env bash
# Runs the Open Brain engines against the fictional example vault.
#
# Nothing is written inside the repository: the vault and the autolink engine
# (which writes entities.json / graph.jsonl next to itself) are copied to a
# temporary directory, the engines run there, and the directory is deleted on exit.
#
# Usage:  bash example-vault/run-demo.sh        (from the repo root or anywhere)
# Needs:  Python 3.9+ (PyYAML optional)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINES="$REPO/engines"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cp -R "$REPO/example-vault" "$WORK/vault"
rm -f "$WORK/vault/run-demo.sh" "$WORK/vault/README.md"
# Standard install layout: engines that keep data files (autolink) live in the vault root.
cp -R "$ENGINES/autolink" "$WORK/vault/autolink"
export OPEN_BRAIN_VAULT="$WORK/vault"
PY="${PYTHON:-python3}"

# Prints selected fields of a JSON file produced by an engine.
show() { "$PY" - "$@" <<'EOF'
import json, sys
path, checks = sys.argv[1], [int(x) for x in sys.argv[2].split(",")]
d = json.load(open(path))
for f in d["findings"]:
    if f["id"] not in checks:
        continue
    print(f"[{f['id']}] {f['name']}: count={f.get('count')}")
    for key in ("items", "yellow_top", "single_author_items", "topic_not_claim", "under_8_words"):
        v = f.get(key)
        if v:
            print(f"     {key}: {json.dumps(v, ensure_ascii=False)}")
EOF
}

echo "== 1. Autolink: index the vault and build the typed graph =="
(cd "$WORK/vault/autolink" && "$PY" indexer.py && "$PY" autolink.py --all --write-graph)

echo
echo "== 2. Health check (deterministic checks) =="
"$PY" "$ENGINES/health-engine/health_check.py" run
echo
echo "-- details of the checks that fired --"
show "$WORK/vault/Resources/Vault Health/findings.json" 1,5,12,16,36,46

echo
echo "== 3. Enrich scan (notes under 3 specific, resolvable search terms) =="
"$PY" "$ENGINES/enrich-engine/enrich_engine.py" scan

echo
echo "== 4. Retrieval: one-hop graph expansion from a seed note =="
(cd "$WORK/vault/autolink" && "$PY" graph_hop.py \
    --seeds "Judge a practice by its weekly review, not by its daily streak" --max 5)

echo
echo "== 5. Eval (L1 metrics across six dimensions) =="
"$PY" "$ENGINES/eval-engine/eval_engine.py" run
