#!/usr/bin/env python3
"""check_alignment: checks that the retrieval engine's artifacts match the index.

Why it exists: after a large extraction, the index was rebuilt in a shell
without scipy; `cmd_index` saved index.json and then failed while building
lsa.npz. The engine was left broken ("lsa.npz out of sync") with nothing to
flag it. open-brain-extract calls this at the end of every extraction.

Exits 0 if everything matches, 1 if something is out of sync or the index does
not cover new notes, 2 if the index is missing. Prints JSON.

The vault root is $OPEN_BRAIN_VAULT if set, otherwise the parent of this folder.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rlib  # noqa: E402

CACHE = os.path.join(HERE, ".cache")
IX = os.path.join(CACHE, "index.json")
ARTS = {"lsa": os.path.join(CACHE, "lsa.npz.vocab.json"),
        "bridge": os.path.join(CACHE, "bridge.json"),
        "embed": os.path.join(CACHE, "embed.npz.meta.json")}
WATCH = ["Literature Notes", "Permanent Notes", "Cases"]


def main():
    if not os.path.exists(IX):
        print(json.dumps({"ok": False, "error": "the index is missing",
                          "fix": "python3 retrieval-eval/eval_retrieval.py index"}))
        return 2
    ix = rlib.Index.load(IX)
    fp = ix.fingerprint()
    res = {"index_fingerprint": fp, "index_docs": len(ix.docs), "artifacts": {}}
    bad = []
    for name, p in ARTS.items():
        if not os.path.exists(p):
            res["artifacts"][name] = "absent"
            if name != "embed":  # embed is optional
                bad.append(name)
            continue
        got = json.load(open(p, encoding="utf-8")).get("fingerprint")
        ok = got == fp
        res["artifacts"][name] = "ok" if ok else "out of sync (%s)" % got
        if not ok:
            if name == "embed" and os.environ.get("OB_EMBED", "0") == "0":
                res["artifacts"][name] += ", channel off (OB_EMBED=0): warning, not a failure"
            else:
                bad.append(name)
    # notes created or touched after the index
    root = os.environ.get("OPEN_BRAIN_VAULT") or os.path.dirname(HERE)
    t_ix = os.path.getmtime(IX)
    indexed = {d["rel"] for d in ix.docs}
    nuevas = 0
    for folder in WATCH:
        fd = os.path.join(root, folder)
        if not os.path.isdir(fd):
            continue
        for f in os.listdir(fd):
            # only count what was created or touched AFTER the index: older
            # unindexed files are excluded by rlib on purpose
            if (f.endswith(".md") and os.path.join(folder, f) not in indexed
                    and os.path.getmtime(os.path.join(fd, f)) > t_ix):
                nuevas += 1
    res["unindexed_notes"] = nuevas
    if nuevas:
        bad.append("unindexed_notes")
    res["ok"] = not bad
    if bad:
        res["failures"] = bad
        res["fix"] = ("python3 retrieval-eval/eval_retrieval.py index  "
                      "(needs scipy in that python3; if missing, the index is NOT touched)")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
