#!/usr/bin/env bash
# ABOUTME: Validates an implementation plan against its spec — Covers tags resolved, every requirement
# ABOUTME: claimed or explicitly not planned, quoted done-conditions real, the task graph agreeing with the task files.
set -uo pipefail

usage() {
  cat <<'USAGE'
usage: check-plan.sh <plan-dir> --spec <path-to-spec.md> [options]

  <plan-dir>      the directory holding plan.md and tasks/

  --spec <path>   The spec every Covers tag and quoted done-condition must
                  resolve against. Required: a tag that cannot be resolved is
                  not a checked tag, and a check that examined nothing must not
                  report a pass — the same reason check-spec.sh demands --tree.

  --repo-root <d> Root for resolving Touches: and ## Seams paths. Default: the
                  nearest ancestor of <plan-dir> holding a .git, falling back to
                  the current directory. The hook cannot pass one — it knows only
                  the file that was written — and a path check resolved against
                  whatever the cwd happened to be would fail on every plan in a
                  repo the current session is not sitting at the root of.

  --closed-world  Check only what the plan ASSERTS, never what it OMITS.
                  A plan mid-write legitimately has three task files of six and
                  no graph table yet. Open-world checks fail on every honest
                  intermediate state, which teaches the writer to evade the
                  checker rather than satisfy it. A fabricated Covers tag is
                  wrong at task two of six exactly as it is wrong at the end.
                  Used by the PostToolUse hook. The full check runs at the gate.

Exit 0 clean · 1 findings · 2 the checker could not run.
USAGE
}

DIR=""; SPEC=""; ROOT=""; CLOSED=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --spec) [ $# -ge 2 ] || { echo "FAIL  --spec needs a path"; exit 2; }; SPEC="$2"; shift 2 ;;
    --repo-root) [ $# -ge 2 ] || { echo "FAIL  --repo-root needs a path"; exit 2; }; ROOT="$2"; shift 2 ;;
    --closed-world) CLOSED=1; shift ;;
    -*) echo "FAIL  unknown option: $1"; usage; exit 2 ;;
    *) [ -z "$DIR" ] || { echo "FAIL  unexpected extra argument: $1"; usage; exit 2; }; DIR="$1"; shift ;;
  esac
done

[ -z "$DIR" ] && { usage; exit 2; }
[ -d "$DIR" ] || { echo "FAIL  no such directory: $DIR"; exit 2; }

if [ -z "$SPEC" ]; then
  echo "FAIL  --spec is required"
  echo "      Covers tags are the whole of R18 and R19. Without the spec this"
  echo "      script can only confirm a tag is shaped like a tag, which is the"
  echo "      check a fabricated citation passes."
  exit 2
fi
[ -f "$SPEC" ] || { echo "FAIL  spec not found: $SPEC"; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "FAIL  python3 not found — check-plan.sh cannot run"; exit 2; }

# Walk up from the plan directory for the repository root. A plan that lives
# outside any repository has no root to find, and its paths resolve against the cwd.
if [ -z "$ROOT" ]; then
  probe="$(cd "$DIR" && pwd)"
  while [ "$probe" != "/" ]; do
    [ -e "$probe/.git" ] && break
    probe="$(dirname "$probe")"
  done
  if [ "$probe" != "/" ] && [ -e "$probe/.git" ]; then ROOT="$probe"; else ROOT="."; fi
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

out=$(PYTHONPATH="$HERE/lib" python3 - "$DIR" "$SPEC" "$ROOT" "$CLOSED" <<'PY'
import os, re, sys
from record import (Spec, Plan, Task, load_tasks, dependency_cycles,
                    STATUSES, IDENT, is_external_path)

plandir, specpath, root, closed = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == '1'
spec = Spec.load(specpath)
planpath = os.path.join(plandir, 'plan.md')
plan = Plan.load(planpath) if os.path.isfile(planpath) else None
tasks = load_tasks(os.path.join(plandir, 'tasks'))

fail = warn = 0
def bad(m, expected=None):
    global fail; print(f"FAIL  {m}"); fail += 1
    if expected:
        for line in expected.splitlines(): print(f"      expected: {line}")
def note(m):
    global warn; print(f"WARN  {m}"); warn += 1
def ok(m): print(f"ok    {m}")
def skip_if_closed(label):
    if closed:
        print(f"skip  {label} (open-world — not checked on a partial plan)")
        return True
    return False

COVERS_SHAPE = ("Covers: FR-003, SC-001\n"
                "an identifier the spec does not define is a fabricated citation;\n"
                "a task that covers nothing writes `Covers: —` and is listed under ## Enabling work")

# ---- the spec supplies the vocabulary everything else resolves against ----
spec_ids = [i for i, _, _, _ in spec.items()]
if not spec_ids:
    bad(f"{specpath} defines no FR-NNN or SC-NNN identifiers — is this a drafted spec?",
        "## Requirements\nFR-001  <one testable statement of behaviour>")
    print(); print("1 PROBLEM(S) — fix before writing"); sys.exit(1)
spec_set = set(spec_ids)
ok(f"spec defines {len(spec_set)} identifiers to plan against")

if not tasks and closed:
    print("ok    no task files yet — nothing asserted to check")
    print(); print("PLAN OK (closed-world)"); sys.exit(0)
if not tasks:
    bad(f"no task files in {os.path.join(plandir, 'tasks')}",
        "tasks/T01.md, tasks/T02.md — a plan with no tasks is not a plan")

def norm(s):
    return re.sub(r'\s+', ' ', s or '').strip().lower()

def _is_new(path):
    """A path the work creates rather than one it opens.

    A plan that adds a file names a path that does not exist yet, and that is not
    a hallucination — it is the point of the task. Saying so explicitly keeps the
    existence check strict for every other path, which is the half that catches
    an invented seam."""
    return bool(re.search(r'\(\s*new\s*\)\s*$', path, re.I))

spec_norm = norm(spec.text)
task_ids = {tid for tid, _ in tasks}

# ---- per task, closed-world -----------------------------------------------
covered = {}
untagged_tasks = []
for tid, t in tasks:
    where = f"tasks/{tid}.md"

    if t.ident() != tid:
        bad(f"{where}: title says {t.ident() or '(no id)'} but the filename says {tid}",
            f"# {tid} — <title>")

    st = t.status()
    if st not in STATUSES:
        bad(f"{where}: status '{st}' is not one of {', '.join(STATUSES)}",
            "Status: Planned")
    if st == 'Blocked' and not t.field('Blocked by'):
        bad(f"{where}: status is Blocked with no `Blocked by:` line",
            "Blocked by: T01   — or the open marker it waits on")

    # Covers: forwards. Every identifier a task claims must exist in the spec.
    cov = t.covers()
    raw_cov = t.field('Covers')
    if raw_cov and not cov:
        bad(f"{where}: `Covers: {raw_cov}` names no FR/SC identifier", COVERS_SHAPE)
    ghost = [c for c in cov if c not in spec_set]
    if ghost:
        for g in ghost:
            bad(f"{where}: covers '{g}' but the spec defines no such identifier "
                f"— a Covers tag that does not resolve is a fabricated citation", COVERS_SHAPE)
    for c in cov:
        covered.setdefault(c, []).append(tid)
    if not cov:
        untagged_tasks.append(tid)

    # Depends on: must name real tasks, and a task may not depend on itself.
    for d in t.depends():
        if d == tid:
            bad(f"{where}: depends on itself")
        elif d not in task_ids:
            bad(f"{where}: depends on {d}, which has no task file",
                "Depends on: T01   — or — for none")

    # Done when: quoted from the spec, never restated.
    for ident, text in t.done_when():
        if ident not in spec_set:
            bad(f"{where}: done-condition cites '{ident}', which the spec does not define",
                COVERS_SHAPE)
        elif norm(text) and norm(text) not in spec_norm:
            bad(f"{where}: done-condition for {ident} is not in the spec — "
                f"a restated condition drifts, and the drift favours the easier one",
                f"quote the spec verbatim:\n{ident}  <the acceptance scenario as written>")

    # Touches: real paths only. A seam nobody could find is a plan built on a guess.
    for p in t.touches():
        if _is_new(p):
            continue
        bare = p.split(':', 1)[0]
        full = os.path.expanduser(bare) if is_external_path(bare) else os.path.join(root, bare)
        if not os.path.exists(full):
            bad(f"{where}: touches '{p}', which does not exist",
                "a path from the record's grounding facts; a file this task creates "
                "is written 'path (new)'")

    # The same adjective rule the spec's criteria are held to. An action item
    # saying "make it fast" is the failure that rule exists for.
    ADJ = (r'\b(fast|quick|quickly|smooth|smoothly|robust|scalable|intuitive|seamless|'
           r'graceful|gracefully|responsive|efficient|reliable|simple|easy|promptly|reasonable)\b')
    for item in t.action_items():
        m = re.search(ADJ, re.sub(r'"[^"]*"', '', item), re.I)
        if m:
            bad(f"{where}: action item uses the unquantified adjective '{m.group(1)}': "
                f"'{item[:60]}'",
                "the observable change the adjective stands in for")

if not fail:
    ok(f"{len(tasks)} task file(s): ids, statuses, dependencies, quotes and paths all resolve")

cycles = dependency_cycles({tid: t.depends() for tid, t in tasks})
if cycles:
    for c in cycles:
        bad(f"dependency cycle: {' → '.join(c)}", "a task graph is a DAG; break the cycle")
elif tasks:
    ok("task dependencies form a DAG")

# ---- plan.md --------------------------------------------------------------
if plan is None:
    if not closed:
        bad(f"no plan.md in {plandir}", "plan.md — the map the task files hang off")
    else:
        print("skip  plan.md not written yet")
else:
    missing = plan.missing_sections()
    if missing and not skip_if_closed("plan.md has every required section"):
        bad(f"plan.md is missing: {', '.join(missing)}",
            "see references/plan-template.md — an empty section says so, it is never deleted")
    elif not missing:
        ok("plan.md has every required section")

    # The graph is generated from the task files. Checking it means checking
    # that the generation is current: recompute, never accept a self-report.
    rows = {r['task']: r for r in plan.graph_rows()}
    # A row for a task file not yet written is the normal state of a plan whose
    # map was drafted before its tasks. That is an assertion about absence, so it
    # belongs at the gate — a hook that fired here would punish writing plan.md
    # first, and teach buffering everything into one unreviewable Write.
    ahead = [tid for tid in sorted(rows) if tid not in task_ids]
    if ahead and not skip_if_closed("every task-graph row has a task file"):
        for tid in ahead:
            bad(f"plan.md task graph lists {tid}, which has no task file",
                f"write tasks/{tid}.md, or regenerate with make-progress.sh")
    drift = []
    for tid, t in tasks:
        r = rows.get(tid)
        if r is None:
            if not closed:
                drift.append(f"{tid} has no row")
            continue
        if r['status'] != t.status():
            drift.append(f"{tid} status: table says {r['status']}, task file says {t.status()}")
        if sorted(r['covers']) != sorted(t.covers()):
            drift.append(f"{tid} covers: table says {r['covers'] or '—'}, task file says {t.covers() or '—'}")
        if sorted(r['depends']) != sorted(t.depends()):
            drift.append(f"{tid} depends: table says {r['depends'] or '—'}, task file says {t.depends() or '—'}")
    if drift:
        for d in drift[:8]:
            bad(f"task graph has fallen behind the task files — {d}",
                "bash scripts/make-progress.sh <plan-dir>  — the table is generated, never hand-edited")
    elif rows:
        ok(f"task graph agrees with all {len(rows)} task file(s)")

    # Milestones a task claims must be declared, and vice versa.
    declared = set(plan.milestone_ids())
    for tid, t in tasks:
        ms = t.field('Milestone')
        if ms and declared and ms not in declared:
            bad(f"tasks/{tid}.md is in milestone {ms}, which plan.md does not declare",
                "- **M1 — P1 shippable slice**: T01, T02 — <what ships>")

    # R19: a task covering nothing is legal, and is never silent.
    unlabelled = [t for t in untagged_tasks if t not in plan.enabling_tasks()]
    if unlabelled and not skip_if_closed("every untagged task is labelled as enabling work"):
        for tid in unlabelled:
            bad(f"tasks/{tid}.md covers no requirement and is not listed under ## Enabling work "
                f"— R19: work nothing asked for is legal, never silent",
                "## Enabling work\n- T01 is enabling work for T02 and T03.")
    elif untagged_tasks and not unlabelled:
        ok(f"{len(untagged_tasks)} enabling task(s), all labelled")

    # R21: an assumption without its reversal cost reads as a settled decision.
    for text, cost in plan.assumptions():
        if not cost:
            bad(f"plan assumption names no reversal cost: '{text[:70]}'",
                "- <the decision> — **Reversing:** <what it would cost>")
    n_asm = len(plan.assumptions())
    if n_asm and all(c for _, c in plan.assumptions()):
        ok(f"{n_asm} plan assumption(s), each with its reversal cost")

    # Not planned must name identifiers that exist, each with a reason.
    for ident, reason in plan.not_planned():
        if ident not in spec_set:
            bad(f"## Not planned names '{ident}', which the spec does not define", COVERS_SHAPE)
        elif not reason:
            bad(f"## Not planned names {ident} with no reason — R18 asks for the reason, "
                f"and 'deferred' is not one",
                f"- {ident} — blocked on [NEEDS CLARIFICATION: <the marker>]")

    for path, tag in plan.seams():
        if _is_new(path):
            continue
        bare = path.split(':', 1)[0]
        full = os.path.expanduser(bare) if is_external_path(bare) else os.path.join(root, bare)
        if not os.path.exists(full):
            bad(f"## Seams names '{path}', which does not exist",
                "a path from the record's ## Grounding facts; a file the work "
                "creates is written 'path (new)'")

    # ---- R18, the half that matters: backwards ---------------------------
    # A plan that silently drops a requirement reads exactly like a plan that
    # covers it. Forwards resolution cannot see that; only this can.
    if not skip_if_closed("every requirement is covered or explicitly not planned"):
        not_planned = {i for i, _ in plan.not_planned()}
        orphans = [i for i in spec_ids if i not in covered and i not in not_planned]
        if orphans:
            bad(f"requirements no task covers and ## Not planned does not name: "
                f"{', '.join(orphans[:8])}{'…' if len(orphans) > 8 else ''}",
                "cover it with a task, or list it under ## Not planned with the reason (R18)")
        else:
            ok(f"every one of {len(spec_set)} identifiers is covered by a task "
               f"or listed under ## Not planned")

    # ---- R20: markers are carried, never planned around ------------------
    if not skip_if_closed("every open marker is carried into the plan"):
        spec_markers = [norm(m) for m in spec.open_markers()]
        plan_markers = [norm(m) for m in plan.open_markers()]
        dropped = [m for m in spec_markers if m not in plan_markers]
        if dropped:
            for m in dropped[:5]:
                bad(f"the spec carries an open question the plan does not: '{m[:60]}' "
                    f"— R20: a marker is carried, never planned around",
                    "## Open questions carried from the spec\n- [NEEDS CLARIFICATION: <copied intact>]")
        elif spec_markers:
            ok(f"all {len(spec_markers)} open marker(s) carried into the plan")
        else:
            ok("the spec carries no open questions")

    # A Blocked by: naming a marker must name a real one.
    for tid, t in tasks:
        b = t.field('Blocked by') or ''
        m = re.search(r'\[NEEDS CLARIFICATION:\s*(.*?)\]', b, re.S)
        if m and norm(m.group(1)) not in [norm(x) for x in spec.open_markers()]:
            bad(f"tasks/{tid}.md is blocked by a marker the spec does not carry: "
                f"'{m.group(1)[:50]}'")

print()
mode = ' (closed-world)' if closed else ''
if fail == 0:
    print(f"PLAN OK{mode}{f' ({warn} warning(s))' if warn else ''}"); sys.exit(0)
print(f"{fail} PROBLEM(S) — fix before writing"); sys.exit(1)
PY
)
status=$?

# Exit 1 is claimed by both a real finding list and a Python traceback. The
# difference is the trailer: every path that reaches a verdict prints one, and a
# crash prints none. Without this, a parser bug reads as "5 problems found".
if [ "$status" -eq 1 ] && ! printf '%s\n' "$out" | grep -qE '^(PLAN OK|[0-9]+ PROBLEM)'; then
  [ -n "$out" ] && echo "$out"
  echo "FAIL  checker did not reach a verdict — no result line in its output"
  exit 2
fi

# 0 = clean, 1 = findings the checker reported. Anything else means it never ran,
# and a checker that did not run must not read as a pass.
if [ "$status" -gt 1 ]; then
  [ -n "$out" ] && echo "$out"
  echo "FAIL  checker did not run to completion (python3 exited $status)"
  exit 2
fi

echo "$out"
exit "$status"
