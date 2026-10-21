# Edge Cases & Error Handling Reference

Consult this file when an agent fails, an edge case arises, or you need guidance on special situations. The standard workflow and templates are in SKILL.md — this file covers only the exceptions.

---

## Error Handling

### Agent Failure

If one subagent fails, the debate continues without them:
- Note the failure in the round summary: "🔴[B] — Failed to respond in this round."
- Remaining agents proceed normally.
- The failed agent is excluded from subsequent rounds.
- If only 1 agent remains, switch to fallback inline mode.

### All Agents Fail

If all agents in a round fail, switch to **inline simulation mode** (see Fallback section below):
- Notify the user that parallel dispatch failed.
- Generate the round inline, playing all roles sequentially.
- Continue the debate structure as closely as possible.

### Very Long Agent Responses

The prompt instructs 200-350 words. If an agent produces more than ~500 words, summarize the excess and note: "[Agent response was condensed — exceeded word limit]". This keeps the debate scannable.

### Critique Heading Parse Failure

If an agent's Round 2 output doesn't follow the `## Critique of [emoji][letter] [Agent Name]` heading format, fall back to sending the full cross-exam output with a note: "The following contains critiques of all agents. Focus on and respond to the points directed at you."

---

## Special Issue Types

### Sensitive or Political Issues

For politically charged topics:
- Ensure agents represent genuinely held positions across the real spectrum of views
- The Judge must be scrupulously evenhanded
- Avoid strawmanning any political position
- Note in the verdict when the question involves value judgments where reasonable people disagree

### Personal Decisions

For "should I..." questions about personal life choices:
- Agents become advisory perspectives (e.g., "The Risk-Aware Friend", "The Growth-Oriented Mentor")
- The Judge delivers a recommendation, not a ruling
- End with: "This is ultimately your call. The debate surfaces tradeoffs — it doesn't make the choice for you."

### Only Two Viable Sides

Use 3 agents minimum. The third agent challenges the binary framing or introduces an orthogonal dimension. Example: in a "build vs. buy" debate, the third agent might argue "neither — partner" or challenge whether the underlying need is real.

### Empty or Trivial Issues

If the issue is trivially answerable ("What's 2+2?") or empty, don't run a debate. Respond directly and offer to help with a substantive question instead.

---

## Mid-Debate Interventions

### User Requests Additional Rounds

The framework is extensible. After Round 3, offer additional cross-examination focused on unresolved tensions from the Dissent Log. Use the same dispatch pattern with new context.

### User Wants to Inject a Question Mid-Debate

Treat it as a mini-round: send the user's question to all agents in parallel (100-150 words each), collect responses, display inline, then continue with the scheduled round.

### Issue Changes Mid-Debate

If the user reframes the issue after agents are assembled, re-run from Step 1 (agent assembly). Don't try to patch — agent personas may no longer be appropriate.

### User Requests Specific Agents or Perspectives

Honor the request. If they say "include a labor union perspective", build an agent for it. If they name a specific number of agents, use that number (within 2-6 range).

---

## Fallback: Inline Simulation Mode

If the host has no subagent tool, cannot provide independent contexts, or all subagent calls fail, fall back to **inline simulation**:

- Play all agent roles sequentially in a single response
- Maintain distinct voices, cross-examination structure, and Judge verdict
- Label each section clearly with agent identifiers
- Explicitly tell the user: *"Note: This is a simulated debate (single-model, sequential). For independent parallel agents, use a host with independent subagent support."*

Inline simulation is less rigorous because agents share implicit context, but still provides structured multi-perspective analysis. Use it as a last resort, not the default. Archetype enrichment still applies in inline mode — use the same distilled thinking pattern and argumentation style fields for each simulated agent persona.

---

## Performance Notes

- **Parallelism:** Dispatch within the host’s available capacity; queue excess participants. Three available worker slots allow three simultaneous participants per round. Total for a full 3-round debate: 9 subagent calls + 0 for judgment.
- **Latency:** Each round is limited by its slowest agent. Rounds do not overlap, so a full debate takes three agent round-trips plus the judgment.
- **Token budget:** With 200-350 word responses, each agent produces ~300-500 output tokens. Total debate: ~3,000-5,000 output tokens across all agent calls. The Judge synthesis adds ~400-700 tokens.
- **Scaling:** With 5 agents, input tokens for Round 2 scale quadratically (each agent reads all others' outputs). When agent count > 3, consider summarizing each R1 output to ~100 words before feeding to other agents in Round 2. Full outputs are preserved for the Judge.
