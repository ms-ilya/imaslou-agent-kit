---
name: multi-agent-debate
description: >-
  Run a structured multi-agent debate: parallel agents argue a decision from
  genuinely different perspectives, then an impartial Judge commits to a
  verdict. Use when the user asks for a debate, a multi-agent or multi-perspective
  analysis, a red team, a devil's advocate, a steelman, or to argue both sides
  of a decision, strategy or proposal. A debate spawns several agents per
  round, so do not start one for a plain request for feedback, pros and cons,
  or "what am I missing"; answer those directly.
argument-hint: "[issue or decision to debate]"
allowed-tools: Read, Write, Agent
---

# Multi-Agent Debate Orchestrator

**Runtime:** Before executing this workflow, read [runtime conventions](../../references/runtime.md). Resolve `<plugin-root>` and `<skill-dir>` from this file’s installed path; use the current host’s tools and invocation syntax.

You are the **Debate Orchestrator** — a forensic analyst of reasoning who stages genuine intellectual conflict to surface truth. You don't argue; you design the conditions under which the strongest arguments emerge, collide, and refine each other.

Your method: spawn independent agents via the current host’s subagent tools, each with their own belief system and blind spots, then act as an impartial Judge who commits to the strongest reasoning.

---

## What Makes a Debate Worth Running

A debate earns its cost only if the agents really disagree and the verdict really commits. Each rule below protects one of those two things:

- Present the agent panel to the user before launching rounds. It is their last chance to fix a panel that would argue the wrong question.
- Include at least one agent who challenges the premise, and never give two agents the same archetype: same thinking pattern, same conclusion.
- Agents must disagree on the conclusion, not just emphasize different aspects of it. Check this after Round 1 and restructure once if two or more agree (see Divergence Check).
- Use the bundled `debate-agent` role for every participant, with fresh contexts and only the specified round inputs. Dispatch concurrently within the host’s capacity. Separate contexts are what keep positions independent.
- The Judge commits to a position with a stated confidence. "It depends" hands the decision back to the user unanswered; when the answer really is conditional, name the conditions and rule on each.
- No fabricated examples, company names, research papers, or statistics, from the agents or the Judge.

---

## Step 0 — Parse & Frame the Issue

Before anything, identify the issue to debate. Sources in priority order:

1. **Explicit statement** — The user states it directly.
2. **Conversation context** — The user references something discussed earlier ("debate this", "stress-test that idea"). Scan history, extract the core question.
3. **Attached file** — The user provides a document. Summarize the core decision or question it contains.
4. **No clear issue** — Ask: *"What specific issue or decision should the panel debate?"* Don't guess.

Once identified, restate it as a single clear sentence:

> **Issue on the table:** [One-sentence framing]

### Narrowing & Validation

Before proceeding, sanity-check the issue:

- **Too broad** (e.g., "Is AI good or bad?") → Narrow it. Propose a specific framing and confirm: *"This is very broad. I'd suggest: [specific question]. Want to adjust?"*
- **Settled fact** (e.g., "Is the earth round?") → Don't debate established science. Offer to help with a related genuine question instead.
- **Deeply personal** (e.g., "Should I leave my job?") → Adapt to advisory mode. Agents become advisory perspectives (pragmatist, risk analyst, etc.). The Judge softens its verdict into a recommendation, not a ruling. Remind the user that personal decisions are ultimately theirs. Archetypes are optional in advisory mode — assign only if the advisory persona naturally aligns.
- **Binary framing** — Always use at least 3 agents. The third challenges the binary itself or introduces a dimension neither side considers.
- **Simple comparison** (e.g., "pros and cons of Python vs Rust") → Offer a choice: *"This could be a quick comparison or a full debate. Quick analysis (2 rounds) or full debate (3 rounds)?"* Default to quick for straightforward tradeoff questions.

### Debate Depth

- **Full debate (3 rounds):** Opening → Cross-Examination → Rebuttal → Judgment. Use for complex, contested, high-stakes decisions.
- **Quick analysis (2 rounds):** Opening → Cross-Examination → Judgment (skip rebuttal). Use for simpler tradeoff questions, time-constrained users, or when the user says "quick take" or "brief analysis."

If the user has been clear and unambiguous, proceed directly into agent assembly without waiting for issue confirmation. Always present the agent panel before launching rounds — that is the user's last chance to adjust.

---

## Step 1 — Agent Assembly

Select agents tailored to the specific issue — no generic "Optimist/Pessimist" panels. Honor user requests for specific counts, but never fewer than 2 or more than 6.

### How Many Agents

- **Default: 3 agents.** Covers most issues well with manageable token cost.
- **Use 4 agents** when the issue has 3+ genuinely distinct stakeholder groups (e.g., engineering + business + legal + users).
- **Use 5 agents** only if the user explicitly requests it, OR the issue spans 4+ orthogonal dimensions that can't be collapsed.
- **Quick analysis mode: always 3 agents** (2 rounds already reduces depth — don't compound with more agents).

Why this matters: With 5 agents, Round 2 input tokens scale quadratically (each agent reads all 4 others' outputs). Defaulting to 3 keeps debates fast and focused.

### Selection Principles

- Agents must **genuinely disagree**, not just emphasize different aspects of the same conclusion.
- Include at least one agent who **challenges the premise** or conventional wisdom.
- No straw-men — every agent must be set up to make a strong case.
- Technical issues need at least one non-technical lens (user impact, ethics, business reality).
- Philosophical/political issues need at least one empirically grounded agent.
- Consider adding a "wildcard" agent whose perspective the user wouldn't expect.

### Agent Profile Schema

Before defining agent profiles, read `<skill-dir>/references/archetypes.md` once. Use it as a lookup during agent assembly.

For each agent, define these fields (used as the foundation for their system prompt):

| Field | Purpose |
|---|---|
| **Name & Role** | Short label + domain (e.g., "The Pragmatist — Senior Engineering Lead") |
| **Emoji** | Unique color circle for visual tracking: 🔵🔴🟢🟡🟣 |
| **Lens** | What they optimize for (e.g., "delivery speed, team morale, debt reduction") |
| **Core assumption** | The foundational belief driving their position |
| **Blind spot** | What they undervalue or ignore — stated honestly, this sets up better cross-examination |
| **Archetype** | *(Optional)* Which thinking archetype from `<skill-dir>/references/archetypes.md` enriches this agent. Use the tag (e.g., `EVIDENCE_ABSOLUTIST`). Set to `NONE` for purely ad-hoc agents. |

### Archetype Selection Logic

For each agent you are assembling:

1. **Check fit**: Does the agent's intended role align with one of the 10 archetypes' "Best deployed when" criteria? If yes, assign that archetype.
2. **Check clash partners**: After assigning archetypes, verify that at least two agents have archetypes listed as each other's clash partners. If all agents have compatible (non-clashing) archetypes, replace one with a clashing archetype or make it ad-hoc with a sharpened contrarian position.
3. **No forced fit**: If no archetype matches the agent's intended role, leave it as `NONE`. The agent is generated purely ad-hoc, exactly as before. Forcing a bad archetype match is worse than no archetype.
4. **No duplicate archetypes**: Never assign the same archetype to two agents in the same debate. Same archetype = same thinking pattern = guaranteed convergence.

### Archetype Enrichment

When an agent has an assigned archetype:
- **Core assumption**: Start from the archetype's core belief, then specialize it to the specific issue being debated.
- **Blind spot**: Start from the archetype's blind spot, then contextualize it to the issue.
- **Thinking pattern and argumentation style** from the archetype are distilled into 2-3 sentences each and injected into the Base Persona Block (see Step 2).

**Specialization constraint**: The specialized core assumption and blind spot must be directly derivable from the archetype's stated beliefs applied to the issue at hand. Do not add domain-specific claims not present in the original archetype. Good specialization applies the thinking pattern to the issue; bad specialization invents new claims.

**Specialization example** — Issue: "Should we adopt microservices?" with `SYSTEMS_PARANOID`:
- **Good:** "Every microservices boundary is a trust boundary. Assume inter-service communication is already partially compromised — each network hop is an attack surface nobody has audited yet." *(Applies the thinking pattern to the specific issue while preserving the cognitive DNA.)*
- **Bad:** "Microservices are insecure." *(Jumped to a conclusion — lost the thinking pattern entirely.)*
- **Bad:** "Assume compromise." *(Just copied the generic core belief — no issue-specific depth.)*

When an agent has `NONE`, construct all profile fields from scratch as before. No archetype DNA is injected.

Present the assembled panel to the user before launching the debate rounds, including archetype tags where assigned. This gives them a chance to swap an agent or adjust.

Example panel display:

| Agent | Archetype | Lens | Core Assumption |
|-------|-----------|------|-----------------|
| 🔵[A] The Pragmatist — Senior Eng Lead | `PROCESS_ENGINEER` | Delivery speed, bottleneck removal | Every delay has a measurable cause that can be fixed |
| 🔴[B] The Guardian — Security Architect | `SYSTEMS_PARANOID` | Threat surface reduction | Assume the system is already partially compromised |
| 🟢[C] The Advocate — Product Designer | `NONE` (ad-hoc) | User satisfaction, adoption | Users will always find the path of least resistance |

---

## Step 2 — Build & Dispatch: The Parallel Agent Engine

In Claude Code, use `Agent` with `subagent_type="multi-agent-debate:debate-agent"`;
the registered role already contains its static rules. In Codex, the parent
reads `<plugin-root>/agents/debate-agent.md` and includes its body inline in a
fresh subagent prompt, followed by the template below. Disable inherited chat
history when the API supports it. Explicitly require one text reply and no tools;
these are task restrictions, not a Codex tool sandbox. The parent supplies all
reference content so participants need no file access.

Queue participants when the host has fewer worker slots than the panel. Do not
feed any result to another participant until the entire round has finished.

Each agent runs in its own context — no shared state, no implicit cross-contamination. The orchestrator (you) collects all responses, then constructs the next round's context and dispatches again.

Subagents may run in the background and report back one at a time. A round is complete only when every agent in it has reported; do not build the next round, or judge, from a partial set.

**Round flow:**
1. Spawn all agents in parallel for Round 1 → collect opening positions
2. Check for divergence (see Divergence Check in Step 3)
3. Spawn all agents in parallel for Round 2, feeding each agent the OTHER agents' R1 outputs → collect cross-examinations
4. Spawn all agents in parallel for Round 3, feeding each agent their own R1 output + ONLY the critiques directed at them → collect rebuttals
5. Synthesize the Judge verdict directly (no subagent needed — you have full context)

### Canonical Prompt Template (per agent, per round)

This is the single source of truth for agent prompts. Combine the base persona block + the appropriate round-specific block. Claude Code loads the role automatically. In Codex prepend the bundled role
body, then include the dynamic content below.

**Base Persona Block** (same across all rounds for a given agent):

```
You are [Agent Name], [Role Description].

WHAT YOU OPTIMIZE FOR: [Lens]
YOUR CORE BELIEF: [Core assumption]
YOUR KNOWN BLIND SPOT (be aware of this, but don't let it paralyze you): [Blind spot]

[Include ONLY if archetype is assigned — omit entirely for ad-hoc (NONE) agents:]
YOUR THINKING PATTERN: [Distill the archetype's thinking pattern from archetypes.md into 2-3 sentences capturing its core cognitive moves]
YOUR ARGUMENTATION STYLE: [Distill the archetype's argumentation style into 2-3 sentences capturing its key rhetorical weapons and attack patterns]

THE ISSUE BEING DEBATED: [Issue — full statement in R1, 1-2 sentence summary in R2/R3]
```

**Round 1 — Opening Position** (append to base block):
```
ROUND 1 — OPENING POSITION
Produce exactly three sections:
1. **Problem as I see it:** Frame the core problem from YOUR perspective. Other agents will frame it differently — that's the point.
2. **My thesis:** State your position as a clear, falsifiable claim.
3. **Strongest argument:** Your single most compelling piece of evidence or reasoning. One powerful argument beats three weak ones.
```

**Round 2 — Cross-Examination** (append to base block):
```
ROUND 2 — CROSS-EXAMINATION
You will receive the opening positions of all other agents. For EACH other agent, produce a clearly labeled section:

## Critique of [emoji][letter] [Agent Name]
1. **Weakest link:** Identify the most vulnerable claim or assumption in their argument.
2. **Edge case:** Under what realistic conditions does their recommendation fail? Your edge cases must be logically grounded — don't invent implausible failure scenarios.
3. **Hidden cost:** What second-order effect are they ignoring?

RULES:
- Use the exact heading format above — it's needed for routing critiques in the next round.
- Quote or reference their specific claims. No straw-manning.
- "I generally agree but..." is BANNED. Find real disagreement or sharpen existing disagreement.
- Each critique must be actionable: force them to concede or defend with new reasoning.
```

**Round 3 — Rebuttal** (append to base block):
```
ROUND 3 — REBUTTAL
You will receive your own Round 1 position and the critiques other agents directed at you. You must:
1. **Concede:** Acknowledge points that genuinely changed your thinking. Explain what shifted. If no critique lands, explain specifically why each one fails — honest non-concession is better than a token concession on a trivial point.
2. **Defend:** For positions you still hold, provide NEW reasoning or evidence not used in Round 1.
3. **Updated thesis:** Restate your position. It may have shifted, narrowed, or been refined. If unchanged, explain specifically why the critiques didn't land.

Intellectual honesty is paramount.
```

### Token Efficiency

**When agent count > 3**: Summarize each agent's R1 output to ~100 words (preserving thesis and key argument) before feeding to other agents in Round 2. Preserve full outputs for the Judge's synthesis.

### Context Routing

| Round | What agents receive | What they produce |
|---|---|---|
| **Round 1: Opening** | Base persona + R1 block + full issue | Problem framing, thesis, strongest argument |
| **Round 2: Cross-Exam** | Base persona + R2 block + summarized issue + all OTHER agents' R1 outputs | Per-opponent critiques with structured headings |
| **Round 3: Rebuttal** | Base persona + R3 block + summarized issue + agent's own R1 output + ONLY critiques directed at them | Concessions, new defenses, updated thesis |
| **Judgment** | All rounds from all agents | Orchestrator (current session) does this directly — no subagent |

**Round 2 prompt construction** — feed other agents' outputs:
```
Here are the opening positions from the other agents. Cross-examine each one.

---
🔴[B] The Systems Architect:
[Full Round 1 output from Agent B]

---
🟢[C] The Product Manager:
[Full Round 1 output from Agent C]
```

**Round 3 prompt construction** — include own R1 + extracted critiques:
```
Here is your Round 1 position for reference, followed by the critiques directed at you. Respond to each critique.

YOUR ROUND 1 POSITION:
[This agent's own R1 output]

---
CRITIQUES DIRECTED AT YOU:

🔴[B] The Systems Architect's critique of you:
[Extracted "## Critique of 🔵[A]..." section from Agent B's R2 output]

---
🟢[C] The Product Manager's critique of you:
[Extracted "## Critique of 🔵[A]..." section from Agent C's R2 output]
```

If heading parsing fails (agent didn't follow the format), fall back to sending the full cross-exam output with a note: "The following contains critiques of all agents. Focus on and respond to the points directed at you."

---

## Step 3 — Round Execution

Each round is one parallel dispatch built from the Canonical Prompt Template and the Context Routing table in Step 2. Only what the templates do not cover is described here.

### Divergence Check (after Round 1)

After collecting all R1 outputs, compare agent theses before proceeding:

1. **Check**: Do 2+ agents reach the same directional conclusion?
2. **If divergent** (all agents take genuinely different positions): Proceed to Round 2.
3. **If convergent** (2+ agents agree directionally):
   - Flag to user: *"Agents [X] and [Y] are converging — restructuring to surface genuine disagreement."*
   - Pick the most convergent agent. Either:
     (a) Sharpen their blind spot to force a different position, OR
     (b) Replace them with a premise-challenger who questions whether the decision is needed at all
   - Re-run Round 1 for the restructured agent ONLY (other agents keep their R1 outputs)
   - Maximum 1 restructure attempt. If divergence still fails after retry, proceed with a note in the Judge's instructions: *"Limited divergence achieved despite restructuring — verdict confidence is reduced."*

### Round 2 and Round 3

Round 2 is the most important phase: Round 3 can only answer critiques that quote a specific claim. If an agent's output ignores the per-opponent heading format, route its whole cross-examination as described under Context Routing rather than re-running it.

In Round 3 each agent gets its own Round 1 position and only the critiques aimed at it, never the full cross-examination: the critiques of other agents are tokens its rebuttal cannot use.

### Quick Analysis Mode (2 rounds)

When using quick analysis mode (decided in Step 0), skip Round 3 entirely:

1. Run Round 1 (Opening Positions) as normal
2. Run Divergence Check as normal
3. Run Round 2 (Cross-Examination) as normal
4. Skip directly to the Judge verdict with adjusted instructions (see Step 4)

---

## Display Protocol

Present each round's results to the user as they complete. This keeps the user engaged and lets them see the argument unfold.

**Between rounds**, display a brief progress note:
- After Round 1: *"Round 1 complete — [N] opening positions collected. Checking divergence..."*
- After divergence check: *"Divergence confirmed. Proceeding to cross-examination..."*
- After Round 2: *"Cross-examination complete. Routing critiques to agents for rebuttals..."*
- After Round 3: *"All rounds complete. Synthesizing the Judge's verdict..."*

**Round output format** — present each agent's output under their identifier:

```
### Round [N]: [Round Name]

**🔵[A] The Pragmatist — Senior Engineering Lead**
[Agent A's output]

**🔴[B] The Systems Architect — Platform Engineer**
[Agent B's output]

**🟢[C] The Product Manager — User Advocate**
[Agent C's output]
```

Maintain consistent agent ordering across all rounds so the user can track each agent's evolution. Each agent should speak distinctly — an economist uses different language than an ethicist, a startup founder sounds different from a policy wonk. The Judge is measured, precise, and authoritative.

---

## Step 4 — Final Judgment

Drop all agent roles. You become an impartial **Judge** whose only loyalty is to the strongest reasoning. Do NOT use a subagent for this — the Judge benefits from having orchestrated the entire debate.

**In quick analysis mode (2 rounds)**, preface the synthesis with: *"Note: No rebuttal round was conducted. This verdict is based on opening positions and cross-examination only."* Note where rebuttals might have changed the outcome.

Produce three sections:

### ⚖️ Synthesis
- **Points of convergence** — Where agents agreed, even from different reasoning. These are high-confidence conclusions.
- **Genuine tensions** — Unresolved disagreements that reflect real tradeoffs, not just different priors. Name each tradeoff explicitly (e.g., "Speed vs. safety — optimizing for one degrades the other").

### ⚖️ Verdict
- **Recommendation** — Clear, actionable. Not "it depends." Commit to a position while acknowledging conditions.
- **Confidence level** — High / Moderate / Low, with one-sentence justification. Calibrate using these criteria:
  - **High:** Agents converged from different reasoning paths + strong real-world evidence supports the conclusion.
  - **Moderate:** Genuine unresolved tensions remain + evidence is mixed or context-dependent.
  - **Low:** Insufficient information to decide, all positions are equally defensible, or the verdict hinges on unknowable future conditions.
- **Key conditions** — What must be true for this verdict to hold? If these conditions change, the verdict may flip.

### ⚖️ Dissent Log
- **Minority positions worth preserving** — Which losing arguments contained insights the majority missed?
- **Flip conditions** — Under what specific, realistic scenarios would the verdict reverse? Be concrete.
- **Open questions** — What couldn't be settled and would need external data or experimentation to resolve?

**Judge citation rule**: Quote VERBATIM text from agent outputs — use exact words, not paraphrases. Every verdict point must cite at least one specific agent by emoji+letter. Do not synthesize claims agents didn't make.

The Judge's synthesis can be 300-500 words. Use consistent visual identifiers — 🔵[A] 🔴[B] 🟢[C] 🟡[D] 🟣[E] — so agents are identifiable at a glance.

---

## Step 5 — Post-Debate Options

After delivering the verdict, offer the user these options:

1. **"Go deeper"** — Spawn agents again on unresolved tensions from the Dissent Log
2. **"Challenge the verdict"** — Introduce a new constraint; all agents respond in a mini-round
3. **"Add an agent"** — Define a new perspective; existing agents cross-examine the newcomer
4. **"Export"** — Write a clean debate transcript to `debate-[topic-slug].md`

When the user selects an option, read `<skill-dir>/references/post-debate.md` for detailed instructions.

---

## Reference Files

- `<skill-dir>/references/archetypes.md` — Thinking archetypes for enriching agent profiles. **Read once at the start of Step 1** (Agent Assembly). Provides cognitive DNA — thinking patterns, blind spots, argumentation styles, and clash partners — for 10 distilled archetypes.
- `<skill-dir>/references/edge-cases.md` — Error handling, special issue types (political, personal, trivial), mid-debate interventions, fallback inline simulation, and performance notes. **Read only when an agent fails or an edge case arises.**
- `<skill-dir>/references/post-debate.md` — Detailed instructions for post-debate options (go deeper, challenge, add agent, export). **Read when the user selects a post-debate option.**
- `<skill-dir>/references/export-template.md` — Markdown template for debate transcript export. **Read when exporting.**
