#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""crosscheck.py — run both implementations and compare row by row.

  python crosscheck.py            # compare verdicts, flags and segments
Exit: 0 when both agree on every row and both match the hand-authored expectations.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, shell=False)
    return p.returncode, p.stdout, p.stderr


def load_py():
    rc, out, err = run([sys.executable, "run_fixtures.py", "--json"])
    if rc != 0:
        print("python runner failed rc=%d\n%s\n%s" % (rc, out[:400], err[:400]))
        raise SystemExit(2)
    return json.loads(out)


def load_js():
    rc, out, err = run(["node", "check.mjs", "--json"])
    if rc != 0:
        print("node runner failed rc=%d\n%s\n%s" % (rc, out[:400], err[:400]))
        raise SystemExit(2)
    return json.loads(out)


def main():
    py = {r["id"]: r for r in load_py()["rows"]}
    js = {r["id"]: r for r in load_js()["rows"]}
    if set(py) != set(js):
        print("row sets differ:", sorted(set(py) ^ set(js)))
        raise SystemExit(1)
    disagreements = []
    for rid in py:
        a, b = py[rid], js[rid]
        for k in ("verdict",):
            if a[k] != b[k]:
                disagreements.append("%s %s: py=%s js=%s" % (rid, k, a[k], b[k]))
        if sorted(a["flags"]) != sorted(b["flags"]):
            disagreements.append("%s flags: py=%s js=%s" % (rid, a["flags"], b["flags"]))
        seg_py = {k: v for k, v in a["segments"].items()}
        seg_js = {k: v for k, v in b["segments"].items()}
        if seg_py != seg_js:
            disagreements.append("%s segments: py=%s js=%s" % (rid, seg_py, seg_js))
        if not a["matches"] or not b["matches"]:
            disagreements.append("%s expectation mismatch" % rid)
    print("rows compared: %d" % len(py))
    print("disagreements: %d" % len(disagreements))
    for d in disagreements:
        print("  -", d)
    raise SystemExit(0 if not disagreements else 1)


if __name__ == "__main__":
    main()
