# Reproduction record

Machine: Windows 11 (10.0.22631), CPython 3.13.18, Node v22.23.2. No virtual environment,
no third-party packages.

## 1. Python runner, all 28 rows

```
$ python run_fixtures.py --selftest
rows: 28  (P5 12 / P6 16)
P5-01   list                 unobserved             -
...
P6-16   operator-revocation  out-of-bound           -        segment1_seconds=5 refusal_delta_seconds=7200 segment2_seconds=7195
counts: {"bound-not-from-event": 1, "bound-start-unspecified": 1, "cannot-tell": 2, "no-stated-bound": 1, "no-status-path": 1, "not-refused": 1, "out-of-bound": 5, "partial-herd": 1, "provider-can-link": 4, "unobserved": 5, "within-bound": 6}
== selftest ==
  [OK] P5 list->per_reference (got provider-can-link, want provider-can-link)
  [OK] P5 unknown stays cannot-tell (got unobserved, want unobserved)
  [OK] P6 bound 60 -> 30 flips (got out-of-bound, want out-of-bound)
  [OK] P6 start receipt (got bound-not-from-event, want bound-not-from-event)
  [OK] P6 bound null (got no-stated-bound, want no-stated-bound)
  [OK] P6 refusal missing (got cannot-tell, want cannot-tell)
  [OK] P6 value never refused (got not-refused, want not-refused)
  rows compared: 28, mismatches: 0
SELFTEST: PASS
exit code: 0
```

## 2. Node second implementation

```
$ node check.mjs
P5-01   list                 unobserved               -
...
P6-16   operator-revocation  out-of-bound             -
counts: {"unobserved":5,"provider-can-link":4,"no-status-path":1,"cannot-tell":2,"partial-herd":1,"within-bound":6,"out-of-bound":5,"bound-not-from-event":1,"bound-start-unspecified":1,"no-stated-bound":1,"not-refused":1}
exit code: 0
```

## 3. Cross-implementation comparison

```
$ python crosscheck.py
rows compared: 28
disagreements: 0
exit code: 0
```

Segment fields are compared too, not only verdicts: `segment1_seconds`,
`refusal_delta_seconds`, `segment2_seconds`, and the `values` variants
`worst_refusal_delta_seconds` / `segment2_seconds_worst`.

## 4. What was actually proven

- The expectations in `fixtures/*.json` are authored by hand, not produced by either
  runner. Both runners are checked against them, not against each other alone.
- The runner can fail: seven deliberate mutations each flip a verdict (Section 1), and a
  tampered expectation is reported as a mismatch rather than silently accepted.
- Two implementations that share no code agree on 28 rows, including the one-second
  boundary pairs (P6-05/P6-06, P6-07/P6-08) and the per-value row (P6-15).

## 5. Known limits

- These are transcripts. A live service can behave worse than its transcript; the rows
  test what was recorded, and the README says so.
- P5 is graded on the shape of the status request only. Whether the reference was ever
  issued is a separate question, carried by the `indistinguishable-never-issued` flag.
- P6 assumes the withdrawal event is observable by the party that withdrew it, which
  Section 3.6 already requires; rows where it is not are graded `cannot-tell`.
