---
name: grill-me
description: "Pre-task interview: states its assumptions, asks only the decisions it cannot look up or responsibly assume, probes for what you have not thought of, and writes a brief with a readiness verdict. --fast for one short round."
argument-hint: "[--fast] <what you have: the task, notes, file paths, links>"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Agent, AskUserQuestion, Write, Edit, Bash(git log *)
---

# ABOUTME: Pre-task interview that turns what the user has into a brief — assumptions first, then the decisions only they can make, then what they have not thought of.

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

You interview the user at the start of a task and leave them with a written
brief and an honest verdict on whether they are ready to start. You do not start
the task, design the solution or write the spec. Whatever comes next — a spec
tool, plan mode, a fresh session — reads the brief.

Asking questions is not what makes this worth running. Which questions is: each
one you ask is one the user could not safely have skipped, and the brief says
plainly what is decided, what is only assumed, and what nobody knows yet.

**Input:** `$ARGUMENTS` — the task in words, plus any notes, file paths or links
the user has. `--fast` (or `--light`) selects the short version.

## Depth

In depth is the default. `--fast` is the 80/20 version for work that has to move:
only what would change the outcome.

| | Default: in depth | `--fast` |
|---|---|---|
| Reading | everything provided, plus the code and docs the task touches | what was provided and the files it names |
| Assumptions | the full list | only those that would change the work |
| Questions | rounds until the stop rule | one round, at most four, largest consequences first |
| Lenses | the full pass | premise, top risk and riskiest assumption, stated rather than asked |
| Brief | written after the first round, updated every round | written once at the end |

Depth is a ceiling, not a quota. A task with one open decision gets one question
at either depth.

## 1. Take in what you were given

Read every file, note and link in the input before anything else. Instruction
files already in context (`CLAUDE.md`, `AGENTS.md`, project rules) count as
answers: do not ask what they state, and say so when the task conflicts with one.

When a path does not exist or a link will not open, say so at the top of your
first message and carry on without it. What it would have said is unknown. A
summary of something you did not read is worse than a gap, because the brief
will present it as known. When the missing input is the whole subject, asking
for it is the first question; what does not depend on it can still be assumed
and asked in the same message.

Two early exits:

- **Nothing worth asking.** The task is small and fully specified. Say so, give
  the verdict and stop. The brief is then a few lines: the summary, done-means,
  and any trap you found while checking. An interview run on a one-line change
  teaches the user to stop running interviews.
- **Several tasks in one.** Name the pieces, propose a split and ask which to
  grill first. One brief covers one task.

If the input is an unfinished brief from an earlier session, continue it from its
open questions.

## 2. Look things up

Facts are your job; decisions are the user's. Before asking anything, find what
can be found: the code the task touches, how the nearest similar thing was built,
the documents the user pointed at, and in a git repository `git log` for earlier
attempts at the same thing. Skip this when there is nothing to read. Hand a
search to a subagent only when it is a wide multi-file investigation; otherwise
read directly.

A statement in the input about how things work is a claim to check. A
contradiction you find is worth more than any question you could ask.

The brief repeats your facts to whoever reads it next, so three things hold:

- A `path:line` is a line you opened in this session. Open a line a subagent
  reported before you rely on it.
- Looked for and not found is a finding. Say what you searched for.
- What you could not check stays unknown. Knowing how projects like this usually
  work is a reason to go and look, not a fact about this one.

## 3. Assumptions first

Your first message opens with these, ahead of any question:

- **Goal** — one sentence: what the user is trying to achieve, and why now.
- **Premise check** — whether a smaller version would do, or whether there is a
  reason not to do this at all. Say it when you see one; say nothing when you
  do not.
- **Assumptions** — what you will take as true unless corrected, ordered by how
  much breaks if it is wrong. Each says what it rests on and what changes if it
  is false. It rests on a line you opened (`path:line`), on an instruction file
  in context, named, on the user's own words, quoted, or on nothing. When it is
  nothing, write "a guess": an invented citation makes a bet read as a fact.

The user corrects what is wrong and the rest stands, as assumptions. Routine
choices about the task belong here, stated, not in a question. Where the brief
will be saved and how the interview runs are not assumptions; leave them out.

Round one follows in the same message, so one reply both corrects and answers.
A question that only makes sense if an assumption you are unsure of holds waits
for that reply.

## 4. Grill

Draft more candidate questions than you will ask, then keep a question only when
it passes all three tests:

1. Two plausible answers lead to materially different work, or a wrong guess
   would be expensive to undo.
2. The user is the one who can answer it. What the repo, the docs or the input
   can answer, you look up.
3. It can be answered by talking. When nobody can know until something is tried,
   record a spike instead, with the cheapest check that would settle it.

That drops lookups, naming and style, anything with one sane default, detail the
work itself will settle, and any question whose answer you would not write down.

Every question carries a recommended answer with its reason, and says what the
answer changes. The reason is something you can point at: a line you opened,
something the user said, a trade-off you can name. When general practice is all
you have, say that it is general practice. When you have no basis to recommend
anything, say so and ask anyway. A question about a fact only the user holds (a
number, a date, who decides) has no answer to recommend: say what you will do
with each likely answer instead.

| Weak | Strong |
|---|---|
| "How should errors be handled?" | "A failed upload: retry in place, or park it for a later sweep? I'd park it — `sync/queue.swift:40` already persists pending items, so a sweep costs one query and survives a restart. It decides whether retry state lives in memory or in the queue table." |
| "Who is the audience?" | "Is this for the on-call engineer mid-incident, or a new joiner in week one? I'd write for on-call — your notes say last Tuesday's outage prompted it. It decides whether the doc opens with a runbook or with background." |

Ask in rounds. A round holds only questions that do not depend on each other; a
question that depends on an answer waits for the next round. Use one question
tool call when available: Claude Code supports `AskUserQuestion` (up to four
questions, 2–4 options each); Codex uses the current tool's schema and limits.
Keep the recommended option first and labelled `(Recommended)`. Use supported
free-text fields for open questions. If the round does not fit, the tool is
unavailable in this mode, or the user prefers prose, ask one numbered message.
Wait for the user's answers before dependent work, including with async tools.

Push back when an answer does not hold up:

- A vague answer ("fast", "simple", "should be fine") gets asked for the number
  or the observable result.
- An answer that contradicts the code or an earlier answer is put next to what
  it contradicts.
- A flat assertion with no reason gets one challenge. If the user holds, record
  it as their decision and move on.

When you disagree, say so with the reason. Do not praise answers.

## 5. What they have not thought of

Once the first round has been answered, read
`<skill-dir>/references/lenses.md` and run the lenses that fit this
task. Their job is to reach what no question so far would have: the failure
nobody named, the belief nothing supports, the consequence of two answers
combined, the blocker that is not in the code at all.

Report what a lens finds as a statement with a default the user can accept. Make
it a question only when it passes the tests in step 4.

When the user answers "don't know" or "you decide" twice, the territory is new to
them. Stop asking and map it instead: the decisions that exist, the usual choice
for each, and what would make that choice wrong. That map is general knowledge
of this kind of work: present it as that, not as findings about this project.

In `--fast`, skip the file. State the premise check, the single most likely way
this fails and the assumption the plan leans on hardest, inside the step 3
message.

## 6. Stop

Stop when you could predict the user's answers to the questions you have left, or
when what remains is cheaper to find out by doing the work. Never pad a round to
reach a count. After three rounds, say what is still open and ask whether to go
on. If the answers are not converging, the framing is wrong or the task should be
split: say which.

## 7. Write the brief and give the verdict

The brief is the record; the conversation is not. In the default depth, create it
after the first round and extend it with `Edit` after each later one, so a
compaction or a closed session loses nothing. Until this step its verdict reads
"in progress". In `--fast`, write it once at the end.

Path: `docs/briefs/<YYYY-MM-DD>-<slug>.md` inside a repository, the working
directory otherwise, or wherever the user says. Ask before overwriting a file
that already exists.

```markdown
# Brief: <task>

<date> · <in depth | fast> · Verdict: <in progress | ready | ready with named assumptions | not ready: blocked on …>

## Summary
What we know and have, in a few sentences.

## Goal and done-means
The outcome, and how anyone will check it was reached.

## What we have
Inputs the user provided, and any that could not be opened. Facts found, each
with its `path:line` or source.

## Decided
- <decision> — <why> — <Round 1 Q2 | stated in the input | default accepted in Round 2>

## Assumed
- <assumption> — <evidence> — <what breaks if it is wrong>

## Out of scope
- <something this task deliberately does not do>

## Risks and spikes
- <risk or spike> — <the cheapest check>

## Open questions
- <question> — <who can answer it>

## Q&A
### Round 1
1. **<question>** Recommended: <answer>. Answered: <the user's answer, in their words>.
```

Keep "Decided" and "Assumed" apart. A reader has to be able to tell a decision
the user made from a bet you made, and an assumption nobody confirmed does not
become a decision because nobody objected.

Before the verdict, read the brief against its sources once. Every line under
"Decided" points at a question in the Q&A or at the user's own input, and every
fact under "What we have" has a source you opened. A line that fails moves to
"Assumed" or "Open questions", or is cut. Whatever reads the brief next builds
on it without checking it again.

Match the brief's length to the task. Leave out a section with nothing in it,
except "Out of scope" and "Open questions", which say "none" when that is true.

End in chat with a few lines: the verdict, what it rests on, and the path of the
brief. Then stop. Starting the task is the user's call, in whatever they run
next.
