# P5/P6 fixtures for `draft-molas-agent-principal-refs`

Small, runnable test fixtures for two properties of
[draft-molas-agent-principal-refs-00](https://datatracker.ietf.org/doc/draft-molas-agent-principal-refs/):

- **P5, Unobserved Status** (Section 3.5): a status check must not carry any value that
  identifies which reference is being checked.
- **P6, Bounded Withdrawal** (Section 3.6): per withdrawal path, a stated numeric bound
  measured from a stated withdrawal event, and a conforming relying party refusing at or
  before that bound.

The point is that each evaluator should not have to invent the rows. These are transcripts,
not a service: a row records what was observed, and the runner turns that record into one
verdict in the vocabulary this repository publishes. Anyone can run them without a live
service, compare results, and disagree with a specific row by name.

## What these fixtures do not do

They test a status source's **observable behaviour**, not the correctness of its records.
A service can pass every row here while its registry is wrong. The rows also do not
establish that a reference was ever issued: where a service answers "never issued" exactly
as it answers "issued then withdrawn", the row says so and the verdict carries the flag
`indistinguishable-never-issued`.

Nothing here is a conformance test for a specification that does not exist yet, and nothing
here grades a draft. The vocabulary used for the verdicts is in `fixtures/p5.json` and
`fixtures/p6.json` under `verdict_vocabulary`, and is deliberately narrower than the
Provides/Allows/Partial scale of the draft's Section 5.

## Run it

```
python run_fixtures.py            # 28 rows, table with verdict, flags, P6 segments
python run_fixtures.py --selftest # proves the runner can fail (7 mutations + expectation check)
node check.mjs                    # second implementation, same fixtures
python crosscheck.py              # both implementations, row by row
```

Exit code 0 means: every row matches its hand-authored expectation, and the two
implementations agree on every verdict, flag and segment. `crosscheck.py` prints
`rows compared: 28` and `disagreements: 0` when this holds.

No third-party packages. Python 3.10+, Node 18+.

## Rows

28 rows: 12 for P5, 16 for P6. What they cover:

| Area | Rows | Purpose |
|---|---|---|
| P5 request shapes | P5-01..P5-06, P5-11, P5-12 | list, commitment, push, list-subset, per-reference, subscription, no status path |
| P5 blind spots | P5-07, P5-08, P5-09, P5-10 | fetch with nothing acting on it; transcription gap; withdrawn answered as never-issued |
| P6 path coverage | P6-01..P6-08, P6-16 | list, feed, single-record, principal standing alone, operator revocation |
| P6 bounds | P6-09, P6-10, P6-11 | bound from receipt, clock start unstated, no numeric bound |
| P6 edge rows | P6-12..P6-15 | record time missing, no refusal observed, status unreadable at refusal, one value never refused |

The pairs are deliberate: P6-05/P6-06 and P6-07/P6-08 differ by one second, so a runner
that compares inclusively at the bound and exclusive one second later is distinguishable
from one that does not. P6-11 shows a fast refusal that does not repair an unstated bound.
P6-14 is the case where a refusal lands inside the bound while the status source is
unreachable — met, but the report has to say the refusal did not come from reading status.

## The two P6 segments

Each P6 row reports `segment1_seconds` (the withdrawal event to the operator's own record,
which only the operator can declare) and `segment2_seconds` (that record to the first
refusal, which a third party can measure). A single bound stated over the sum is not
measurable by a third party, which is why the fixtures keep them apart and print both.

## Adding a row

Copy the shape of an existing row, change the transcript, write the verdict you expect by
hand, and run `python run_fixtures.py --selftest`. If your expectation and the runner
disagree, one of the two is wrong and that is the whole point: put the disagreement in a
PR rather than editing the runner until it agrees.

## Licence

Apache-2.0. Text and fixtures are meant to be copied into other test suites with
attribution.
