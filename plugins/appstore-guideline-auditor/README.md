# App Store Guideline Auditor

Works in **Claude Code and Codex**. Install the complete plugin so its skills,
references, scripts and agent instructions stay together.

## Installation and invocation

**Claude Code** (inside the Claude Code prompt):

```text
/plugin marketplace add ms-ilya/imaslou-agent-kit
/plugin install appstore-guideline-auditor@imaslou-agent-kit
```

**Codex** (in a terminal with a plugin-capable Codex CLI):

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add appstore-guideline-auditor@imaslou-agent-kit
```

Start a new session after installation. Invoke `/appstore-guideline-auditor:appstore-audit` in
Claude Code or `$appstore-audit` in Codex. The slash examples below use Claude
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

Requires Bash, Python 3 and standard Unix tools (macOS, Linux or WSL). Live
citation checking needs web access; offline audits label citations unverified.


Audits a native iOS Xcode project for App Store rejection risks. Read-only: it
modifies nothing that was already in the project, and creates exactly one file —
its report. That is checked, not only promised: the audit records the project's
file list when it starts and, before it finishes, lists every file created,
changed or deleted since, other than the report.

```
/appstore-guideline-auditor:appstore-audit ~/Projects/MyApp
```

## What makes it different from a checklist

**Two grades on every finding, and they are independent.** Severity says how bad
it is if true. Verifiability says how firmly the code supports saying it is true:

| Tier | Means |
|---|---|
| `PROVEN` | Evidence at a file and line, or a required thing confirmed absent |
| `PROBABLE` | The pattern matched but the surrounding context could not be confirmed — and the finding says *which* context |
| `MANUAL` | Undecidable from code. Goes to the App Store Connect checklist, never into the findings list |

Nothing is dropped for being uncertain; uncertainty is labelled. That is what
lets the auditor cast a wide net without the usual cost — a report where a guess
and a fact look identical.

**Citations are checked, not copied.** Apple reuses and retires guideline
numbers: 2.5.10 is now marked *intentionally omitted*, and Push Notifications
moved from 4.5.5 to 4.5.4 — 4.5.5 is Game Center Player IDs today. A rule
cannot enter the catalogue until its number resolves against Apple's text, and
at run time each audit resolves Apple's current guidelines page by search and
re-checks every cited number against it. Policy pages are fetched too, but no
check reads them: a regional or dated requirement is reported with its policy
source marked retrieved, not verified.

**Every target, separately.** ITMS-91053 is evaluated per target by an automated
scanner. A widget extension is a separate product from Apple's side, and an
audit that reads only the app target misses the entire class of blocker that
motivated the privacy-manifest rules.

**71 rules, derived rather than copied.** They were merged from 249 named rule
topics across four MIT-licensed upstream sources — re-authored with executable
detection patterns, re-graded against one severity vocabulary in place of four
incompatible ones, and re-cited against Apple's own text. What was deliberately
not adopted is listed under [Known gaps](#known-gaps).

## What it does not do

- **Fix anything.** It reports; you decide.
- **Audit cross-platform projects.** Flutter, React Native, Expo, Kotlin
  Multiplatform, .NET MAUI, Cordova/Ionic, Capacitor and Unity are detected and
  reported as out of scope. Auditing one would mean emitting confident findings
  from a scan that could not see where that framework keeps its configuration.
- **Cover Google Play.** Different store, different project shape.
- **Review your Swift.** `ios-quick-review` and `ios-comprehensive-review` in
  this marketplace own that.

## Where the report goes

`.appstore-audit/report.md` inside the audited project, or the path you pass to
`--out`. That file is the only thing the audit creates there — per-target
context, per-category findings and any fetched text stay in a scratch directory
outside the project. Add `.appstore-audit/` to that project's `.gitignore` if
you would rather it stayed out of your diffs.

## Network

Each audit reaches the network to resolve Apple's current guidelines and policy
pages. It still completes without one — findings then record their citations as
`unverified` for that run, per source, and the verdict line says the run was
degraded. A transient network failure does not make a read-only advisory tool
unavailable.

## Layout

```
rules/            the catalogue, one file per Apple guideline section
schemas/          finding.schema.json — the closed shape every subagent must emit
scripts/          context collection, the catalogue gate, findings validation
agents/           the per-category auditor, dispatched once per rule category
skills/           the orchestrator and its detection references
```

Everything here runs during an audit. Nothing in the installed plugin exists
only to check the plugin itself — the regression fixtures that guard the
collector and the two validators are maintainer tooling and are not
distributed with this repository.

## The catalogue gate

```bash
bash scripts/check-catalogue.sh                              # shape and patterns
bash scripts/check-catalogue.sh --guideline-text apple.md    # and citations
```

Without `--guideline-text` it checks what needs no network: every rule
record is well-formed and closed, every id unique across categories, every
detection pattern compiles, and every `guidance` slug resolves to a section that
exists in `detection-<category>.md`. A pattern that does not compile is a rule
that can never fire, which is indistinguishable from a rule that simply never
matches — so it is checked rather than assumed.

With it, the audit's Phase 1 points the same script at the text it just
retrieved from Apple, and any rule whose number no longer resolves — or now
resolves to a clause marked *intentionally omitted* — is withheld from that run
rather than cited wrongly. That is the whole check: it does not compare what a
clause says with what the rule claims, so a number Apple has reused for a
different clause still passes. A text that cannot be the whole page — fewer
clause numbers than the catalogue cites, or none in a cited section — is not
judged at all, and the run's citations are reported as unverified. There is no
vendored snapshot of Apple's text: the only copy that can be current is the one
fetched on the day of the run.

## Design notes

Decisions that look arbitrary until you hit the thing they prevent. The
reasoning lives here because it is what a change to this plugin has to argue
against.

- **Rule ids are opaque and encode no guideline number.** Apple reuses and
  retires numbers — 2.5.10 is now *intentionally omitted*, and 4.5.5 went from
  Push Notifications to Game Center Player IDs. Keying rules by number means
  re-keying every rule and every emitted finding each time Apple renumbers.
- **The plugin registers no hooks.** An earlier draft ran the catalogue gate from
  a plugin-level `PostToolUse` hook. That fires on every `Write`/`Edit` in every
  project the plugin is installed into, so every user paid a subprocess per file
  write for a check only a maintainer editing the catalogue benefits from. The
  gate is a script you run, not a tax on everyone who installed the auditor.
- **Apple's guideline text is fetched, never vendored.** A snapshot pinned at
  release cannot reach a clause renumbered afterwards, and a stale anchor is
  worse than a missing one: it makes a drifted citation look verified.
- **`line` is required for PROVEN findings only when `absence` is false.** A
  finding about something missing has a file but no line. Requiring one
  unconditionally would force a fabricated line number onto the largest class of
  App Store rejections, which is the fabrication the tier system exists to stop.
- **An unread substrate is `null`, never `[]`.** Absence findings are most of
  this catalogue, and they are graded PROVEN, so the difference between "I read
  the Info.plist and the key is not in it" and "I never read the Info.plist" is
  the difference between the tool's best output and its worst. They were the
  same value once. A project one directory below the scanned path, or one using
  Xcode's generated Info.plist, produced a page of confident critical findings
  about keys that were there the whole time — and `parse_degraded` stayed
  `false`, so nothing in the report warned the reader. Now the collector reports
  what it read (`info_plist_source`), an unread substrate carries `null`, and a
  rule that needed one is withheld and listed rather than graded.
- **Findings are checked against the catalogue, not only against the schema.**
  The schema knows what a finding must look like; it has never seen the
  catalogue, so it cannot know whether the rule exists. Contract rules R2 and R3
  forbid inventing a rule id or a guideline number, and they were requests made
  of a language model until `check_findings.py` made them facts: a document
  naming `totally-invented-rule-id` at guideline `7.9.9(z)` — a section Apple
  does not have — used to validate cleanly.
- **One agent definition, dispatched once per category.** The five categories run
  the same procedure over different slices, unlike `ios-comprehensive-review`'s
  five agents, which have five different jobs.
- **Subagent output goes to a scratch directory outside the audited project.** A
  git-ignored temp file is still a file created in a tree the audit promised not
  to touch. Only the report lands in the project.
- **The severity enum is copied from `ios-comprehensive-review`, not imported.**
  Plugins in this marketplace do not depend on each other. If the two must stay
  in step automatically, that needs a shared schema and a dependency that does
  not currently exist.
- **A detection pattern is an executable matcher, never a prose instruction.** No
  upstream source ships one — the corpus states detection as prose naming API
  symbols, with zero search commands across its 1091-line check file. A prose
  "pattern" is one a subagent improvises against, which is how false positives
  get generated. Where a rule genuinely needs judgement, its tier drops to
  PROBABLE rather than the pattern shape loosening.

### Known gaps

Real, detectable rejection vectors this catalogue does not carry yet, named
rather than silently dropped, and the first candidates for the next round:
Dynamic Type support, orientation and safe-area compliance, advertising inside a
widget or extension target, `SKStoreReviewController` misuse,
keyboard-extension network restrictions, and screen-recording disclosure.

Whole classes were left out on purpose, and stay out: anything decided in App
Store Connect rather than in the repository (it becomes a checklist item
instead), anything needing a compiled binary, a deployed backend or a licence
database, and anything that would mean judging what user-facing content *means*
— a matcher over strings produces noise, and noise is the failure this catalogue
is most careful about.

Three design questions were left open deliberately and the implementation
answers each by demonstration rather than by decree:

1. **May a rule ship with no anchor in Apple's text?** Two currently do —
   `export-compliance-undeclared` and `age-rating-social-descriptor` — because
   neither requirement is a numbered guideline clause. The gate counts them so
   the number cannot creep up unnoticed.
2. **Is the catalogue's field set complete?** It grew to a rejection-case field
   and then to conflicting-statement and storefront-scope fields during the
   build. Nothing forces a new field to be justified against the corpus.
3. **Should a rejection case name the ITMS code it produced?** `itms` is optional
   today. Four of the seven shipped cases carry one.

## Attribution

This plugin is derived from four MIT-licensed upstream App Store review skills,
each pinned to the commit in the table below. No copy of them is distributed
with this repository and no shipped script reads one; each can be fetched from
its upstream repository at the pinned revision.

The merge is not a copy: rules were re-authored with executable detection
patterns (no upstream source ships any — the largest source states detection as
prose across 1091 lines with zero search commands), re-graded against a single
severity vocabulary in place of four incompatible ones, and re-cited against
Apple's own text, which contradicts two of the four sources on Guideline 4.8.

| Source | Upstream | Pinned commit | What it contributed |
|---|---|---|---|
| Copyright (c) 2026 Justin Perea | [JustinPerea/app-store-review-skill](https://github.com/JustinPerea/app-store-review-skill) | `62f9edc` (2026-03-08) | 53 numbered checks; per-target extension validation; false-positive carve-outs |
| Copyright (c) 2026 Cruz | [cruisediary/apple-app-review-skills](https://github.com/cruisediary/apple-app-review-skills) | `f9a746f` (2026-05-02) | Root-caused rejection cases with source URLs; layout and HIG coverage; the collect-context-once pattern |
| Copyright (c) 2026 devsemih | [devsemih/appstore-review-skill](https://github.com/devsemih/appstore-review-skill) | `ab77bb7` (2026-07-13) | The verbatim Apple guideline text the citations were first anchored against; the cross-platform framework table |
| Copyright (c) 2026 safaiyeh | [safaiyeh/app-store-review-skill](https://github.com/safaiyeh/app-store-review-skill) | `3878420` (2026-08-29) | The 2026 regional and dated policy layer and its sources; the correct reading of Guideline 4.8 |

Each upstream repository is MIT licensed and carries its own `LICENSE` file at
the pinned commit.
