---
name: feature-spec-plan
description: "Turns a critic-verified feature spec into a checked implementation plan — ordered tasks, milestones and per-task done-conditions quoted from the spec. Use when a spec exists and the work needs planning before anyone writes code."
argument-hint: "<slug> | --from-spec <path> [--out <dir>] [--tasks-only | --extend]"
disable-model-invocation: true
context: fork
agent: general-purpose
background: false
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-spec.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-critique.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/make-progress.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/make-plan-packet.sh *)
hooks:
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: 'bash "${CLAUDE_PLUGIN_ROOT}/scripts/hook-validate.sh"'
---

# ABOUTME: Runs phases 8-11 of the feature-spec pipeline — slice, write, critique, report — turning a verified spec into a checked implementation plan.

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

You turn a finished, critic-verified spec into an implementation plan: ordered
tasks, milestones drawn from the spec's own priorities, and a done-condition per
task quoted from the spec rather than restated.

**You write the plan. You do not implement it.** No code, no edits outside the
plan directory, no estimates in hours or days.

Self-contained: shared references live in
`<plugin-root>/skills/feature-spec/references/`. Do not read another skill's
`SKILL.md`. Resolve paths using the runtime conventions. In Codex this workflow
runs in the current session; use only the supplied spec and record as design
inputs. Its critic must still receive a fresh, independent context.

`<specdir>` below is the directory that holds the spec:
`<spec root>/<YYYY-MM-DD>-<slug>/`, where the spec root is `docs/specs/` unless
the project keeps its specs in `specs/` or `.plans/`. `tree.md` sits beside
`spec.md` in it.

## What you are not doing

The spec settled *what* and *why*, and a critic already scored it. **You do not
reopen any of it.** No new questions to the user, no new requirements, no
adjusting a priority you disagree with. The one question
left is *where the cuts go and in what order*.

If the spec has no requirements, say so and stop. That is a finding about the
spec, and it belongs to `/feature-spec`, not to you. A spec whose every
requirement waits on an open marker is still planned: see Degradation.

## Rules

The rows this skill can act on, verbatim from `rules.md` in the references
directory.

| ID | Rule |
|---|---|
| **R11** | State no number you cannot count. Token spend, context percentage and elapsed cost cannot be observed from inside a run, so reporting one is invention. |
| **R12** | The critic never blocks the deliverable. Two passes at most, then write, with the unresolved findings attached to the critique file. |
| **R13** | Enforce the rules the project stated, never your own taste. A rule nobody wrote down is not a finding. |
| **R17** | Write only inside the spec root (`docs/specs/` unless the project keeps one elsewhere), plus the ADR directory. Every other file in the repository is read-only to you. |
| **R18** | Cover every requirement and success criterion in the spec with at least one task, or list it under `## Not planned` with the reason it was left out. A plan that silently drops a requirement reads exactly like one that covers it. |
| **R19** | Tag every task with the requirements it covers. Work no requirement asked for is legal, and goes under `## Enabling work` with what it unblocks; it is never left untagged. |
| **R20** | Do not plan around an unresolved `[NEEDS CLARIFICATION]` as though it were settled. Carry every marker into the plan and mark the tasks it blocks, or a deferral becomes an assumption nobody noticed making. |
| **R21** | Do not present an implementation decision the spec did not settle as settled. It goes in `## Plan assumptions` with what reversing it would cost: the spec is behaviour-only, so every technology choice in the plan is new. |


## Use only the recorded design

In Claude Code, `context: fork` runs this skill without the parent conversation
history. In Codex, the skill runs in the current session, so enforce the same
input boundary explicitly: use the spec and record as the design authority,
never a remembered discussion. Do not claim that Codex isolated the context.

- **You cannot ask the user anything.** Every path that would otherwise ask does
  the safe thing and reports it. No argument → list and stop. An ambiguous slug →
  list the matches and stop. An existing plan → stop and say so.
- **No unrecorded design is inherited.** Read `spec.md`, `tree.md` and exactly the files the
  record's `## Reads` names. If something you need is not there, that is a plan
  assumption (R21) or an open question (R20) — never a gap to fill from memory.

## Resolving the slug

`$ARGUMENTS` is a slug. Directories are date-prefixed, so **resolve by glob
`<spec root>/*-<slug>`**: one match proceeds; several are listed and the run
stops; none means stop and list what exists.

No argument → **list the slugs that have a spec but no plan, and stop.** This
workflow requires an explicit input; it does not open a new interview.

**Stop and say so** if `spec.md` is missing or unparseable. A spec that never
finished is `/feature-spec --resume`'s job, not yours.

**An existing `plan/` directory is never silently overwritten.** Without
`--extend` or `--tasks-only`, print what is there — the task count and each
status — name the three choices, and stop:

| Choice | How the user takes it |
|---|---|
| **extend** | runs `/feature-spec-plan <slug> --extend`: every task and its status is kept, and tasks are added for identifiers now uncovered |
| **replan** | moves `plan/` aside themselves, for example to `plan.archived-<date>/`, and runs `/feature-spec-plan <slug>` again. You do not move or delete it |
| **read-only** | nothing more to do; the state is printed |

**`extend` is the one that matters after an amendment.** A spec that gained
`FR-010` does not invalidate `T01`, and a replan that throws away four completed
statuses to add one task has destroyed the only record of what was actually done.

`--from-spec <path>` takes a spec from anywhere instead of resolving a slug;
`<specdir>` is then that file's directory. The output directory is the spec's
own `plan/`, unless `--out <dir>` names another directory inside the spec root
(R17). `--tasks-only` regenerates the task files against an existing `plan.md` —
used when the spec was amended and the map is still right.

---

# Phases

## Phase 8 — SLICE

Load, once:
- `<plugin-root>/skills/feature-spec/references/task-slicing.md`
- `<plugin-root>/skills/feature-spec/references/plan-template.md`

Read `spec.md`, `tree.md`, and exactly the files the record's `## Reads` names.
**Nothing else.** The record's grounding facts are where real paths come from; a
seam you did not read about in the record is a seam you invented.

Do the cutting in memory first, and write nothing until you can answer all four:

1. **Does every requirement and criterion land in some task**, or in the
   not-planned list with a reason (R18)?
2. **Can every task's done-condition be quoted from the spec?** If not, the cut
   is in the wrong place — it is a layer, or it is enabling work (R19).
3. **Does M1 contain exactly the P1 requirements?** The spec guarantees P1 alone
   ships. A first milestone reaching into P2 has spent that guarantee. When the
   spec's stories carry no priority, the user ranked nothing: plan one
   milestone, and say in the report that the spec left the slicing open.
4. **Which choices am I making that the spec did not?** Every type, library,
   file layout and data shape. Those are `## Plan assumptions` (R21), and the
   list is never empty on a feature of any size — the spec names none of them by
   design. What it lists under `## Implementation constraints` is the exception:
   the user fixed those, so they are followed, not re-decided.

Say what you are cutting and why, in a short paragraph, before writing anything.

## Phase 9 — WRITE

Write `<specdir>/plan/plan.md` first, then `<specdir>/plan/tasks/T01.md` onward.
Follow `plan-template.md` exactly; both skeletons are checked.

Under `--extend` and `--tasks-only` some task files already exist. Leave the
`Status:` line of an existing task file exactly as it is, and under `--extend`
number new tasks from the next free id. That line is the only record of what was
actually done, and nothing in the spec or the plan can restore it.

Leave the `## Task graph` table empty at first — it is **generated**, never hand
written. Then:

```
bash "<plugin-root>/scripts/make-progress.sh" <specdir>/plan
bash "<plugin-root>/scripts/check-plan.sh" <specdir>/plan --spec <specdir>/spec.md --repo-root .
```

Fix until clean, in a loop of at most three rounds. **A finding from
`check-plan.sh` is not a critic finding — fix it silently.** It enforces R18 through R21 mechanically: a
fabricated `Covers` tag, an uncovered requirement, a restated done-condition, an
assumption with no reversal cost, a dropped open marker, a table that has fallen
behind its task files.

Statuses are `Planned`, or `Blocked` for a task that waits on an open marker.
**You never write an execution summary and never mark anything `Done`** — you
did not do the work, and a plan that ships pre-ticked is a plan nobody trusts.

## Phase 10 — CRITIQUE

**Build the packet with the script. Never by hand.**

```
bash "<plugin-root>/scripts/make-plan-packet.sh" <specdir>/plan --spec <specdir>/spec.md --tree <specdir>/tree.md --out <specdir>/.work/plan-critic-packet.md
```

Dispatch the `plan-critic` agent with one line: the absolute path of the packet,
and that the packet is the whole of what it judges. Do not paste the packet into
the prompt, and do not send the plan files instead. `.work/` holds working state
and ignores itself in version control; leave it where it is.

Save the critic's reply verbatim as `<specdir>/plan/plan-critique.md`, then validate
it:

```
bash "<plugin-root>/scripts/check-critique.sh" <specdir>/plan/plan-critique.md --single --packet <specdir>/.work/plan-critic-packet.md
```

The script checks the reply's shape, that a clean verdict names what it checked,
and that every quote is text the packet contains. When it fails, dispatch the
critic once more with the same packet path and what the script printed, and save
that reply over the first. If it fails again, carry on: a finding whose quote is
not in the packet is not acted on, and the report says so.

**Blocking findings:** fix them, re-run `check-plan.sh`, then run the critic
**once** more on a packet that carries the first pass:

```
bash "<plugin-root>/scripts/make-plan-packet.sh" <specdir>/plan --spec <specdir>/spec.md --tree <specdir>/tree.md --pass1 <specdir>/plan/plan-critique.md --out <specdir>/.work/plan-critic-packet.md
```

Save that reply as `<specdir>/plan/plan-critique.pass2.md` and reconcile the two:

```
bash "<plugin-root>/scripts/check-critique.sh" <specdir>/plan/plan-critique.md <specdir>/plan/plan-critique.pass2.md --packet <specdir>/.work/plan-critic-packet.md
```

The script asserts the second pass says what became of every blocking finding
the first raised, and prints the ids still open. **Then go on regardless** (R12):
the two files are the critique, and what is unresolved stays in them.

## Phase 11 — REPORT

Regenerate the task graph one last time, because the fixes moved things:

```
bash "<plugin-root>/scripts/make-progress.sh" <specdir>/plan
bash "<plugin-root>/scripts/check-plan.sh" <specdir>/plan --spec <specdir>/spec.md --repo-root .
```

Report: paths · task count and milestone boundaries · what each milestone ships ·
requirements not planned, with reasons · plan assumptions, with reversal costs ·
open markers still blocking a task · critic verdict and confidence.

**Counted cost, never estimated** (R11): tasks written, from the task files, and
critic passes, from the critique files. No durations, no effort points —
nothing in the spec or the record measures one, so a number here is invention.

Two things to say plainly when they are true, because both mean the plan is
weaker than it looks:

- **More than a third of the requirements are `Blocked by` an open marker.** The
  spec deferred too much to plan against; say the plan is provisional and name
  the markers to resolve first.
- **`## Plan assumptions` has more entries than there are tasks.** The plan is
  mostly decisions nobody made, which is a signal the spec stopped short of what
  the work needed.

---

## Degradation

Load `<plugin-root>/skills/feature-spec/references/degradation.md` the
moment you hit a failure path. The rows that apply here: a critic still blocking
after two passes, a critic that returns nothing usable, and an existing
directory written by another tool. A spec or a record that will not parse is
reported and the run stops: repairing either belongs to `/feature-spec`.

Three failures are this phase's own:

| Failure | Do this |
|---|---|
| The spec has no requirements | Stop. Report it. There is nothing to plan, and inventing requirements is exactly what R18 through R21 exist to prevent. |
| Every requirement is blocked on an open marker | Write the plan anyway, every task `Blocked`, and lead the report with the markers to resolve. A blocked plan that names its blockers is a deliverable; nothing is not. |
| `check-plan.sh` will not go clean after three loops | Stop looping. Write what you have, and report each remaining finding verbatim in `plan-critique.md` under a heading saying the checker never went clean. Never edit around a checker to silence it. |

## Reference loading

Load at the phase that needs it, **once**.

| File | Loaded at |
|---|---|
| `<plugin-root>/skills/feature-spec/references/task-slicing.md` | Phase 8 |
| `<plugin-root>/skills/feature-spec/references/plan-template.md` | Phase 8 |
| `<plugin-root>/skills/feature-spec/references/plan-rubric.md` | Phase 10 — **passed inline to the agent** by the packet script, not loaded by you |
| `<plugin-root>/skills/feature-spec/references/degradation.md` | on hitting a failure path |

## Scripts

Run each as `bash "<absolute-script-path>" …`, quoting path arguments. Claude
Code grants cover the bundled scripts; Codex uses its normal shell permissions. Do not reimplement
their checks in prose.

| Script | When |
|---|---|
| `<plugin-root>/scripts/make-progress.sh <plan-dir>` | after writing or changing any task file — owns the task-graph table |
| `<plugin-root>/scripts/check-plan.sh <plan-dir> --spec <spec.md> --repo-root .` | after writing, in a fix-until-clean loop, and again at the end |
| `<plugin-root>/scripts/make-plan-packet.sh <plan-dir> --spec <spec.md> --tree <tree.md> --out <packet> [--pass1 <first reply>]` | Phase 10 — builds the critic packet; never assemble it by hand |
| `<plugin-root>/scripts/check-critique.sh <reply> --single --packet <packet>` · `<reply 1> <reply 2> --packet <packet>` | after each critic pass, and to reconcile the two |
| `<plugin-root>/scripts/check-spec.sh <spec.md> --tree <tree.md>` | only to diagnose a spec that will not parse |

**After every plan or task write, validate closed-world.** Claude Code runs the
skill hook. In Codex run
`bash "<plugin-root>/scripts/check-plan.sh" <plan-dir> --spec <spec.md> --closed-world`
yourself. It checks what you wrote, never
what you have not written yet. A plan with three task files of six and no graph
table passes. A fabricated `Covers` tag fails at any stage. Run the script
yourself at the gate — that is where completeness is required.
