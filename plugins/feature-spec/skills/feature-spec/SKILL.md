---
name: feature-spec
description: "Turns what the user provides into a critic-verified feature spec: builds a design record from the input, asks only about what is still unclear, then drafts, critiques and writes. Use when planning a feature before any code is written, or to amend an existing spec."
argument-hint: "<idea and/or documents: a brief, notes, an analysis> [--resume] [--scope <path>]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
  - SendMessage
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-tree.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-spec.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/make-packet.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-critique.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/publish-spec.sh *)
hooks:
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: 'bash "${CLAUDE_PLUGIN_ROOT}/scripts/hook-validate.sh"'
---

# ABOUTME: Turns the user's input into a critic-verified feature spec — intake, clarify only what is unclear, strategy, draft, critique, publish.

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

You turn what the user already has into a verified feature spec: take in their
input → build the design record → ask only about what is still unclear → choose a
strategy → promote decisions → draft → critique → publish.

The run adapts to the input. A complete brief needs no interview and goes
straight through. A bare idea gets up to two short rounds. You stop at the spec:
no implementation, no task breakdown, no estimates.

References live in `<skill-dir>/references/`. A reference named below without
a path is in that directory. Resolve all paths using the runtime conventions.

**Input:** `$ARGUMENTS`

## Rules

The rows this skill can act on, verbatim from `rules.md`.

| ID | Rule |
|---|---|
| **R1** | Write every decision and its rationale to `tree.md` before rendering the next round and before any other tool call: at intake for what the input already decided, then once per round. Whatever exists only in the conversation is gone after a compaction. |
| **R2** | Find facts before a round, never during one. A prompt that is open to the user cannot be held while an agent runs. |
| **R4** | Give every question a recommended answer and one line naming what the answer changes. Without them a round reads as a form. |
| **R6** | Report counted cost when the run ends: clarifying rounds and critic passes. Both can be counted from the files the run wrote. |
| **R8** | Do not ask the user what a fact-finder could look up, or what their own input already answers. One such question costs the trust every other question depends on. |
| **R9** | Ask at most 5 questions in a round and run at most 2 rounds in a session. What is still open after that ships as `[NEEDS CLARIFICATION]`: an interview that keeps growing means the input needs work, not that the run needs more rounds. |
| **R10** | Every requirement, success criterion, out-of-scope line and implementation constraint in the spec carries a source tag that resolves in `tree.md`. Cut anything that does not, or mark it `[NEEDS CLARIFICATION]`: a spec asserting what was never decided is the failure this plugin exists to prevent. |
| **R11** | State no number you cannot count. Token spend, context percentage and elapsed cost cannot be observed from inside a run, so reporting one is invention. |
| **R12** | The critic never blocks the deliverable. Two passes at most, then write, with the unresolved findings attached to the critique file. |
| **R13** | Enforce the rules the project stated, never your own taste. A rule nobody wrote down is not a finding. |
| **R14** | Write an ADR only for a decision that passes all three tests: hard to reverse, surprising without context, the result of a real trade-off. A long decision record is a worthless one. |
| **R15** | Never silently overwrite an existing spec. Offer amend, restart or read-only, and wait for the choice. |
| **R16** | Never silently skip a phase. When the clarifying phase or the strategy phase does not run, say so and say why. |
| **R17** | Write only inside the spec root (`docs/specs/` unless the project keeps one elsewhere), plus the ADR directory. Every other file in the repository is read-only to you. |

One thing holds in every phase. Nothing enters the record or the spec because
it is likely. A fact about the repository was looked up, and says where. A
decision was made by the user, and keeps their words. Anything else stays open:
on the frontier, deferred, or marked `[NEEDS CLARIFICATION]`. An open question
costs the user a follow-up; an invented answer costs them the feature.

## The design record

Two directories, and the difference matters. The **spec root** holds every
spec in the project and the shared glossary: `docs/specs/` by default. This
feature's own directory, written `<specdir>` everywhere below, is
`<spec root>/<YYYY-MM-DD>-<slug>/`. Dates are today's, as the session gives it.

`<specdir>/tree.md` is the only input to drafting. You build it from whatever
arrives; the user never has to supply one. `Next phase` in its `## Protocol`
block names the phase to resume at: `1` when the record is created, then the
next number as each phase completes, so a later session can pick the run up
with `--resume`.
A run is in progress while `<specdir>/spec.draft.md` exists and finished once
only `spec.md` does.

In Claude Code, a `PostToolUse` hook checks every write to the record and draft.
In Codex, after each write run the matching closed-world check yourself:

- `bash "<plugin-root>/scripts/check-tree.sh" <specdir>/tree.md --closed-world`
- `bash "<plugin-root>/scripts/check-spec.sh" <draft> --tree <specdir>/tree.md --closed-world`

Run these checks before continuing to the next workflow step. They check
what you wrote, never what you have not written yet, so a half-written record
passes and a fabricated citation fails at any stage. Run the scripts yourself at
the points named below: that is where completeness is required. A finding from a
script or the hook is not a critic finding. Fix what it names and carry on.

## Phase 0 — RESOLVE

Load `invocation.md`.

Work out what you were given: the idea in words, and every path that names a
document. Read the documents now; the two stop cases below and the feature's
scope depend on what they say. A path that does not exist is named to the user
and left out; what it would have said is unknown. Then detect the rest by
looking. The table says what
to establish, not how; how deep to search is a judgement about this repository.

| Thing | Default | Detection wins |
|---|---|---|
| Spec root | `docs/specs/` | existing `docs/specs/`, `specs/`, `.plans/` |
| Glossary | `<spec root>/GLOSSARY.md` | never overridden. An existing root glossary or `memory-bank/` is read and linked, never written |
| ADR directory | `docs/adr/` | existing `docs/adr/`, `docs/adrs/`, `adr/` |
| Stack layer | none | within the feature's scope (`--scope`, or the directories the input names), by content: `.swift`, `Package.swift`, `*.xcodeproj`, `*.xcworkspace` → `swift` · `tsconfig.json`, `.ts`, `.tsx` → `typescript` · `pyproject.toml`, `requirements.txt`, `.py` → `python`. A layer is for an application in that stack: a shell script that embeds Python, or a build file, loads none. When unsure, none |
| Principles | none | instructions already supplied by the host, then applicable project `AGENTS.md` / `AGENTS.override.md`, `CLAUDE.md` and conditional rule files. In Claude Code include applicable user instructions under `~/.claude/`; in Codex include the host-provided global instructions (normally under `~/.codex/`, or its configured home). Follow the host’s precedence and directory scope; do not activate unrelated language rules or load another host’s personal settings as instructions |
| Version control | — | whether a `.git` directory sits at or above the spec root. An amendment replaces `spec.md`, so without history the previous version is gone: say so before amending |

An existing slug offers three choices (R15):

- **amend**: append a session to the record, reopen deferred items, strike
  through superseded answers, draft again.
- **restart**: copy `tree.md` to `tree.archived-<date>.md`, then start the
  record again. The `## Sessions` line says `(restart)`.
- **read-only**: print the state, stop.

On amend, and on `--resume`, load `tree-format.md` now. Both work on a record
that already exists, and a resumed run can re-enter past Phase 1, where every
other run loads it.

Two cases stop here, before anything is created:

- **The idea is too vague to name.** Ask one clarifying question and stop. An
  unformed idea needs an interview before it needs a spec: say so, and name
  `/grill-me` as the tool for that. A suggestion, never a call.
- **A one-line change with no decision in it.** Say there is nothing here a spec
  would decide, and stop. If the user disagrees, the run goes on.

Otherwise say in a few lines what you received and what you resolved. Nothing is
written in this phase.

## Phase 1 — INTAKE AND GROUND

Load `tree-format.md` unless Phase 0 did: this phase creates the record, and
that file is the shape of every entry in it.

Sort what each document says, and what the request itself says:

- **A decision the user made** becomes a `## Settled` entry tagged `(r0)`. The
  answer keeps the input's own wording. Its `*Why:*` ends with where it came
  from: the document's path as `## Reads` lists it and the section, or "stated
  in the request". The validator holds the answer against that document and fails a
  paraphrase, because the entry is what every requirement is later compared
  with.
- **A claim about the repository** is something to verify, not to believe. A
  document was true when it was written.
- **An assumption or an open question** is not a decision. It goes to the
  frontier.

Then create `<specdir>` and write `## Problem`, `## Protocol` (`Round: 0 of 2`),
`## Reads`, `## Sessions` and the `(r0)` entries to `tree.md`, before dispatching
anything (R1). `## Reads` lists what drafting will need, and only files that
exist: the input documents, each principles file you take a rule from, and
later the glossary and any ADR that bears on this feature. An ADR about another
part of the project is not a drafting input. Source code does not go there:
grounding facts carry what drafting needs from it.

On a stack detection, load that stack's two `references/<stack>/` files before
dispatching; they say what to look for. Exactly one layer loads, or none. When
the scope spans two stacks, ask which side the feature lives on first.

A source file the input names is yours to read when it is short enough to read
whole; record what you find as `(read at intake, r0, high)`. Fact-finders are
for what lies beyond it: other files, call sites, conventions, whether something
exists. Do not send a question you have already answered.

Dispatch fact-finders in **one message** so they run together: one for
questions a search settles (a path, a name, whether something exists) and one
for questions that need code read and understood. Use `feature-spec:fact-finder`
in Claude Code; in Codex load `<plugin-root>/agents/fact-finder.md` into a fresh
worker. Let the host resolve the model for either kind under the runtime policy.
Dispatch only the kind you have questions for, and none when there is no code to
ground in. Each gets specific questions, any claims the input makes to grade as
confirmed, contradicted or unverifiable, and the scope path when there is one.
Never "sweep the repo". Keep a dispatch to about six questions and claims; an
agent given more runs out of turns and returns nothing, so split a longer list
across a second dispatch of the same kind.

A return that does not contain `Q:` / `FACT:` / `EVIDENCE:` / `CONFIDENCE:` /
`NOT_FOUND:`, plus `VERDICT:` for a claim, is not an answer. Continue the worker
once with the host's follow-up/resume tool, asking for the report in the schema,
and only then treat the dispatch as failed. A message that does not start a
new turn is not a retry.

Read the glossary, the ADR directory and the principles files yourself: they are
small and needed verbatim.

Add `## Grounding facts` and `## Principles in force` to the record. A fact
cites its `path:line` from the repository root; the validator fails a citation that
points at no file. Before you tell the user their document is wrong, open the
cited line yourself: a contradicted claim is the most valuable thing this phase
produces, and the one that costs most when it is mistaken.

Then show the user, briefly: what you found and what it made unnecessary to
ask, every contradicted claim, and the decisions you took from their input, one
line each. That list is everything the spec will be built on, and this is where
a mis-sorted line is cheapest to catch. Do not wait for a reply; go on.

## Phase 2 — CLARIFY *(only when the input leaves something open)*

Load `coverage-taxonomy.md` and `frontier.md`.

1. Score coverage from the record, using the taxonomy's category names verbatim,
   and write the table to `## Coverage`.
2. Build the frontier: categories that are Missing or Partial, contradicted
   claims, the input's own open questions, and, when there is more than one
   user-visible behaviour, behaviours the input did not rank. Apply the
   frontier's "earns a slot" test to each. Write `## Frontier`, `## Blocked` and
   `## Deferred`; a list with nothing in it keeps its heading and stays empty.
3. **Decide whether to ask at all.** If no category is Missing and nothing
   high-impact is on the frontier, no round runs. Move what is left on the
   frontier to `## Deferred`, each with a question id and `(r0)`, and score a
   category they leave open as `Clear* (n deferred)`. Say in a line or two (R16)
   what the input already settled and what was deferred. Go to Phase 3.
4. Otherwise render a round. Load `question-format.md` the first time. Take
   the top questions by Impact × Uncertainty, five at most (R9). A term an
   answer hinges on is challenged inside the question that uses it, two per
   round at most. The Phase 1 summary is the round's grounding block; do not
   write it twice.
5. Append every answer and its rationale to `tree.md` with `Edit` (R1). Write a
   glossary entry for each term that resolved; load `glossary-format.md` on the
   first.
6. Re-score coverage and update `Round` and `## Sessions`.
7. Validate, and fix until clean:
   `bash "<plugin-root>/scripts/check-tree.sh" <specdir>/tree.md`

A second round runs only if a category is still Missing or a high-impact question
is still open. After two rounds, everything left moves to `## Deferred`. A
category still Missing then gets one deferred question of its own, so it ships
as an open question like any other.

Deferral is transitive: deferring a question defers everything blocked behind it,
in one step. A category is `Clear*` only if nothing high-impact in it was
deferred, and prints with its count everywhere.

When no round ran, run `check-tree.sh` once here before going on.

## Phase 3 — STRATEGY

Skipped when exactly one approach is viable. Say so to the user, with the
reason (R16), and leave `## Strategy` out of the record.

Otherwise propose 2–3 approaches with their trade-offs. Use the host’s question
tool. In Claude Code, `preview` blocks of at most 12 lines can show shape, not
code. In Codex, put the same comparison in supported question text or chat; do
not send unsupported `preview` or `multiSelect` fields. Record the
chosen approach and the rejected ones, with reasons.

If the choice is contested and hard to reverse, point at `/multi-agent-debate`.
A suggestion, never a call.

## Phase 4 — PROMOTE DECISIONS

Load `adr-format.md` only if a candidate exists. Apply R14's three tests; a typical run promotes zero or one.

Write qualifying ADRs as `Status: Proposed`, with a back-link to `<specdir>` and
a name that matches the directory's own convention. Add them to `## Reads`.

## Phases 5 to 7 — DRAFT, CRITIQUE, PUBLISH

Load `drafting.md` and follow it.

Read `tree.md` and exactly the files its `## Reads` names. Nothing else: not the
conversation, not `## History`. Every requirement, criterion, out-of-scope line
and constraint carries a source tag naming the record entry it came from (R10),
and says no more than that entry says.

## Scripts

Run each as `bash "<absolute-script-path>" …`, quoting path arguments. Claude
Code grants cover the bundled scripts; Codex uses its normal shell permissions. Do not reimplement
their checks in prose.

| Script | When |
|---|---|
| `<plugin-root>/scripts/check-tree.sh <tree.md>` | end of Phase 2, and after every round |
| `<plugin-root>/scripts/check-tree.sh <tree.md> --doctor` | only when the record will not parse; it names the broken section |
| `<plugin-root>/scripts/check-spec.sh <draft> --tree <tree.md> [--prev <spec being amended>]` | after drafting, before the critic |
| `<plugin-root>/scripts/make-packet.sh <draft> --tree <tree.md> --out <specdir>/.work/critic-packet.md [--pass1 <first reply>]` | Phase 6; the critic reads the file |
| `<plugin-root>/scripts/check-critique.sh <reply> --single --packet <packet>` · `<reply 1> <reply 2> --packet <packet>` | after each critic pass, and to reconcile the two |
| `<plugin-root>/scripts/publish-spec.sh <specdir> [--allow-reword \| --fresh]` | Phase 7; turns the checked draft into `spec.md` and writes `traceability.md` |

## References

Each phase above names the reference it loads; load each once. Two are not
named there:

- `degradation.md`: load it the moment you hit a failure path, or are about to
  invent one. Every failure path degrades toward producing something, and none
  is papered over silently.
- `critic-rubric.md`: never loaded by you. `make-packet.sh` inlines it for the
  critic.
