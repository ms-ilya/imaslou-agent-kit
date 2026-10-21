# Scratchpad plugin

Works in **Claude Code and Codex**. Install the complete plugin so its skills,
references, scripts and agent instructions stay together.

## Installation and invocation

**Claude Code** (inside the Claude Code prompt):

```text
/plugin marketplace add ms-ilya/imaslou-agent-kit
/plugin install scratchpad@imaslou-agent-kit
```

**Codex** (in a terminal with a plugin-capable Codex CLI):

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add scratchpad@imaslou-agent-kit
```

Start a new session after installation. Invoke `/scratchpad:scratchpad` in
Claude Code or `$scratchpad` in Codex. The slash examples below use Claude
Code syntax; Codex uses `$<skill-name>` with the same input and flags. Natural
language triggers apply only to skills that allow automatic invocation.
See the [kit installation guide](../../README.md#installation) and the bundled
[runtime conventions](references/runtime.md) for tool and subagent differences.

Model selection follows your host configuration, including subagent defaults.
The plugin supplies no model override; workers normally inherit the active
session's model when no host override applies. You can request a supported
model explicitly.


## The problem

AI agents make mistakes during debugging. They try approaches that fail, go in circles, and lose context between sessions. Without a record of what was tried and why it failed, every new session starts from zero.

## The solution

A `.md` file per bug or issue acts as a debugging notebook during investigation, then becomes a clean summary once the fix lands. One command handles everything: `/scratchpad:scratchpad`.

Failed attempts stay visible. They form a map of dead ends so the AI does not repeat them. When the issue is resolved, noise gets stripped and only the solution remains.

## What it does

The scratchpad guides what to do next. It answers two questions:
1. Where NOT to go - failed approaches with reasons
2. Where to go next - updated understanding, edge cases, plan to fix

Every `/scratchpad:scratchpad` call runs a single automatic flow:

```
LOCATE → find or create the right scratchpad (Glob scan of .scratchpads/)
READ   → re-read from disk (never trust in-memory — another session may have changed it)
DIFF   → extract new findings from conversation (dedup against existing content via Grep)
WRITE  → append to appropriate sections (Edit for updates, Write for new files)
CONFIRM → brief summary of what changed
```

### What gets tracked

- Failed approaches - what was tried, what happened, why it is wrong, actual insight (2-4 lines each)
- Edge cases - living checklist that grows into the definition of "done"
- Related files - investigated, changed, root cause
- Architectural decisions - short decision records, expanded into full format when resolved
- Error messages and symptoms - key observations, not full stack traces

### Lifecycle

```
investigating → attempted → resolved
                    ↓            ↓
                abandoned    regressed
```

- **investigating** - gathering info, no fix tried yet
- **attempted** - fix tried, failed approaches documented
- **resolved** - cleaned into a solution summary, moved to `resolved/`
- **abandoned** - dead end, kept in `.scratchpads/` as a warning (can be reopened)
- **regressed** - was resolved, broke again; auto-transitions to attempted on first update

## Usage

| Skill | What it does |
|-------|--------------|
| `/scratchpad:scratchpad` | Create, update, resolve, abandon, or switch scratchpads |

Intent is detected from natural language. No sub-commands to remember:

| You say... | What happens |
|-----------|--------------|
| `/scratchpad:scratchpad` | Create new or update existing scratchpad from conversation context |
| `/scratchpad:scratchpad resolve` | Confirm with user, then transform into a solution record and move to `resolved/` |
| `/scratchpad:scratchpad abandon` | Confirm with user, mark as dead end, keep as warning |
| `/scratchpad:scratchpad switch` | List active scratchpads, let user pick a different one |

### Resolve transformation

Resolving a scratchpad rewrites it completely:
- All failed approaches are removed (useful insights are saved first)
- The issue description becomes a clean 3-8 sentence summary
- A solution section is populated from the successful fix
- The file moves to `.scratchpads/resolved/`

### Anti-hallucination rules

- Only findings explicitly stated or demonstrated in the conversation are recorded
- Discussed-but-untested hypotheses are NOT failed approaches
- Files mentioned but not opened are NOT "investigated"
- Plan to Fix is user-written only; The agent never auto-populates it
- Root Cause is only populated when conclusively demonstrated

## Capabilities used

| Tool | Purpose |
|------|---------|
| Glob | Scan `.scratchpads/SP-*.md` for discovery (`ls` through Bash where the session has no Glob tool) |
| Read | Fetch scratchpad content from disk, read templates |
| Edit | Append findings to existing scratchpads (preferred for updates) |
| Write | Create new scratchpads, full resolve transformations |
| Grep | Check if a finding is already recorded (dedup; `grep` through Bash where the session has no Grep tool) |
| Bash | `git rev-parse --show-toplevel` (project root), `mv` (resolve/regress), `wc -l` (size check) |

## Output

```
<project-root>/
└── .scratchpads/
    ├── SP-auth-token-refresh-loop.md
    ├── SP-race-condition-ws-handler.md
    └── resolved/
        └── SP-null-ref-user-service.md
```

File naming: `SP-<kebab-case-issue-name>.md` - The agent proposes the name, the user confirms.

## Design principles

1. One command - `/scratchpad:scratchpad` does everything; it understands intent from plain language
2. Points forward - "don't go there" plus "try this instead"
3. Failed approaches are protected - never changed during active debugging, only removed on resolve
4. Clean resolve - becomes a 3-8 sentence solution summary
5. Stays small - every word takes up AI context; auto-shrinks at 150+ lines
6. Always re-reads from disk - never trusts memory, safe when multiple sessions run at once

## Inspiration

- [obra/superpowers](https://github.com/obra/superpowers) - systematic-debugging: 4-phase root cause investigation
- [compound-engineering (EveryInc)](https://every.to/chain-of-thought/the-case-for-compound-engineering) - each unit of work makes future work easier
- [nikiforovall structured-note-taking](https://github.com/nikiforovall/structured-note-taking) - CURRENT_SESSION.md, DECISIONS.md, ADR patterns
- Anthropic context engineering - scratchpad files as persistent memory across sessions
