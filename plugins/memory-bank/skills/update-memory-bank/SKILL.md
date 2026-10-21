---
name: update-memory-bank
description: >-
  Update or create Memory Bank documentation for a specific feature. Performs deep
  code analysis, generates/updates feature documentation, and runs mandatory
  anti-hallucination verification. Use this skill whenever the user says "document
  feature X", "update memory-bank for X", "update docs for feature X", "create
  context for feature X", or "what's the state of feature X". This is the primary
  Memory Bank workflow — it creates the per-feature documentation files
  (IMPLEMENTATION.md, ACTIVE_CONTEXT.md, TROUBLESHOOTING.md) with verified content.
argument-hint: "<feature name>"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Update Memory Bank — Feature Documentation

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

You are documenting a feature in the project's Memory Bank — a living documentation system that captures current codebase state.

**Feature to document:** `$ARGUMENTS`

If no arguments provided, ask which feature to document. Show existing documented features if `memory-bank/` exists.

**Sanitize the feature name to kebab-case** for the folder name (e.g., "Push Notifications" → `push-notifications`, "UserAuth" → `user-auth`). Use this sanitized name for the `memory-bank/<feature-name>/` folder.

---

## Pre-Flight

1. Find the project root (look for `.git/`, `Package.swift`, `package.json`, `Cargo.toml`, etc.)
2. If `memory-bank/` doesn't exist → tell the user to run `/init-memory-bank` first
3. Detect project language by checking for config files at the root (use `Glob`):
   Swift (`Package.swift`, `*.xcodeproj`) · TypeScript (`tsconfig.json`) · Python (`pyproject.toml`, `setup.py`) · Rust (`Cargo.toml`) · Go (`go.mod`) · Kotlin (`build.gradle.kts`) · Java (`pom.xml`, `build.gradle`)
   Use the detected language's file extensions for all subsequent searches. If a language-specific reference exists (e.g., `<plugin-root>/skills/memory-bank/references/swift-intelligence.md` for Swift/iOS), read it

Note: Read templates from `<plugin-root>/skills/memory-bank/references/templates.md` just before writing each file — only the section you need, not the whole file.

## Step 1 — Feature Discovery

Find all files related to the feature using `Grep` and `Glob`:

1. Generate search variations: original, camelCase, PascalCase, snake_case, kebab-case
2. **Run all searches in parallel** — launch multiple `Grep` and `Glob` calls in a single response:
   - `Grep` each variation with `output_mode: "files_with_matches"`
   - `Glob` patterns like `**/*FeatureName*` for filename matches
3. Exclude: build artifacts, dependencies, `memory-bank/`, `.git/`
4. **Cap at 30 files.** If more, rank by relevance:
   - Feature name in filename (highest)
   - Feature name in class/struct/type declaration
   - Feature name in imports/references
   - Feature name only in comments/strings (lowest)

**Show the top files to the user and ask:** "Does this file list look right? Anything to add or remove?"

**If zero files found:** Tell the user no matching files were found and suggest checking the feature name, providing specific file paths, or trying alternative search terms.

Wait for confirmation before proceeding.

## Step 2 — Deep Analysis

Use a tiered reading strategy to stay within context limits:

**Tier 1 — Full read** (up to ~10 files): Entry points, primary types, main views/controllers — files where the feature name appears in the filename or type declaration. **Read these in parallel** (multiple `Read` calls in one response) to understand architecture and data flow.

**Tier 2 — Targeted read** (remaining files): For secondary files (imports, helpers, utilities), read only the relevant sections — type declarations, public API, and function signatures. Use `Grep` to locate specific patterns instead of reading entire files.

**Tier 3 — Pattern scan**: **Run in parallel** — multiple `Grep` calls across all confirmed files for: `TODO`, `FIXME`, `HACK`, `@deprecated`, test assertions.

Extract:
- **Architecture:** Entry points, data flow, key types
- **Dependencies:** What this feature imports from other modules/features
- **External deps:** Third-party libraries used
- **UI layer:** Views, view models, controllers
- **State management:** How state flows
- **Patterns:** Workarounds, TODOs, FIXMEs, HACKs
- **Tests:** Related test files and coverage

## Step 3 — Check Existing Documentation

If `memory-bank/<feature-name>/` exists → **Update mode:**
1. Read existing files
2. Compare against current code analysis
3. Identify: new files not documented, removed files still documented, changed types, stale descriptions
4. Preserve accurate content, update what changed, remove what no longer exists

If folder doesn't exist → **Creation mode:** Generate from scratch.

## Step 4 — Write Feature Files (One at a Time)

For each file below, read its template section from `<plugin-root>/skills/memory-bank/references/templates.md` (only that section), write the file, then verify immediately (see Step 5) before writing the next:

1. **IMPLEMENTATION.md** — from deep analysis
2. **ACTIVE_CONTEXT.md** — fill "Current State" and "Known TODOs" from code analysis (verifiable). For "In-Progress Work" and "Next Steps", use `⚠️ Ask user` placeholders and ask the user to fill in or confirm.
3. **TROUBLESHOOTING.md** — from TODOs, FIXMEs, compiler warnings, known patterns

**Do NOT create DECISIONS.md** — it's user-curated only, created via `/add-decision`.

## Step 5 — Verify Each File

Read `<plugin-root>/skills/memory-bank/references/verification.md` for the full procedure. After writing each file:

1. Verify every file path using `Glob`
2. Verify every type name using `Grep` with language-appropriate extensions
3. Verify behavioral claims by reading actual function bodies with `Read`
4. Check internal cross-references between memory-bank files
5. Flag unverifiable content with `⚠️ INFERRED` (with evidence) or remove it

**Output a verification summary** in the conversation after each file:
```
Verified: IMPLEMENTATION.md
- Paths: N checked, N verified, N flagged
- Types: N checked, N verified, N flagged
- Behaviors: N checked, N verified, N inferred
- INFERRED rate: X% (must be ≤30%)
```

If INFERRED rate exceeds 30%, read more source files before proceeding.

## Step 6 — Update Root-Level Files

- **WIKI.md** — add or update the feature entry in the index table
- **TROUBLESHOOTING.md** (root) — update the feature link; add cross-cutting issues
- **systemPatterns.md** — update if new patterns discovered
- **techContext.md** — update if new dependencies found

## Key Rules

- **Current state only** — never write changelogs or date-stamped entries
- **No speculation without flags** — use `⚠️ INFERRED` with evidence of what WAS verified
- **Never invent file paths** — if not found, say "file not found"
- **Search with what the session has** — the Grep and Glob tools where they exist, otherwise `rg` and `rg --files` through the available shell. Wherever these steps name `Grep` or `Glob`, either form counts; what matters is that the result comes from a search run in this session
- **User confirms file discovery** — always wait before deep analysis
