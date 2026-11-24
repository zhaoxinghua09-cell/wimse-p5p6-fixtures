// check.mjs — P5/P6 fixture runner, second implementation (Node, no dependency)
// Written independently of run_fixtures.py: same fixtures, same published
// vocabulary, different code path. Disagreement between the two is a defect.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const read = (p) => JSON.parse(readFileSync(join(HERE, "fixtures", p), "utf8"));

function epoch(s) {
  if (s === null || s === undefined || s === "") return null;
  const t = Date.parse(String(s).trim());
  return Number.isNaN(t) ? null : Math.trunc(t / 1000);
}

function flagsForP5(o) {
  const f = [];
  if (o.never_issued_answered_as_withdrawn === true) f.push("indistinguishable-never-issued");
  const hasPath = ["list", "commitment", "push", "list_subset"].includes(o.status_request_shape);
  if (hasPath && o.refused_after_standing_change === false) f.push("no-refusal-observed");
  return f;
}

function verdictP5(row) {
  const o = row.observation || {};
  const shape = o.status_request_shape || "unknown";
  let v;
  switch (shape) {
    case "list":
    case "commitment":
    case "push":
      v = "unobserved";
      break;
    case "list_subset":
      v = "partial-herd";
      break;
    case "per_reference":
    case "push_per_reference":
      v = "provider-can-link";
      break;
    case "none":
      v = "no-status-path";
      break;
    default:
      v = "cannot-tell";
  }
  const f = flagsForP5(o);
  if (shape === "list_subset") f.unshift("audience-at-issuance");
  return { verdict: v, flags: f, segments: {} };
}

function verdictP6(row) {
  const bound = row.declared_bound_seconds;
  const tl = row.timeline || {};
  const obs = row.observation || {};
  const flags = [];
  if (bound === null || bound === undefined) return { verdict: "no-stated-bound", flags, segments: {} };
  if (row.bound_start === "receipt") return { verdict: "bound-not-from-event", flags, segments: {} };
  if (row.bound_start !== "event") return { verdict: "bound-start-unspecified", flags, segments: {} };

  const t0 = epoch(tl.t0);
  if (t0 === null) return { verdict: "cannot-tell", flags, segments: {} };
  const rec = epoch(tl.t_operator_record);
  if (rec === null) flags.push("segment2-unobservable");
  if (obs.status_source_reachable_at_refusal === false) flags.push("refused-without-status");

  const seg = {};
  if (rec !== null) seg.segment1_seconds = rec - t0;

  const vals = row.values || null;
  if (vals) {
    const ds = [];
    for (const v of vals) {
      const t = epoch(v.t_refused);
      if (t === null) return { verdict: "not-refused", flags, segments: seg };
      ds.push(t - t0);
    }
    const worst = Math.max(...ds);
    seg.worst_refusal_delta_seconds = worst;
    if (rec !== null) seg.segment2_seconds_worst = worst - seg.segment1_seconds;
    return { verdict: worst <= bound ? "within-bound" : "out-of-bound", flags, segments: seg };
  }

  const tr = epoch(tl.t_first_refusal);
  if (tr === null) return { verdict: "cannot-tell", flags, segments: seg };
  const d = tr - t0;
  seg.refusal_delta_seconds = d;
  if (rec !== null) seg.segment2_seconds = d - seg.segment1_seconds;
  return { verdict: d <= bound ? "within-bound" : "out-of-bound", flags, segments: seg };
}

const result = [];
for (const [file, fn] of [["p5.json", verdictP5], ["p6.json", verdictP6]]) {
  for (const row of read(file).rows) {
    const r = fn(row);
    const exp = row.expect || {};
    const expFlags = exp.flags || [];
    const same =
      r.verdict === exp.verdict &&
      JSON.stringify([...r.flags].sort()) === JSON.stringify([...expFlags].sort());
    result.push({ id: row.id, path: row.path, verdict: r.verdict, flags: r.flags, segments: r.segments, matches: same });
  }
}

const counts = {};
for (const r of result) counts[r.verdict] = (counts[r.verdict] || 0) + 1;
const mismatches = result.filter((r) => !r.matches).map((r) => r.id);

if (process.argv.includes("--json")) {
  console.log(JSON.stringify({ rows: result, counts, mismatches }, null, 1));
} else {
  for (const r of result) {
    console.log(`${r.id.padEnd(7)} ${String(r.path).padEnd(20)} ${r.verdict.padEnd(24)} ${r.flags.join(",") || "-"}`);
  }
  console.log("counts:", JSON.stringify(counts));
}
process.exit(mismatches.length === 0 ? 0 : 1);
