# Drafting, critique and publishing — phases 5 to 7

Loaded at Phase 5. The input to everything below is `tree.md` and the files its
`## Reads` names: not the conversation, not `## History`.

Commands are written with `<plugin-root>`. `SKILL.md` gives its value.

---

## Phase 5 — DRAFT

Load `<plugin-root>/skills/feature-spec/references/spec-template.md`. It
is instructions, not content to copy.

Write the draft to `<specdir>/spec.draft.md`. `spec.md` is never written by
hand: Phase 7 renames the draft, so the spec that ships is the file that was
checked and critiqued.

- **Tag every statement that decides something.** Each requirement, criterion,
  out-of-scope line and implementation constraint names the record entry it came
  from. A statement with no entry behind it is cut, or kept and marked (R10). A
  scenario is keyed by its requirement and takes that requirement's sources.
- **Say what the source says.** A requirement may restate a decision as testable
  behaviour. It may not add a number, a condition or a case the entry does not
  contain. When the requirement needs one, that is an open question, not a gap
  for you to fill.
- **The opening paragraph and the stories summarise.** They carry no tag, so
  they say nothing the tagged statements do not.
- **One marker per deferred question.** Each `## Deferred` entry becomes one
  `[NEEDS CLARIFICATION: Q<n> — …]` under `## Open questions`. A requirement that
  depends on it names the question id in words and does not repeat the marker:
  every marker is counted, and carried into a plan, as its own question.
- **A decision about how is a constraint.** What the user fixed about a library
  or where the code lives goes under `## Implementation constraints` with its
  tag. Nothing else in the spec names a type, a library or a function.
- **Priorities come from the record's `[P1]`/`[P2]`/`[P3]` tags.** When the
  record ranks nothing, the stories carry no priority; the ranking is the open
  question the record already defers. Assigning one here would be a decision the
  user never made.
- **`## Clarifications` is copied.** One line per `## Settled` entry: its id,
  round, title and answer as the record has them, without the priority tag.
- **Identifiers never move.** They are assigned in draft order. A withdrawn
  requirement stays in place as `(withdrawn)`; a split becomes `007a`/`007b`.
- **A justified principle deviation gets a row** under `## Principle
  deviations`, quoting the rule verbatim. No row means no deviation.

Then fix until clean:

```
bash "<plugin-root>/scripts/check-spec.sh" <specdir>/spec.draft.md --tree <specdir>/tree.md
```

The script resolves every source tag against the record: `Settled Q7` has to be
a question the record settled, `Grounding fact 3` an item that exists. It also
fails a statement with no identifier, a section the template does not define, an
untagged scope line or constraint, and a deferred question the draft does not
carry.

On an amendment add `--prev <specdir>/spec.md`. Text changed under an existing
identifier fails; re-run with `--allow-reword` once you have confirmed the
rewording is deliberate. A statement that moved to another identifier fails
either way.

## Phase 6 — CRITIQUE

One `spec-critic` agent runs all three lenses, on a packet the script builds:

```
bash "<plugin-root>/scripts/make-packet.sh" <specdir>/spec.draft.md --tree <specdir>/tree.md --out <specdir>/.work/critic-packet.md
```

Dispatch the critic with one line: the absolute path of the packet, and that the
packet is the whole of what it judges. Do not paste the packet into the prompt
and do not assemble one by hand. The script carries every part a lens needs, and
a part lost on the way is a check the critic cannot run. `.work/` holds working
state and ignores itself in version control; leave it where it is.

Save the critic's reply verbatim as `<specdir>/critique.md`, then validate it:

```
bash "<plugin-root>/scripts/check-critique.sh" <specdir>/critique.md --single --packet <specdir>/.work/critic-packet.md
```

The script checks the reply's shape, that a clean verdict names what it
checked, and that every quote is text the packet contains. When it fails, send
its findings to the same critic once with `SendMessage` and save the corrected
reply over the first. If it fails again, carry on: a finding whose quote is not
in the packet is not acted on, and the report says so.

**Blocking findings:** fix them in the draft, re-run `check-spec.sh`, then run
the critic once more on a packet that carries the first pass:

```
bash "<plugin-root>/scripts/make-packet.sh" <specdir>/spec.draft.md --tree <specdir>/tree.md --pass1 <specdir>/critique.md --out <specdir>/.work/critic-packet.md
```

Save that reply as `<specdir>/critique.pass2.md` and reconcile the two:

```
bash "<plugin-root>/scripts/check-critique.sh" <specdir>/critique.md <specdir>/critique.pass2.md --packet <specdir>/.work/critic-packet.md
```

It asserts the second pass says what became of every blocking finding the first
raised, and prints the ids that are still open. Then go on, whatever the verdict
(R12). The two files are the critique: what is unresolved stays in them and goes
in the report.

Advisory findings are yours to weigh. Apply one when it corrects the draft
against the record. Leave one that asks for something the record does not hold:
that is a question for the user, not an edit. The report lists the ones left.

A critic that returns nothing, or nothing in the shape after one retry, does not
stop the run. Publish without a critique and say so.

## Phase 7 — PUBLISH AND REPORT

```
bash "<plugin-root>/scripts/publish-spec.sh" <specdir>
```

It runs the full check on the draft one last time, renames the draft to
`spec.md` and writes `traceability.md`: every requirement joined to the
decision, reasoning and round behind it, and any decision no line of the spec
cites.

- On an amendment it compares against the existing `spec.md` and prints what
  changed before replacing it. Pass `--allow-reword` on the same condition as in
  Phase 5.
- After a restart the user chose, pass `--fresh`, so the old spec is replaced
  without being compared.
- When it refuses, fix what it names in the draft and run it again. After three
  attempts stop: leave the draft where it is and report the findings as printed.

Then set every ADR this run proposed to `Status: Accepted`.

Report: paths · the coverage table with deferral counts · deferred items ·
phases that did not run, with the reason · ADRs written · glossary terms · the
critic's verdict and confidence, with the blocking ids that ship unresolved and
the advisory ones left unapplied · decisions the publish output lists as cited
nowhere.

Counted cost (R6, R11): clarifying rounds, from `Round` in the record, and
critic passes, from the critique files.

When more than a third of categories ended `Clear*`, or any ended Missing, say
so plainly: *"most of this spec is open questions — fuller input would close
them, or a narrower feature."*

If the user wants a one-page summary for an issue, write it inline from the
spec.

If the project keeps a `memory-bank/`, say in one line that this spec is ready
to document once the feature ships, and name `/update-memory-bank`. A suggestion,
never a call.

Say in one line that `/feature-spec-plan <slug>` turns this spec into an
implementation plan, giving the slug without its date. A suggestion, never a call, and never mentioned before this
point: a spec written as a step toward a plan gets written to be passed rather
than to be right.
