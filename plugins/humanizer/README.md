# Humanizer plugin

Works in **Claude Code and Codex**. Install the complete plugin so its skills,
references, scripts and agent instructions stay together.

## Installation and invocation

**Claude Code** (inside the Claude Code prompt):

```text
/plugin marketplace add ms-ilya/imaslou-agent-kit
/plugin install humanizer@imaslou-agent-kit
```

**Codex** (in a terminal with a plugin-capable Codex CLI):

```sh
codex plugin marketplace add ms-ilya/imaslou-agent-kit
codex plugin add humanizer@imaslou-agent-kit
```

Start a new session after installation. Invoke `/humanizer:humanizer` in
Claude Code or `$humanizer` in Codex. The slash examples below use Claude
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

AI-generated text has tells. Detectors catch them; careful readers do too. Words like "delve" and "leverage", uniform sentence lengths, neat three-item lists, participial tails on every sentence -- these patterns are statistically abnormal in human writing. Running text through "make it more natural" does not fix the underlying structure.

This is not limited to English. AI text in any language shares the same statistical signature: uniform rhythm, predictable structure, safe vocabulary, and absent voice.

## The solution

A universal AI-to-human text converter for any language and content type. The agent analyzes the text first (language, content type, voice signals, AI density), then applies universal principles, fixes known patterns, adjusts statistical texture, and verifies the output.

The goal is not to avoid AI tells. It is to write like a specific human would.

## How it works

A 9-step pipeline with Content Intelligence, structured self-audit, and verification:

```
1. Content Intelligence    →  Language, content type, mixed content, voice signals, AI density
2. AI Score Gate           →  Low density? Offer targeted fixes. Full treatment? Continue.
3. Load References         →  Conditional: skip for short/non-English text, load for full treatment
4. Apply 5 Core Rules     →  Delete filler, break formula, vary rhythm, trust reader, kill quotables
5. Fix Tier 1 + 2         →  8 always-fix + 15 situational patterns (23 total)
6. Universal Principles   →  Information density, sentence variance, cohesion, punctuation
7. Self-Audit (two-pass)  →  Adversarial self-question + 14-point checklist (internal)
8. Verification           →  Self-check + independent judge agent for long text (≥35/50)
9. Present Result         →  Final rewrite + changes summary + verification line
```

## Skills and agents

| Component | Name | Purpose |
|-----------|------|---------|
| Skill | `/humanizer:humanizer` | Core rewriting pipeline. Content Intelligence, pattern detection, rewrite, self-audit, verification |
| Agent | `judge` | Independent quality evaluator. Scores rewritten text without seeing the editing process |

The skill orchestrates the full pipeline. For long text (over 2000 words), it spawns the judge agent for objective verification. The judge receives only the original and rewritten text, with no editing rationale and no pattern analysis. It evaluates like a skeptical reader would.

**Triggers:** "humanize this", "make it sound human", "de-slop", "sounds like AI", "too robotic", "reads like ChatGPT", "make this less AI", "too polished", "make it sound natural"

Pass text directly: `/humanizer:humanizer [paste your text]`

It does not start on its own because pasted text looks AI-generated; ask for the rewrite.

### Examples

| You say... | What happens |
|-----------|--------------|
| "Humanize this blog post" | Full rewrite with blog/essay voice archetype |
| "This sounds like AI wrote it" | Content Intelligence, pattern detection, statistical texture fix |
| "De-slop this email" | Quick rewrite (short text path) |
| "Make this README less robotic" | Technical documentation voice parameters |
| "Clean up this AI-generated marketing copy" | Marketing voice with high fragment tolerance |
| "Humanize just the intro" | Scoped rewrite, only touches the intro section |
| "Tier 1 only" | 5 Core Rules and Tier 1 patterns only |
| "Humanize this French article" | Universal principles plus agent delegation for language-specific patterns |

## Design principles

- **Universal-first** - Principles work for any language; English patterns are examples
- **Content intelligence** - Analyze before rewriting; AI Score Gate knows when not to act
- **Content integrity** - Never add facts, claims, or opinions not in the original
- **Anti-hallucination** - Never invent statistics, fabricate citations, or upgrade vague to specific
- **Priority-tiered** - Fix Tier 1 first (worst tells), then Tier 2 (situational)
- **Statistical, not cosmetic** - Target underlying statistical signatures rather than surface-level word swaps
- **Adaptive voice** - Mechanical voice detection with 12 archetypes; personality gated by decision rule
- **Era-aware** - AI vocabulary tagged by model generation (2023, 2024, 2025+)
- **Verifiable** - Quantitative quality scoring (5 dimensions, >=35/50 gate) with independent judge agent for long text

## Verification

The skill self-scores across 5 dimensions (directness, rhythm, trust, authenticity, preservation) with a gate at 35/50. For long text, the judge agent provides independent scoring on the same dimensions plus content preservation and anti-hallucination checks. When self-score and judge score disagree by more than 10 points, the lower score wins.

| Text length | Verification |
|-------------|-------------|
| <100 words | Optional (self-scoring if run) |
| 100-500 words | Self-scoring only |
| 500-2000 words | Self-scoring; judge on request or borderline scores (35-38/50) |
| >2000 words | Self-scoring + mandatory judge agent |

## Reference files

Word lists, pattern details, and examples are in `references/` for independent updates.

| File | Purpose |
|------|---------|
| `references/pattern-library.md` | 23-pattern detection guide with before/after examples |
| `references/full-example.md` | Complete before/after walkthrough |
| `references/voice-archetypes.md` | 12 content archetypes with voice parameters |
| `references/vocabulary-by-era.md` | AI vocabulary by model era (English + Claude) |
| `references/ai-tells-lexicon.md` | Word lists from 10 patterns, filler phrases |

## Sources

- [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) - primary pattern source
- [WikiProject AI Cleanup](https://en.wikipedia.org/wiki/Wikipedia:WikiProject_AI_Cleanup) - maintaining organization
- AI detection research (GPTZero, Originality.ai, DetectGPT) - statistical texture techniques
