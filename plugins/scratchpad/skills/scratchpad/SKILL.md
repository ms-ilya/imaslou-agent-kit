---
name: scratchpad
description: >-
  Bug-fixing scratchpad that persists investigation state, failed approaches,
  decisions and findings across sessions in .scratchpads/ files. Use only
  when the user names it: /scratchpad, "use the scratchpad", "scratchpad
  this", "open/check/update scratchpad", or "scratchpad resolve/abandon/switch".
  Do not start one on your own because a debugging session is under way.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(mkdir -p *), Bash(mv *)
---

# Scratchpad Skill

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

A single, evolving `.md` file per issue that serves as a **living investigation journal** during debugging and transforms into a **clean knowledge artifact** on resolution.

**Philosophy: "Keep the wrong stuff in."** Agents make mistakes — erasing failure removes evidence. Without evidence, the model can't adapt. Failed approaches stay visible until the issue is resolved.

The scratchpad is a **directional document** — a map that leads away from known dead ends and toward working solutions. It is NOT a changelog or diff history.

---

## The Single Flow

Every `/scratchpad` call runs one automatic flow. No sub-commands. The user's message provides context — you figure out the rest.

### Step 1: LOCATE — Find or create the right scratchpad

Determine project root: use `git rev-parse --show-toplevel` if in a git repo, otherwise use the current working directory. All `.scratchpads/` paths are relative to this root — resolve to absolute paths for all tool calls.

- **First call in conversation?** List `.scratchpads/SP-*.md` at the project root.
  - No folder or no `.md` files → Create new (propose a name, ask user to confirm). If no clear issue in conversation, ask the user to describe it first.
  - One active scratchpad → Auto-select it, confirm to user.
  - Multiple active scratchpads → List them with status, ask user to pick (or create new). If >10 active scratchpads, show the 5 most recently modified + total count.
- **Already selected this conversation?** Use the same one (it's in your conversation context). No re-scanning.
- User says **"switch"** or names a different scratchpad → Re-run selection.

### Step 2: READ — Re-read from disk

Always re-read the scratchpad file from disk before doing anything. Never trust in-memory content — another session may have modified it. If content changed since your last read, note: *"Scratchpad updated externally. Incorporating."*

### Step 3: DIFF — Extract new findings from conversation

Focus on conversation content not yet captured in the scratchpad. If this is the first call in a long conversation, focus on the most recent ~20-30 exchanges — tell the user if you suspect earlier messages contain uncaptured findings.

**Dedup strategy:** Before adding any finding, check the scratchpad for matches. Search the scratchpad file for key identifiers (file paths, function names, approach descriptions). If a match exists, the finding is already recorded — skip it.

**Contradictory findings:** If the conversation contains contradictions (e.g., "bug is in file A" then later "actually, it's in file B"), record only the latest understanding. If the earlier version is already in the scratchpad, update it and note: "Corrected: previously [X], now [Y]."

**Extraction categories** (use this priority when a finding fits multiple — never duplicate across categories):

1. Failed approaches (a specific fix was attempted and failed — with why-it's-wrong)
2. Related files — root cause (a specific function/file identified as the source)
3. Edge cases / test scenarios (a scenario to test or verify)
4. Architectural decisions (a design choice was made)
5. Evolved understanding (new insight that doesn't fit above)
6. Error messages / symptoms (key observations, not full stack traces)

**Anti-hallucination rules:**
- Only record findings explicitly stated or demonstrated in the conversation. If you cannot point to a specific exchange where this was confirmed, do not include it.
- Discussed-but-untested hypotheses are NOT failed approaches.
- Files mentioned but not opened/read are NOT "investigated."
- Never auto-populate Plan to Fix — only the user writes there.
- When uncertain whether something qualifies, omit it. The user can add it manually.
- No code blocks in scratchpad content. Inline references to function names and short expressions within prose are fine.
- Only populate Root Cause when the investigation conclusively demonstrated it or the user explicitly identified it. Suspected root causes go under Evolved Understanding with a "suspected" qualifier.
- Edge cases and test scenarios must come from the conversation — do not invent additional scenarios the user hasn't discussed.

### Step 4: WRITE — Apply changes

- **New scratchpad?** Read `<skill-dir>/references/template-active.md` for the structure. Create with Write tool, populated from context.
- **Existing + new findings?** Use Edit tool to append new content to appropriate sections (see Tool Strategy). Never modify existing failed approaches — they are sacred during active debugging.
- **Existing + nothing new?** Tell user: *"Scratchpad is up to date."* Show a one-line status summary.
- Update status per valid transitions only (see Status Workflow).

### Step 5: CONFIRM — Brief summary

Tell the user what was added or changed. Keep it short.

---

## Intent Detection

The user controls special flows by stating intent in their message alongside `/scratchpad`. These are natural language — not sub-commands.

| User says something like... | Action |
|---|---|
| "resolve", "mark as resolved" | Run the **Resolve Flow** |
| "abandon", "give up on this" | Run the **Abandon Flow** |
| "switch", "different one" | Re-run selection from Step 1 |
| *(nothing special)* | Default flow: locate → read → diff → write → confirm |

---

## Resolve Flow

Triggered when user clearly intends to mark the scratchpad as done/fixed. Uses of "resolve" in other contexts (git conflicts, resolving questions, proposing a fix) do NOT trigger this flow — when ambiguous, ask.

1. **Confirm with user**: "This will delete all Failed Approaches, rewrite the description as a knowledge artifact, and move the file to `resolved/`. Proceed?"
2. If edge cases are unchecked → warn the user, proceed only if they confirm.
3. **Transfer insights**: Before deleting Failed Approaches, extract all "Actual insight" lines. Verify each is incorporated into the resolved description or explicitly noted as no longer relevant.
4. **Transform** the scratchpad — read `<skill-dir>/references/template-resolved.md` for the target structure:
   - Delete all "Failed Approaches"
   - Rename `## Issue Description` → `## Description`. Rewrite as a clean 3–8 sentence past-tense knowledge artifact. Every claim must be traceable to existing scratchpad content — do not add explanations not recorded during investigation.
   - Populate `## Solution` from the successful fix — the approach that worked. If the working fix isn't recorded in the scratchpad (e.g., user fixed it outside the scratchpad workflow), ask the user to describe it before resolving. Do not invent solution details.
   - Drop `### Investigated` from Related Files — only `### Changed` and `### Root Cause` are relevant post-resolution.
   - Promote ADRs to full format — only populate Consequences and Alternatives if they were explicitly discussed. Omit sub-sections without grounding rather than inventing them.
   - Mark edge cases as confirmed/checked
5. Move the file: `mkdir -p .scratchpads/resolved && mv <file> .scratchpads/resolved/`

## Abandon Flow

Triggered when user clearly intends to abandon the entire scratchpad. "Abandon" refers to the whole scratchpad, not a single approach — if the user wants to abandon one approach, record it as a Failed Approach instead. When ambiguous, ask.

1. **Confirm with user**: "This will mark the scratchpad as abandoned. It stays in `.scratchpads/` as a warning. Proceed?"
2. Ask for a reason (optional).
3. Set status to `abandoned`.
4. Keep the file in `.scratchpads/` — it's still valuable as a "don't go here" warning.

---

## Status Workflow

**Statuses:**
- **investigating**: Gathering information. No fix attempts yet.
- **attempted**: At least one fix tried. Failed approaches being documented.
- **resolved**: Fix confirmed. Transformed into knowledge artifact, moved to `resolved/`.
- **abandoned**: Dead end. Stays in `.scratchpads/` as a warning.
- **regressed**: Was resolved, broke again.

**Valid transitions (no other transitions are allowed):**
- `investigating` → `attempted` — when a fix is first tried
- `investigating` → `abandoned` — via Abandon Flow (no fix was ever attempted)
- `attempted` → `resolved` — via Resolve Flow only
- `attempted` → `abandoned` — via Abandon Flow only
- `resolved` → `regressed` — when re-targeting a resolved scratchpad
- `regressed` → `attempted` — automatic on first update
- `abandoned` → `investigating` — on revival

---

## File Structure

### Location
```
<project-root>/
└── .scratchpads/
    ├── SP-auth-token-refresh-loop.md
    ├── SP-race-condition-ws-handler.md
    └── resolved/
        └── SP-null-ref-user-service.md
```

### Naming
- Format: `SP-<kebab-case-issue-name>.md`
- No date prefix.
- Propose the name; user confirms or overrides.
- On creation, check for name collisions with existing scratchpads — flag similarity if found.

### Git
Team decision. The skill takes no opinion on whether `.scratchpads/` is gitignored or committed.

---

## Token Efficiency Rules

Every word costs tokens every time the scratchpad is loaded in future sessions.

1. **Be concise.** Failed approaches: 2–4 lines each. Issue descriptions: 1–3 sentences. ADRs: 1–2 sentences. The scratchpad is a map, not a novel.
2. **Omit empty sections.** Do NOT include section headers with no content. Add sections when they first have content.
3. **Condense on growth.** If a scratchpad exceeds 150 lines (verify with `wc -l` via Bash), condense older failed approaches to one-liners: `### Approach: [name] — Tried [X], wrong because [Y], learned [Z]`. Never delete — condense. If still >300 lines after condensation, warn the user and suggest splitting or resolving.
4. **No timestamps.** What matters is what was tried and why it failed, not when.

---

## Tool Strategy

- **Listing**: Find `.scratchpads/SP-*.md` and `.scratchpads/resolved/SP-*.md` for the LOCATE step with the Glob tool where the session has one, otherwise `rg --files --hidden` or `ls` through the available shell.
- **Read**: Fetch scratchpad content from disk before any write. Read templates from `<skill-dir>/references/` when creating or transforming. Always use absolute paths.
- **Edit**: Preferred for updates to existing scratchpads (append findings, condense, status change). Use the last line of the target section as anchor in `old_string`, then replace with anchor + new content in `new_string`. This avoids accidentally modifying sacred failed approaches.
- **Write**: Only for new scratchpad creation and full resolve transformation (entire content is rewritten). Before the first Write in a project, create the directory via Bash: `mkdir -p .scratchpads/`.
- **Searching**: Search scratchpad content by keyword when needed (e.g., checking if a finding is already recorded), with the Grep tool or `grep` through Bash.
- **Bash**: File moves (`mkdir -p .scratchpads/resolved && mv <source> <target>`), line count checks (`wc -l`), project root detection (`git rev-parse --show-toplevel`), and listing or searching where the session has no Glob or Grep tool.

If file operations fail due to permissions or missing paths, inform the user of the specific error.

## Templates

Read the template file before writing; do not generate the structure from memory, because the section names and order are what later sessions rely on to find things.

- **`<skill-dir>/references/template-active.md`** — Structure for active (investigating/attempted) scratchpads. Includes Failed Approach format. Only include sections that have content.
- **`<skill-dir>/references/template-resolved.md`** — Structure for resolved scratchpads after transformation.

---

## Edge Cases

### First call, no `.scratchpads/` folder
Create the folder. Propose a new scratchpad from conversation context. If no clear issue in conversation, ask the user to describe it.

### First call, multiple issues in conversation
List the distinct issues found. Ask which one this scratchpad is for. Never pick silently.

### Ambiguous debugging context
If the conversation contains debugging context but the user's intent is unclear, ask: *"I see debugging context about [X]. Should I create a scratchpad for that, or do you have a different issue in mind?"*

### Nothing new to capture
Tell the user: *"Scratchpad is up to date."* Show a one-line status summary.

### Targeting a resolved scratchpad
Change status to `regressed`. Move back from `resolved/` to `.scratchpads/` via Bash `mv`. Preserve the resolved description under a new `## Previous Resolution` section. Re-add `## Failed Approaches — DO NOT RETRY` and `## Plan to Fix` headers as scaffolding (exception to the "omit empty sections" rule — these sections will imminently receive content). Proceed with update.

### Abandoned scratchpad revival
Change status to `investigating`. Proceed normally. All existing content preserved.

### Name collision on creation
Flag a collision if: (a) the proposed name is a substring of or contains an existing name, (b) the proposed name shares 2+ consecutive kebab-case segments with an existing name, or (c) the issue descriptions seem related. When in doubt, ask: related or distinct?

