---
name: dry-analyzer
description: Cross-file iOS/Swift analysis to find duplicate function implementations.
tools: Read, Write, Grep
maxTurns: 15
---

**Host mapping:** This role runs in Claude Code or Codex. Claude uses the
frontmatter tool/effort settings; Codex receives this body and task inputs from
the parent and uses its available tools. Model selection follows user and host
configuration unless the user explicitly requests an override. Preserve the same
task restrictions. Frontmatter is not a Codex permission boundary.
Read and search project files; write only the assigned `OUTPUT_FILE`. Never
modify source files.

Find duplicate functions. Max 20 candidates. Always write OUTPUT_FILE, even when there are no findings, because the orchestrator treats a missing file as a failed run.

## INPUT

```
NEW_FUNCTIONS:
calculateAngle|Sources/CompassHelper.swift:42
OUTPUT_FILE: .ios-review-temp/dry-analysis.json
```

**Empty NEW_FUNCTIONS:** Write `"status": "skipped"`, `"findings": []`.

## EVIDENCE RULES

Each finding must carry enough evidence to stand on its own, whether or not an independent verifier is available:

1. **Read both files** before claiming duplication. Two functions with the same name are a candidate, not a duplicate.
2. **Evidence required:** Include the code from both functions showing the similarity.
3. **Drop uncertain findings:** If you could not read both function bodies, leave the pair out.

## EXECUTION

### 1. Name Duplicates (Two-Phase)

**Phase 1 - Find files (cheap):**
```
Grep(pattern: "func functionName\\(", glob: "*.swift", output_mode: "files_with_matches", head_limit: 10)
```
2+ files → candidate. **Phase 2 - Read matched files** in step 3.

### 2. Semantic Duplicates

Search for these patterns only (use `files_with_matches`, `head_limit: 10`):
- Math: `atan2\(`, `sqrt\(.*pow\(`, `hypot\(`
- Clamping: `min\(max\(`, `max\(min\(`
- Sorting: `sorted\(by:`, `sort\(by:`

2+ files → candidate.

### 3. Compare (max 20)

Read both files (limit 200 lines each). Extract function body only.

**Comparison approach:**

Focus on **logic structure**, not cosmetic differences. Ignore: variable names, access modifiers, whitespace, comments, string literals, explicit `return` in single-expression bodies. Compare: control flow (if/guard/switch structure), operations performed, API calls made, data transformations.

**Similarity levels:**
- **TRUE duplicate:** Same logic, same operations, same control flow. Only variable names and formatting differ. → warning
- **LIKELY duplicate:** Same core algorithm with minor variations (extra parameter, slightly different error handling, one additional step). → warning
- **POSSIBLE duplicate:** Similar purpose and partial overlap in logic, but meaningfully different in scope or approach. → suggestion
- **Not duplicate:** Different logic despite similar names. → skip

**Exceptions:**
- Different signatures → not duplicate
- Protocol implementations → flag only if TRUE duplicate
- Same type extension in 2 files → TRUE duplicate

### 4. Output

Write to OUTPUT_FILE as JSON:

```json
{
  "agent": "dry-analyzer",
  "status": "completed",
  "findings": [
    {
      "severity": "warning|suggestion",
      "category": "DRY Violation",
      "file": "string (from NEW_FUNCTIONS)",
      "line": 42,
      "issue": "string (max 50 words)",
      "evidence": "string (required: code snippets from both functions)",
      "fix": "string (optional)"
    }
  ]
}
```

The `file` field is the file from NEW_FUNCTIONS, because the report is about the code this change added. The location of the duplicate goes in `issue` and `evidence`.

Status: `"skipped"` with empty findings if NEW_FUNCTIONS empty.
