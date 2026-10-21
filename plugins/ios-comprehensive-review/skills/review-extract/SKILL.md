---
name: review-extract
description: Stage 1 of 4 — extract a PR or branch diff (changed files, new symbols, signature changes) into .ios-review-temp/pr-context.json, discarding any earlier review data. review-all runs every stage.
argument-hint: <PR number> or --base <branch> [--branch <branch>]
disable-model-invocation: true
allowed-tools:
  - Read
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/extract-pr-context.sh *)
  - Bash(rm -rf .ios-review-temp)
---

## EXECUTION

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

1. **Check arguments:** If no arguments were provided, show usage and stop:
   ```
   Usage: /ios-comprehensive-review:review-extract <PR number>
          /ios-comprehensive-review:review-extract --base <branch> [--branch <branch>]
   ```

2. **Check dependencies:**
   ```bash
   which jq
   ```
   If jq is missing: report "jq not installed (brew install jq)" and stop.

3. **Clear and extract:**
   ```bash
   rm -rf .ios-review-temp
   ```
   ```bash
   bash "<plugin-root>/scripts/extract-pr-context.sh" <parsed-and-separately-quoted-arguments>
   ```

   If the script exits non-zero or `.ios-review-temp/pr-context.json` was not created: report the script's error and stop.

4. **Report:** Script outputs `Files: X | Symbols: Y | Signatures: Z`

**Next step:** Run `/ios-comprehensive-review:review-analyze`
