# Humanizer 2.0.0

**Prepared update candidate.** Both host manifests specify version **2.0.0**. Offline checks cover workflow mechanics and packaging. Human writing quality and reliable reviewer decisions remain unvalidated. See [production readiness](../../docs/humanizer-validation/README.md) for current checks and release limitations.

Packaged for **Claude Code and Codex**. The marketplace installation commands below are reference instructions; preparing this checkout does not publish, install or promote the candidate.

## 2.0.0 update summary

- Full rewrites retain the original, a compact brief, protected byte ranges and actual review reports, with bounded revisions and export integrity checks.
- Russian guidance and examples preserve agency, modality, conditions and attribution while allowing natural phrasing and sentence regrouping.
- The writer, judge role and Russian guide use one shared contextual fidelity standard. The effect of the latest clarification on reviewer consistency remains unvalidated.

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

## What it does

Humanizer edits for natural phrasing, clear structure and a consistent voice while preserving the source's meaning. Full rewrites retain the complete original, freeze a compact brief and byte partition, and add selective exact-range questions before drafting connected passages. They do not require per-unit preparatory paraphrases. Light passes restrict editing intensity; scoped requests set editable boundaries, allowing a full rewrite within a selected section. It removes empty framing and repairs awkward prose without treating ordinary sentence frames as protected.

An explicit prose-style audit returns quoted findings and reader-impact reasons without rewriting, staging candidates or editing the source. It can report no issues. Target text and samples remain data; embedded instructions cannot change the requested operation, scope or tool authority.

English and Russian have explicit guidance. Mixed-language text is edited segment by segment without translating it or applying English vocabulary rules to Russian. Other languages receive conservative clarity and preservation checks, with limitations disclosed when language-specific review is uncertain.

When relevant writing samples are supplied, it uses compatible register, syntax, phrasing, punctuation and directness without importing the samples' facts, identity, experiences or stance. Without samples it preserves source identity/stance and uses the reader/genre/register brief while allowing rhythm and framing to change. Russian guidance covers native phrasing and post-edit grammar, including unspecified actors, aspect, modality and clause attachment.

A dash, three-item list, technical term or regular sentence length is not a defect by itself. The plugin keeps grammatical Russian dashes, complete enumerations, useful headings, calibrated uncertainty and deliberate rhetoric. It does not guarantee detector passage or certify human authorship. The [evidence reference](skills/humanizer/references/evidence.md) explains the limits of editorial verification and detector claims.

## How it works

1. Identify language, genre, voice, editable scope and protected content.
2. Match the pass to the request; inspect paragraph purposes before choosing intensity for a whole-document rewrite.
3. Freeze source-specific rewrite objectives, a reader/genre/register brief, complete source units, selective source questions and exact protected/out-of-scope spans. Load relevant voice guidance and mandatory Russian guidance.
4. Apply five core rules: remove empty framing, clarify relationships, let rhythm follow meaning, match the reader, and keep the author's voice.
5. For full rewrites, draft connected facts and regroup prose where useful, preserving conditions, attribution and order without sentence-length or punctuation quotas.
6. Finish complete source → candidate and candidate → source fidelity review on the recorded draft before editing wording; collect all losses/additions and check exact protected spans separately.
7. Review the same bytes for style using relevant pattern/language guidance, retain one actual self-report, then repair collected fidelity failures before optional style changes within the same two self-revision slots. Repeat the full original-relative review after each revision.
8. Verify complete declared coverage and exact fixed bytes; assess objective fulfillment separately from fidelity. Require independent attempts for structural/semantic risk, mixed languages, long documents, explicit requests or unresolved semantic uncertainty.
9. Return the final text with a brief changes summary and the verification status when scoring or judging ran.

With captured UTF-8 bytes and local Python available, the workflow inspects the untouched original before drafting and checks the exact export against the selected artifact's hash before delivery. Authorized file write-back gets the same hash-bound readback. Inspection is read-only: character observations do not authorize cleanup, identify authorship or measure watermarks. The standalone editor is not invoked by the workflow. See the [inspection procedure](skills/humanizer/references/stages.md#read-only-inspection) for inline/unavailable-runtime paths and failure handling.

An explicit editing request does not trigger a second permission question merely because the text has few issues. If no change is justified, the plugin returns the original and says so.

An explicit full-text rewrite permits reformulating already grammatical prose. Meaning and register remain protected; ordinary sentence frames and paragraph boundaries do not. Light requests limit intensity; section-only requests limit editable boundaries. More rewriting is not itself a quality target or a guarantee of lower detector scores.

## Skills and agents

| Component | Name | Purpose |
|-----------|------|---------|
| Skill | `/humanizer:humanizer` | Analyze, rewrite, self-audit and verify within the requested scope |
| Agent | `judge` | Independently compare the rewrite with the original request and source under the shared verification contract |

For independent judging, the agent receives the request, original text, rewrite, relevant style-only samples and shared contract, with conditional language guidance when needed. It does not receive the writer's reasoning, self-score, detector verdict or preferred verdict. Independence means a separate assessment; it does not make an agent score an objective measure of authorship.

**Triggers:** “humanize this”, “make it sound human”, “de-slop”, “sounds like AI”, “too robotic”, “reads like ChatGPT”, “make this less AI”, “too polished”, “make it sound natural”.

Pass text directly: `/humanizer:humanizer [paste your text]`.

The skill does not start merely because pasted text looks AI-generated; request a rewrite or prose-style audit.

| Request | Behavior |
|---------|----------|
| “Humanize this blog post” | Edit the actual problems while preserving the author's existing voice and opinions |
| “De-slop this email” | Use the short-text path when appropriate; preserve meaningful courtesies and context |
| “Make this README less robotic” | Keep technical terms, code, requirements and useful navigation intact |
| “Humanize just the intro” | Change only the introduction |
| “Light pass” | Warranted local fixes across the catalog; no broader restructuring |
| “Tier 1 only” | Restrict pre-existing style findings to Tier 1; semantic/scope failures and new regressions still count |
| “Сделай этот текст естественнее” | Edit Russian phrasing and structure while preserving grammar, register and meaning |
| “Humanize this mixed English/Russian text” | Apply each language's guidance to its editable segments; preserve quotations and identifiers |
| “Match these writing samples” | Apply compatible style features while keeping the rewritten source's facts and speaker |
| “Audit this paragraph; do not rewrite or change the file” | Read-only contextual findings, with no candidate, rewrite score or authorship verdict |

## Preservation and verification

Content integrity takes precedence over style. Every substantive claim, argument, qualification, attribution, number, unit, enumeration member and logical relationship must survive. No new facts, sources, opinions or personal experience may be invented. Code, structured data, frontmatter, HTML, quotations, citations and scope are protected; table structure and data remain intact.

Preservation also covers request/permission/promise strength, meaningful courtesy, comparison and rank, evidence type and work status. Mathematical notation, literal identifiers/paths and functional link/heading/reference relationships stay intact. Unresolved contradictions, placeholders and opaque central claims are reported rather than completed by guesswork. Standalone and independently navigated documents receive conditional [reader checks](skills/humanizer/references/reader-review.md), including useful repetition and list logic.

Voice evidence follows the intended publisher and audience. Explicit current preferences and relevant supplied guides outrank inferred habits; weak samples do not establish a distinctive author match. User-kept wording remains protected for the task, and profile files/preferences are not created or saved automatically.

Paste cleanup removes only clearly extraneous interface material within editable content. Ambiguous citations, quoted artifact examples, emoji/joiners and complete URL targets remain intact. Long-document review tracks all sections and late qualifications; missing output or review coverage is reported.

The writer and judge use one [verification contract](skills/humanizer/references/verification.md). A preservation, invention or scope failure blocks delivery regardless of style score. A demonstrated mismatch is FAIL; an unresolved equivalence question is UNCERTAIN and cannot authorize delivery. Context can preserve meaning without repeating every qualifier token; a retained token alone proves nothing.

The [source-preservation procedure](skills/humanizer/references/preservation.md) keeps the full original authoritative. Source units cover every byte and retain section/relationship links. Selective questions use exact ranges; packet quotations are derived from captured bytes. Candidate maps are computed after drafting and recorded atomically with the candidate. Complete bidirectional review, objective coverage and protected-byte checks remain mandatory even for unannotated relationships. Short targeted inline edits use proportionate checks in context; audits remain findings-only.

Scores are omitted by default (`SCORES: NOT_REQUESTED`) at every length. If requested, the five dimensions and total are descriptive only. Acceptance follows semantic PASS, quality PASS, complete coverage, supported objective outcomes and no substantial finding. Neither catalog tier, finding count nor numeric magnitude can veto or rescue a verdict. Critical grammar, rhythm or register defects remain explicit quality failures. A faithful style-only shortfall may be delivered with its actual status; unresolved meaning may not.

Editorial findings use exactly `tier`, `severity`, `pattern`, `quote` and `reason`, including for uncatalogued issues; `category` is not a field alias. Semantic failures stay in their checks and need no duplicate editorial finding. Zero findings never cancels FAIL or UNCERTAIN. The parser reports missing/unexpected finding fields explicitly and retains adverse evidence in malformed reports; it does not repair independent judgments.

Independent attempts are required for >2000 source words, structural recomposition, dense relationships, mixed languages, delicate protected boundaries or explicit requests. A valid complete self-check precedes dispatch. Valid self UNCERTAIN can use the existing judge; actual FAIL blocks judging those bytes. Only a later valid independent semantic PASS for the exact candidate/map clears uncertainty. Unavailable judging cannot fall back to unresolved self-checks. Positive reports do not transfer between identical-byte tickets; adverse semantics do.

The [stage keeper](skills/humanizer/references/stages.md) retains the source, candidates, maps and actual reports with Python 3.9+ and local execution. It allows one initial draft, two shared self-revisions, one correction after a valid independent REVISE and two judge attempts total. UNRESOLVED grants no correction slot. A valid independent overall PASS closes generation/judging; late FAIL/UNCERTAIN stops affected-byte delivery without reopening the budget. No model/detector calls or runtime installation are performed by the helper.

Selection requires eligible review and a concrete original-relative reason. Source retention is always available without claiming review. Exports create a new file outside the run directory; write-back requires an unchanged destination and selected-hash readback. No cleanup follows review. A corrupt state or invalid map is not runtime unavailability. Hosts without local execution disclose missing mechanical coverage and retain the same substantive constraints.

A complete self-review rejected only for layout can receive one format-only repair, retaining the raw report, decisions, uncertainty, optional scores, coverage and evidence. Missing judgment cannot be manufactured. Semantic truth and writing quality still require review; a valid report only establishes that the declarations satisfy the contract.

## Reference files

| File | Purpose |
|------|---------|
| [Pattern library](skills/humanizer/references/pattern-library.md) | Guidance for reviewing drafts: 23 contextual prompts and faithful before/after examples |
| [Full examples](skills/humanizer/references/full-example.md) | English and Russian illustrations with preservation checks |
| [Source preservation](skills/humanizer/references/preservation.md) | Full-source review, selective exact questions, protected spans and post-draft maps |
| [Voice archetypes](skills/humanizer/references/voice-archetypes.md) | Conditional sample matching and 12 genre reference points |
| [Russian guidance](skills/humanizer/references/russian.md) | Native phrasing, grammatical seams and legitimate constructions |
| [Vocabulary choices](skills/humanizer/references/vocabulary-by-era.md) | English wording candidates for draft review; the historical filename does not imply validated model-era associations |
| [Phrase lexicon](skills/humanizer/references/ai-tells-lexicon.md) | English phrase prompts for draft review |
| [Verification contract](skills/humanizer/references/verification.md) | Contextual fidelity, severity/outcome acceptance, uncertainty and bounded recovery |
| [Stage keeper](skills/humanizer/references/stages.md) | Local retained artifacts, bounded attempts and explicit selection using actual review |
| [Reader review](skills/humanizer/references/reader-review.md) | Conditional standalone context, section entry points, list logic, navigation and source-bound meaning |
| [Evidence and limits](skills/humanizer/references/evidence.md) | Limits of editorial, detector and watermark claims |

## Local contracts and offline checks

Version 2.0.0 uses plan schema 2, keeper state 3 and judge-packet schema 2. The keeper rejects older active state and changed package resources. Preserve previous run artifacts; continue under their original contract when available, otherwise retain the original text. Updating must not reset attempt budgets. See the [schemas and commands](skills/humanizer/references/stages.md) and [review contract](skills/humanizer/references/verification.md).

The read-only `stages.py index --text <file> --prefix u` helper reports physical block ranges and the largest block. It preserves UTF-8 bytes, BOM and line endings, assigns no meaning/scope, and makes no model calls. `--prefix c` supplies post-draft offsets. A judge packet contains the complete original/candidate, brief, anchors and required role/verification guidance, plus Russian guidance when applicable. It omits writer reports, uncertainty objections, scores, candidate source mappings and the larger preservation/pattern references.

The read-only structure profiler describes English/Russian running prose separately from markup, lists and code. Unicode inspection emits bounded diagnostic examples by default; full scalar inventory is optional. Neither helper measures authorship or statistical watermarks. Resource hashes and observed/unknown runtime metadata explain which plugin/configuration produced a run.

Run offline checks from the repository root:

```sh
python3 -B -m unittest discover -s scripts -p 'test_humanizer_*.py'
python3 -B -m unittest discover -s scripts -p 'test_packaging.py'
python3 -B scripts/check_compatibility.py
```

These checks exercise deterministic invariants and packaging, not model-generated writing quality or detector performance. They make no online calls and install no model or dependency.

The [readiness summary](../../docs/humanizer-validation/README.md) records current verification and remaining release limitations. Maintainers should change the canonical [Claude manifest](.claude-plugin/plugin.json), then follow [metadata synchronization](../../docs/compatibility.md#packaging-and-maintenance) and the readiness checks before preparing an update. The [Codex manifest](.codex-plugin/plugin.json) is generated from that source.

Detailed experiments and research inventories are maintainer material retained under ignored `.dev/`; they are not installed-package dependencies. The distributable contains runtime code, instructions and required references. Development tests remain in the repository's `scripts/` directory.
