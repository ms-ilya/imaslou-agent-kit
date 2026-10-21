# Round format

A round is **one markdown block followed by one question-tool call.** They
render differently and have different limits. The block is your message; the
picker shows only its own fields. Anything the user needs in order to answer has
to be in a field or in the block above the call, because text written after the
call is not seen until the picker has been answered.

The content is the same every round, whatever the feature. The field table
below describes **Claude Code only**. In Codex, use the available question
tool's actual schema and limits (including Plan-mode-only restrictions). If the
whole round does not fit, ask one numbered message instead of splitting it into
multiple pickers. Put open questions in a supported free-text field when the
host provides one. Never send `preview` or `multiSelect` unless supported.
An asynchronous tool call does not answer the questions: wait for the reply
before recording decisions or drafting from them.

## Contents
- The two channels
- The field mapping
- Two more rules
- Content discipline
- Round layout, in order
- How round 2 differs

## The two channels

| | **Channel A** — `AskUserQuestion` | **Channel B** — markdown |
|---|---|---|
| Carries | closed questions, 2–4 mutually exclusive answers | open questions, grounding recap, coverage table, the offer |
| Rendered as | a picker showing only its own fields | the assistant message |
| Hard limits | ≤4 questions per call, 2–4 options each | none |
| Per question | `header` ≤12 chars · `question` prose · `multiSelect` · `options[]` | free |
| Per option | `label` 1–5 words · `description` prose | free |
| Always added | an **"Other"** option, automatically | — |

**≤5 questions per round across both channels** (R9). Four closed plus one open
is the usual shape. Five open is legal; five closed is not — the picker caps at
four. When fewer earn a slot, ask fewer.

## The field mapping

```skeleton
header:      "Trigger"                     ← ≤12 chars, renders as a chip
question:    "What starts a retry?
              Why it matters: it decides whether retry state lives in the row or
              in a queue, which changes the schema."
multiSelect: false
options:
  - label:       "Periodic sweep (Recommended)"
    description: "No new infrastructure, and the table is already the source of
                  truth for delivery state."
  - label:       "In-process timer"
    description: "Lowest latency; lost on restart."
  - label:       "External queue"
    description: "Most durable; adds a dependency this service does not have."
```

Three consequences that are easy to lose:

1. **"Why it matters" goes inside `question`.** A separate line above the call is
   not part of the picker.
2. **The recommendation is the first option, with `(Recommended)` appended to the
   label** — not bolded prose, not a sentence afterwards. Labels are 1–5 words,
   so the *reason* lives in `description`.
3. **"Other" always exists.** An Other answer is recorded verbatim as the
   decision. If it raises a new question, that question joins the frontier for
   the next round — it never reopens this one.

`multiSelect: true` is right for exactly one shape: *"which of these are in
scope?"*, or its twin *"which of these belong in the first shippable slice?"* A
multi-select on a genuine either/or produces an unanswerable spec.

`preview` is single-select only and renders monospace, side by side. It is for
**strategy selection**, where the user compares shapes, and never for a round.
Blocks are ≤12 lines and show *shape*, never full code.

## Two more rules

- **One `AskUserQuestion` call per round, never two.** Two pickers in a row read
  as an interrogation.
- **If `AskUserQuestion` is unavailable, the whole round is Channel B**, as one
  numbered block. The cap and the content rules do not change. Number the
  questions by their ids in the record, keep a closed question's options as a
  lettered list with the recommended one first and labelled, say that an answer
  in the user's own words is accepted, and leave out the line announcing a
  picker.

## Content discipline

**Every question carries a recommendation, and the recommendation says what it
rests on**: the repo, a stated constraint, or a trade-off you can name. When
general practice is all there is, say that it is general practice. When you have
no basis to recommend anything, say so and ask anyway; a reason made up to fill
the slot is worse than none.

| ✗ Ungrounded | ✓ Grounded |
|---|---|
| "Recommended: idempotent writes — it's best practice." | "Recommended: idempotent writes — every row already carries a stable source id, so dedupe costs one index." |
| "Recommended: MVVM — it's the standard pattern." | "Recommended: keep state on the parent — the two sibling screens already do, and the diff stays in one file." |

**Every question names what the answer changes** — a file, a shape, a schema, a
test. Never "this is important".

| ✗ Generic | ✓ Names the change |
|---|---|
| "Why it matters: this is an important architectural decision." | "Why it matters: it decides whether retry state is a column on the existing row or a new queue — a migration either way, but a different one." |
| "Why it matters: it affects the user experience." | "Why it matters: it decides whether progress goes to stdout, which makes the tool unpipeable, or to stderr, which does not." |

## Round layout, in order

Everything but the picker is one markdown block, and the picker comes last.

1. **Grounding block** — round 1 only, under ten lines: what was found, with
   paths, and what it made unnecessary to ask. When Phase 1 already showed this,
   do not repeat it.
2. **Coverage table**, with a line on anything that did not move since the last
   one.
3. **Open questions**, numbered, each with a suggestion and a why-it-matters.
   Then, when there are any, the defaults you are taking as given unless
   corrected: one line each, no question mark.
4. **The offer** — `skip` defers a question; `stop` ends the interview and drafts
   from what exists. Offered every round.
5. **One line saying a picker follows**, then the `AskUserQuestion` call.

When the round has open questions, end your turn after the picker so the user
can answer them in a reply. If the picker returns the user's answers to every
question synchronously, the run can continue. An asynchronous acknowledgment
is not an answer; wait for the user's reply before continuing.

**No preamble, no praise.** The block opens on the grounding or on the table.

A fact needed for a question is found before the round is rendered (R2). One
that turns out to be needed mid-round becomes a grounding task for the next
round, never a pause in this one.

## How round 2 differs

There is no grounding block, and questions may refer to settled answers by
number (*"given Q2 → shared in-flight work, what should a second caller see if
it fails?"*). Everything else is the same.
