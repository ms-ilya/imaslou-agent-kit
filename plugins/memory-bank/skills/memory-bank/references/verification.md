# Verification Procedure

Run this procedure for every Memory Bank write. Readers trust this documentation without re-checking it, so an unverified claim does more harm than a missing one.
Run verification **after writing each file**, not after writing all files — this prevents narrative anchoring where early assumptions propagate unchecked across documents.

---

## Overview

The verification pass catches hallucinations before they enter documentation.
Every claim in a Memory Bank file must be traceable to actual source code.

**Key principle:** Every verdict comes from a search or a read run in this session, never from memory. Use the Grep and Glob tools where the session has them; when those tools are absent, use `rg` and `rg --files` through the available shell. Wherever this procedure names `Grep` or `Glob`, either form counts. Read a search's output before concluding: an empty result from a mistyped pattern looks the same as a genuine absence.

---

## Language Detection (Run Once)

Before verification, detect the project's primary language to determine file extensions and type keywords:

| Language | Detect via | Extensions | Type Keywords |
|----------|-----------|------------|---------------|
| **Swift** | `Package.swift`, `*.xcodeproj`, `*.xcworkspace` | `*.swift` | `class, struct, protocol, enum, actor, typealias` |
| **Python** | `setup.py`, `pyproject.toml`, `*.py` | `*.py` | `class, def` (+ `@dataclass`, `Protocol`) |
| **TypeScript** | `tsconfig.json`, `*.ts`, `*.tsx` | `*.{ts,tsx}` | `class, interface, type, enum` |
| **JavaScript** | `package.json`, `*.js`, `*.jsx` | `*.{js,jsx}` | `class, function` |
| **Rust** | `Cargo.toml`, `*.rs` | `*.rs` | `struct, trait, enum, impl, mod, type` |
| **Go** | `go.mod`, `*.go` | `*.go` | `type .* struct, type .* interface, func` |
| **Kotlin** | `build.gradle.kts`, `*.kt` | `*.kt` | `class, data class, sealed class, interface, object, enum class` |
| **Java** | `pom.xml`, `build.gradle`, `*.java` | `*.java` | `class, interface, enum, record` |

Use `Glob` to detect the language. If multiple languages are present, include all relevant extensions in verification searches.

---

## Step-by-Step Procedure

### Phase 1: File Path Verification

For every file path mentioned in the document you just wrote:

1. Use `Glob` to check if the path exists:
   - Pattern: the exact relative path
   - If not found, search by filename: `**/filename.ext`
2. If found at a different path → fix the path in docs
3. If not found anywhere → remove the reference or mark `⚠️ FILE NOT FOUND`

**Never leave an unverified path in documentation without a flag.**

### Phase 2: Type Name Verification

For every type (class, struct, protocol, enum, interface, trait, etc.) mentioned in docs:

1. Use `Grep` with the detected language extensions:
   - Pattern: `\b(class|struct|protocol|enum)\s+TypeName\b` (adjust keywords per language)
   - Use `glob` parameter to filter by language extensions
   - Use `output_mode: "content"` to see the actual declaration
2. Verify the type is in the **file you documented it in** — not just that it exists somewhere
3. If not found:
   - Check for typos and naming variations
   - Check for type aliases / re-exports
   - Check dependencies (note "from dependency: [library]" if found there)
   - If genuinely not found → remove or mark `⚠️ TYPE NOT FOUND`

**Use word-boundary matching (`\b`) to avoid false positives** (e.g., matching `UserManager` when searching for `User`).

### Phase 3: Behavioral Claim Verification

For every statement about what code does (e.g., "TokenManager handles OAuth refresh"):

1. Use `Grep` to find the function/method in the claimed file
2. Use `Read` to read the actual function body (not just the signature)
3. Verify the description matches what the code **actually does**, not just what the name suggests

**Levels of confidence:**
- **Verified** (no flag): Function found, body read, behavior matches description
- **⚠️ INFERRED**: Function found by name, but behavior inferred from name/context without tracing the full implementation. Must include evidence: "Contains `refresh()` method (verified). OAuth relationship is INFERRED from class name `TokenManager`."
- **⚠️ UNVERIFIED**: Cannot trace to actual code — remove the claim or flag it

### Phase 4: Cross-Reference Verification

For every cross-feature dependency mentioned:

1. Use `Grep` to verify that feature A actually imports/references feature B
2. Search for import statements and type references from the other feature
3. Use the detected language's file extensions

### Phase 5: Internal Cross-Reference Check

For every reference between memory-bank files (e.g., "See TROUBLESHOOTING.md for details"):

1. Verify the referenced file exists in `memory-bank/`
2. Verify the referenced section/heading exists within that file
3. Fix or remove broken internal cross-references

### Phase 6: Staleness Check (Update Mode Only)

When updating existing docs:

1. For each file path in existing docs → verify it still exists via `Glob`
2. For each type name in existing docs → verify it still exists via `Grep`
3. **Stale content policy:**
   - Removed files → remove from docs entirely
   - Renamed files → update the path
   - Renamed types → update the type name
   - Changed behavior → update the description

---

## INFERRED Claims Threshold

If more than **30% of behavioral claims** in a single file are marked `⚠️ INFERRED`, the analysis is insufficient. Stop and either:
- Read more source files to gather evidence
- Ask the user for clarification about the feature's scope
- Narrow the feature scope to areas you can verify

Do not paper over knowledge gaps with INFERRED flags.

---

## Verification Summary

After verifying each file, output a verification summary in the conversation (not in the docs):

```
Verified: <filename>
- Paths: N checked, N verified, N flagged
- Types: N checked, N verified, N flagged
- Behaviors: N checked, N verified, N inferred
- INFERRED rate: X% (must be ≤30%)
```

This summary is how the user confirms verification actually ran, so output it for every file.

---

## Common Pitfalls

| Pitfall | Prevention |
|---------|------------|
| **Case sensitivity** | macOS is case-insensitive, Linux is not. Use exact casing from the filesystem. |
| **Substring matches** | Use word-boundary `\b` in Grep patterns to avoid matching `UserManager` when searching for `User`. |
| **Generated files** | Files in `*.generated.*` or build artifacts may not exist until build. Note this if applicable. |
| **Dependency types** | Types from package managers exist in `Pods/`, `.build/`, `node_modules/` — note "from dependency: [library]". |
| **Protocol/trait extensions** | A method may be defined in an extension, not the conforming type. Check both. |
| **Name ≠ behavior** | A function named `refresh()` could refresh anything. Read the body, not just the name. |

---

## When to Flag vs. Remove

| Situation | Action |
|-----------|--------|
| Path exists but content changed | Update description, no flag |
| Path doesn't exist, similar file found | Fix path, no flag |
| Path doesn't exist, nothing similar | Remove from docs |
| Type exists but behavior unclear | Keep type, flag behavior `⚠️ INFERRED` with evidence |
| Type doesn't exist anywhere | Remove from docs |
| Behavior plausible but unconfirmed | Flag `⚠️ INFERRED` with what WAS verified |
| Behavior contradicts code | Fix description to match code |
