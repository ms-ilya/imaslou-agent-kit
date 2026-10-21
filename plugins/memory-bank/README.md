# Memory Bank plugin

Works in **Claude Code and Codex**. Install the complete plugin so its skills,
references, scripts and agent instructions stay together.

## Installation and invocation

**Claude Code** (inside the Claude Code prompt):

```text
/plugin marketplace add ms-ilya/imaslou-agent-kit
/plugin install memory-bank@imaslou-agent-kit
```

**Codex** (in a terminal with a plugin-capable Codex CLI):

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add memory-bank@imaslou-agent-kit
```

Start a new session after installation. Invoke `/memory-bank:init-memory-bank` in
Claude Code or `$init-memory-bank` in Codex. The slash examples below use Claude
Code syntax; Codex uses `$<skill-name>` with the same input and flags. Natural
language triggers apply only to skills that allow automatic invocation.
See the [kit installation guide](../../README.md#installation) and the bundled
[runtime conventions](references/runtime.md) for tool and subagent differences.

Model selection follows your host configuration, including subagent defaults.
The plugin supplies no model override; workers normally inherit the active
session's model when no host override applies. You can request a supported
model explicitly.


## The problem

AI agents and new developers spend too much time figuring out how features work. Wikis go stale. READMEs get outdated. Knowledge lives in git history, code comments, and people's heads; every new session starts from zero.

## The solution

A documentation system that records what is true right now about a project, organized by feature. One command documents a feature through code analysis, structured output, and checks against actual source code.

No made-up information. Every file path, type name, and behavioral description is checked against the real codebase using the host’s file search and reading tools before anything is written.

## What it does

The Memory Bank creates a `memory-bank/` folder at the project root with two layers.

Root-level documentation covers the whole project:

- **WIKI.md** - navigation hub and feature index
- **systemPatterns.md** - architecture, design patterns, conventions
- **techContext.md** - tech stack, dependencies, build setup
- **TROUBLESHOOTING.md** - project-wide known issues

Per-feature documentation lives in one folder per feature:

- **IMPLEMENTATION.md** - how the feature works, key files, data flow, dependencies
- **ACTIVE_CONTEXT.md** - current state, in-progress work, known TODOs
- **TROUBLESHOOTING.md** - feature-specific gotchas and known issues
- **DECISIONS.md** - technical decisions in ADR style, manually curated via `/memory-bank:add-decision`

## Usage

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `/memory-bank:init-memory-bank` | "create memory-bank", "initialize memory-bank" | Scans the project, detects language/framework, creates `memory-bank/` with root-level docs |
| `/memory-bank:update-memory-bank <feature>` | "document feature X", "update memory-bank for X" | Finds related files via Grep/Glob, analyzes them, generates 3 feature docs (IMPLEMENTATION, ACTIVE_CONTEXT, TROUBLESHOOTING), runs verification, updates root WIKI |
| `/memory-bank:update-memory-bank-system` | "refresh system docs", "rebuild wiki index" | Re-scans architecture and dependencies, rebuilds the WIKI index and root-level files |
| `/memory-bank:add-decision <feature>: <desc>` | "add decision for X: ..." | Records a technical decision (ADR style) in the feature's DECISIONS.md |
| `/memory-bank:memory-bank` | "how does the memory bank work" | Shows Memory Bank structure, routes to the right sub-skill |

### Workflow

```
/memory-bank:init-memory-bank                                     (one-time setup)
  ↓
/memory-bank:update-memory-bank authentication                    (document each feature)
/memory-bank:update-memory-bank push-notifications
  ↓
/memory-bank:update-memory-bank-system                            (refresh root docs periodically)
  ↓
/memory-bank:add-decision authentication: Use Keychain for tokens (record decisions as they happen)
```

### What happens when you document a feature

1. The agent searches the codebase for all files related to the feature, trying camelCase, PascalCase, snake_case, and kebab-case variants.
2. It shows discovered files and asks for confirmation before proceeding.
3. Files are read using a tiered strategy: full read for core files, targeted read for secondary ones.
4. The three feature documentation files are generated or updated.
5. A verification pass runs next. Every file path is checked via Glob, every type name via Grep, and behavioral claims are traced via Read.
6. Anything unverifiable is flagged with `⚠️ INFERRED` or removed.
7. The root WIKI.md and other root files are updated.

## Accuracy verification

Every update includes a check against fabrication:

- **File paths** - each path in the docs is confirmed to exist on disk
- **Type names** - every class, struct, protocol, and enum is searched for in source files
- **Behavior descriptions** - traced back to actual code
- **Unverifiable content** - flagged with `⚠️ INFERRED` (with notes on what was verified) or removed
- **Verification summary** - shown after each file with pass/fail counts; the threshold is 30% or fewer INFERRED entries

## Capabilities used

| Tool | Purpose |
|------|---------|
| **Glob** | Find project files, verify file paths exist (`find` through Bash where the session has no Glob tool) |
| **Grep** | Discover feature-related files, verify type names (`grep` through Bash where the session has no Grep tool) |
| **Read** | Read source code for analysis, read templates, verify behavioral claims |
| **Write** | Create new documentation files |
| **Edit** | Update existing documentation files |

Claude Code can use its file tools directly. Codex can use file tools or shell
commands for reading/searching and patches for writes; no additional service is needed.

## When to use this

The Memory Bank works well when AI agents need fast, accurate information about features or when new developers need to get up to speed. It also helps if existing wikis and READMEs keep going stale.

It is not a changelog (use git), a task tracker (use an issue tracker), or auto-generated API docs (use DocC/Jazzy/TypeDoc for those).

## Output structure

```
your-project/
├── memory-bank/
│   ├── WIKI.md
│   ├── systemPatterns.md
│   ├── techContext.md
│   ├── TROUBLESHOOTING.md
│   ├── authentication/
│   │   ├── IMPLEMENTATION.md
│   │   ├── ACTIVE_CONTEXT.md
│   │   ├── DECISIONS.md          (created via /memory-bank:add-decision)
│   │   └── TROUBLESHOOTING.md
│   └── push-notifications/
│       └── ...
```

## Tips

- Run `/memory-bank:update-memory-bank <feature>` after significant changes to keep docs current.
- Run `/memory-bank:update-memory-bank-system` periodically to refresh root-level docs.
- Commit the `memory-bank/` folder to the repo. It is meant to be shared.
- DECISIONS.md is manually curated; The agent will not auto-populate it. Use `/memory-bank:add-decision` to record decisions explicitly.
- The verification step takes extra time but prevents fabricated information.

## Design

Works with any language. It detects project type and adapts to Swift, TypeScript, Python, Rust, Go, Kotlin, and Java (with a dedicated reference file for Swift/iOS/macOS projects). Documentation is organized by feature for quick access and tracks current state only, with no changelogs or date-stamped entries.
