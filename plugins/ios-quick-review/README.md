# iOS quick review plugin

Works in **Claude Code and Codex**. Install the complete plugin so its skills,
references, scripts and agent instructions stay together.

## Installation and invocation

**Claude Code** (inside the Claude Code prompt):

```text
/plugin marketplace add ms-ilya/imaslou-agent-kit
/plugin install ios-quick-review@imaslou-agent-kit
```

**Codex** (in a terminal with a plugin-capable Codex CLI):

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add ios-quick-review@imaslou-agent-kit
```

Start a new session after installation. Invoke `/ios-quick-review:ios-quick-review` in
Claude Code or `$ios-quick-review` in Codex. The slash examples below use Claude
Code syntax; Codex uses `$<skill-name>` with the same input and flags. Natural
language triggers apply only to skills that allow automatic invocation.
See the [kit installation guide](../../README.md#installation) and the bundled
[runtime conventions](references/runtime.md) for tool and subagent differences.

Model selection follows your host configuration, including subagent defaults.
The plugin supplies no model override; workers normally inherit the active
session's model when no host override applies. You can request a supported
model explicitly.


A step-by-step code review for iOS/Swift that scales depth to diff size. Checks eight areas: correctness, architecture, naming, dead code, performance, side effects, and AGENTS.md compliance.

**When to use this vs `ios-comprehensive-review`:** This plugin suits smaller changes, uncommitted work, and cases where you want scope confirmation, performance checks, or compliance checks. Use `ios-comprehensive-review` for large PRs that need parallel analysis, cross-file checks (duplicates, breaking changes, SOLID), or the ability to resume interrupted reviews.

## Problem

Code reviews are inconsistent. Reviewers skip things - thread safety, retain cycles, naming, dead code, performance, side effects. A single pass through a diff catches obvious problems but misses deeper issues that cause production bugs.

AI-powered reviews have a different problem: fabricated findings. Fake line numbers, issues in code that was never read, references to checks that never ran. A review that invents problems is worse than no review.

## Solution

An eight-phase code review (Phase 0 through 7) that checks every changed file and traces where that code is used across the project. Small diffs get a single pass; large diffs are split across parallel agents. Every issue found is reported. If there are 47, all 47 appear.

Each phase targets a different class of problem (correctness, architecture, naming, performance, side effects). Every reported issue references code that was actually read, with snippets as proof. Large diffs (15+ files) get split into batches for parallel agents.

## What it does

Eight sequential phases, each targeting a specific issue class:

```
Phase 0: Acquire Changes    →  Get the diff via git commands (uncommitted, commit, or PR)
Phase 1: Scope Mapping      →  Map what's affected: changed files, changed symbols, all places they're used
Phase 2: Correctness        →  Logic errors, thread safety, retain cycles, optionals, error handling
Phase 3: Architecture       →  SRP, DRY, YAGNI, coupling, abstraction consistency
Phase 4: Naming             →  AGENTS.md compliance, no abbreviations or temporal names
Phase 5: Dead Code          →  Unused code, stale TODOs, missing ABOUTME comments
Phase 6: Performance        →  Hot path allocations, O(n²), missing lazy, caching
Phase 7: Side Effects       →  Hidden mutations, order-dependent operations, AGENTS.md compliance
```

### Features

- **No fabricated findings** - reads actual code before reporting, includes real snippets, rechecks line numbers before writing each finding
- **Scales to diff size** - small diffs run fast (~1 min), large diffs split into batches across parallel agents
- **Phase 1 checkpoint** - shows what will be reviewed, and asks for confirmation before deep analysis when the scope is ambiguous or the diff is large
- **Progress tracking** - names the phases up front and reports each one as it runs
- **Traces usage** - every changed function or variable is searched across the entire project; unchanged files that might be affected get flagged

### How it scales

| Diff size | Strategy |
|-----------|----------|
| Small (1-3 files, <50 lines) | Phase 0, brief Phase 1, single combined pass for Phases 2-7 |
| Medium (3-15 files, 50-500 lines) | All phases sequentially |
| Large (15+ files, 500+ lines) | Phase 1 scope map, then Agent subagents per batch of 5-8 files |

### Output

Findings use severity-appropriate formatting:

| Severity | Meaning | Format | Action |
|----------|---------|--------|--------|
| CRITICAL | Crash, data loss, security vulnerability | Full (code + fix) | Must fix before merge |
| MAJOR | Incorrect behavior, memory leak, race condition | Full (code + fix) | Should fix before merge |
| MINOR | Code smell, DRY violation, naming issue | Compact (one-line) | Fix when convenient |
| NIT | Style, formatting, trivial improvement | Compact (one-line) | Fix if touching the file anyway |

The final report includes a summary table, risk assessment (top 3 riskiest findings), top 5 actions ordered by risk x effort, and missed call sites.

Reviews with 20+ findings also get written to a `code-review-YYYY-MM-DD.md` file.

## Usage

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `/ios-quick-review:ios-quick-review` | "review my code", "review this commit", "check my changes", "look at my diff", "find bugs", "code review", "PR review", "what do you think about this code" | Full multi-pass code review |

You can pass arguments: `/ios-quick-review:ios-quick-review <commit SHA or PR number>`

**Auto-trigger condition:** Only activates for Swift/iOS codebases (must contain `.swift` files, `.xcodeproj`, `.xcworkspace`, or `Package.swift`). Won't trigger for non-Swift projects.

## Capabilities used

| Tool | Purpose |
|------|---------|
| **Read** | Read source files to verify findings; re-read before writing each finding |
| **Search** | Find symbol usages, call sites, conformances and files by pattern: the Grep and Glob tools where the session has them, otherwise `grep` and `find` through Bash |
| **Bash** | Read-only git and `gh` commands - `git diff`, `git log`, `git show`, `git status`, `gh pr diff` |
| **Agent** | Parallelize call-site tracing (10+ symbols) and large-diff reviews (15+ files) |
| **Write** | Save full review report to file for reviews with 20+ findings |
| **AskUserQuestion** | Phase 1 checkpoint - confirm scope before deep analysis when it is ambiguous or the diff is large |

## Git state and prerequisites

This plugin reviews uncommitted changes by default. That makes it the right choice for work-in-progress code. It also handles specific commits and PRs.

### Default (no arguments): uncommitted changes

Runs `git diff HEAD` to capture all staged and unstaged changes against the current HEAD.

| Scenario | What happens |
|----------|-------------|
| Uncommitted/staged changes exist | Reviews them - the default workflow |
| Clean working tree, no arguments | Asks what to review; no error |
| On any branch (main, feature, etc.) | Works - compares working tree to HEAD |

### With arguments

| Argument | Git command | What it reviews |
|----------|------------|-----------------|
| `<commit SHA>` | `git diff <sha>~1 <sha>` | Changes introduced by that specific commit |
| `<PR number>` | `gh pr diff <number>` | Full PR diff from GitHub |

### When to use which plugin

| Situation | Use |
|-----------|-----|
| Uncommitted/staged changes you want reviewed | `ios-quick-review` (reviews working tree by default) |
| Specific commit to review | `ios-quick-review <commit SHA>` |
| Feature branch with commits ready for PR | `ios-comprehensive-review --base main` |
| Open PR on GitHub | `ios-comprehensive-review <PR number>` |

### Requirements

- **Swift/iOS codebase** (required)
- **`gh` CLI authenticated** (PR mode only)
- **AGENTS.md in project root** (optional - turns on naming convention enforcement and compliance checks in Phases 4 and 7; the skill works fine without it)

## Design

Eight phases (0 through 7), from acquiring the diff to checking compliance. Every finding is backed by code that was actually read, with snippets. Changed symbols are searched across the entire project.

No limits on findings - everything found gets reported. Small changes are reviewed quickly; large ones split across parallel agents. When an AGENTS.md file exists, naming rules and code standards are enforced. Critical issues get full format; minor ones get one-liners.
