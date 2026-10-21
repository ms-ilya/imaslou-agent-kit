---
name: review-cleanup
description: Remove the intermediate files in .ios-review-temp/ after review-report, keeping only the final report. review-all cleans up by itself.
disable-model-invocation: true
allowed-tools:
  - Read
  - "Bash(find .ios-review-temp -type f ! -name 'ios-review-report.md' -delete)"
---

## EXECUTION

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

1. **Verify report exists:**
   ```bash
   ls .ios-review-temp/ios-review-report.md
   ```

   If the file is missing: report "No report found. Run `/ios-comprehensive-review:review-report` first." → exit.

2. **Remove intermediate files:**
   ```bash
   find .ios-review-temp -type f ! -name 'ios-review-report.md' -delete
   ```

3. **Report:** `Cleanup complete. Kept: .ios-review-temp/ios-review-report.md`
