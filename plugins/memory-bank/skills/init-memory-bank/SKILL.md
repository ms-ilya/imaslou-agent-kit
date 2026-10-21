---
name: init-memory-bank
description: >-
  Initialize a new Memory Bank for the current project. Scans the codebase and
  creates root-level documentation files (WIKI.md, systemPatterns.md, techContext.md,
  TROUBLESHOOTING.md). Use this skill when the user says "create memory-bank",
  "initialize memory-bank", "init memory-bank", "set up memory bank", or
  "start memory bank". This is a one-time setup — after initialization, use
  /update-memory-bank to document individual features.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Initialize Memory Bank

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

You are creating a new Memory Bank for this project — a living documentation system that captures current codebase state, organized by feature.

---

## Pre-Flight

1. Find the project root (look for `.git/`, `Package.swift`, `package.json`, `Cargo.toml`, etc.)
2. If `memory-bank/` already exists → inform the user and ask if they want to reinitialize (overwrites root files) or just update with `/update-memory-bank-system`
3. Detect project language by checking for config files at the root (use `Glob`):
   Swift (`Package.swift`, `*.xcodeproj`) · TypeScript (`tsconfig.json`) · Python (`pyproject.toml`, `setup.py`) · Rust (`Cargo.toml`) · Go (`go.mod`) · Kotlin (`build.gradle.kts`) · Java (`pom.xml`, `build.gradle`)
   Use the detected language's file extensions for all subsequent searches. If a language-specific reference exists (e.g., `<plugin-root>/skills/memory-bank/references/swift-intelligence.md` for Swift/iOS), read it

Note: Read templates from `<plugin-root>/skills/memory-bank/references/templates.md` just before writing each file — only the section you need, not the whole file.

## Step 1 — Scan the Project

Analyze the project for:
- **Tech stack:** Language(s), framework(s), minimum deployment targets
- **Architecture:** Module/target structure, design patterns in use
- **Dependencies:** Package manager, third-party libraries and versions
- **Build setup:** Schemes, configurations, build phases, CI/CD
- **Project structure:** Top-level directory layout

Use `Glob` to find project files and `Grep` to identify patterns. Read key config files (`Package.swift`, `package.json`, `Cargo.toml`, `build.gradle`, etc.)

## Step 2 — Create memory-bank/ Directory

Create `memory-bank/` at the project root.

## Step 3 — Write Root-Level Files (One at a Time)

For each file below, read its template section from `<plugin-root>/skills/memory-bank/references/templates.md` (only that section), write the file, then verify immediately before writing the next:

1. **WIKI.md** — project overview + empty features table + "How to use" section
2. **systemPatterns.md** — architecture, patterns, conventions discovered
3. **techContext.md** — stack, dependencies, build setup, tooling
4. **TROUBLESHOOTING.md** — any project-wide issues found (or minimal template)

## Step 4 — Verify Each File

Read `<plugin-root>/skills/memory-bank/references/verification.md` for the procedure. After writing each file:

1. Verify every file path using `Glob`
2. Verify every type/module name using `Grep`
3. Flag unverifiable content with `⚠️ INFERRED` or remove it

**Output a verification summary** after each file:
```
Verified: systemPatterns.md
- Paths: N checked, N verified, N flagged
- Types: N checked, N verified, N flagged
```

## Step 5 — Inform the User

Tell the user the Memory Bank is ready. Suggest next steps:
- `/update-memory-bank <feature-name>` to document individual features
- `/update-memory-bank-system` to refresh root-level docs later

## Key Rules

- **Current state only** — no changelogs or history
- **Every path and type must be verified** against actual source code
- **Search with what the session has** — the Grep and Glob tools where they exist, otherwise `rg` and `rg --files` through the available shell. Wherever these steps name `Grep` or `Glob`, either form counts; what matters is that the result comes from a search run in this session
