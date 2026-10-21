---
name: ios-quick-review
description: >-
  Efficient multi-pass iOS/Swift code review for commits or uncommitted changes.
  Use this skill when the project is an iOS/Swift project (contains .swift files,
  .xcodeproj, .xcworkspace, or Package.swift) and the user asks to review code,
  review a commit, review changes, check a diff, do a code review, or PR review.
  Triggers on "review", "check my code", "check changes", "review commit",
  "code review", "PR review", "audit", "look at my diff", "check for issues",
  or "what do you think about this code" — but ONLY for Swift/iOS codebases.
  Also use when asked to find bugs, code smells, DRY/YAGNI violations, naming
  issues, retain cycles, or thread safety problems in Swift code. Do NOT trigger
  for non-Swift projects (Python, JS, Rust, etc.).
allowed-tools: Read, Write, Grep, Glob, Agent, AskUserQuestion, Bash(gh pr diff *), Bash(gh pr view *)
---

# iOS Quick Review — Efficient Multi-Pass Code Review

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

Perform an efficient, focused multi-pass code review. Every finding references exact symbols, exact files, exact lines — verified by reading the actual code. If you find 47 issues, report all 47 — incomplete reviews create false confidence.

Read AGENTS.md from the project root before starting — cross-check findings against its rules. A project that keeps its rules in CLAUDE.md instead counts the same: wherever this skill says AGENTS.md, use that file. If neither is found, skip naming enforcement in Phase 4 and compliance checks in Phase 7 that depend on project-specific rules, and note the absence.

## Verification Rules

The most common failure mode in LLM code reviews is fabricating findings — reporting issues in code that wasn't actually read, inventing line numbers, or claiming to have traced call sites without actually searching. These rules exist because a single hallucinated finding destroys trust in the entire review:

- Only report findings for code you have read in this session. Never report an issue based on inference or memory alone.
- Before writing each finding, re-read the specific lines being cited to verify the issue still exists and line numbers are correct. Working memory degrades over long reviews — re-reading is cheap, hallucinated findings are expensive.
- Include the actual code snippet (2-4 lines) from the file in each finding as proof.
- Never guess line numbers. Read the file, find the exact line, cite it.
- For call-site tracing (Phase 1), search for usages and read each caller. List the search results as evidence.
- When uncertain, flag as a question rather than asserting as fact.

## Tool Strategy

- **Searching**: Find symbol usages, call sites, conformances and files by name with whatever search the session has: the Grep and Glob tools where they exist, otherwise `rg` and `rg --files` through the available shell. Ask for file paths only when that is all you need, and for matching lines with context when you need the surrounding code.
- **Read**: Read specific files or line ranges to verify findings. Always read before reporting. Use line offsets for large files — don't read 2000 lines when you need 50.
- **Bash**: Besides searching, only the read-only git and `gh` commands in Phase 0. A review changes nothing in the working tree.
- **Agent**: Parallelize call-site tracing when there are 10+ changed symbols, and batch analysis on large diffs. Use `subagent_type: "general-purpose"`. A subagent sees only its prompt, so give it everything it needs: the symbols or files, the command that reproduces the diff, the checklist of the phases it covers, the Verification Rules above, and the Output Format below. Re-read the lines a subagent cites before you report its finding as yours; its report is a claim, not evidence.
- **Write**: For reviews with 20+ findings, write the full report to `code-review-YYYY-MM-DD.md` in the project root, in addition to conversation output.

## Execution Plan

Before starting, list the phases that apply, and say which phase you are on as you move through them — this gives the reviewer visible progress.

Output findings after completing each phase — don't batch everything to the end. This prevents losing findings if context fills up, and gives the reviewer incremental value.

### Scope-Proportional Strategy

Adjust effort to match diff size — "quick" means smart, not sloppy:

- **Small diff (1-3 files, <50 lines):** Run Phase 0, brief Phase 1 (list changed symbols, skip full call-site tracing if changes are self-contained), then a single combined analysis pass covering Phases 2-7 together by reading each changed file once and checking all dimensions. This avoids re-reading the same small set of files 6 times.
- **Medium diff (3-15 files, 50-500 lines):** Run all phases sequentially. Use Agent subagents to parallelize call-site tracing in Phase 1 if there are 10+ changed symbols.
- **Large diff (15+ files, 500+ lines):** Split files into batches of 5-8. Use Agent subagents (`subagent_type: "general-purpose"`) per batch for Phases 2-7. Merge findings at end. Phase 1 scope mapping is critical at this scale — invest the time.

If a phase produces zero findings after thorough analysis, state "Phase N: No issues found" and proceed — don't pad with filler.

---

### PHASE 0: ACQUIRE CHANGES (always first)

Determine what's being reviewed and get the actual diff:

**For uncommitted changes:**
```bash
git status
git diff HEAD
```
`git diff HEAD` leaves out untracked files. Every untracked source file that `git status` lists is part of the change: read it in full and review all of it as added lines.

**For a specific commit:**
```bash
git show <sha> --stat
git diff <sha>~1 <sha>
```

**For a PR:**
```bash
gh pr diff <number>
```

Save the list of changed files and the diff content — reference these throughout the review.

**Merge commits:** If the target commit is a merge commit, `git diff <sha>~1 <sha>` diffs against the first parent only. This is typically correct, but warn the user if the diff is unexpectedly large.

**Non-Swift files in diff:** For non-Swift files (`.plist`, `.json`, `.xib`, `.strings`, `.storyboard`), check only for obvious issues (malformed structure, missing keys) and move on. Focus review effort on `.swift` files.

**Early exit:** If the diff is empty (no changed files, clean working tree, or invalid commit SHA), inform the user immediately and stop. Do not proceed to Phase 1.

---

### PHASE 1: SCOPE MAPPING

Before reviewing anything, map the blast radius:

1. From the diff acquired in Phase 0, list every changed file.
2. For each changed symbol (function, property, type, protocol, enum case):
   - Search for all call sites, conformances, and overrides across the project.
   - Read each caller to note which might be affected.
3. List files NOT changed but potentially SHOULD have been (e.g., a function signature changed but a caller wasn't updated).

**Output a dependency map like this before proceeding:**

```
Changed files: UserService.swift, UserViewModel.swift, UserProfile.swift

Changed symbols and their call sites:
  - UserService.fetchUser(id:) [signature changed]
    → UserViewModel.swift:L23 (loadUser method)
    → ProfileViewController.swift:L88 (viewDidLoad)
    → UserSearchResultsController.swift:L145 (didSelectRow)
  - UserProfile.displayName [new computed property]
    → No existing callers (new symbol)
  - UserProfile.fullName [deleted]
    → ProfileHeaderView.swift:L34 (configure method) — NOT IN DIFF

Potentially affected files not in diff:
  - ProfileViewController.swift (calls fetchUser with old signature)
  - ProfileHeaderView.swift (references deleted fullName property)
```

**Checkpoint:** Present this scope summary and continue. Stop and confirm with AskUserQuestion only when a wrong guess about scope would waste the review:
- the request does not say what to review and more than one target is plausible (uncommitted changes and also unpushed commits, or several candidate commits);
- the diff is large (15+ files) or much larger than the request suggests;
- the diff mixes unrelated changes and the user may have meant only some of them.

Options when asking: "Looks correct, continue review", "Wrong scope, let me clarify", "Skip to specific phase".

---

### PHASE 2: CORRECTNESS & SAFETY

This is the highest-priority pass. A bug here = production crash or data corruption.

**Logic errors:**
- Trace every code path including edge cases: nil, empty collections, Int overflow, index out of bounds, off-by-one errors, negative values, empty strings.
- Check switch statements for missing cases, especially with enums.
- Verify guard/if-let chains handle the failure path correctly.

**Thread safety:**
- Isolation defaults are a per-target build setting, so read them before judging: default actor isolation (new app targets default to `@MainActor`) and `NonisolatedNonsendingByDefault`, in the target's build settings or `Package.swift`. An app and its packages often differ. A "missing `@MainActor`" in a target that is main-actor by default is a false finding.
- Mutable state accessed from multiple threads or queues without synchronization?
- UI-touching code that visibly runs off the main actor?
- Actor reentrancy: state read before an `await` and relied on after it without re-checking?
- An isolation error silenced instead of fixed (`DispatchQueue.main.async`, `Task.detached`, `assumeIsolated`, `nonisolated(unsafe)`)?
- Long loops or computations in a `Task` that never check for cancellation?
- Race conditions in async/await, Combine pipelines, or GCD?
- Shared mutable state protected only by assumptions, not by actual synchronization primitives?
- `DispatchQueue` barriers used correctly?

**Retain cycles:**
- Closures that `self` stores or that are long-lived — is `[weak self]` missing? A non-escaping closure or a short one-shot `Task` does not need it; flag blanket `[weak self]` too.
- Long-lived `Task { [weak self] }` loops — is `self` unwrapped inside the loop? A top-level `guard let self` holds it for the task's whole life.
- Every `sink`/`assign` in Combine — stored in cancellables correctly? `assign(to:on: self)` retains `self`.
- Delegate properties — are they `weak`?
- Repeating timers and notification observers — invalidated or removed explicitly, not only in `deinit`?

**SwiftUI & Observation** (when the diff touches views or models):
- `ForEach` identity taken from an array index or `id: \.self` on mutable data?
- An `@Observable` type held in `@State` whose initializer does I/O or registers observers? It re-runs on every view rebuild.
- A view that depends on a value its `body` never reads (used only in a helper, closure or untaken branch), or on a nested reference type that is not itself `@Observable`?

**Optionals:**
- Force unwraps (`!`) — each one must be justified or flagged.
- `try?` silently swallowing errors where failure matters.
- Optional chaining (`?.`) silently producing nil where a crash would be more informative.
- Nil coalescing (`??`) hiding bugs by providing a default that masks a real problem.

**Error handling:**
- Errors swallowed silently (empty catch, ignored Result.failure)?
- Generic `catch` blocks losing error specificity?
- Missing error propagation up the call chain?
- `fatalError` / `preconditionFailure` used where recoverable error handling is appropriate?

**API contracts:**
- Preconditions and postconditions maintained?
- Protocol conformances complete and semantically correct (not just syntactically)?
- Are public API guarantees (documented or implied) still honored after the change?

---

### PHASE 3: ARCHITECTURE & DESIGN

**Single Responsibility:**
- Does each type do exactly one thing? Flag god-objects (types with 5+ unrelated responsibilities).
- Does each function do exactly one thing? Flag functions over ~40 lines or with multiple levels of nesting.

**DRY violations:**
- Identify ANY duplicated logic — even if expressed with different variable names or slightly different structure.
- Structural duplication counts (two switch statements over the same enum with similar logic).
- Propose concrete extractions: name the function/type, show the signature.

**YAGNI violations:**
- Parameters that no caller uses.
- Abstractions/protocols with only one conformance and no clear reason to expect more.
- "Future-proofing" code that solves problems that don't exist yet.
- Configuration options nobody configures.
- Unused generic type parameters.

**Coupling:**
- Hidden coupling through singletons, globals, or NotificationCenter?
- Dependencies injected or hardcoded?
- Does the change increase coupling between modules that should be independent?

**Abstraction consistency:**
- Is each function operating at one consistent abstraction level?
- Or does it mix high-level orchestration ("fetch user, validate, save") with low-level details ("append byte to buffer")?

---

### PHASE 4: NAMING

Check every new or changed symbol name against the naming rules in AGENTS.md. If AGENTS.md was not found, apply standard Swift API Design Guidelines instead.

**Flag immediately:**
- Abbreviated or ambiguous names: `data`, `info`, `mgr`, `mgmt`, `vc`, `vm`, `btn`, `lbl`, `img`, `val`, `tmp`, `temp`, `res`, `result`, `item`, `model`, `object`, `ctx`, `config` (when vague)
- Vague "manager/handler/helper/utility" names that don't describe what they actually do
- Temporal/historical names: "New", "Legacy", "Old", "Unified", "Improved", "Enhanced", "Updated", "Refactored", "V2", "Better"
- Inconsistent naming: same concept called different names in different places

**Also check:**
- Parameter names — are they descriptive at the call site?
- Closure parameter names — are they meaningful or just `$0`, `$1` for non-trivial closures?
- Enum case names — do they read naturally in a switch?

---

### PHASE 5: DEAD CODE & HYGIENE

- Unused `import` statements.
- Unused properties, functions, parameters, local variables, type aliases, enum cases — introduced OR left behind by the changes.
- Code made unreachable by the changes (dead branches, impossible conditions).
- Commented-out code — should be deleted, not commented.
- Stale `TODO` / `FIXME` / `HACK` markers — addressed or new?
- If AGENTS.md requires `ABOUTME` comments: check presence and accuracy at top of every changed file.
- If AGENTS.md prohibits temporal comments: flag comments that explain "how it's better than before" or contain "refactored", "moved", "new approach".
- Print/debug statements left in production code.

---

### PHASE 6: PERFORMANCE

- Unnecessary allocations in hot paths: loops, collection view/table view cell configuration, layout passes.
- Missing `lazy` for expensive initialization that isn't always used.
- Large value types (structs with many properties or nested arrays) copied unnecessarily — should they use `inout`, or be reference types?
- Hidden O(n²): nested `filter`/`contains`/`first(where:)` on arrays. Should be a Set or Dictionary lookup?
- String interpolation or string concatenation in logging calls that execute even when logging is disabled.
- Unnecessary main thread work that could be offloaded.
- Image/data loading without caching where caching is warranted.
- Redundant or excessive network calls, file I/O, or UserDefaults access in loops.

---

### PHASE 7: SIDE EFFECTS & COMPLIANCE

This phase combines side effects audit with AGENTS.md compliance — both concern "hidden behavior" that isn't obvious from the code surface.

**Side effects:**
- Functions with hidden side effects not obvious from their name or signature (e.g., a `validate()` that also mutates state).
- Pure computations mixed with mutations in the same function.
- Computed properties or getters that trigger side effects (network calls, state changes, analytics events).
- Order-dependent operations that would break silently if call order changes.
- Initializers that perform work beyond simple assignment (network calls, subscriptions, file I/O).

**AGENTS.md compliance** (skip if AGENTS.md was not found):
- Are changes the SMALLEST reasonable for the desired outcome?
- Does code style MATCH the surrounding file (consistency within file > external standards)?
- Were any implementations REWRITTEN without explicit permission? (Flag immediately.)
- Was backward compatibility added without approval? (Flag immediately.)
- Root cause fixes, not symptom patches or workarounds?
- Code written in the appropriate extension/MARK group, not dumped at file bottom?

---

## Output Format

For CRITICAL and MAJOR findings, use the full format:

```
[CRITICAL] File.swift:L42 — `symbolName`
Phase 2: Thread Safety
Code:
    ```swift
    // Lines 42-44
    sharedCounter += 1  // unsynchronized write
    ```
Issue: `sharedCounter` is mutated from both `processQueue` and Main thread without synchronization. Race condition will cause intermittent crashes.
Fix:
    ```swift
    private let lock = OSAllocatedUnfairLock(initialState: 0)
    func increment() { lock.withLock { $0 += 1 } }
    ```
```

For MINOR and NIT findings, use compact format to reduce output noise:

```
[MINOR] File.swift:L42 · Phase 4 — `userData` is vague. Rename to `userProfileResponse` to clarify it's the API response, not the domain model.

[NIT] File.swift:L88 · Phase 5 — Unused import `Foundation` (already imported transitively).
```

**Severity decision guide** — when unsure, ask "What happens if this ships to production unchanged?"
- **[CRITICAL]**: Crash, data loss, or security vulnerability. Must fix before merge.
- **[MAJOR]**: Incorrect behavior users will notice, memory leak, race condition. Should fix before merge.
- **[MINOR]**: Maintainability degrades — code smell, naming issue, DRY violation. Fix when convenient.
- **[NIT]**: Only aesthetics affected. Fix if touching the file anyway.

---

## Final Report Structure

After all phases, end with:

### Summary Table
| Severity | Count |
|----------|-------|
| CRITICAL | N |
| MAJOR | N |
| MINOR | N |
| NIT | N |

### Risk Assessment
What is most likely to cause a production incident? Rank the top 3 riskiest findings.

### Top 5 Actions
The most impactful fixes to make first, ordered by risk x effort.

### Missed Call Sites
List any callers of changed code that may need updates but weren't part of this diff.
