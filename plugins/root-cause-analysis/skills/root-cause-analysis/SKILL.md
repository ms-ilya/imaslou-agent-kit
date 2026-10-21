---
name: root-cause-analysis
description: >-
  Systematic root cause analysis: investigates a codebase to find why a bug,
  crash, regression or incident happened, and ends in an evidence-backed 5 Whys
  chain or RCA report. Use when the user asks for a root cause analysis, an
  RCA, a postmortem, or the root cause of a recurring or unexplained failure
  (production incident, regression, flaky test, CI failure, memory leak,
  performance degradation). Not for ordinary debugging where the user wants
  the bug fixed rather than explained.
allowed-tools: Read, Write, Glob, Grep, Agent, AskUserQuestion
---

# Root Cause Analysis

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

Investigate codebases to find the underlying reason for failures. Produce evidence-backed findings, not speculation.

**Core principle:** A symptom is what you see (crash, error, slow response). A root cause is the systemic reason it happened (missing validation, no test coverage, config drift). Always dig past the symptom.

## Phase 0: Understand the Symptom

Gather what the user knows before investigating.

1. Identify the symptom from the user's message or conversation context
2. If unclear, use AskUserQuestion to clarify:
   - What is the observable problem? (error message, wrong behavior, performance)
   - When did it start or when was it noticed?
   - Is it reproducible? How?
   - Any recent changes (deploys, config changes, dependency updates)?
3. Determine investigation scope:

| Signal | Scope |
|--------|-------|
| Single file, obvious bug, user knows the area | **Quick** |
| Multi-file issue, regression, unclear cause | **Standard** |
| Production incident, complex failure, multiple contributing factors | **Full** |

4. **State the scope and proceed:** Say which scope you picked and the signal that decided it ("Standard investigation: the regression spans several files"), then start. The user can redirect at any point. Ask with AskUserQuestion only when the signals point to different scopes and the difference matters, such as a Full investigation that would spawn agents for what may be a one-file bug.
5. **Detect project technology** (if not already known from conversation context):
   - Glob for manifest files: `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, `requirements.txt`, `*.csproj`, `Gemfile`, `build.gradle`
   - Read the manifest to identify language, framework, and dependency versions
   - This informs which grep patterns and config files to check in Phase 1
   - Skip if the user already identified the technology or you've been working in this codebase

For Standard/Full scope, say which phase you are in as you move through them.

## Phase 1: Gather Evidence

Investigate the codebase systematically. Every claim must come from a tool result — never from memory or assumption.

### Scope-Proportional Depth

| Scope | Steps | File Budget | Agent Delegation |
|-------|-------|-------------|-----------------|
| **Quick** | 1.1 + 1.2 only | 3-5 files | None |
| **Standard** | All steps | 10-15 files | Optional Explore agent for unfamiliar codebases |
| **Full** | All steps + fishbone sweep | No hard limit | 2 parallel investigation agents |

**Early exit:** If root cause is evident after steps 1.1-1.2, move directly to Phase 2. Not every investigation needs exhaustive evidence gathering.

### 1.1 Recent changes

Use Bash for git operations:
- `git log --oneline -20` — what changed recently?
- `git log --oneline --since="<date>"` — if user mentioned a timeframe
- `git blame -L <start>,<end> <file>` — who changed the relevant lines? (specific ranges, not whole files)
- `git diff <commit>~1 <commit>` — what exactly changed in a suspect commit?
- `git log --oneline --all --grep="<error keyword>"` — find commits mentioning the error or relevant terms
- `git log --oneline --all --grep="revert\|fix\|workaround\|hack\|fixme"` — find patches and workarounds (use selectively — can be noisy)

### 1.2 Find relevant code

- Use Grep to search for error messages, function names, class names from the symptom
- Use Glob to find related files (test files, configs, migrations)
- Use Read to examine actual code — focus on the error path, not just the happy path
- For files >200 lines, use Read with offset/limit to read only the relevant section

### 1.3 Trace the dependency chain

- From the symptom location, trace upstream: what calls this code? (Grep for function/class name usage)
- Trace downstream: what does this code depend on? (Read imports, follow calls)
- Check for recent changes in the chain: `git log --oneline <file>` on each relevant file

### 1.4 Check for patterns

- Grep for the same pattern elsewhere — does the same bug exist in other places?
- Glob for test files — is this code path tested?
- Glob for config files — could environment differences explain the issue?

**Standard scope:** Use the Quick Investigation Checklist from `<skill-dir>/references/techniques.md` mentally — have you considered factors beyond code? (Data, Infrastructure, Process, People)

**Full scope:** Read `<skill-dir>/references/techniques.md` and use the fishbone categories to structure a broader investigation. Trigger parallel agent delegation (see below).

### Agent Delegation (Full Scope)

Spawn 2 parallel investigation agents to cover fishbone categories simultaneously:

**Agent A — Code & Data** (`subagent_type: "general-purpose"`):
```
Investigate the [Code] and [Data] dimensions of this issue. You are one of two parallel investigation agents.

SYMPTOM: [symptom description]
RELEVANT FILES FOUND SO FAR: [file paths from steps 1.1-1.2]

INVESTIGATE:
- Code: Trace the code path from symptom. Check imports, dependencies, error handling, edge cases, type safety.
- Data: Check for schema mismatches, missing migrations, query issues, data format problems, encoding.

USE ONLY read-only operations: file reads, searches (the Grep and Glob tools, or grep and find through Bash), and git log, git blame, git diff, git show. Change nothing.

RULES:
- Verify that a file path exists before citing it.
- Only describe behavior of code you've Read — never infer from names alone.
- Mark unverified claims as ⚠️ HYPOTHESIS.
- Keep output ≤200 words.

OUTPUT: Summarize your findings. Format each finding as:
- [finding]: [file:line or commit SHA] — [what you found]
Mark unverified claims as ⚠️ HYPOTHESIS.
```

**Agent B — Infrastructure & Process** (`subagent_type: "general-purpose"`):
```
Investigate the [Infrastructure] and [Process] dimensions of this issue. You are one of two parallel investigation agents.

SYMPTOM: [symptom description]
RELEVANT FILES FOUND SO FAR: [file paths from steps 1.1-1.2]

INVESTIGATE:
- Infrastructure: Check config files, environment variables, resource limits, connection pools, timeouts, deployment config.
- Process: Check test coverage for this code path, CI config, monitoring/alerting setup, deployment scripts.

USE ONLY read-only operations: file reads, searches (the Grep and Glob tools, or grep and find through Bash), and git log, git blame, git diff, git show. Change nothing.

RULES:
- Verify that a file path exists before citing it.
- Only describe behavior of code you've Read — never infer from names alone.
- Mark unverified claims as ⚠️ HYPOTHESIS.
- Keep output ≤200 words.

OUTPUT: Summarize your findings. Format each finding as:
- [finding]: [file:line or commit SHA] — [what you found]
Mark unverified claims as ⚠️ HYPOTHESIS.
```

Spawn both agents in a **single message** (parallel execution). Collect results and synthesize into the evidence ledger.

**Fallback:** If agents fail, investigate these categories sequentially yourself. Note the failure and continue.

**Standard scope — optional agent:** If the codebase is unfamiliar (user didn't point to specific files), spawn a single `subagent_type: "Explore"` agent to map project structure before investigating.

### Evidence Ledger

Maintain an in-context evidence ledger throughout Phase 1. One line per finding, referenced by ID in Phase 2.

```
## Evidence Ledger
- [E1] git log: commit abc123 changed auth.js validation — removed null check (2024-03-01)
- [E2] auth.js:47 — validateToken() returns undefined when token is empty (Read)
- [E3] Grep: no test file covers validateToken() empty-token path
- [E4] ⚠️ HYPOTHESIS: config drift between staging and prod (no evidence yet)
```

Max ~15 entries. If exceeding, merge related findings or drop weakest evidence.

### Evidence Summary

After completing Phase 1, show the user where the investigation stands, then carry on into Phase 2:

**Key findings:**
- [E1] [source] — [finding summary]
- [E2] [source] — [finding summary]
- [E3] [source] — [finding summary]
(top 3-5 from evidence ledger, ordered by relevance)

**Initial hypothesis:** [1-sentence candidate root cause]
**Confidence so far:** [High/Medium/Low]

Stop and ask with AskUserQuestion only when the answer changes what you do next:
- **The evidence splits:** two or more candidate causes have comparable support and point the analysis in different directions. Present them and ask which to pursue first.
- **Something only the user has is needed:** logs, reproduction steps, access to a system. Say exactly what and why.
- **Upgrade:** the issue is more complex than the scope allows for ("I'm seeing [evidence of complexity]"). Ask before upgrading to Standard or Full, because that costs more time and may spawn agents.

**Downgrade** without asking: "This is simpler than expected — root cause is clear from [evidence]. I'll provide a [Quick/Standard] analysis instead."

## Phase 2: 5 Whys Analysis

Build the causal chain from symptom to root cause. Each "Why" must reference evidence ledger IDs.

### 5 Whys Structure

```
Symptom: [Observable problem]

Why 1: Why did [symptom] happen?
  → [Answer] [E1, E2]

Why 2: Why did [answer 1] happen?
  → [Answer] [E3]

Why 3: Why did [answer 2] happen?
  → [Answer] [E5] or ⚠️ HYPOTHESIS

(continue until systemic cause reached)

Root Cause: [The systemic issue — not the immediate trigger]
Confidence: [High / Medium / Low]
```

**Rules:**
- Stop when you reach a systemic cause (a process or structural gap, not a specific code line)
- Go beyond 5 if still at symptom level. Stop before 5 if root cause is reached earlier.
- If an answer lacks evidence, mark it `⚠️ HYPOTHESIS` and either investigate further or note it.
- **Dead end:** If a "Why" can't be answered with available evidence:
  1. Return to Phase 1 for targeted investigation — search specifically for evidence to answer THIS question
  2. If still no evidence after targeted search, mark as `⚠️ HYPOTHESIS` and continue the chain
  3. Note the gap in the evidence ledger
- **Branching:** If a "Why" has multiple plausible answers:
  1. Follow the path with the strongest evidence first
  2. Note alternative paths as contributing factors
  3. If evidence is equal, present both paths to the user and ask which to pursue
- **Information boundary:** If you can't investigate further (no access to logs, external service, etc.), state the boundary explicitly and recommend what the user should investigate manually

### Confidence Rating

- **High:** 3+ independent evidence sources, complete causal chain, no hypothesis steps
- **Medium:** 1-2 evidence sources, plausible chain but has gaps or one hypothesis step
- **Low:** Hypothesis-level, multiple gaps, needs more investigation

### Root Cause Confirmation

**Quick scope:** no checkpoint. The inline result in Phase 3 is the confirmation; the user replies if it is wrong.

**Standard / Full scope:** a report file is about to be written around this root cause, so confirm it first. Present the 5 Whys chain and confidence rating via AskUserQuestion:
- "Root cause ([confidence] confidence): [root cause]. Does this match your understanding?"
- Options: "Looks correct", "Root cause is different — I'll explain", "Need to dig deeper"

If the user says "Root cause is different", ask what direction to investigate. Return to Phase 1 evidence gathering **focused on the new direction only** — don't re-run everything.

**Validation test:** The root cause must explain ALL observed symptoms. If it only explains some, it's a contributing factor, not the root cause — keep investigating.

## Phase 3: Report & Solutions

### Quick scope

Present inline in conversation — no file, no reference reads needed:

```
**Root Cause:** [1 sentence]
**Confidence:** [High / Medium / Low]
**Evidence:** [file:line or commit SHA]
**Fix:** [What to change]
**Prevention:** [How to prevent recurrence]
```

### Severity determination

Assign severity based on impact:
- **P1 (Critical):** Data loss, security breach, or complete service outage. Immediate action required.
- **P2 (Major):** Significant functionality broken, degraded experience for many users. Action within 24h.
- **P3 (Minor):** Edge case, cosmetic, or low-impact issue. Scheduled fix.

### Standard / Full scope

1. Read `<skill-dir>/references/templates.md` for the RCA Report template (read once — this is the only read of this file)
2. Write the report to `rca-reports/RCA-<kebab-case-issue-name>.md` (create the parent directory first if the host’s write tool requires it)
3. Include the evidence ledger in the report
4. Include confidence rating with the root cause
5. For solutions, always include three tiers:
   - **Immediate:** Fix the specific symptom
   - **Short-term:** Prevent this exact recurrence (test, alert, validation)
   - **Long-term:** Systemic fix that prevents the class of failure
6. Prefer systemic solutions over individual fixes — see `<skill-dir>/references/techniques.md` Systemic vs Individual table
7. **Contributing Factors:** Review the evidence ledger for findings that contributed to the incident but aren't part of the main 5 Whys chain. Record these in the Contributing Factors table with their category (Code/Data/Infrastructure/Process) and evidence ID.
8. Run the Follow-Up Checklist from `<skill-dir>/references/templates.md` to verify completeness

## Tool Strategy

| Tool | Purpose |
|------|---------|
| **Grep** | Search for error messages, function names, patterns. Ask for file paths only for discovery, matching lines with context for analysis |
| **Glob** | Find relevant files (tests, configs, migrations). Verify file paths exist before including in report |
| **Read** | Examine source code. Always Read before claiming anything about code behavior. Use offset/limit for files >200 lines |
| **Bash** | Git operations: `git log`, `git blame`, `git diff`, `git show`, `git bisect`. Always use `--oneline` for log. Also `grep` and `find` where the session has no Grep or Glob tool. An investigation changes nothing in the working tree |
| **Agent** | Full scope: spawn 2 parallel investigation agents (Code+Data, Infrastructure+Process). Standard scope: optional Explore agent for unfamiliar codebases. Use `subagent_type: "general-purpose"` for investigation, `"Explore"` for codebase mapping |
| **Write** | Create RCA report file (Standard/Full scope) |
| **AskUserQuestion** | Clarify an unclear symptom (Phase 0), resolve split evidence or a scope upgrade (Phase 1), confirm the root cause before a report is written (Phase 2) |

`Grep` and `Glob` in this skill name the search, not a particular tool: tool availability depends on the host; use `rg` and `rg --files` through the shell when dedicated search tools are absent. Either form is fine; what matters is that every claim rests on a search or read run in this session.

## Token Management

- `git log --oneline` always — never full log unless examining a specific commit with `git show`
- `git blame -L <start>,<end>` on specific line ranges — never blame an entire file
- Read files with offset/limit when >200 lines — read the relevant section, not everything
- Evidence ledger: 1 line per finding, max ~15 entries. Merge related findings if exceeding.
- Reference files: Read each at most once. `templates.md` in Phase 3 only. `techniques.md` in Phase 1 (Full scope only).
- Agent prompts: include only symptom + relevant file paths. Never include full investigation history. 200-word output ceiling.

## Verification Rules

Every RCA finding must be traceable to actual evidence. These rules prevent hallucination.

1. **File paths:** Verify that each path exists before including it in the report. If a file doesn't exist, don't reference it.
2. **Code behavior:** Only describe behavior of code you've Read with the Read tool. Never infer behavior from function names alone.
3. **Git history:** Only cite commits from actual `git log` or `git show` output. Never invent commit SHAs or messages.
4. **Git SHA verification:** When citing a commit in the report, confirm with `git show --stat <SHA>` that it exists and touches the claimed files.
5. **Re-read before citing:** Before including a file path or code behavior in the final report, re-read the relevant lines to confirm they still match your claim.
6. **Hypotheses:** If you can't verify a claim with tool output, mark it `⚠️ HYPOTHESIS`. Never state unverified claims as fact.
7. **Root cause completeness:** The root cause must logically explain ALL observed symptoms. If it only explains some, it's a contributing factor, not the root cause.

## Edge Cases

- **No error logs available:** Focus on git history and static code analysis. Use `git log --oneline --all -- <file>` to trace file history. State the limitation explicitly in the report.
- **Can't reproduce:** Analyze code paths statically. Grep for: `async`, `await`, `Promise.all`, `setTimeout`, `setInterval`, `mutex`, `lock`, `concurrent`, `shared`, `global`. Look for race conditions and data-dependent branches. Use `git bisect` to narrow the introducing commit. Flag as `⚠️ NOT REPRODUCED`.
- **Environment-dependent:** Grep for: `process.env`, `ENV`, `config`, `.env`, `environment`, `staging`, `production`. Compare config files across environments with `git diff`.
- **Multiple candidate root causes:** Present all candidates with evidence and confidence ratings. Let the user decide or investigate further.
- **User doesn't know when it started:** Use `git log --oneline -50` with broader range. Search for related patterns across recent commit history.
- **Unfamiliar codebase:** Spawn an Explore agent to map project structure. Read package.json / Cargo.toml / go.mod / pyproject.toml first. Glob for project structure (`**/*.{ts,js,py,go,rs}`) to understand layout.
- **Root cause in a dependency:** Check dependency versions in manifest file. Search for recent dependency changes: `git log --oneline -- <lockfile>`. Grep for the dependency name in error output. Note the specific version and suggest checking the dependency's changelog/issues. Flag as `⚠️ EXTERNAL DEPENDENCY`.
- **Issue spans multiple repos/services:** Identify the service boundary from config, API calls, or network patterns. Investigate this repo's side thoroughly. Document the boundary point and what the OTHER side should investigate. Don't speculate about code you can't read.
- **Simple bug (not systemic):** Use Quick scope. An obvious typo or off-by-one doesn't need a full postmortem — say so and suggest the fix.

## Inconclusive Investigation

If the investigation cannot determine a definitive root cause:

1. **Insufficient evidence:** If the evidence ledger has fewer than 3 entries after Phase 1, tell the user: "I couldn't find enough evidence. This may require: [specific suggestions — runtime logs, debugger, access to specific systems]."
2. **Multiple equal candidates:** If 2+ root causes have equal evidence strength, present all candidates with their evidence in the report. Mark as "INCONCLUSIVE — multiple candidates" rather than picking one.
3. **Information boundary:** If the root cause appears to be outside the codebase (dependency, infrastructure, external service), document what IS known and specify exactly what to investigate externally.
4. **Partial report:** For Standard/Full scope, write a partial RCA report to `rca-reports/RCA-<name>-PARTIAL.md` using the same template but:
   - Mark the Root Cause section as "## Root Cause (Inconclusive)"
   - Add a "## Recommended Next Steps" section listing specific investigations needed
   - Include all evidence gathered — partial findings are still valuable
   - Set confidence to "Low" with explanation of what's missing
5. **Quick scope:** Present inline with: "I couldn't determine the root cause definitively. Here's what I found: [findings]. To resolve, try: [specific next steps]."

## Key Principles

- A symptom is not a root cause. "The query was slow" is a symptom. "No query performance testing in CI" is the root cause.
- Prefer systemic fixes over individual fixes. Fix the process that allowed the bug, not just the bug itself.
- Every claim needs evidence. No evidence means hypothesis, not finding.
- Stop at the actionable level. Don't ask "why" past the point where you can recommend a concrete fix.
- Simple bugs get simple treatment. Not every issue needs a full postmortem.
- Token-efficient. Minimize context consumption — summarize, limit reads, use agents to parallelize without bloating the main context.
- Confidence-rated. Every root cause finding carries a confidence level so users know how much to trust it.
