#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Opens and closes Retrieval Log entries — the query is recorded at the START.

Why it exists. Log entries used to exist only because the model remembered to
write them at the end, after answering. Queries often arrive through clients
that leave no local transcript, so no piece of software sees them go by: if the
final step is skipped, the query never existed as far as the dashboard is
concerned. A record written after answering measures the answerer's memory,
not what was asked.

This command inverts the order. `open` writes the entry with the query and
nothing else, BEFORE searching; `close` completes it when the retrieval ends.
The gain is not convenience: a session abandoned halfway still leaves its query
in the log, marked as open. Open entries are not noise — they measure how many
retrievals start and never get recorded, a number that was impossible to count
before.

The log stays append-only: `open` appends at the end and `close` touches ONLY
the lines of the entry carrying its id, never another entry and never deleting.
If the id is not found, `close` fails instead of guessing.

Log field names and values (`Estado: abierta/cerrada`, `ninguno`, `tarea`,
`auditoría`, …) are Spanish identifiers parsed by the engines; keep them as is.

Vault root: --root, else $OPEN_BRAIN_VAULT, else the parent of this folder if it
holds Resources/Retrieval Log.md, else the first ancestor of the cwd that does.

Usage:
    python3 log_entry.py open  --query "literal text" [--intent Operative] [--origen desktop]
    python3 log_entry.py close --id ID --returned "[[A]], [[B]]" --used "[[A]] — gloss" \
                               [--outcome success] [--expansion "..."] [--dominio Design] \
                               [--track text] [--tarea explicar] [--gaps "..."] [--intent Critical] \
                               [--origen_uso tarea|auditoría]
    python3 log_entry.py open-list [--days 30]     # open entries never closed
    python3 log_entry.py coverage [--days 30]      # open vs closed in the window
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib  # noqa: E402

LOG_REL = os.path.join("Resources", "Retrieval Log.md")
ID_RE = re.compile(r"<!--\s*log-entry id:\s*([A-Za-z0-9:+\-]+)\s*-->")

# Fields `close` fills, in the order of the skill's log schema. Order matters
# because the log is read by eye as much as by parser, and an entry that orders
# the fields differently reads as if it came from another system.
CLOSE_FIELDS = [
    ("expansion", "Expansión"),
    ("dominio", "Dominio detectado"),
    ("track", "Track"),
    ("returned", "Notas devueltas"),
    ("refs", "Design References devueltas"),
    ("used", "Notas usadas sustantivamente"),
    ("modo", "Output mode"),
    ("prefiltro", "Candidates pre-filtered"),
    ("motor", "Motor determinista"),
    ("terminos", "Términos que matchearon"),
    ("tokens", "Tokens served (est.)"),
    ("outcome", "Outcome"),
    ("reform", "Reformulation?"),
    ("gaps", "Gaps detectados"),
    ("tarea", "Tarea"),
    ("juicio", "Juicio que no estaba en el vault"),
    ("artefacto", "Artefacto producido"),
    ("origen_uso", "Origen de uso"),
]

# Usage origin. A query about the system itself (challenge, audit, health) is
# not use of the knowledge: a periodic system challenge once raised
# `times_retrieved` on dozens of week-old notes without any of them changing
# anything for the user. `auditoría` (audit) does not myelinate and records the
# read in `audit_retrievals`, a separate counter that `maturity` does not read.
# `tarea` (task) leaves the protocol as it was (counters are raised per the
# retrieve skill).
ORIGENES = {"tarea": "tarea", "auditoria": "auditoría", "auditoría": "auditoría"}

# The three fields the schema declares MANDATORY with an explicit escape value
# ("ninguno" = none, "no disponible" = not available): omitting them is not the
# same as saying there were none. If not passed, `close` writes them with their
# escape value instead of leaving them out — which is how they used to vanish
# from the log.
DEFAULTS = {"artefacto": "ninguno", "juicio": "ninguno", "gaps": "ninguno"}

# Only fields that are lists of notes get a link count. `Términos que
# matchearon` also carries wikilinks, but its number counts attributions, not
# returned notes: counting it there would invite reading two different figures
# as the same.
LINK_COUNTED = ("returned", "refs", "used")


def log_path(root):
    return os.path.join(root, LOG_REL)


def read_log(root):
    p = log_path(root)
    if not os.path.exists(p):
        raise SystemExit("%s does not exist. Create Resources/Retrieval Log.md in your vault "
                         "(an empty file with a `# Retrieval Log` heading is enough)." % p)
    with open(p, encoding="utf-8") as f:
        return f.read()


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# ------------------------------------------------------------------------ open

def cmd_open(root, query, intent, origen):
    """Appends the entry with the query and the clock, before searching anything.

    It deliberately does NOT write empty fields that would later be trusted: an
    open entry says the only thing truly known at that moment — that this query
    was made, at this time, from here. `close` adds the rest when it exists. An
    empty `**Notas devueltas**: ` would be worse than absent: the parser would
    read it as a list of zero returned notes, which is a false statement about
    the retrieval, not the absence of a measurement.
    """
    query = (query or "").strip()
    if not query:
        raise SystemExit("empty --query: an entry without a query is not an entry")
    now = dt.datetime.now()
    eid = "%s-%s" % (now.strftime("%Y%m%dT%H%M%S"), uuid.uuid4().hex[:6])
    block = (
        "\n## %s — [intent: %s]\n\n"
        "**Query**: \"%s\"\n"
        "**Estado**: abierta <!-- log-entry id: %s -->\n"
        "**Origen**: %s · opened by log_entry.py before searching\n\n"
        "---\n"
    ) % (now.strftime("%Y-%m-%d %H:%M"), intent, query.replace('"', "'"), eid, origen)
    with open(log_path(root), "a", encoding="utf-8") as f:
        f.write(block)
    out({"ok": True, "id": eid, "date": now.strftime("%Y-%m-%d %H:%M"),
         "next": "when done: python3 log_entry.py close --id %s --returned ... --used ..." % eid})


# ----------------------------------------------------------------------- close

def _find_block(text, eid):
    """-> (start, end) of the `## ...` block carrying that id, or None.

    Finds the id first and walks up to its heading, instead of splitting the
    whole file: that way an id quoted inside another entry (a note about the
    system itself, for instance) does not drag the cut to the wrong entry.
    """
    m = re.search(r"<!--\s*log-entry id:\s*%s\s*-->" % re.escape(eid), text)
    if not m:
        return None
    start = text.rfind("\n## ", 0, m.start())
    if start == -1:
        return None
    start += 1
    nxt = text.find("\n## ", m.end())
    end = len(text) if nxt == -1 else nxt + 1
    return (start, end)


def cmd_close(root, eid, values, intent):
    text = read_log(root)
    span = _find_block(text, eid)
    if not span:
        raise SystemExit("No entry with id %s. The log is not touched blindly." % eid)
    start, end = span
    block = text[start:end]
    if re.search(r"(?m)^\*\*Estado\*\*:\s*cerrada", block):
        raise SystemExit("Entry %s is already closed. Reopening it would rewrite "
                         "a measurement already recorded; write a new entry." % eid)

    o = (values.get("origen_uso") or "").strip().lower()
    if o:
        if o not in ORIGENES:
            raise SystemExit("--origen_uso must be tarea (task) or auditoría (audit), not %r" % o)
        values["origen_uso"] = ORIGENES[o]
    auditoria = values.get("origen_uso") == "auditoría"

    lines = []
    for key, label in CLOSE_FIELDS:
        v = (values.get(key) or "").strip() or DEFAULTS.get(key, "")
        if not v:
            continue
        if key in LINK_COUNTED:
            n = len(rlib.LINK_RE.findall(v))
            lines.append("**%s** (%d): %s" % (label, n, v))
        else:
            lines.append("**%s**: %s" % (label, v))
    # What was not passed is not invented: it is named as absent, which is a
    # different datum from zero. An absent `Notas devueltas` already has its own
    # meaning in the engine (`sin_devueltas`) and the dashboard counts it apart.
    # `Design References devueltas` only applies to the visual track: listing it
    # as absent in a text retrieval turns "not applicable" into "missing", which
    # is the cheap way to make a control line stop being read.
    visual = "visual" in (values.get("track") or "").lower()
    faltan = [label for key, label in CLOSE_FIELDS
              if not ((values.get(key) or "").strip() or DEFAULTS.get(key, ""))
              and not (key == "refs" and not visual)]

    block = re.sub(r"(?m)^\*\*Estado\*\*:\s*abierta(\s*<!--[^>]*-->)?$",
                   "**Estado**: cerrada\\1", block)
    if intent:
        block = re.sub(r"(?m)^(## \d{4}-\d{2}-\d{2}[^\n]*?)\[intent:[^\]]*\]",
                       lambda m: m.group(1) + "[intent: %s]" % intent, block, count=1)
    cierre = "\n".join(lines)
    if faltan:
        cierre += "\n**Campos no registrados**: %s" % " · ".join(faltan)
    # The closing block goes after `Origen`, before the `---` separating entries.
    block = block.rstrip("\n")
    block = re.sub(r"\n---$", "", block).rstrip("\n")
    block = block + "\n" + cierre + "\n\n---\n"

    with open(log_path(root), "w", encoding="utf-8") as f:
        f.write(text[:start] + block + text[end:])
    # Automatic myelination: it used to be a manual protocol step and traversals
    # went unrecorded for days. Notes used together in the same entry are the
    # co-used pair; they are recorded here, on close. Optional: if
    # autolink/myelinate.py is absent or fails, closing continues.
    myel = 0
    try:
        used = [m.split("|")[0].strip() for m in rlib.LINK_RE.findall(values.get("used") or "")]
        used = list(dict.fromkeys(used))[:6]
        if len(used) >= 2 and not auditoria:
            import importlib.util
            myel_path = os.path.join(root, "autolink", "myelinate.py")
            if not os.path.exists(myel_path):
                raise FileNotFoundError("autolink/myelinate.py not installed")
            spec = importlib.util.spec_from_file_location("myelinate", myel_path)
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            pairs = [(a, b) for i, a in enumerate(used) for b in used[i + 1:]]
            q = rlib._field(block, "Query") or ""
            myel = mod.cmd_record_batch(pairs, query=q.strip().strip('"'), intent=intent or "implicit")
    except Exception as e:
        sys.stderr.write("myelination not recorded: %s\n" % e)
    audit_n = _bump_audit(root, values.get("used") or "") if auditoria else 0
    out({"ok": True, "id": eid, "traversals_recorded": myel,
         "usage_origin": values.get("origen_uso") or "not declared",
         "audit_retrievals_added": audit_n,
         "fields_written": [l for k, l in CLOSE_FIELDS
                             if ((values.get(k) or "").strip() or DEFAULTS.get(k, ""))],
         "fields_not_recorded": faltan})


def _bump_audit(root, used_field):
    """Adds 1 to `audit_retrievals` on every note used by an audit query.
    Does not touch `times_retrieved` or `last_retrieved`. Returns how many
    notes it touched."""
    n = 0
    titles = list(dict.fromkeys(m.split("|")[0].strip()
                                for m in rlib.LINK_RE.findall(used_field)))
    for t in titles:
        for folder in ("Literature Notes", "Permanent Notes", "Cases"):
            p = os.path.join(root, folder, t + ".md")
            if not os.path.exists(p):
                continue
            s = open(p, encoding="utf-8").read()
            if not s.startswith("---"):
                break
            if re.search(r"(?m)^audit_retrievals:\s*\d+", s):
                s = re.sub(r"(?m)^audit_retrievals:\s*(\d+)",
                           lambda m: "audit_retrievals: %d" % (int(m.group(1)) + 1), s, count=1)
            else:
                s = s.replace("\n---", "\naudit_retrievals: 1\n---", 1)
            open(p, "w", encoding="utf-8").write(s)
            n += 1
            break
    return n


# -------------------------------------------------------------------- reads

def _entries_with_state(root):
    text = read_log(root)
    parts = re.split(r"(?m)^(## \d{4}-\d{2}-\d{2}.*)$", text)
    rows = []
    for header, body in zip(parts[1::2], parts[2::2]):
        m = ID_RE.search(body)
        if not m:
            continue
        est = re.search(r"(?m)^\*\*Estado\*\*:\s*(\w+)", body)
        q = rlib._field(body, "Query") or ""
        rows.append({
            "id": m.group(1),
            "date": re.match(r"##\s*(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?)", header.strip()).group(1),
            "state": est.group(1) if est else "?",
            "query": q.strip().strip('"')[:120],
            "origin": (rlib._field(body, "Origen") or "").split("·")[0].strip(),
        })
    return rows


def _in_window(rows, days):
    if not days:
        return rows
    lim = (dt.datetime.now() - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    return [r for r in rows if r["date"][:10] >= lim]


def cmd_open_list(root, days):
    rows = [r for r in _in_window(_entries_with_state(root), days) if r["state"] == "abierta"]
    out({"ok": True, "open": len(rows), "rows": rows})


def cmd_coverage(root, days):
    """How many retrievals were opened and how many got fully recorded.

    This is the figure that did not exist: "log entries" and "queries made"
    used to be the same number by construction, so the log could not reveal its
    own gap. With `open` writing before searching, the difference between open
    and closed entries is the gap, measured.
    """
    rows = _in_window(_entries_with_state(root), days)
    ab = [r for r in rows if r["state"] == "abierta"]
    ce = [r for r in rows if r["state"] == "cerrada"]
    total_log = len([e for e in rlib.parse_log(root) if e.get("query")])
    out({"ok": True, "window_days": days,
         "instrumented": len(rows), "closed": len(ce), "open": len(ab),
         "close_rate": round(len(ce) / len(rows), 3) if rows else None,
         "log_entries_total": total_log,
         "note": "hand-written entries (no id) do not count here: this only "
                 "measures what went through log_entry.py"})


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("open")
    o.add_argument("--query", required=True)
    o.add_argument("--intent", default="pending")
    o.add_argument("--origen", default="unknown")

    c = sub.add_parser("close")
    c.add_argument("--id", required=True, dest="eid")
    c.add_argument("--intent", default="")
    for key, label in CLOSE_FIELDS:
        c.add_argument("--%s" % key, default="", help=label)
    c.add_argument("--json", default="", help="JSON file with the fields, to avoid "
                                              "fighting the shell quoting of 20 wikilinks")

    for name in ("open-list", "coverage"):
        s = sub.add_parser(name)
        s.add_argument("--days", type=int, default=30)

    a = ap.parse_args()
    # The default vault is the one containing THIS script, not the cwd: the
    # skill calls it by absolute path from wherever it is working, and
    # `vault_root()` walks up from the cwd.
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if a.root:
        root = a.root
    elif os.environ.get("OPEN_BRAIN_VAULT"):
        root = os.environ["OPEN_BRAIN_VAULT"]
    elif os.path.exists(os.path.join(here, LOG_REL)):
        root = here
    else:
        root = rlib.vault_root()
    if a.cmd == "open":
        cmd_open(root, a.query, a.intent, a.origen)
    elif a.cmd == "close":
        vals = {k: getattr(a, k) for k, _ in CLOSE_FIELDS}
        if a.json:
            with open(a.json, encoding="utf-8") as f:
                blob = json.load(f)
            labels = dict(CLOSE_FIELDS)
            for k in vals:
                v = blob.get(k) or blob.get(labels[k])  # key or log label
                if not vals[k] and v:
                    vals[k] = v
        cmd_close(root, a.eid, vals, a.intent)
    elif a.cmd == "open-list":
        cmd_open_list(root, a.days)
    else:
        cmd_coverage(root, a.days)


if __name__ == "__main__":
    main()
