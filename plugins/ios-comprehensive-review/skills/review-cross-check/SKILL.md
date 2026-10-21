---
name: review-cross-check
description: Stage 3 of 4 — cross-file iOS/Swift checks of the extracted diff (duplicate functions, breaking API changes, SOLID) with parallel agents. Run review-extract first; review-all runs every stage.
disable-model-invocation: true
allowed-tools:
  - Read
  - Agent
  - Bash(jq *)
---

## Load context explicitly

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

Run this through the host's shell tool in the project directory:

```bash
jq -e '.changed_files | type == "array"' .ios-review-temp/pr-context.json
```

If the file is absent, malformed, or the command fails, report the error and
stop; run `review-extract` before this stage. A missing context is not an empty
diff. No inline shell expansion is required from the host.

## EXECUTION

### 1. Load Context

Count functions, types and signature changes from the context. If ALL counts are 0: report "No cross-file analysis needed (no new functions, types, or signature changes)" → exit.

Extract detailed data as needed:

```bash
# Functions (name|file:line)
jq -r '.changed_files[] | .path as $p | .new_symbols[] | select(.type == "function") | "\(.name)|\($p):\(.line)"' .ios-review-temp/pr-context.json
```
```bash
# Types (name|file:line)
jq -r '.changed_files[] | .path as $p | .new_symbols[] | select(.type != "function" and .type != "property") | "\(.name)|\($p):\(.line)"' .ios-review-temp/pr-context.json
```
```bash
# Signature changes (method|old_sig|new_sig|file:line|change_type)
jq -r '.signature_changes[] | "\(.method)|\(.old_signature)|\(.new_signature // "")|\(.file):\(.line)|\(.change_type)"' .ios-review-temp/pr-context.json
```

### 2. Resume

`ls .ios-review-temp/` → check existing outputs.

Skip agent if file exists: `dry-analysis.json` → dry-analyzer, `breaking-analysis.json` → breaking-analyzer, `solid-analysis.json` → solid-analyzer.

If all exist: report "All cross-checks already complete" → exit.

### 3. Spawn Agents

Spawn ALL applicable agents (not already complete) concurrently up to the available worker limit:

```
Agent(subagent_type: "ios-comprehensive-review:dry-analyzer",
     prompt: "NEW_FUNCTIONS:\n[list]\nOUTPUT_FILE: .ios-review-temp/dry-analysis.json")

Agent(subagent_type: "ios-comprehensive-review:breaking-analyzer",
     prompt: "SIGNATURE_CHANGES:\n[list]\nOUTPUT_FILE: .ios-review-temp/breaking-analysis.json")

Agent(subagent_type: "ios-comprehensive-review:solid-analyzer",
     prompt: "NEW_TYPES:\n[list]\nNEW_FUNCTIONS:\n[list]\nOUTPUT_FILE: .ios-review-temp/solid-analysis.json")
```

Spawn conditions:
- New functions exist → dry-analyzer
- Signature changes exist → breaking-analyzer
- New types OR new functions exist → solid-analyzer

Report: `Spawned N cross-check agents`

### 4. Collect Results

Subagents run in the background and each one reports back on its own when it finishes. Wait until every spawned agent has reported; use the host’s completion notifications or wait tool; do not busy-poll or read their transcripts. Their findings are in the output files, not in the reports.

Then `ls .ios-review-temp/` and re-spawn once any agent whose output file is missing. One still missing after its second attempt is `failed`.

### 5. Final Report

```
DRY: done/skipped/failed | Breaking: done/skipped/failed | SOLID: done/skipped/failed
```

**Next step:** Run `/ios-comprehensive-review:review-report`
