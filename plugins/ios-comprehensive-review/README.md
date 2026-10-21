# iOS comprehensive review plugin

Works in **Claude Code and Codex**. Install the complete plugin so its skills,
references, scripts and agent instructions stay together.

## Installation and invocation

**Claude Code** (inside the Claude Code prompt):

```text
/plugin marketplace add ms-ilya/imaslou-agent-kit
/plugin install ios-comprehensive-review@imaslou-agent-kit
```

**Codex** (in a terminal with a plugin-capable Codex CLI):

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add ios-comprehensive-review@imaslou-agent-kit
```

Start a new session after installation. Invoke `/ios-comprehensive-review:review-all` in
Claude Code or `$review-all` in Codex. The slash examples below use Claude
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

Requires Bash, `jq` and Git; PR mode also needs an authenticated `gh` CLI. Use
macOS, Linux or WSL. The individual stage skills require explicit invocation.


Multi-agent code review for iOS/Swift projects. Five parallel agents run a 4-stage pipeline (resumable if interrupted) to check code quality, find duplicate code, detect breaking API changes, and flag design issues.

What it checks:
- Per-file: force unwraps, memory leaks, threading, Swift Concurrency (`@Sendable`, actor isolation, continuations), unused code, naming
- Cross-file: duplicate code, breaking API changes (including deleted functions), design violations, over-engineering
- Test-aware: fewer warnings for test files (force unwraps, naming)
- Verified: an independent agent re-reads the code behind every critical and warning finding. What it can disprove is moved to a "Dropped by verification" section with the reason; what it cannot decide stays, marked unverified
- Resumable: picks up where it left off if interrupted

**When to use this vs `ios-quick-review`:** This plugin targets large PRs and branch reviews requiring parallel analysis, cross-file checks (duplicates, breaking changes, design issues), and resumability. `ios-quick-review` fits smaller changes where detailed per-file checks (performance, side effects, compliance) and scope confirmation matter more.


## Commands and skills

### Full review (recommended; single command)

```
/ios-comprehensive-review:review-all <PR number>
/ios-comprehensive-review:review-all --base main
/ios-comprehensive-review:review-all --base main --branch feature
```

Runs all 4 stages automatically: extract, analyze, cross-check, report.

| Command | What it does |
|---------|--------------|
| `/ios-comprehensive-review:review-all <PR number>` | Review a specific PR |
| `/ios-comprehensive-review:review-all --base <branch>` | Review current branch against base |
| `/ios-comprehensive-review:review-all --base <branch> --branch <branch>` | Review a specific branch against base |

### Stage-by-stage commands (for debugging, partial re-runs, or splitting across sessions)

Run individual stages to split work across sessions or re-run one stage:

```
/ios-comprehensive-review:review-extract <PR number>       # Stage 1: fetch diff and metadata
/ios-comprehensive-review:review-analyze                   # Stage 2: per-file analysis (parallel agents)
/ios-comprehensive-review:review-cross-check               # Stage 3: DRY, breaking changes, SOLID
/ios-comprehensive-review:review-report                    # Stage 4: verify findings, build final report
/ios-comprehensive-review:review-cleanup                   # Remove intermediate files, keep only report
```

| Command | Stage | Description |
|---------|-------|-------------|
| `/ios-comprehensive-review:review-extract <PR number>` | 1. Extract | Fetch diff, parse changed files, symbols, signature changes |
| `/ios-comprehensive-review:review-extract --base <branch>` | 1. Extract | Same, but from branch diff instead of PR |
| `/ios-comprehensive-review:review-analyze` | 2. Analyze | Per-file review: style, unused code, threading, memory, safety |
| `/ios-comprehensive-review:review-cross-check` | 3. Cross-check | Cross-file: DRY violations, breaking API changes, SOLID issues |
| `/ios-comprehensive-review:review-report` | 4. Report | Verify critical and warning findings, then build the final markdown report |
| `/ios-comprehensive-review:review-cleanup` | Cleanup | Remove intermediate files, keep only the final report |

Stages 2-4 depend on stage 1 (they read from `.ios-review-temp/pr-context.json`). Re-running a stage skips work already done. Run `/ios-comprehensive-review:review-cleanup` after the report to remove temporary JSON files.

## Architecture

Five agents, parallelized within each stage:

| Agent | Focus |
|-------|-------|
| `file-analyzer` | Per-file: style, unused code, safety, threading, Swift Concurrency |
| `dry-analyzer` | Cross-file: duplicate function detection |
| `breaking-analyzer` | Cross-file: breaking API changes + deleted functions + affected callers |
| `solid-analyzer` | Cross-file: design principle violations, over-engineering |
| `finding-verifier` | Re-read the code behind every critical and warning finding and record a verdict |

All five roles leave model selection to the host. The verifier's independence
comes from a fresh context and its own code inspection.

## Output

- Final report: `.ios-review-temp/ios-review-report.md`
- Temporary JSON files are removed automatically by `/ios-comprehensive-review:review-all`, or manually via `/ios-comprehensive-review:review-cleanup`

## Resumption

If interrupted, re-run the same command to continue. The analyze stage skips files already processed, cross-check skips if outputs exist, verification skips findings that already have a verdict, and the report is rebuilt by a script, so it can be re-run safely. To start over instead, delete `.ios-review-temp/`.

## Git state and prerequisites

This plugin only reviews **committed** changes. Each mode interacts with git state differently.

### PR mode (`/ios-comprehensive-review:review-all <PR number>`)

Fetches the diff from GitHub via `gh pr diff`. Works from **any** local branch; local git state does not matter.

**Requires:** `gh` CLI authenticated and the PR must exist in the current repo's remote.

### Branch mode (`/ios-comprehensive-review:review-all --base <branch>`)

Uses `git diff <base>...<head>` (three-dot diff) to compare commits between two branches.

| Scenario | What happens |
|----------|-------------|
| Feature branch with commits ahead of `--base` | Works - reviews all committed changes |
| `--base main --branch feature` from any branch | Works - explicitly targets the right branches |
| On `main`, run `--base main` | **Empty diff** - comparing main to itself, 0 findings |
| Feature branch with only uncommitted/staged changes | **Empty diff** - uncommitted changes are not included |
| `--base` branch doesn't exist locally | **git error** - the base branch must be reachable |

Branch mode compares **committed code only**, not unsaved changes. To review uncommitted work, commit first or use `ios-quick-review` instead.

### When to use which plugin

| Your situation | Use |
|----------------|-----|
| Uncommitted/staged changes you want reviewed | `ios-quick-review` (reviews working tree by default) |
| Feature branch with commits ready for PR | `ios-comprehensive-review --base main` |
| Open PR on GitHub | `ios-comprehensive-review <PR number>` |
| Specific commit to review | `ios-quick-review <commit SHA>` |

### Requirements

- `jq` for JSON processing (`brew install jq`)
- GitHub CLI (`gh`) authenticated - PR mode only
- `git` - branch mode only
- Swift files in diff
