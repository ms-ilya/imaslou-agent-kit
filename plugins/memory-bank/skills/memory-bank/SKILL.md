---
name: memory-bank
description: >-
  Memory Bank navigation and help. Use this skill ONLY when the user asks about
  the memory bank system itself — "how does the memory bank work", "what is in
  the memory bank", "show memory bank structure", "memory bank help", or gives
  an ambiguous documentation request that doesn't clearly map to a specific action.
  Do NOT use this skill when the user wants to document a feature (use update-memory-bank),
  initialize the memory bank (use init-memory-bank), refresh root docs
  (use update-memory-bank-system), or record a decision (use add-decision).
allowed-tools: Read, Glob, Grep
---

# Memory Bank — Living Project Documentation

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

## Purpose

The Memory Bank captures **what is true right now** about a project, organized by feature. It gives an AI agent (or a new developer) the fastest path to understanding any feature.

**This is NOT a changelog.** Git tracks history. The Memory Bank tracks current state.

## Core Principles

1. **Current state only** — no date-stamped entries, no "on Jan 5 we changed X"
2. **Feature-centric** — each feature gets its own folder with a consistent file set
3. **Fast context loading** — read WIKI.md → pick a feature → be productive
4. **Anti-hallucination** — every file path, type name, and behavioral claim is verified against actual source code by a search or a read run in the session, never from memory
5. **Language-agnostic** — works on any codebase; detects language and adapts verification

## Memory Bank Structure

```
memory-bank/
├── WIKI.md                          # Navigation hub — read this first
├── systemPatterns.md                # Architecture, patterns, conventions
├── techContext.md                   # Stack, deps, build setup, tooling
├── TROUBLESHOOTING.md               # Project-wide issues
│
├── <feature-name>/
│   ├── IMPLEMENTATION.md            # How the feature works
│   ├── ACTIVE_CONTEXT.md            # Current state + in-progress work
│   ├── DECISIONS.md                 # Key decisions (created on-demand via /add-decision)
│   └── TROUBLESHOOTING.md           # Feature-specific gotchas
```

## Workflow Routing

Determine which sub-skill to use based on the user's request:

| User says | Sub-skill |
|-----------|-----------|
| "document feature X" / "update memory-bank for X" | `/update-memory-bank X` |
| "create memory-bank" / "initialize memory-bank" | `/init-memory-bank` |
| "refresh system docs" / "update memory-bank system" | `/update-memory-bank-system` |
| "add decision for X: ..." | `/add-decision X: ...` |

If `memory-bank/` does not exist when any workflow triggers, run `/init-memory-bank` first.

If the user's intent is ambiguous, ask which workflow they need.

## Key Guarantee

Every Memory Bank file is verified against actual source code — file paths and type names by searching for them, behavioral claims by reading the function body. Unverifiable content is flagged `⚠️ INFERRED` or removed. Full verification procedure is in the sub-skills and `references/verification.md`.

## Reference Files

Shared references live in this skill's `references/` directory. Sub-skills read them from the same absolute paths.

| Reference | When to read |
|-----------|-------------|
| `<skill-dir>/references/templates.md` | Just before writing each file (read only the relevant section) |
| `<skill-dir>/references/verification.md` | At verification time (not during Pre-Flight) |
| `<skill-dir>/references/swift-intelligence.md` | Only for Swift/iOS/macOS projects |
