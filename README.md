# imaslou-agent-kit

Plugins and shared agent skills for **Claude Code and OpenAI Codex**, by Ilya Maslau.

Each plugin can be integrated into either environment. The same workflow files
ship with host-specific marketplace metadata, resource-path guidance and agent
handoffs. Install the complete plugin; copying a single skill folder can leave
its shared references or scripts behind.

Examples below use Claude Code’s `/plugin:skill` syntax. In Codex select the
installed skill or use `$skill-name` with the same input and flags. For example,
`/ios-comprehensive-review:review-all --base main` becomes `$review-all --base main`.
Automatic triggers apply only to skills that permit them.

The kit leaves model selection to your host configuration: workers use your
configured subagent default or inherit the active session's model, subject to
the host's routing rules. Plugins do not choose a different model for a role.
You can explicitly request a supported model for a particular task. Existing
reasoning-effort settings and workflow limits are separate from this policy.

## Plugins

### iOS code review

Two plugins for reviewing iOS/Swift code. They differ in what they review and how they do it.

| Plugin | Reviews | Approach | Best for |
|--------|---------|----------|----------|
| [ios-quick-review](./plugins/ios-quick-review) | Uncommitted changes (default), commits, PRs | Single agent, 8 sequential phases | Work-in-progress code, small diffs, scope confirmation |
| [ios-comprehensive-review](./plugins/ios-comprehensive-review) | Committed branch/PR history only | 5 parallel agents, 4-stage pipeline | Large PRs, cross-file analysis, resumable reviews |

`ios-comprehensive-review` uses `git diff base...head` and only sees committed history. Uncommitted or staged changes are not included. To review uncommitted work, use `ios-quick-review` or commit first.

#### [ios-quick-review](./plugins/ios-quick-review)

Step-by-step code review that adjusts depth based on diff size.

- 8 phases: scope confirmation, then 7 review areas (correctness, architecture, naming, dead code, performance, side effects, AGENTS.md compliance)
- Adapts to diff size: small diffs get a quick combined pass; large diffs are split across parallel agents
- Confirms scope before starting deep analysis
- Searches the entire codebase to find every call site for each changed function or variable

**Skills:**

| Skill | Trigger |
|-------|---------|
| `/ios-quick-review:ios-quick-review` | "review my code", "review this commit", "check my changes", "find bugs" |

Auto-triggers only for Swift/iOS codebases.

**Requires:** Swift/iOS codebase. AGENTS.md in project root (optional, for naming/compliance checks)

---

#### [ios-comprehensive-review](./plugins/ios-comprehensive-review)

Multi-agent code review using 5 parallel agents across a 4-stage pipeline. Can resume if interrupted.

- Per-file analysis: unused code, force unwraps, memory leaks, threading, Swift Concurrency (`@Sendable`, actor isolation, continuations), naming
- Cross-file analysis: duplicate code, breaking API changes (including deleted functions), design violations with over-engineering check
- Test-aware: reports fewer warnings for test files
- Verified: an independent agent re-reads the code behind every critical and warning finding; what it can disprove is dropped with the reason, what it cannot decide is marked unverified
- Resumable: picks up where it left off if interrupted

**Commands and skills:**

| Skill | Trigger |
|-------|---------|
| `/ios-comprehensive-review:review-all <PR number>` | "Review PR <number>", "Full iOS review for branch developer against main" |
| `/ios-comprehensive-review:review-all --base <branch>` | Review current branch against base |

`/ios-comprehensive-review:review-all` runs all 4 stages in one command with progress tracking.

Individual stage commands for debugging, partial re-runs, or splitting across sessions:

| Command | Stage |
|---------|-------|
| `/ios-comprehensive-review:review-extract <PR number>` | 1. Extract diff and metadata |
| `/ios-comprehensive-review:review-analyze` | 2. Per-file analysis (parallel agents) |
| `/ios-comprehensive-review:review-cross-check` | 3. DRY, breaking changes, SOLID |
| `/ios-comprehensive-review:review-report` | 4. Generate final report |
| `/ios-comprehensive-review:review-cleanup` | Remove intermediate files, keep only report |

**Branch mode:** use `--base <branch>` in place of `<PR number>` in extract commands.

**Requires:** `jq`, `gh` CLI (PR mode), `git` (branch mode)

---

### App Store compliance

#### [appstore-guideline-auditor](./plugins/appstore-guideline-auditor)

Audits a native iOS Xcode project for App Store rejection risks against a checked rule catalogue. Read-only: it modifies nothing that was already in the project and creates exactly one file, its report, and it checks that against a file list taken when the audit starts.

Distinct from the two review plugins above. They ask whether your Swift is good; this asks whether Apple will reject it.

- Every finding carries **two independent grades** — a severity, and how firmly code evidence supports it: `PROVEN` (a file and line, or a required thing confirmed absent), `PROBABLE` (the pattern matched but the finding says *which* context it could not confirm), `MANUAL` (undecidable from code — routed to a checklist, never into the findings list)
- Nothing is dropped for being uncertain; uncertainty is labelled, so a wide net does not cost you a report where a guess and a fact look identical
- **Citations are checked, not copied.** Apple reuses and retires guideline numbers — 2.5.10 is now *intentionally omitted*, and 4.5.5 went from Push Notifications to Game Center Player IDs. No rule enters the catalogue until its number resolves against Apple's text, and each run re-checks against Apple's current published text
- Resolves Apple's guidelines and policy pages by **search, then fetch**, so a requirement announced after the plugin shipped is still reached. A run that cannot reach them still completes, recording per source whether each citation was verified
- **Every shipping target separately** — ITMS-91053 is evaluated per target by an automated scanner, so a widget extension is a separate product and gets its own privacy-manifest check
- Regional and dated requirements (Brazil, EU, Korea, the September 2026 age-rating mandate) name the storefront or date they apply to and the source they were verified against
- Refuses cross-platform projects by name rather than auditing them badly — Flutter, React Native, Expo, Kotlin Multiplatform, .NET MAUI, Cordova/Ionic, Capacitor, Unity
- **68 rules, derived rather than copied** — merged from 249 named rule topics across four MIT-licensed upstream sources, re-authored with executable detection patterns, re-graded against one severity vocabulary in place of four incompatible ones, and re-cited against Apple's text, which contradicts two of the four sources on Guideline 4.8
- **Registers no hooks and ships nothing that only checks itself.** Every file in the installed plugin runs during an audit

**Commands:**

| Command | What it does |
|---------|--------------|
| `/appstore-guideline-auditor:appstore-audit [path]` | Audit an Xcode project; `--out <path>` to redirect the report |

**Produces:** `.appstore-audit/report.md` in the audited project — a readiness verdict, findings grouped by target, and an App Store Connect checklist generated from what the scan actually found.

**Reaches the network.** Declared in the skill's `compatibility` field so you learn it before running, not after.

**Works with:** native iOS/Swift Xcode projects only

---

### Planning and specification

#### [grill-me](./plugins/grill-me)

Pre-task interview that ends in a written brief and a verdict on whether you are ready to start. It is for the part models still do poorly on their own: finding the requirement you never stated, and knowing when to stop asking.

- Reads everything you hand it first, and checks claims about the code against the code
- States its assumptions before asking anything, ordered by how much breaks if one is wrong; you correct only what is wrong
- Says what each assumption rests on: a line it opened, your own words, or "a guess". A file or link it could not open is named, never summarised
- Asks a question only when two plausible answers lead to materially different work, or a wrong guess would be expensive to undo; every question carries a recommended answer
- Looks for what you have not thought of: pre-mortem, riskiest assumption, example mapping, a blindspot pass for unfamiliar territory, an integration check across your answers
- Says "nothing worth asking" on a small, fully specified task instead of running an interview anyway
- Writes one brief that keeps what you decided apart from what was only assumed, with the full Q&A

**Commands:**

| Command | What it does |
|---------|--------------|
| `/grill-me:grill-me <what you have>` | In-depth interview: rounds of questions until the answers stop changing the work, then the brief |
| `/grill-me:grill-me --fast <what you have>` | The 80/20 version: one round of at most four questions, top risks stated rather than asked |

**Produces:** `docs/briefs/<date>-<slug>.md`

**Stops at the brief.** No implementation, no design, no spec. Hand the brief to `/feature-spec:feature-spec`, plan mode or a fresh session.

**Works with:** any task, code or not; grounds itself in the repository when there is one

---

#### [feature-spec](./plugins/feature-spec)

Turns what you already have into a critic-verified spec, and a separate command turns that spec into a checked implementation plan. The spec run stops at the spec and never learns a plan can follow it — a spec written as a gate on the way to code gets optimised to be *passed* rather than to be good.

- Takes an idea, a brief, or any documents you pass; decisions you already made are recorded and never asked again
- Reads a document, does not believe it: every claim about the repo is checked against the code and graded confirmed, contradicted or unverifiable
- A decision taken from your document keeps your wording: a script compares each one with the document and fails a paraphrase
- Asks only about what is still unclear, tracked against a fixed 10-category coverage taxonomy: no round for complete input, two short rounds at most
- Compaction-proof: every decision is written to a design record **with its reasoning** the moment it is known, so drafting reads the record rather than the conversation
- Enforces the rules you already wrote down (applicable project and user instructions supplied by Claude Code or Codex) and ships none of its own; a justified deviation is recorded with the rule quoted verbatim
- Every requirement, success criterion, scope line and constraint carries a source tag naming where in the record it came from — anything untraceable is cut or marked, never asserted
- The spec that ships is the draft that was checked: publishing renames the file, so nothing is retyped after the checks ran
- Proposes competing strategies and records the chosen one *and the rejected ones*, with reasons
- Builds a project glossary and promotes hard-to-reverse decisions to ADRs via a three-part test
- An independent critic scores the draft before anything is written, and cannot rubber-stamp: zero findings requires a list of what it checked, and every quote in its reply is compared with what it was shown
- Every `path:line` a grounding fact cites is opened by a script: a file that is not there, or a line past its end, fails the record
- Detachable Swift/iOS, TypeScript and Python layers that load only on stack detection
- Ships deterministic validators that check the plugin's **own output** — the design record, the draft before the critic, the plan against its spec — and that refuse to report a pass they did not actually establish
- The plan stage proves the join to the spec **in both directions**: no task may cite a requirement the spec does not define, and no requirement may be silently dropped
- Task done-conditions are the spec's own acceptance scenarios, quoted and looked up rather than restated; milestones come from the spec's P1/P2/P3 priorities
- Every implementation decision the spec did not settle is recorded as an assumption with its reversal cost

**Commands:**

| Command | What it does |
|---------|--------------|
| `/feature-spec:feature-spec <idea and/or documents>` | Intake, clarify only what is unclear, strategy, draft, critique, publish |
| `/feature-spec:feature-spec-plan <slug>` | Turn a finished spec into ordered tasks with milestones, dependencies and quoted done-conditions — then have a critic score the plan |

**Spec flags** (`/feature-spec:feature-spec`): `--resume` (finish a run that stopped) · `--scope <path>` (confine grounding to one directory)

**Plan flags** (`/feature-spec:feature-spec-plan`): `--extend` (keep the existing tasks, add what the spec gained) · `--tasks-only` · `--from-spec <path>` · `--out <dir>`

**Produces:** `docs/specs/<date>-<slug>/{spec.md, tree.md, critique.md, traceability.md}`, `plan/{plan.md, tasks/T0N.md, plan-critique.md}` if you run the plan command, `docs/specs/GLOSSARY.md`, and ADRs in `docs/adr/`

**Stops at the plan.** No code, no `/implement`, and no estimates in hours or days at either stage.

**Works with:** any project; sharpest on iOS/Swift. Pairs with `grill-me`: pass its brief as the input

---

### Knowledge and context

Plugins for saving project knowledge and debugging notes so they persist across sessions.

#### [memory-bank](./plugins/memory-bank)

Documentation system that records the current state of a project, organized by feature. Every claim is checked against actual source code.

- Creates a structured `memory-bank/` folder with per-feature documentation
- Deep code analysis: architecture, data flow, key types, dependencies, tests
- Accuracy verification: every file path, type name, and behavior description is checked against real code
- Root-level docs: WIKI index, system patterns, tech context, troubleshooting

**Skills:**

| Skill | What it does |
|-------|--------------|
| `/memory-bank:init-memory-bank` | Scan project and create `memory-bank/` with root-level docs |
| `/memory-bank:update-memory-bank <feature>` | Deep-analyze and generate verified feature docs |
| `/memory-bank:update-memory-bank-system` | Refresh root-level docs (architecture, deps, WIKI index) |
| `/memory-bank:add-decision <feature>: <desc>` | Record a technical decision (ADR-style) |
| `/memory-bank:memory-bank` | Navigate the Memory Bank, route to the right sub-skill |

**Works with:** Any language (detects project type automatically; optimized for Swift/iOS)

---

#### [scratchpad](./plugins/scratchpad)

Debugging notebook that saves investigation notes across sessions.

- Creates `.scratchpads/` directory with one markdown file per issue (`SP-<issue-name>.md`)
- Tracks failed attempts, edge cases, related files, and design decisions
- On resolution, cleans up into a solution summary (moved to `resolved/`)
- Re-reads from disk on every call, so multiple concurrent sessions are safe
- Auto-shrinks at 150+ lines to keep AI context usage low

**Skills:**

| Skill | What it does |
|-------|--------------|
| `/scratchpad:scratchpad` | Create new, update existing, resolve, abandon, or switch scratchpads |

Intent is detected from natural language: "resolve", "abandon", "switch." No sub-commands to remember.

**Works with:** Any project

---

### Analysis and decision making

Plugins for in-depth analysis, challenging ideas from multiple angles, and finding root causes.

#### [multi-agent-debate](./plugins/multi-agent-debate)

Multi-agent debate that analyzes topics from genuinely different perspectives.

- Launches independent participants instructed to produce text without tools; host enforcement differs (see the plugin README)
- 10 built-in thinking styles give agents distinct personalities and reasoning patterns
- 3-round debate: Opening Positions, Cross-Examination, Rebuttals (or 2-round quick mode)
- If agents agree too early after Round 1, the panel is reshuffled to force real disagreement
- A neutral Judge delivers a verdict with direct quotes, confidence level, minority opinions, and conditions that would change the answer
- Post-debate options: go deeper, challenge the verdict, add a new agent, or export to markdown

**Skills and agents:**

| Component | Name | Trigger |
|-----------|------|---------|
| Skill | `/multi-agent-debate:multi-agent-debate` | "debate this", "red team", "devil's advocate", "steelman", "argue both sides" |
| Agent | `debate-agent` | Spawned automatically by the skill for each participant |

**Works with:** Any topic; technical decisions, strategies, proposals, tradeoffs

---

#### [root-cause-analysis](./plugins/root-cause-analysis)

Finds the real cause of bugs and incidents using the 5 Whys method and structured reports.

- Guides investigation from observed symptom to actual root cause using the 5 Whys technique
- Groups contributing factors into categories: Code, Data, Infrastructure, Process, People
- 7-step process: gather facts, reproduce, identify factors, find root cause, propose solutions, implement, document
- Structured report with timeline, impact, solutions, prevention plan

**Skills:**

| Skill | What it does |
|-------|--------------|
| `/root-cause-analysis:root-cause-analysis` | Guided analysis with 5 Whys, fishbone diagram, and RCA report |

**Works with:** Any project; production incidents, repeated bugs, performance issues, post-incident reviews

---

### Writing and editing

#### [humanizer](./plugins/humanizer)

AI-to-human text converter. 9-step pipeline: Content Intelligence, pattern detection, rewrite, two-pass self-audit, independent judge verification.

- 23 patterns in two priority tiers: tier 1 (8 patterns, ~80% of detectable AI tells) always fixed; tier 2 (15 patterns) fixed when present
- Statistical texture: information density variation, sentence length variance, referential cohesion, punctuation variety
- Adaptive voice: 12 content archetypes (blog, technical, email, marketing, academic, etc.) with mechanical voice parameter detection
- Two-pass self-audit: adversarial self-question + 14-point mechanical checklist
- Independent judge agent: for long text (>2000 words), a separate agent scores the rewrite without seeing the editing process
- Content integrity: never adds facts, claims, or opinions absent from the original; anti-hallucination guardrails block fabricated statistics and citations
- Era-aware vocabulary: AI word lists tagged by model generation (2023, 2024, 2025+) in `references/` for easy updates

**Skills and agents:**

| Component | Name | Trigger |
|-----------|------|---------|
| Skill | `/humanizer:humanizer` | "humanize this", "de-slop", "sounds like AI", "too robotic", "reads like ChatGPT", "make it sound natural" |
| Agent | `judge` | Spawned automatically by the skill for long text verification |

**Works with:** Any text in any language; blog posts, documentation, emails, marketing copy, academic writing

---

## Installation

### Codex

With a plugin-capable Codex CLI, run in your terminal:

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add <plugin-name>@imaslou-agent-kit
```

For a local checkout, use its absolute path instead of the GitHub identifier:

```sh
codex plugin marketplace add /absolute/path/to/imaslou-agent-kit
```

Use `codex plugin list --marketplace imaslou-agent-kit` to inspect the catalog,
or `/plugins` inside the Codex CLI to browse it. Start a new session after
installing. Desktop marketplace controls vary by version; the repository also
ships `.agents/plugins/marketplace.json` for hosts that discover repo catalogs.
This repository is a custom marketplace, not a listing in OpenAI’s public directory.

Install any of the ten plugins listed above, then use its `$skill-name` command.
For example: `$appstore-audit /path/to/MyApp`, `$feature-spec <idea>`, or
`$init-memory-bank`. Explicit-only skills stay explicit-only in Codex through
`agents/openai.yaml`.

The scripts need a Unix shell (macOS, Linux or WSL). `feature-spec` and the App
Store auditor need Python 3; comprehensive reviews need `jq` and Git, plus
an authenticated `gh` for PRs. Independent critics and debate participants need
subagent support. Without it, skills disclose reduced coverage or self-review.
Model selection follows your host configuration in both environments. Claude's
automatic skill hooks do not carry over: Codex runs the feature-spec validators
explicitly.

See [runtime conventions](docs/runtime.md) for the host mapping and
[compatibility and validation](docs/compatibility.md) for maintainer checks.
The packaging follows [OpenAI’s plugin documentation](https://developers.openai.com/plugins/build/plugins).

### Claude Code

The commands in this section run inside Claude Code, including its terminal
CLI and editor panel.

#### Migrating from `imaslov-claude-plugins`

The repository and marketplace are now named `imaslou-agent-kit`. Existing installations use the old marketplace ID and need to be reinstalled under the new one.

1. Note which plugins you have installed and their scopes in `/plugin`.
2. Remove the old marketplace with `/plugin marketplace remove imaslov-claude-plugins`. This also uninstalls its plugins; save any plugin data or settings you need first.
3. Add the renamed marketplace with `/plugin marketplace add ms-ilya/imaslou-agent-kit`.
4. Reinstall your plugins with `/plugin install <plugin-name>@imaslou-agent-kit`, choosing the same scopes as before. Update any project settings that explicitly reference the old marketplace ID.

#### Prerequisites

- **Terminal:** [Claude Code CLI](https://code.claude.com/docs/en/overview) installed and authenticated
- **VS Code / Cursor:** [Claude Code extension](https://marketplace.visualstudio.com/items?itemName=anthropics.claude-code) installed and signed in

#### Visual guide (VS Code / Cursor)

The screenshots show the previous repository name. Use the repository URL and commands written below.

##### Step 1: Open plugin manager

Type `/plugin` in the Claude Code input field and select **Manage plugins**.

<p align="center">
  <img src="docs/images/install-step1-plugin-command.png" width="600" alt="Type /plugin to open the plugin manager">
</p>

##### Step 2: Add the marketplace

Switch to the **Marketplaces** tab. Paste the marketplace URL into the input field and click **Add**:

```
https://github.com/ms-ilya/imaslou-agent-kit.git
```

<p align="center">
  <img src="docs/images/install-step2-add-marketplace.png" width="600" alt="Add marketplace URL in the Marketplaces tab">
</p>

Once added, **imaslou-agent-kit** appears alongside other marketplaces:

<p align="center">
  <img src="docs/images/install-step3-marketplace-added.png" width="600" alt="Marketplace successfully added">
</p>

##### Step 3: Install plugins

Switch to the **Plugins** tab. All available plugins from the marketplace are listed here. They are sorted by install count, so newly added marketplace plugins will likely appear at the bottom of the list. Scroll down or use the search box to find them.

Click **Install** on any plugin. You will be prompted to choose an installation scope:

- **Install for you** — available in all your projects (user scope)
- **Install for this project** — shared with collaborators via `.claude/settings.json` (project scope)
- **Install locally** — only for you, only in the current repo (local scope)

<p align="center">
  <img src="docs/images/install-step4-install-plugin.png" width="600" alt="Install plugin with scope selection">
</p>

##### Step 4: Enable, disable, and manage

After installation, all plugins appear in the **Plugins** tab with toggle switches. Enable or disable any plugin at any time without uninstalling it. A restart banner appears when changes need to take effect.

<p align="center">
  <img src="docs/images/install-step5-plugins-installed.png" width="600" alt="Installed plugins with enable/disable toggles">
</p>

#### Terminal CLI commands

The same operations are available as CLI commands:

```bash
# Step 1: Add the marketplace
/plugin marketplace add ms-ilya/imaslou-agent-kit

# If you've cloned this repo locally, you can add it by path instead:
/plugin marketplace add ~/downloads/imaslou-agent-kit

# Step 2: Install a plugin (user scope — default)
/plugin install <plugin-name>@imaslou-agent-kit

# Install to project scope (shared with team)
/plugin install <plugin-name>@imaslou-agent-kit --scope project
```

**Available plugins:**

| Plugin name | Install command |
|-------------|----------------|
| `ios-quick-review` | `/plugin install ios-quick-review@imaslou-agent-kit` |
| `ios-comprehensive-review` | `/plugin install ios-comprehensive-review@imaslou-agent-kit` |
| `memory-bank` | `/plugin install memory-bank@imaslou-agent-kit` |
| `scratchpad` | `/plugin install scratchpad@imaslou-agent-kit` |
| `multi-agent-debate` | `/plugin install multi-agent-debate@imaslou-agent-kit` |
| `root-cause-analysis` | `/plugin install root-cause-analysis@imaslou-agent-kit` |
| `humanizer` | `/plugin install humanizer@imaslou-agent-kit` |
| `grill-me` | `/plugin install grill-me@imaslou-agent-kit` |
| `feature-spec` | `/plugin install feature-spec@imaslou-agent-kit` |
| `appstore-guideline-auditor` | `/plugin install appstore-guideline-auditor@imaslou-agent-kit` |

#### Managing plugins

```bash
# Open the interactive plugin manager
/plugin

# List marketplaces
/plugin marketplace list

# Disable a plugin without uninstalling
/plugin disable <plugin-name>@imaslou-agent-kit

# Re-enable a disabled plugin
/plugin enable <plugin-name>@imaslou-agent-kit

# Uninstall a plugin
/plugin uninstall <plugin-name>@imaslou-agent-kit

# Update marketplace listings
/plugin marketplace update imaslou-agent-kit

# Reload after changes
/reload-plugins
```

#### Scopes

| Scope | File | Use case |
|-------|------|----------|
| `user` (default) | `~/.claude/settings.json` | Personal — all projects |
| `project` | `.claude/settings.json` | Team — shared via git |
| `local` | `.claude/settings.local.json` | Personal — this project only (gitignored) |

## License

[MIT](./LICENSE)
