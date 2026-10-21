# Root cause analysis plugin

Works in **Claude Code and Codex**. Install the complete plugin so its skills,
references, scripts and agent instructions stay together.

## Installation and invocation

**Claude Code** (inside the Claude Code prompt):

```text
/plugin marketplace add ms-ilya/imaslou-agent-kit
/plugin install root-cause-analysis@imaslou-agent-kit
```

**Codex** (in a terminal with a plugin-capable Codex CLI):

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add root-cause-analysis@imaslou-agent-kit
```

Start a new session after installation. Invoke `/root-cause-analysis:root-cause-analysis` in
Claude Code or `$root-cause-analysis` in Codex. The slash examples below use Claude
Code syntax; Codex uses `$<skill-name>` with the same input and flags. Natural
language triggers apply only to skills that allow automatic invocation.
See the [kit installation guide](../../README.md#installation) and the bundled
[runtime conventions](references/runtime.md) for tool and subagent differences.

Model selection follows your host configuration, including subagent defaults.
The plugin supplies no model override; workers normally inherit the active
session's model when no host override applies. You can request a supported
model explicitly.


## The problem

When things break, the natural reaction is to fix what you see. A service crashes; restart it. A query is slow; add a cache. The same problems recur because nobody traced the real cause.

## What this does

An investigation tool that uses Claude Code or Codex to trace from symptom to root cause. It reads code, searches for patterns, checks git history, runs parallel investigations, and builds a chain of evidence using the 5 Whys technique.

The agent follows dependency chains and determines what went wrong. The output is a verified report with confidence ratings and fixes at three levels: immediate, short-term, and long-term.

## How it works

The agent runs a 4-phase investigation. It states its scope and what it found as it goes, and stops to ask only when your answer changes what it does next.

```
Phase 0: Understand the Symptom  →  Clarify an unclear symptom, state the scope and proceed
Phase 1: Gather Evidence          →  Grep, Read, git history, parallel agents (Full) → evidence summary; asks if the evidence splits or the scope must grow
Phase 2: 5 Whys Analysis          →  Build evidence-backed causal chain, confidence rating → ✓ Root cause confirmed before a report is written
Phase 3: Report & Solutions        →  Write RCA report, propose systemic fixes
```

### Scales to the problem

| Scope | When | Agent delegation | Output |
|-------|------|-----------------|--------|
| Quick | Single file, obvious bug | None | Inline summary in conversation |
| Standard | Multi-file regression, unclear cause | Optional Explore agent | RCA report written to `rca-reports/` |
| Full | Production incident, complex failure | 2 parallel investigation agents | Report with fishbone analysis |

### Techniques

**5 Whys** - Each "why" is backed by evidence from the investigation. The chain continues until it reaches a system-level cause.

**Fishbone diagram** - Groups contributing factors into categories: Code, Data, Infrastructure, and Process. Full investigations get the complete version; standard ones get a checklist.

**Confidence rating** - Every finding gets a High/Medium/Low rating based on evidence strength.

**Evidence log** - Organized record of all findings with source code references, used throughout the analysis.

Solutions target the system, not the person. "Add CI performance tests" over "train one developer."

### Verification

Every finding is checked against the actual codebase:
- File paths checked for existence before inclusion
- Code behavior confirmed via Read (never inferred from names)
- Git history cited from actual `git log`/`git blame` output
- Git SHAs verified with `git show --stat` before citing
- Code re-read before including in final report
- Unverified claims marked as hypothesis

## Usage

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `/root-cause-analysis:root-cause-analysis` | "root cause analysis", "RCA", "postmortem", "what's the root cause of this regression / incident / flaky test" | Evidence-backed root cause investigation. Ordinary "fix this bug" requests are left to normal debugging |

You can pass arguments too: `/root-cause-analysis:root-cause-analysis <description of the symptom>`

### Examples

| You say... | What happens |
|-----------|--------------|
| "Why does this test keep failing?" | Quick scope - traces the failure, finds root cause inline |
| "Investigate this crash" | Standard scope - full investigation, writes RCA report |
| "Do an RCA on last week's outage" | Full scope - parallel agents, fishbone analysis, detailed report |
| "What caused this regression?" | Standard scope - git history analysis, dependency tracing |
| "This test is flaky, figure out why" | Standard scope - race condition analysis, environment check |
| "Why does this work locally but fail in CI?" | Standard scope - environment-dependent investigation |

## Capabilities used

| Tool | Purpose |
|------|---------|
| Grep | Search for error messages, function names, patterns across the codebase (`grep` through Bash where the session has no Grep tool) |
| Glob | Find relevant files (tests, configs, migrations) and verify file paths exist (`find` through Bash where the session has no Glob tool) |
| Read | Examine source code, read reference templates |
| Bash | Git operations: `git log`, `git blame`, `git diff`, `git show`, `git bisect` |
| Agent | Full scope: 2 parallel investigation agents (Code+Data, Infrastructure+Process). Standard: optional Explore agent |
| Write | Create RCA report file (Standard/Full scope) |
| AskUserQuestion | Clarify an unclear symptom, resolve split evidence or a scope upgrade, confirm the root cause before a report is written |

## Design principles

1. Symptom is not root cause - always dig deeper than the first "why"
2. Evidence over guessing - every claim backed by actual findings
3. Fix the system, not the person - improve processes, do not blame people
4. Simple bugs get simple treatment
5. User stays in control - scope and evidence are stated as the work proceeds, and the root cause is confirmed before a report is written
6. Every finding carries a confidence level
7. Keeps AI context usage low with limits, summaries, and parallel agents
8. Blameless - focus on what happened and why, not who did it
