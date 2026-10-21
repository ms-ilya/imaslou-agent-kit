# feature-spec

Works in **Claude Code and Codex**. Install the complete plugin so its skills,
references, scripts and agent instructions stay together.

## Installation and invocation

**Claude Code** (inside the Claude Code prompt):

```text
/plugin marketplace add ms-ilya/imaslou-agent-kit
/plugin install feature-spec@imaslou-agent-kit
```

**Codex** (in a terminal with a plugin-capable Codex CLI):

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add feature-spec@imaslou-agent-kit
```

Start a new session after installation. Invoke `/feature-spec:feature-spec` in
Claude Code or `$feature-spec` in Codex. The slash examples below use Claude
Code syntax; Codex uses `$<skill-name>` with the same input and flags. Natural
language triggers apply only to skills that allow automatic invocation.
See the [kit installation guide](../../README.md#installation) and the bundled
[runtime conventions](references/runtime.md) for tool and subagent differences.

Model selection follows your host configuration, including subagent defaults.
The plugin supplies no model override; workers normally inherit the active
session's model when no host override applies. You can request a supported
model explicitly.

Independent agent stages require host subagent support. Runs with limited
delegation report that limitation.

Requires Bash and Python 3. Claude Code runs the skill’s validation hooks; Codex
runs the same checks explicitly after writes and at phase gates. Both skills
require explicit invocation.


**Turns what you already have into a critic-verified spec — and a separate
command that turns that spec into a checked implementation plan.**

Most spec tooling is a gate on the way to code, so the spec is optimised to be
*passed* rather than to be good. This one exists for the case where the spec is
the deliverable: a feature you are not building this week, a decision that needs
recording, a handoff.

You hand it what you have: a brief from an interview, a findings write-up, a
design note, or a plain idea. It builds a design record from that, checks every
claim about the repo against the code, and asks only about what is still unclear.
Complete input gets no questions at all. Then it records the strategy you chose
*and the ones you rejected*, builds a glossary, promotes hard-to-reverse decisions
to ADRs, drafts a spec, and has an independent critic score it before anything is
written.

**The spec run stops at the spec, and never learns that a plan can follow it.**
That separation is load-bearing: a spec written as a gate on the way to code gets
optimised to be *passed* rather than to be good. `/feature-spec:feature-spec-plan` is a
downstream consumer, mentioned once in the final report and nowhere else.

Sharpest on Swift/iOS, TypeScript/React and Python. Fully functional everywhere else.

---


## Commands

| Command | Runs | Writes |
|---|---|---|
| `/feature-spec:feature-spec <idea and/or documents>` | intake, clarify if needed, strategy, draft, critique, publish | `spec.md`, `tree.md`, `critique.md`, `traceability.md`, glossary, ADRs |
| `/feature-spec:feature-spec-plan <slug>` | slice a finished spec into tasks | `plan/plan.md`, `plan/tasks/T0N.md`, `plan/plan-critique.md` |

**Flags:** `--resume` · `--scope <path>`. For the plan: `--extend`,
`--tasks-only`, `--from-spec <path>`, `--out <dir>`.

**Input** is free text: an idea in words, any number of paths to documents, or
both. A document is read, not believed: every claim it makes about the repo is
checked against the code and graded confirmed, contradicted or unverifiable. It
was true when it was written, which is not evidence it is true now.

## How much it asks

That depends on what you pass, not on a mode.

| You pass | Clarifying rounds |
|---|---|
| A brief that settles every coverage category | none, and it says so |
| A document with gaps, or with a claim the code contradicts | one, about those |
| A bare idea | up to two, five questions each |

**Never more than two rounds in a session.** What is still open after that ships
in the spec as `[NEEDS CLARIFICATION]`, and the report says so. If two rounds are
not enough, the input needs work: run an interview first, or narrow the feature.
This plugin drafts specs; it is not the place for a long interview.

Three things intake does with your input:

- **A decision you made** is recorded as settled, in your own wording, tagged
  as coming from your input, and never asked again. Before drafting, the run
  lists every decision it took from your input, one line each, so a line it
  sorted wrongly is caught before it becomes a requirement.
- **A claim about the repo** is verified before anything is built on it. A
  contradicted claim is the most valuable thing the run can find, and the run
  opens the cited line itself before telling you your document is wrong.
- **An assumption or an open question** is not promoted to a decision because
  someone wrote it down. It becomes a question, or an open marker.

A document it could not open is named and left out. Nothing is inferred about
what it would have said.

A decision you made about *how* — a library, where the code lives — is kept too.
Requirements stay behaviour-only; the spec lists such a decision under
`## Implementation constraints`, with its source.

## What it produces

```
docs/specs/<YYYY-MM-DD>-<slug>/
├── spec.md            ← the deliverable
├── tree.md            ← the design record: every decision, with its reasoning
├── critique.md        ← the critic's reply, verbatim (critique.pass2.md beside it if a second pass ran)
├── traceability.md    ← requirement → decision → reasoning → where it came from
└── plan/              ← only if you run /feature-spec:feature-spec-plan
    ├── plan.md            ← approach, seams, milestones, generated task graph
    ├── tasks/T01.md …     ← one file per task; the only place a status lives
    └── plan-critique.md   ← the plan critic's reply, verbatim
docs/specs/GLOSSARY.md
docs/adr/…             ← only decisions that pass a three-part test
```

All of that is meant to be committed. The one exception is a `.work/` directory
inside the spec directory: it holds the packet the critic was handed, and it
carries an ignore file of its own, so it never shows up in version control and
nothing has to clean it up. You never supply `tree.md`; the run builds it.

`spec.md` is never typed out twice. The draft is checked and critiqued as
`spec.draft.md`, and publishing renames that file, so the spec you get is byte
for byte the one that passed.

**Date-prefixed, not `NNNN-`:** sequential numbering races when two branches both
create `0007-`.

## The plan stage

`/feature-spec:feature-spec-plan <slug>` is the only command that reads a finished spec. It
skips everything the spec run already did — research, approach options, the user
picking one — and starts where a generic planner cannot: with a verified spec, a
prioritised story list, acceptance scenarios, real seams from the grounding
facts, and a bounded set of open questions.

What it adds that a task list from any agent does not:

- **The join is proved, in both directions.** Every task tags the requirements it
  covers, and `check-plan.sh` resolves each tag against `spec.md`. Forwards: a
  task claiming `FR-042` where the spec stops at `FR-009` fails as a fabricated
  citation. **Backwards — the one that matters — every identifier the spec
  defines is claimed by some task or listed under `## Not planned` with a
  reason.** A plan that silently drops a requirement reads exactly like a plan
  that covers it, and nothing but this check can tell them apart.
- **Done-conditions are quoted, never restated.** A task's `## Done when` holds
  the spec's own acceptance scenarios verbatim, and the checker looks each one up.
  Two versions of one condition drift, and the drift always favours the easier one.
- **Open questions cannot be answered by stealth.** Every `[NEEDS CLARIFICATION]`
  the spec carries is carried into the plan, and a task waiting on one is marked
  `Blocked by` it. Quietly picking a branch in an action item is the failure R20
  exists for.
- **Implementation decisions arrive labelled as decisions.** The spec states
  behaviour and names no type, library or function by design — so every
  technology choice in the plan is new, and goes under `## Plan assumptions`
  with what reversing it would cost. The exception is a choice you made
  yourself: the spec lists it under `## Implementation constraints`, and the
  plan follows it instead of re-deciding it. An empty section on a real feature does not
  mean there were no assumptions; it means they are invisible.
- **Milestones are derived, not guessed.** The spec already guarantees P1 alone
  is a shippable slice, so M1 is the P1 tasks and nothing else.
- **Enabling work is legal and never silent.** A task no requirement asked for —
  extracting a seam, adding a migration — is listed under `## Enabling work` with
  what it unblocks. The rule is not *don't*; it is *say so*.
- **One status, in one place.** The task file owns its status; `plan.md`'s task
  graph is **generated** by `make-progress.sh`, and the checker fails if the two
  disagree.

An existing plan is never silently overwritten: the command prints its state
and stops. `/feature-spec:feature-spec-plan <slug> --extend` keeps every task and status and
adds tasks for what the spec gained; to replan from scratch, move `plan/` aside
yourself and run the command again. After an amendment you almost always want
`--extend`: a spec that gained `FR-010` does not invalidate `T01`, and a replan
that discards four completed statuses to add one task has destroyed the only
record of what was done.

**It writes the plan and stops.** No code, no `/implement`, and no estimates in
hours or days — nothing in the spec measures one, so a number there would be
invention (R11).

## The coverage taxonomy

Ten categories, scored from your input and re-scored after **every round**, each
`Clear` / `Partial` / `Missing` / `N/A`. It decides whether any question is asked
at all, turns "complete" from a feeling into a number, and gives the critic a
definition of complete that is not taste.

Problem & outcome · Scope boundary · Behaviour & flows · Domain & data ·
Interface & platform surface · Failure & edge cases · Constraints & quality bar ·
Integration & dependencies · Verification · Vocabulary

**The number has to be honest to be worth anything**, so deferral is bounded. A
category cleared by deferral prints as `Clear*` with its count, and a
**High-impact** deferral does not clear a category at all — it holds it at
`Partial`. Otherwise "no category is Missing" would be satisfiable by deferring
everything.

The *idea* of scoring against a fixed ambiguity taxonomy is spec-kit's. The
category list is this plugin's own — see Prior art.

## What makes it different

- **It reads before it asks.** What you already decided is recorded as decided
  and never shown back to you as a question. What your document claims about the
  code is checked. What it only assumed stays an assumption.
- **It survives compaction.** The design record — not the conversation — is the
  authoritative input to drafting. Every decision is written with its *reasoning*
  the moment it is known. Auto-compaction mid-run is the failure mode that kills
  this kind of tool, and it is designed around rather than hoped against.
- **It enforces the rules you already wrote down.** It reads the project's
  applicable project and user instructions from the current host (including
  scoped `AGENTS.md` in Codex and `CLAUDE.md`/rules in Claude Code), and checks
  the spec against them using the host's instruction precedence. It
  ships **no rules of its own and invents none.** A justified deviation is
  recorded with the rule quoted verbatim and what was considered instead.
- **Every requirement is traceable, and the tag is resolved rather than trusted.**
  Each `FR-NNN` and `SC-NNN` carries a source tag naming the line of the design
  record it came from, and `check-spec.sh` looks every tag up in that record: a
  spec citing `Settled Q7` when the record settled no `Q7` fails as a fabricated
  citation. Anything untraceable is cut or marked — never asserted.
- **The critic cannot rubber-stamp.** Zero blocking findings requires a list of
  what was specifically checked and found sound, citing verbatim. "Looks good" is
  not a valid return. The plan critic works the same way, against its own rubric.
- **The plan is checked against the spec, not just written from it.** See *The
  plan stage*.
- **It is resumable.** `--resume` re-anchors from the record's protocol block, in
  the same session or a fresh one.
- **A checker that did not run does not read as a pass.** `check-tree.sh` and
  `check-spec.sh` fail on any line they cannot read as an entry or a statement,
  rather than silently examining less of the file than they claim to, and a
  checker that crashed is reported as one that did not reach a verdict.
  `check-spec.sh` refuses to run at all without the design record.
- **The critic is only asked what it can see.** Its packet carries every
  statement the spec makes and the text of everything those statements cite, and
  the rubric no longer asks for a check the packet has no input for. Every quote
  in its reply is compared with the packet; a finding about words that are not
  there is discarded instead of acted on.
- **The checkers are themselves tested.** A maintainer self-test, not shipped
  with the plugin, asserts the shipped skeletons validate, then mutates one rule
  at a time and asserts that rule's specific failure fires — 237 assertions.
- **Validation distinguishes incomplete from wrong.** In Claude Code a
  `PostToolUse` hook runs the checker after writes to the record, draft, plan or
  task files. In Codex the skill explicitly runs the same check after writes. It
  runs **closed-world** checks only: assertions about what the file says, never
  about what it has not said yet. A record at the end of intake legitimately has
  no coverage table; a draft at write three of nine has no acceptance scenarios.
  A hook that called those broken would not teach compliance, it would teach
  evasion. A fabricated citation is wrong at every stage, so that still fires.
  The open-world checks run at the gate, where completeness is required.

## Interop

- **`grill-me`** — upstream, and independent. Its brief keeps what you decided
  apart from what was only assumed, which is exactly the split intake needs:
  `/feature-spec:feature-spec docs/briefs/<file>`. Neither plugin requires the other. When an
  idea is too vague to slug, this plugin names `/grill-me:grill-me` as the place to start;
  a suggestion, never a call.
- **`memory-bank`** — no conflict by construction. This plugin writes only inside
  its own spec root, so its glossary cannot collide with anything. An
  existing `memory-bank/`, `CONTEXT.md` or project glossary is **read** as
  grounding and cited; a term defined there is never redefined here.
- **`multi-agent-debate`** — when a strategy choice looks genuinely contested,
  the strategy phase points you at `/multi-agent-debate:multi-agent-debate` rather than rebuilding
  it. A suggestion, never an automatic call.
- **`ios-quick-review` / `ios-comprehensive-review`** — downstream. They review
  code this spec eventually produces.

## Non-goals

**The spec contains no plan**, and the spec run does not know one can follow it.
`spec.md` stops at what and why, with no file-by-file change list and no task
breakdown in it. *How* is a separate document, written by a separate command,
from the finished spec.

No long interview: two short rounds at most, by design. No implementation, no
TDD, no `/implement` — `/feature-spec:feature-spec-plan` writes the plan and stops. No
issue-tracker publishing. No estimates in hours, days or story points, at either
stage. No dependency on other plugins. No config file. **No rules of its own.**

## Known caveats

- **ADR numbering races.** When your project already numbers records `NNNN-`, the
  plugin scans for the highest and adds one — which two concurrent branches can
  both do. When it creates the directory itself it uses a date prefix.
- **Models and context depend on the host.** Both hosts resolve models from
  user configuration; the plugin supplies no model override. Claude Code keeps
  the registered effort settings and forks the planning skill. Codex runs
  planning in the current session from the spec and record; each critic receives
  a fresh context with only its role and packet.
  Missing independent review is reported, never presented as a critic pass.
- **Claude Code script approvals can be requested again after a round.** The skills pre-approve their checker
  scripts, and Claude Code applies that approval to the turn that invokes the
  skill. A run with no clarifying round finishes inside it. After you answer a
  round, you may be asked before a checker runs again; allow it once for the
  session.
- **The plugin never reports a token figure**, because it cannot count one, and a
  number it cannot count would be fabrication (R11). Use the host’s usage display
  when available (`/context` in Claude Code).
- **The plan cannot check that a task does what its tag claims.** `check-plan.sh`
  proves `T03` claims `FR-002` and that `FR-002` exists. Whether `T03`'s action
  items deliver `FR-002`'s behaviour is a judgement, and it is the plan critic's
  first lens rather than a script's.
- **`/feature-spec:feature-spec-plan` has one shape**, with one critic pass by default. If
  that proves wrong on large specs, the packet script already supports three
  parallel lenses.

## Upgrading from 1.x

| 1.x | 2.0 |
|---|---|
| `/feature-spec-grill` | removed. Interview with a dedicated tool such as `grill-me`, then pass its brief |
| `/feature-spec-write <slug>` | removed. `/feature-spec:feature-spec <slug> --resume` finishes an unfinished run |
| `--fast`, `--deep` | removed. The input decides how much is asked; the critic always runs once |
| `--prior-art <doc>` | removed as a flag. Pass the path; every document is checked this way |
| Up to five rounds | two per session |
| A file as a source tag (`← docs/notes.md`) | not a source. Cite the `Settled` entry or grounding fact that came from the file |
| `critique.md` as a written summary | the critic's reply, saved verbatim; a second pass is `critique.pass2.md` |

A `tree.md` written by 1.x still loads. Its `Mode:`, `Counters:` and `Guard:`
lines are ignored.

## Self-validation

The plugin ships deterministic checkers it runs on **its own output**, rather
than trusting itself to follow the rule in prose:

| Script | Runs | Enforces |
|---|---|---|
| `scripts/check-tree.sh` | end of the clarifying phase, and after every round | verbatim category names, `Clear*` with a count `## Deferred` backs, `N/A` with a reason, **an answer, a rationale and a round on each decision, entry by entry**, unique question ids, transitive deferral, a round and next phase that agree with the record, every `## Reads` entry resolving to a real file, **every `path:line` a grounding fact cites pointing at a file that exists and a line it has**, and **every decision taken from an input document naming that document and keeping its wording** |
| `scripts/check-spec.sh` | after drafting, before the critic | **every source in every tag resolved against the design record**; **a tag on every out-of-scope line and constraint**; no statement without an identifier and no section the template does not define; no requirement resting on a claim graded unverifiable; identifier stability against the spec being amended, with a renumber failing even when rewording is allowed; an acceptance scenario keyed to each requirement; no unquantified adjectives; and **the markers matching the record's deferred questions exactly**, one each |
| `scripts/check-critique.sh` | after each critic pass | the reply's shape, a verdict that agrees with its findings, `QUOTE:` and `FIX:` on every blocking finding, **every quote found in the packet the critic was given**, a clean pass that names what it checked, and a second pass that states a disposition for every finding the first raised |
| `scripts/make-packet.sh` | Phase 6 | writes the critic packet to a file the critic reads — the opening paragraph and stories, statements with their tags, **the text of every decision and grounding fact those tags cite**, scenarios, coverage with `Clear*` intact, deferrals, strategy, ADR decisions, principles verbatim and declared deviations, glossary entries, the scope boundary, the implementation constraints, the rubric, and on a second pass the first pass's findings |
| `scripts/publish-spec.sh` | Phase 7 | runs the full spec check one last time, **renames the checked draft to `spec.md`** so nothing is retyped, prints what an amendment changed, and writes `traceability.md` |
| `scripts/check-plan.sh` | after writing the plan, in a fix-until-clean loop | **every `Covers:` identifier resolved against the spec**, and **every spec identifier claimed by a task or listed under `## Not planned` with a reason**, quoted done-conditions found verbatim in the spec, real `Touches:` and seam paths, a DAG with no cycle, legal statuses, a `Blocked` task naming its blocker, an assumption naming its reversal cost, an untagged task labelled as enabling work, and **a task-graph table that agrees with the task files** |
| `scripts/make-progress.sh` | after writing or changing any task file | owns `plan.md`'s task-graph table outright — regenerates it from the task files, which are the only place a status lives. `--check` reports staleness and changes nothing |
| `scripts/make-plan-packet.sh` | Phase 10 | writes the plan-critic packet to a file the critic reads, with the first pass's findings on a second pass. `--lens` emits one lens with its own id prefix |
| `scripts/make-traceability.sh` | by `publish-spec.sh` | generates `traceability.md` — every requirement joined to its decision, reasoning and round, the decisions cited by out-of-scope lines and constraints, and any decision no line of the spec cites |
| `scripts/spec-diff.sh` | by `publish-spec.sh`, on an amendment | renders what actually changed: added, withdrawn, reworded under a stable identifier, and criteria whose numbers moved |

The checkers are run by the skill itself in a fix-until-clean loop, **and again
by a Claude Code `PostToolUse` hook or explicit Codex checks** on every write to the record, a draft, the plan or a
task file. A finding from any of them is not a critic finding — it is fixed
silently.

`scripts/lib/record.py` is the only parser of `tree.md`, of a drafted spec and of
a plan. Every checker reads through it, and the maintainer self-test asserts
they still do, because a second parser is a second thing to keep in step with
`tree-format.md`.

Each refuses to report a verdict it did not reach: if `python3` is missing or the
check cannot run to completion, it exits non-zero and says so.

## How you would know it is working

Claims are cheap; this section is the falsifiable version of the one above. The
plugin is doing its job if, over a handful of real features:

- **A complete brief gets no questions.** If the run asks about something your
  input already decided, intake failed at the one thing it exists for.
- **It contradicts your document sometimes.** A run that never finds a stale
  claim is either reading very fresh documents or not checking.
- **Specs are not amended within a week of being written.** An early amendment
  means the input and the two rounds together missed something the taxonomy
  should have flagged.
- **Fewer than a third of categories end `Clear*`.** Above that, the spec reads
  finished while being mostly open. The final report is required to say so.
- **The critic returns `fix-first` sometimes.** A critic that returns `ship`
  every single time is not a quality gate, it is a ceremony.
- **The refusal paths fire.** "This does not need a spec" and "this needs an
  interview first" are signs the tool knows its own scope.
- **`## Plan assumptions` is never empty on a real feature.**
- **`extend` is used more often than `replan`.**
- **The backwards coverage check fires at least sometimes.**

If none of those hold, the honest conclusion is that this is process theatre, and
the README should say so before the next person installs it.

## Prior art

Nothing here is vendored. The ideas below were reimplemented from scratch; this
section is courtesy, not a licence obligation.

| Idea | Origin |
|---|---|
| Design tree with a dependency-ordered question frontier | mattpocock `grilling` |
| Term challenge and a live glossary | mattpocock `domain-modeling` |
| The three-part ADR test | mattpocock `domain-modeling` |
| "Prefer the highest existing seam; the ideal count is one" | mattpocock `to-spec` |
| Scoring against a fixed ambiguity taxonomy; Impact × Uncertainty; `[NEEDS CLARIFICATION]` | GitHub `spec-kit` |
| Measurable, technology-agnostic success criteria; P1/P2/P3 independently-testable stories | GitHub `spec-kit` |
| Cross-artifact consistency checking | GitHub `spec-kit` |
| Per-feature directory; strategy proposal with user selection | `structured-plan-mode` |
| Per-feature plan directory with numbered task files; task metadata | `structured-plan-mode` |
| Cutting tasks by observable behaviour rather than by layer | common practice; stated explicitly in `references/task-slicing.md` |
| Project principles as a gate — though this plugin *reads* your file rather than generating one | GitHub `spec-kit` |
| Verbatim-citation rule; forced verdict with calibrated confidence; declared blind spot; anti-rubber-stamp check | `multi-agent-debate` (this marketplace) |

**One thing was deliberately not taken.** `structured-plan-mode` keeps a task's
status in three places at once — the task file, the plan document and a native
task list — and asks that all three be updated together. That is three chances to
update two. Here the task file owns the status and the table is regenerated from
it: recompute, never accept a self-report.

Its phases 1–3 are also absent, because the spec run already did them: research,
2–3 approach options with trade-offs, and the user picking one, with the rejected
options recorded. `/feature-spec:feature-spec-plan` starts at what that skill calls Phase 4.

## Licence

MIT, as the rest of this marketplace.
