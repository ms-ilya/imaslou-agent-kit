---
name: review-analyze
description: Stage 2 of 4 — per-file iOS/Swift analysis of the extracted diff with parallel file-analyzer agents. Run review-extract first; review-all runs every stage.
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

### 1. Load File List

Count non-deleted entries in `.changed_files`. If none exist, report "No analyzable files" and stop.

Load full file list:

```bash
jq -r '.changed_files[] | select(.change_type != "deleted") | "\(.path)|\(.added_lines | @json)|\(.new_symbols | @json)"' .ios-review-temp/pr-context.json
```

Output format per line: `path|["42-50","88"]|[symbols json]`

### 2. Resume

SafePath: replace `/` with `--`, spaces with `__`, dots with `_DOT_`, remove `.swift` extension only.

`ls .ios-review-temp/` → a file is done when its `review-[SAFEPATH].json` exists. Keep only the files without one.

If all files processed: report "All files already processed" → exit.

### 3. Process Files

Group remaining files into batches of at most 10, bounded by the host’s available worker slots. Queue remaining files until a slot is free.

For each batch:

**3a. Spawn ALL files in batch concurrently up to the available worker limit:**

```
Agent(subagent_type: "ios-comprehensive-review:file-analyzer",
     prompt: "FILE_PATH: [path]
ADDED_LINES: [\"42-50\", \"88\"]
NEW_SYMBOLS: [JSON array]
OUTPUT_FILE: .ios-review-temp/review-[SAFEPATH].json")
```

Report: `Spawned batch X/Y (N files)`

**3b. Wait for the batch.** Subagents run in the background and each one reports back on its own when it finishes. Wait until every agent in the batch has reported; use the host’s completion notifications or wait tool; do not busy-poll or read their transcripts. Their findings are in the output files, not in the reports.

**3c. Handle failures:** After the batch has reported, `ls .ios-review-temp/` and re-spawn, once, in the next batch every file whose `review-[SAFEPATH].json` is missing. A file still missing after its second attempt is a failure: record it for the final report and continue.

### 4. Count Findings

After all batches complete:

```bash
jq -s '[.[].findings | length] | add // 0' .ios-review-temp/review-*.json
```

### 5. Final Report

```
Complete. Files: X/Y | Findings: Z | Failed: F
```

If failures exist:
```
Failed files:
- [path]: [error reason]
```

**Next step:** Run `/ios-comprehensive-review:review-cross-check`
