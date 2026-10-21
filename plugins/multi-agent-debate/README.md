# Multi-agent debate plugin

Works in **Claude Code and Codex**. Install the complete plugin so its skills,
references, scripts and agent instructions stay together.

## Installation and invocation

**Claude Code** (inside the Claude Code prompt):

```text
/plugin marketplace add ms-ilya/imaslou-agent-kit
/plugin install multi-agent-debate@imaslou-agent-kit
```

**Codex** (in a terminal with a plugin-capable Codex CLI):

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add multi-agent-debate@imaslou-agent-kit
```

Start a new session after installation. Invoke `/multi-agent-debate:multi-agent-debate` in
Claude Code or `$multi-agent-debate` in Codex. The slash examples below use Claude
Code syntax; Codex uses `$<skill-name>` with the same input and flags. Natural
language triggers apply only to skills that allow automatic invocation.
See the [kit installation guide](../../README.md#installation) and the bundled
[runtime conventions](references/runtime.md) for tool and subagent differences.

Model selection follows your host configuration, including subagent defaults.
The plugin supplies no model override; workers normally inherit the active
session's model when no host override applies. You can request a supported
model explicitly.

Independent agent stages require host subagent support. Runs with limited
delegation report that limitation.


## The problem

When one AI is asked to "consider both sides," it tends to agree with itself. All the "perspectives" share the same context, so they converge on the same conclusion in different words. There is no real disagreement.

## The solution

Separate AI agents each receive their own instructions, point of view, and biases. They cannot see each other's instructions, so they disagree for real.

The core idea is productive conflict. Agents challenge each other, attack weak points, and concede when the other side is right. A neutral Judge then picks the best reasoning and delivers a final verdict.

## What it does

The debate runs through structured rounds, each dispatched as parallel Agent tool calls:

```
Step 0: Parse & Frame       →  Identify the issue, narrow if too broad, choose debate depth
Step 1: Agent Assembly      →  Select 3-5 agents tailored to the specific issue
Step 2: Build & Dispatch    →  Construct role prompts, spawn independent subagents
Step 3: Round Execution     →  Opening → Cross-Examination → Rebuttals (3 rounds or 2 for quick)
Step 4: Final Judgment      →  The agent steps into Judge role, synthesizes verdict
Step 5: Post-Debate Options →  Go deeper, challenge, add agent, or export
```

### Agent design

Each debate gets 2-6 custom agents (typically 3-5), chosen for the topic. There are no generic "Optimist/Pessimist" panels. Agents are built using a hybrid system: 10 built-in thinking styles give them deeper personalities (how they think, how they argue, what they tend to miss), while fully custom agents can be created from scratch when no built-in style fits.

Every agent has:

- **Name and role** - a domain-specific identity (e.g., "The Pragmatist, Senior Engineering Lead")
- **Lens** - what they optimize for (e.g., delivery speed, team morale, debt reduction)
- **Core assumption** - the foundational belief driving their position
- **Blind spot** - what they undervalue, stated honestly for better cross-examination
- **Archetype** - *(optional)* a built-in thinking style that shapes how the agent reasons and argues; agents without a matching style are created from scratch

The agent panel is presented for review before the debate starts. Agents can be swapped or adjusted.

### Thinking styles

Ten built-in thinking styles give agents distinct personalities and reasoning patterns:

| Archetype | Core Belief | Best For |
|-----------|-------------|----------|
| Evidence Absolutist | Can't prove it with data? It doesn't count. | Technical tradeoffs, quality |
| Narrative Architect | Can't persuade? Your argument loses. | Strategy, buy-in |
| Systems Paranoid | Assume it's already compromised. | Security, high-stakes |
| User Empath | What do real people actually need? | Product, DX |
| Process Engineer | Find the bottleneck, fix it, measure it. | Operations, scaling |
| Experiment Scientist | Don't decide — test. | Prioritization, growth |
| Foundation Builder | Get the architecture right first. | Platform, tech debt |
| Adoption Realist | Nobody uses it? It's worthless. | Adoption, migration |
| Bias Archaeologist | Who is excluded by the defaults? | Inclusion, global audiences |
| Choice Architect | People follow defaults, not reason. | Behavioral design, onboarding |

Thinking styles add depth but never replace custom agents. The system only assigns a style when it genuinely fits the topic and never uses the same style twice in one debate.

### Debate rounds

**Round 1, opening positions:** Each agent independently describes the problem, states a clear position that can be proven wrong, and presents their strongest argument.

**Round 2, cross-examination:** Each agent receives all other agents' opening positions and must attack each opponent's weakest claim, find edge cases, and expose hidden costs. "I generally agree but..." is banned.

**Round 3, rebuttals:** Each agent receives only the critiques directed at them (not all cross-examination). They must concede valid points honestly or explain specifically why critiques miss the mark, then defend with new reasoning.

Quick analysis mode (2 rounds) is available for simpler tradeoff questions; it skips the rebuttal round.

### Judge verdict

The final verdict includes:

- **Synthesis** - where agents agreed and where they genuinely disagreed
- **Verdict** - a clear recommendation with confidence level (High/Moderate/Low) and conditions that must hold true
- **Dissent log** - minority opinions worth keeping, conditions that would change the verdict, and questions that need more data

### Post-debate options

After the verdict:

1. **"Go deeper"** - Spawn agents again on unresolved tensions from the Dissent Log
2. **"Challenge the verdict"** - Introduce a new constraint; all agents respond in a mini-round
3. **"Add an agent"** - Define a new perspective; existing agents cross-examine the newcomer
4. **"Export"** - Write a clean summary to `debate-[topic-slug].md` via the Write tool

## Skills and agents

This plugin provides:

| Component | Name | Purpose |
|-----------|------|---------|
| **Skill** | `/multi-agent-debate:multi-agent-debate` | Orchestrator workflow: assembles panels, dispatches rounds, synthesizes verdicts |
| **Agent** | `debate-agent` | Debate participant subagent for text-only arguments: one reply (`maxTurns: 1`) and no tool that writes or runs anything |

Trigger with: `/multi-agent-debate:multi-agent-debate <issue or decision to debate>`

It also triggers when you ask for one by name: "debate this", "red team", "devil's advocate", "steelman", "argue both sides", "multi-perspective analysis". A plain request for feedback or pros and cons gets a direct answer, not a debate.

### Examples

| You say... | What happens |
|-----------|--------------|
| "Debate whether we should use microservices" | Full 3-round debate with tailored agents |
| "Red team this proposal" | Adversarial analysis with pressure-testing |
| "Analyze this from all angles" | Multi-perspective analysis with synthesis |
| "Devil's advocate on our auth strategy" | Structured challenge with cross-examination |
| "Stress-test this idea" | Edge cases and hidden costs surfaced |
| "Quick take on Python vs Rust for this" | 2-round quick analysis mode |

## Capabilities used

| Tool | Purpose |
|------|---------|
| **Agent** | Spawn independent parallel `debate-agent` subagents for each debate participant; genuine parallelism with separate context |
| **Read** | Read attached files, reference documents, and skill reference files |
| **Write** | Export debate transcript to a markdown file |

Participants are instructed to return one text reply without tools. Claude Code
also limits their registered tool set and turn count. In Codex the parent passes
the role instructions into a fresh worker; those instructions are not a tool
sandbox. Only the orchestrator should use tools during the debate.

## Architecture

```
┌─────────────────────────────────────────────┐
│         ORCHESTRATOR (Host / Skill)       │
│                                             │
│  1. Build persona prompts per agent         │
│  2. Dispatch parallel debate-agent calls    │
│  3. Collect & route responses               │
│  4. Check divergence, restructure if needed │
│  5. Feed cross-agent context for rebuttals  │
│  6. Step into Judge role for final verdict  │
└──────────┬──────────┬──────────┬────────────┘
           │          │          │
     ┌─────▼──┐ ┌─────▼──┐ ┌────▼───┐
     │Agent A │ │Agent B │ │Agent C │  ... (parallel)
     │debate- │ │debate- │ │debate- │
     │agent   │ │agent   │ │agent   │
     │no tools│ │no tools│ │no tools│
     │maxT: 1 │ │maxT: 1 │ │maxT: 1 │
     └────────┘ └────────┘ └────────┘
```

### How thinking styles work

The system reads `references/archetypes.md` once when building agents. Agents that receive a thinking style get two extra instructions: how to think and how to argue. This makes their reasoning genuinely different from other agents. Those without a matching style use a fully custom profile instead. Both types participate in the debate the same way.

## Quality guardrails

- **Agreement detection** - After Round 1, if two or more agents reach the same conclusion, the panel is reshuffled and the agreeing agent re-runs Round 1 (max 1 retry)
- **No made-up facts** - Agents must never invent examples, company names, or statistics; guesses must be clearly labeled
- **Judge must quote directly** - The Judge uses exact quotes from agents, not summaries from memory
- **No early agreement** - If all agents agree too soon, the Judge flags it
- **Style clash check** - After building the panel, the system verifies that at least two agents have thinking styles that naturally oppose each other
- **Fallback** - If the Agent tool is unavailable, a simpler version runs (one model, one at a time) and reports the limitation

## Requirements

- Claude Code or Codex with subagent support for independent participants
- No API keys, external services, or dependencies needed

## Design

- Agents are truly independent: separate `debate-agent` subagents with one requested reply and no inherited conversation context before cross-examination (`maxTurns: 1` is Claude-specific)
- Minimum 3 agents per debate to avoid simple "for vs against" framing
- Full debate (3 rounds) or quick analysis (2 rounds)
- Organized cross-examination where each agent gets a dedicated section per opponent
- Responses kept short, 200-350 words per agent per round
- Handles tricky cases: yes/no questions, topics that are too broad, already-settled facts, personal decisions
