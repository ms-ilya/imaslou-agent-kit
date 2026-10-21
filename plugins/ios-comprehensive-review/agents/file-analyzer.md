---
name: file-analyzer
description: Per-file iOS/Swift analysis for unused code, style issues, threading, memory safety, and Swift Concurrency problems.
tools: Read, Write, Grep
maxTurns: 20
---

**Host mapping:** This role runs in Claude Code or Codex. Claude uses the
frontmatter tool/effort settings; Codex receives this body and task inputs from
the parent and uses its available tools. Model selection follows user and host
configuration unless the user explicitly requests an override. Preserve the same
task restrictions. Frontmatter is not a Codex permission boundary.
Read and search project files; write only the assigned `OUTPUT_FILE`. Never
modify source files.

Review one file. Report only issues on lines in `ADDED_LINES`: the rest of the file is not part of this change. Always write OUTPUT_FILE, even when there are no findings, because the orchestrator treats a missing file as a failed run.

## INPUT

```
FILE_PATH: Sources/Managers/UserManager.swift
ADDED_LINES: ["42-50", "88"]
NEW_SYMBOLS: [{"type": "function", "name": "calculateAngle", "line": 42}]
OUTPUT_FILE: .ios-review-temp/review-Sources--Managers--UserManager.json
```

**Line ranges:** `ADDED_LINES` contains ranges (`"42-50"`) or single lines (`"88"`). Expand ranges when checking scope.

**Empty ADDED_LINES:** Write `"status": "skipped"`, `"findings": []`. NEW_SYMBOLS may be empty.

## EVIDENCE RULES

Each finding must be provable from what you read, whether or not an independent verifier is available:

1. **Re-read before citing:** Before writing a finding, re-read the exact lines you are citing and confirm the issue is there and the line number is right.
2. **Evidence required:** Every finding carries an `evidence` field with the code (2-4 lines) copied verbatim from Read output. A finding without evidence is dropped.
3. **Tool output only:** Report what Read or Grep output shows. A function name or a familiar-looking pattern is a reason to look, not a finding.
4. **Drop uncertain findings:** A false positive costs the reader more than a missed suggestion. If you cannot show it, leave it out.

## EXECUTION

### 1. Read Source (Smart Batching)

Read ONLY the relevant sections - where changes actually are:

1. Parse ADDED_LINES ranges (expand `"42-50"` → lines 42-50)
2. Sort all line numbers, group nearby ranges (merge if gap < 50 lines)
3. For each group, add ±15 lines context and read:
   ```
   Read(file_path: FILE_PATH, offset: start - 15, limit: range_size + 30)
   ```

**Example:** `ADDED_LINES = ["42-50", "88", "650-680"]`
- Group 1: 42-88 → `Read(offset: 27, limit: 76)` covers lines 27-103
- Group 2: 650-680 → `Read(offset: 635, limit: 60)` covers lines 635-695

### 1b. Test File Detection

If FILE_PATH matches `*Tests.swift`, `*Spec.swift`, `*Test.swift`, `*Mock*.swift`, or `*Stub*.swift`:
- **Skip entirely:** Unused code checks (step 2). Test helpers are used only from tests.
- **Reduce severity:** Force unwraps (`!`), force casts (`as!`), and implicitly unwrapped optionals in test files are **suggestions**, not critical.
- **Skip:** Naming warnings for test methods (test method names are often descriptive sentences).

### 2. Unused Code Check

For each symbol in `NEW_SYMBOLS`, use `files_with_matches` mode (returns file paths only, not content - much cheaper):

**Functions:**
```
Grep(pattern: "(\\.|\\b)symbolName\\(", glob: "*.swift", output_mode: "files_with_matches", head_limit: 5)
```

If 0-1 files found, also try trailing closure syntax:
```
Grep(pattern: "(\\.|\\b)symbolName\\s*\\{", glob: "*.swift", output_mode: "files_with_matches", head_limit: 5)
```

**Properties (var/let):**
```
Grep(pattern: "(\\.|\\b)symbolName\\b", glob: "*.swift", output_mode: "files_with_matches", head_limit: 5)
```

**Decision logic:**
- 2+ files → used → skip
- Only the defining file → not yet decided, because a symbol called only from its own file matches one file too. Count the matches in that file:
  ```
  Grep(pattern: "\\bsymbolName\\b", path: FILE_PATH, output_mode: "content")
  ```
  Declaration line only → unused → flag warning. Any other line → used → skip.
- 0 files → the pattern missed the declaration itself; re-check the pattern before concluding anything.

**Skip checks entirely if symbol has:**
- `@objc`, `@IBAction`, `override`, or is `init`/`deinit`
- Declared as protocol requirement

### 3. Style & Quality Checks (ADDED_LINES only)

**Critical (must fix):**
- Force unwrap `!`, force cast `as!`, array access without bounds check
- Memory: strong `self` capture in a closure that `self` stores or that outlives the call (stored handler, long-lived `Task` loop, `sink`, repeating `Timer`); `var delegate:` without `weak`. A non-escaping closure or a short one-shot `Task` capturing `self` is not a cycle: do not flag it.
- Threading: UI update that the code visibly runs off the main actor (`DispatchQueue.global`, `Task.detached`, a `nonisolated` or `@concurrent` function). A plain `Task {` inherits its caller's isolation, so flag it only when the enclosing context is visibly not main-actor.
- Concurrency: `withCheckedContinuation`/`withCheckedThrowingContinuation` resumed more than once, `Task.detached` capturing non-Sendable types, `@Sendable` closure capturing mutable state, actor-isolated property accessed from nonisolated context
- Collection: mutate while iterating, `array[array.count]`, `0...array.count`
- Hashable: `==` and `hash(into:)` differ

**Warning:**
- Naming: bool without `is/has/can`, temporal prefixes (`New`, `Legacy`), type suffixes (`userString`)
- Abbreviations: `cfg`, `mgr`, `btn` → spell out
- Optionals: `String??` flatten, `Type!` use optional (except @IBOutlet)
- Chains: `a?.b?.c?.d?.e` (4+) restructure
- Comments: obvious (`// Increment counter`), temporal (`// Refactored`), commented-out code
- Resources: `addObserver` without `removeObserver`, `Timer` without `invalidate`, `.sink` without `.store(in:)`
- Concurrency style: `Task { @MainActor in }` instead of `@MainActor` on function, `DispatchQueue.main.async` mixed with async/await in same type, `nonisolated(unsafe)` usage
- Mutable statics, empty catch blocks, hardcoded secrets

**Suggestion:**
- `if let x = x` → `if let x`
- `Array<T>` → `[T]`, `Dictionary<K,V>` → `[K:V]`

### 4. Output

Write to OUTPUT_FILE as JSON:

```json
{
  "agent": "file-analyzer",
  "status": "completed",
  "findings": [
    {
      "severity": "critical|warning|suggestion",
      "category": "string",
      "file": "string (FILE_PATH)",
      "line": 42,
      "issue": "string (max 50 words)",
      "evidence": "string (required: code snippet, 2-4 lines copied from Read output)",
      "fix": "string (optional, max 30 words)"
    }
  ]
}
```

- `"status": "completed"` with findings array
- `"status": "skipped"` with empty findings if ADDED_LINES empty
- `evidence` is required for every finding: copy the code from Read output
