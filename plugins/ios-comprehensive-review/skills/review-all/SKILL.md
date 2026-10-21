---
name: review-all
description: >-
  Run a complete iOS/Swift comprehensive code review in one command.
  Uses 5 specialized parallel agents across 4 stages: extraction, per-file
  analysis, cross-file checks (DRY/breaking/SOLID), and a verified report.
  Use when the project is iOS/Swift and the user asks for "full review",
  "comprehensive review", "deep review", "review PR N", "review everything",
  "complete code review", "multi-agent review", "analyze PR", "review branch",
  "full iOS review", "run comprehensive review", or "check PR N".
  Do NOT use for quick single-file reviews — use ios-quick-review instead.
argument-hint: <PR number> or --base <branch> [--branch <branch>]
allowed-tools:
  - Read
  - Agent
  - Bash(jq *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/extract-pr-context.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/findings-worklist.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/build-report.sh *)
  - Bash(rm -rf .ios-review-temp)
  - "Bash(find .ios-review-temp -type f ! -name 'ios-review-report.md' -delete)"
---

## EXECUTION

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

Report one line of progress as each stage starts and finishes.

### 1. Extract Context

If no arguments were provided, show usage and stop:
```
Usage: Review PR <number>
       Review branch developer against main
       /ios-comprehensive-review:review-all <PR number>
       /ios-comprehensive-review:review-all --base <branch> [--branch <branch>]
```

Check the dependency:
```bash
which jq
```
If jq is missing: report "jq not installed (brew install jq)" and stop.

**Resume check.** A finished run deletes `pr-context.json` (step 5), so one that is still there belongs to an interrupted run:
```bash
jq -r '"\(.pr_number)|\(.head_branch)|\(.base_branch)"' .ios-review-temp/pr-context.json
```
- The command fails (no file): this is a fresh run. Extract.
- It prints the same PR number, or the same base and head branch, as the arguments: resume. Tell the user the interrupted review is being continued and that deleting `.ios-review-temp/` starts over, then go to step 2 without extracting.
- It prints a different target: extract.

Extract:
```bash
rm -rf .ios-review-temp
```
```bash
bash "<plugin-root>/scripts/extract-pr-context.sh" <parsed-and-separately-quoted-arguments>
```

If the script exits non-zero or `.ios-review-temp/pr-context.json` was not created: report the script's error and stop.

### 2. Analyze Files

Load file list:

```bash
jq -r '.changed_files[] | select(.change_type != "deleted") | "\(.path)|\(.added_lines | @json)|\(.new_symbols | @json)"' .ios-review-temp/pr-context.json
```

If no files: report "No analyzable files" → skip to step 3.

SafePath: replace `/` with `--`, spaces with `__`, dots with `_DOT_`, remove `.swift` extension only.

**Resume check:** `ls .ios-review-temp/` → a file is done when its `review-[SAFEPATH].json` exists. Keep only the files without one.

If all files processed: report "All files already analyzed" → skip to step 3.

**Process files in batches of at most 10, bounded by the host’s available worker slots.** Queue remaining files until a slot is free.

For each batch, spawn ALL files concurrently up to the available worker limit:

```
Agent(subagent_type: "ios-comprehensive-review:file-analyzer",
     prompt: "FILE_PATH: [path]
ADDED_LINES: [\"42-50\", \"88\"]
NEW_SYMBOLS: [JSON array]
OUTPUT_FILE: .ios-review-temp/review-[SAFEPATH].json")
```

Report: `Spawned batch X/Y (N files)`

Subagents run in the background and each one reports back on its own when it finishes. Wait until every agent in the batch has reported; use the host’s completion notifications or wait tool; do not busy-poll or read their transcripts. Their findings are in the output files, not in the reports.

After the batch has reported, `ls .ios-review-temp/` and re-spawn, once, in the next batch every file whose `review-[SAFEPATH].json` is missing. A file that is still missing after its second attempt is a failure: record it and continue.

### 3. Cross-File Checks

Load counts:

```bash
jq -r '"FUNCTIONS:\([.changed_files[] | .new_symbols[] | select(.type == "function")] | length) TYPES:\([.changed_files[] | .new_symbols[] | select(.type != "function" and .type != "property")] | length) SIGNATURES:\(.signature_changes | length)"' .ios-review-temp/pr-context.json
```

If ALL counts are 0: report "No cross-file analysis needed" → skip to step 4.

**Resume check:** `ls .ios-review-temp/` → skip an agent whose `*-analysis.json` output exists.

Extract detailed data:

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

Spawn ALL applicable agents (not already complete) concurrently up to the available worker limit:

- New functions exist AND no `dry-analysis.json` → spawn dry-analyzer
- Signature changes exist AND no `breaking-analysis.json` → spawn breaking-analyzer
- (New types OR new functions) AND no `solid-analysis.json` → spawn solid-analyzer

```
Agent(subagent_type: "ios-comprehensive-review:dry-analyzer",
     prompt: "NEW_FUNCTIONS:\n[list]\nOUTPUT_FILE: .ios-review-temp/dry-analysis.json")

Agent(subagent_type: "ios-comprehensive-review:breaking-analyzer",
     prompt: "SIGNATURE_CHANGES:\n[list]\nOUTPUT_FILE: .ios-review-temp/breaking-analysis.json")

Agent(subagent_type: "ios-comprehensive-review:solid-analyzer",
     prompt: "NEW_TYPES:\n[list]\nNEW_FUNCTIONS:\n[list]\nOUTPUT_FILE: .ios-review-temp/solid-analysis.json")
```

Wait until every spawned agent has reported, as in step 2. Then `ls .ios-review-temp/` and re-spawn once any agent whose output file is missing. One still missing after its second attempt is a failure: record it and continue.

### 4. Verify Findings and Build the Report

The analyzers each saw a narrow slice of the code, so their critical and warning findings are re-checked by an agent that did not write them before anything reaches the report.

List the findings that still need a verdict:

```bash
bash "<plugin-root>/scripts/findings-worklist.sh"
```

Each output line is one finding as a JSON object. No output: nothing to verify → go straight to building the report.

Split the lines into batches of at most 15, keeping the findings of one `file` in the same batch so that a verifier reads each file once. `ls .ios-review-temp/` and number the batches after the highest existing `verdicts-N.json`. Spawn ALL batches concurrently up to the available worker limit:

```
Agent(subagent_type: "ios-comprehensive-review:finding-verifier",
     prompt: "WORKLIST:
[the batch's lines, copied exactly]
OUTPUT_FILE: .ios-review-temp/verdicts-[N].json")
```

Wait until every verifier has reported, as in step 2. Run the worklist script again: findings it still lists got no verdict, so spawn one more round for them. Whatever is still listed after that round stays in the report, marked unverified.

Build the report:

```bash
bash "<plugin-root>/scripts/build-report.sh"
```

The script writes `.ios-review-temp/ios-review-report.md` and prints the counts. If it exits non-zero: report its error and stop. Leave the intermediate files in place so that a re-run resumes from here.

### 5. Clean Up Temp Files

Remove all intermediate files from `.ios-review-temp/`, keeping only the final report:

```bash
find .ios-review-temp -type f ! -name 'ios-review-report.md' -delete
```

### 6. Final Summary

`Complete. Report: .ios-review-temp/ios-review-report.md | ` followed by the count line `build-report.sh` printed.

List any files or agents recorded as failures in steps 2 and 3. A review that silently skipped a file reads as a clean one.
