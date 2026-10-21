# grill-me

Works in **Claude Code and Codex**. Install the complete plugin so its skills,
references, scripts and agent instructions stay together.

## Installation and invocation

**Claude Code** (inside the Claude Code prompt):

```text
/plugin marketplace add ms-ilya/imaslou-agent-kit
/plugin install grill-me@imaslou-agent-kit
```

**Codex** (in a terminal with a plugin-capable Codex CLI):

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add grill-me@imaslou-agent-kit
```

Start a new session after installation. Invoke `/grill-me:grill-me` in
Claude Code or `$grill-me` in Codex. The slash examples below use Claude
Code syntax; Codex uses `$<skill-name>` with the same input and flags. Natural
language triggers apply only to skills that allow automatic invocation.
See the [kit installation guide](../../README.md#installation) and the bundled
[runtime conventions](references/runtime.md) for tool and subagent differences.

Model selection follows your host configuration, including subagent defaults.
The plugin supplies no model override; workers normally inherit the active
session's model when no host override applies. You can request a supported
model explicitly.

This skill requires explicit invocation in both hosts.


**A pre-task interview that ends in a written brief and a verdict on whether you
are ready to start.**

Models already ask a clarifying question or two before building. What they do
poorly is find the requirement you never stated, and know when to stop asking.
This plugin is for that part: it states what it assumes, asks only the decisions
it cannot look up or responsibly assume, looks for what you have not thought of,
and writes down what is decided, what is only assumed and what nobody knows yet.

It does not start the task, design the solution or write a spec. It prepares you
for whichever of those comes next.

---


## Usage

```
/grill-me:grill-me <what you have: the task, notes, file paths, links>
/grill-me:grill-me --fast <what you have>
```

Give it everything you have. It reads the files and links you pass before it asks
anything.

| | Default: in depth | `--fast` (or `--light`) |
|---|---|---|
| For | work that is hard to undo, or new to you | work that has to move; the 80/20 version |
| Reads | everything provided, plus the code and docs the task touches | what you provided and the files it names |
| Asks | rounds of questions until the answers stop changing the work | one round, at most four questions |
| Looks for blind spots | a full pass through the lenses below | premise, top risk and riskiest assumption, stated rather than asked |

Depth is a ceiling, not a quota. A small, fully specified task gets "nothing
worth asking" and a short brief at either depth.

It runs only when you invoke it. It never triggers on its own.

## How an interview runs

1. **Takes in what you gave it.** Files, notes, links, and the instruction files
   already loaded (`CLAUDE.md`, `AGENTS.md`, project rules). It does not ask what
   those already answer, and tells you when the task conflicts with one. A file
   or link it could not open is named, not summarised.
2. **Looks things up.** Facts are its job; decisions are yours. A claim in your
   input about how the code works is checked against the code. A `path:line` in
   its output is a line it opened; what it could not check stays unknown.
3. **States its assumptions first.** Your goal in one sentence, a premise check,
   then what it will take as true unless you correct it, ordered by how much
   breaks if it is wrong. Each says what it rests on: a line of code, your own
   words, or "a guess". The first round of questions comes in the same message,
   so one reply corrects and answers.
4. **Grills.** A question is asked only if two plausible answers lead to
   materially different work, or a wrong guess would be expensive to undo. Each
   comes with a recommended answer and what the answer changes. Vague answers
   and answers that contradict the code get pushed back on.
5. **Looks for what you have not thought of.** Pre-mortem, riskiest assumption,
   example mapping, a blindspot pass for unfamiliar territory, an integration
   check across your answers, and blockers that are not in the code at all.
6. **Stops** when your remaining answers are predictable, or when what is left
   is cheaper to learn by doing the work.
7. **Writes the brief** and gives the verdict: ready, ready with named
   assumptions, or not ready and what it is blocked on.

## The brief

`docs/briefs/<YYYY-MM-DD>-<slug>.md` in a repository, the working directory
otherwise, or a path you give. In the default depth it is written after the first
round and updated every round, so a compaction or a closed session loses nothing.
Pass an unfinished brief back to `/grill-me:grill-me` to continue it.

```
Summary              what we know and have
Goal and done-means  the outcome, and how it will be checked
What we have         your inputs; facts found, with path:line
Decided              decision · why · where it was decided (round and question, or your input)
Assumed              assumption · evidence · what breaks if wrong
Out of scope
Risks and spikes     cheapest check first
Open questions       and who can answer each
Q&A                  every question, its recommendation, your answer
```

"Decided" and "Assumed" are separate on purpose. Anyone reading the brief can
tell a decision you made from a bet the interview made. Before the verdict the
brief is read against its sources once: a "Decided" line that points at no
question and no input moves to "Assumed".

## With feature-spec

The two plugins are independent. Together:

```
/grill-me:grill-me <what you have>
/feature-spec:feature-spec docs/briefs/<date>-<slug>.md
```

`feature-spec` reads the brief, checks its claims against the code, and asks only
about what the brief left open. A complete brief means no interview there at all.
The brief works equally well as the opening message of a fresh session or of plan
mode.

## Non-goals

No implementation, no design, no spec, no plan. No scripts, hooks or state beyond
the one brief file. No question budget to fill: an interview that asks three
questions and stops has done its job.

## How you would know it is working

- **It sometimes says there is nothing worth asking.** A tool that always finds
  questions is being run as ceremony.
- **It finds a contradiction in your input now and then**, from the code, before
  asking you anything.
- **You rarely answer a question whose answer was in the repo or in your notes.**
- **"Assumed" is not empty.** An empty list on real work means the assumptions
  were made silently.
- **Specs and plans written from a brief need few follow-up questions.**

If none of that holds over a handful of real tasks, a plain "interview me before
I start" prompt is doing as well, and the plugin is not earning its place.

## Prior art

Nothing is vendored. The ideas were reimplemented; this is courtesy.

| Idea | Origin |
|---|---|
| Rounds of mutually independent questions, each with a recommended answer | mattpocock `grilling` |
| Facts are the agent's job, decisions are the user's | mattpocock `grilling`; OpenAI Codex plan mode |
| Assumptions presented with evidence and what breaks if wrong | GSD `discuss-phase` assumptions mode |
| Blindspot pass for unfamiliar territory | Thariq's "Know your unknowns" (Anthropic); EveryInc `ce-brainstorm` |
| Stop when the next answers are predictable | addyosmani `interview-me` |
| Integration check across answers; one challenge for an unreasoned assertion | EveryInc `ce-brainstorm` |
| Keep a question only if its answers lead to different work | GitHub `spec-kit` `/clarify` |
| Example mapping, pre-mortem, riskiest-assumption test | Matt Wynne; Gary Klein; lean-startup practice |

## Licence

MIT, as the rest of this marketplace.
