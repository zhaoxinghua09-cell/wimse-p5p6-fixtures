#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_fixtures.py — P5/P6 fixture runner (Python reference implementation)

Input: fixtures/p5.json, fixtures/p6.json (transcripts, hand-authored expectations)
Output: one verdict per row, with flags and the two P6 segments.

Commands:
  python run_fixtures.py                 # table
  python run_fixtures.py --json          # machine-readable, for crosscheck
  python run_fixtures.py --selftest      # proves the runner can fail
Exit codes: 0 all rows match expectations, 1 mismatch or error.
"""
import argparse
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")

NO_STATUS_SHAPES = {"list", "commitment", "push", "list_subset"}
CAN_LINK_SHAPES = {"per_reference", "push_per_reference"}


def ts(s):
    if not s:
        return None
    v = s.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    return datetime.fromisoformat(v)


def p5_verdict(row):
    obs = row.get("observation", {})
    shape = obs.get("status_request_shape", "unknown")
    flags = []
    if shape in ("list", "commitment", "push"):
        verdict = "unobserved"
    elif shape == "list_subset":
        verdict = "partial-herd"
        flags.append("audience-at-issuance")
    elif shape in CAN_LINK_SHAPES:
        verdict = "provider-can-link"
    elif shape == "none":
        verdict = "no-status-path"
    else:
        verdict = "cannot-tell"
    if obs.get("never_issued_answered_as_withdrawn") is True:
        flags.append("indistinguishable-never-issued")
    if shape in NO_STATUS_SHAPES and obs.get("refused_after_standing_change") is False:
        flags.append("no-refusal-observed")
    return verdict, flags, {}


def p6_verdict(row):
    bound = row.get("declared_bound_seconds")
    start = row.get("bound_start")
    tl = row.get("timeline", {})
    obs = row.get("observation", {})
    flags = []
    if bound is None:
        return "no-stated-bound", flags, {}
    if start == "receipt":
        return "bound-not-from-event", flags, {}
    if start != "event":
        return "bound-start-unspecified", flags, {}
    t0 = ts(tl.get("t0"))
    if t0 is None:
        return "cannot-tell", flags, {}
    rec = ts(tl.get("t_operator_record"))
    if rec is None:
        flags.append("segment2-unobservable")
    seg = {}
    if rec is not None:
        seg["segment1_seconds"] = int((rec - t0).total_seconds())
    if obs.get("status_source_reachable_at_refusal") is False:
        flags.append("refused-without-status")

    values = row.get("values")
    if values:
        deltas = []
        for v in values:
            tr = ts(v.get("t_refused"))
            if tr is None:
                return "not-refused", flags, seg
            deltas.append(int((tr - t0).total_seconds()))
        worst = max(deltas)
        seg["worst_refusal_delta_seconds"] = worst
        if rec is not None:
            seg["segment2_seconds_worst"] = worst - seg["segment1_seconds"]
        return ("within-bound" if worst <= bound else "out-of-bound"), flags, seg

    tr = ts(tl.get("t_first_refusal"))
    if tr is None:
        return "cannot-tell", flags, seg
    delta = int((tr - t0).total_seconds())
    seg["refusal_delta_seconds"] = delta
    if rec is not None:
        seg["segment2_seconds"] = delta - seg["segment1_seconds"]
    return ("within-bound" if delta <= bound else "out-of-bound"), flags, seg


def evaluate():
    out = []
    for name, fn in (("p5.json", p5_verdict), ("p6.json", p6_verdict)):
        with open(os.path.join(FIX, name), "r", encoding="utf-8") as f:
            data = json.load(f)
        for row in data["rows"]:
            verdict, flags, seg = fn(row)
            exp = row.get("expect", {})
            ok = verdict == exp.get("verdict") and sorted(flags) == sorted(exp.get("flags", []))
            out.append({
                "id": row["id"],
                "path": row.get("path"),
                "verdict": verdict,
                "flags": flags,
                "segments": seg,
                "expect": exp,
                "matches": ok,
            })
    return out


def counts(rows):
    c = {}
    for r in rows:
        c[r["verdict"]] = c.get(r["verdict"], 0) + 1
    return dict(sorted(c.items()))


def selftest(rows):
    """Mutations that must flip a verdict, plus one that must leave it alone."""
    cases = []
    p5 = {"observation": {"status_request_shape": "list", "refused_after_standing_change": True,
                          "never_issued_answered_as_withdrawn": False}}
    cases.append(("P5 list->per_reference", p5_verdict({"observation": {"status_request_shape": "per_reference",
                                                                        "refused_after_standing_change": True,
                                                                        "never_issued_answered_as_withdrawn": False}})[0], "provider-can-link"))
    cases.append(("P5 unknown stays cannot-tell", p5_verdict(p5)[0], "unobserved"))
    p6 = {"declared_bound_seconds": 60, "bound_start": "event",
          "timeline": {"t0": "2026-11-20T10:00:00Z", "t_operator_record": "2026-11-20T10:00:01Z",
                       "t_first_refusal": "2026-11-20T10:00:59Z"}}
    cases.append(("P6 bound 60 -> 30 flips", p6_verdict({**p6, "declared_bound_seconds": 30})[0], "out-of-bound"))
    cases.append(("P6 start receipt", p6_verdict({**p6, "bound_start": "receipt"})[0], "bound-not-from-event"))
    cases.append(("P6 bound null", p6_verdict({**p6, "declared_bound_seconds": None})[0], "no-stated-bound"))
    cases.append(("P6 refusal missing", p6_verdict({**p6, "timeline": {**p6["timeline"], "t_first_refusal": None}})[0], "cannot-tell"))
    cases.append(("P6 value never refused",
                  p6_verdict({"declared_bound_seconds": 600, "bound_start": "event",
                              "timeline": {"t0": "2026-11-20T10:00:00Z", "t_operator_record": "2026-11-20T10:00:10Z",
                                           "t_first_refusal": "2026-11-20T10:03:20Z"},
                              "values": [{"value_id": "A", "t_refused": "2026-11-20T10:03:20Z"},
                                         {"value_id": "B", "t_refused": None}]})[0], "not-refused"))
    bad = [n for n, got, want in cases if got != want]
    print("== selftest ==")
    for n, got, want in cases:
        print("  [%s] %s (got %s, want %s)" % ("OK" if got == want else "FAIL", n, got, want))
    mism = [r["id"] for r in rows if not r["matches"]]
    print("  rows compared: %d, mismatches: %d %s" % (len(rows), len(mism), ",".join(mism)))
    return not bad and not mism


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    rows = evaluate()
    if a.json:
        print(json.dumps({"rows": rows, "counts": counts(rows)}, ensure_ascii=False, indent=1))
        sys.exit(0 if all(r["matches"] for r in rows) else 1)
    print("rows: %d  (P5 %d / P6 %d)" % (len(rows), sum(r["id"].startswith("P5") for r in rows),
                                        sum(r["id"].startswith("P6") for r in rows)))
    for r in rows:
        seg = " ".join("%s=%s" % kv for kv in r["segments"].items())
        print("%-7s %-20s %-22s %-28s %s" % (r["id"], r["path"], r["verdict"],
                                             ",".join(r["flags"]) if r["flags"] else "-", seg))
    print("counts:", json.dumps(counts(rows), ensure_ascii=False))
    if a.selftest:
        ok = selftest(rows)
        print("SELFTEST:", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)
    bad = [r["id"] for r in rows if not r["matches"]]
    if bad:
        print("MISMATCH:", ",".join(bad))
        sys.exit(1)


if __name__ == "__main__":
    main()
