# Local artifact retention

Use bundled `scripts/stages.py` with Python 3.9+ already available. It makes no model/network calls and installs nothing. It enforces supplied contracts, byte identities and budgets; semantic truth and scope identification remain the host's responsibility. Resolve `<plugin-root>` from the installed skill per [runtime conventions](../../../references/runtime.md).

Use one new temporary run directory for the entire rewrite. Keeper state version 3 freezes the schema-2 plan and installed plugin versions/resource hashes. It deliberately refuses version-1/2 active state or changed installed resources rather than silently mixing contracts. Do not reset or migrate an active run to gain attempts. Preserve old evidence and safely retain the original if continuing under its original contract is unavailable.

## Read-only inspection

Before drafting, inspect the untouched captured original. After export, inspect the exact destination against the **selected artifact's** expected hash, never a hash derived from that destination. `text_integrity.py inspect` preserves BOM, CRLF and combining forms; it emits category/script-name counts, interesting-control/spacing/combining examples (maximum 32), exact hash/scalar counts and Unicode database version. Controls take priority over combining/spacing examples so numerous accents cannot hide a later control. Counts are observations, not defects. `--full-inventory` emits every non-ASCII/control occurrence for optional diagnostics saved outside model context. Ordinary Russian letters no longer create per-character prompt records.

The separate `apply-edits` command is standalone, outside this workflow and outside its tool grant. Ambiguous Unicode stays unchanged or is flagged. No normalization, cleaner, watermark detection or extra candidate allowance follows inspection.

For full treatment, run read-only `structure.py` on the original and recorded candidate, and an optional relevant supplied sample. It describes running-prose sentence/paragraph lengths, single-sentence paragraphs and repeated openings/closings/local phrases with locations. Code, frontmatter, HTML, quotations, headings, lists and tables are counted separately. Markdown/language segmentation is heuristic; inspect ambiguous boundaries. English/Russian summaries require at least five sentences and three paragraphs; this is a reporting floor, not an editing target. For mixed/unknown languages, withhold distributions and use language-specific manual review. Do not split a document into independent rewrites just to obtain metrics.

```sh
python3 -B "<plugin-root>/scripts/structure.py" "<original-file>" --candidate "<candidate-file>" --language en
```

Optional `--sample` is style evidence only. Metrics authorize no automatic edits, quality score, human percentage or detector/watermark conclusion. Use a source-located reader problem to justify an objective, then assess the actual prose.

## Frozen plan and post-draft map

All ranges are zero-based half-open UTF-8 byte ranges `[start, end)` at scalar boundaries, not character indices. Unit arrays partition every byte in order without gaps/overlaps, including BOM, separators and final whitespace. IDs are unique within each array. Preserve exact bytes; do not normalize Unicode or line endings.

`stages.py index` is read-only and needs no run directory:

```sh
python3 -B "<plugin-root>/scripts/stages.py" index --text "<original-file>" --prefix u
python3 -B "<plugin-root>/scripts/stages.py" index --text "<candidate-file>" --prefix c
```

The JSON contains `sha256`, `offset_unit`, `units` (`id`, `start`, `end`) and `largest_block_bytes`. Blank-line runs attach to the preceding physical block; leading blank lines may form their own block. A long unbroken block stays whole. These are offset suggestions, not semantic segmentation, scope, protection or source/candidate matching. Review/refine units when useful, preserving complete coverage. Add source `section`/`links` before initialization; add candidate `source_units` only after drafting.

The plan has exactly these fields:

| Field | Shape and requirement |
|---|---|
| `schema_version` | `2` |
| `source_sha256` | SHA-256 of the captured original bytes |
| `request` | Actual request, including relevant supplied style evidence |
| `brief` | Fields listed below |
| `units` | Complete partition: `{ "id": "u1", "start": 0, "end": 42, "section": "intro", "links": [] }`; links identify related source units, including cross-section relationships. No per-unit `meaning` paraphrase. |
| `anchors` | Zero or more `{ "id": "a1", "spans": [{ "start": 0, "end": 20 }], "question": "What does this qualification govern?" }`; nonempty question and span list. Ranges inside one anchor are sorted/nonoverlapping; different anchors may overlap. Cross-unit/disjoint ranges are allowed. Authored quotations/answers are not fields. The packet derives exact text and intersecting source IDs from source bytes. |
| `fixed` | Sorted/nonoverlapping `{ "id": "f1", "start": 20, "end": 42, "kind": "protected" }`; kind is `protected`, `out-of-scope` or `verbatim`. Empty is valid only when nothing needs exact protection. |
| `runtime` | Nonempty strings `writer`, `judge`, `settings`, `watermark`; use `unknown` when unobserved. |

The brief has exactly `intensity` (`targeted`, `full`, `unchanged`), nonempty `reader`, `genre`, `register`, `purpose`, a nonempty `languages` list, `objectives`, `no_change_reason`, `risks`, and boolean `judge_requested`. An objective has `id`, nonempty `source_units`, `issue` (reader impact) and `action`. Supply objectives with an empty no-change reason, or no objectives with a justified no-change reason. `unchanged` intensity cannot promise edits; no-objective plans permit only original bytes. Risks are unique values from `structural-recomposition`, `dense-relationships`, `mixed-language`, `protected-boundaries`.

A candidate map has exactly `source_sha256`, `candidate_sha256`, `units` and `fixed`. Each unit has `id`, `start`, `end`, and nonempty `source_units`; together these associations account for every source ID and no unknown IDs. Splits, merges and reorderings are allowed. Fixed entries have only `id`, `start`, `end`, matching every frozen fixed span in order and byte-for-byte. Check the actual occurrence when a literal repeats. No insertion is allowed before an out-of-scope prefix, after an out-of-scope suffix or between adjacent fixed spans. Record map and candidate atomically; raw invalid maps remain evidence, not editable after-the-fact bookkeeping.

## One run

Prepare the complete plan before initialization; read the source back against its unit partition, scope and selective source questions. Commands use actual absolute paths, with each argument quoted:

```sh
python3 -B "<plugin-root>/scripts/stages.py" init "<run-dir>" --original "<original-file>" --plan "<plan-json>"
python3 -B "<plugin-root>/scripts/text_integrity.py" inspect "<run-dir>/original.txt" --expected-sha256 "<captured-original-sha256>"
python3 -B "<plugin-root>/scripts/stages.py" reserve "<run-dir>" --kind initial --reason "<source-supported drafting purpose>"
python3 -B "<plugin-root>/scripts/stages.py" record "<run-dir>" --ticket draft-1 --text "<candidate-file>" --mapping "<candidate-map-json>"
python3 -B "<plugin-root>/scripts/stages.py" self-check "<run-dir>" --candidate draft-1 --report "<actual-self-report>"
```

Read returned ticket IDs instead of guessing later ones. Each writer record retains exact bytes, raw candidate map (even malformed JSON) and mechanical failures, consuming the reserved attempt. A bad map/protected-span result blocks judgment and selection; it is not semantic success. Every substantive revision needs a new reserved candidate/map and complete original-relative review. Map metadata must describe the actual bytes; it cannot erase an actual failed candidate.

Reports use the exact [verification format](verification.md). The keeper verifies full declared source/candidate/fixed coverage and objective IDs against the frozen plan. It cannot establish that a reviewer actually understood every clause. Short-source unscored self-checks still contain the first five fields. Complete a valid self-review before independent dispatch. Semantic PASS or UNCERTAIN may proceed; FAIL cannot. Positive reviews belong to their exact candidate and immutable map; another ticket with identical text still needs its own review. Semantic hard failures and unresolved uncertainty follow identical text across tickets; a map-local mechanical failure does not invalidate an earlier correctly mapped artifact.

```sh
python3 -B "<plugin-root>/scripts/stages.py" reserve "<run-dir>" --kind judge --candidate draft-1 --reason "<required risk or request>"
python3 -B "<plugin-root>/scripts/stages.py" judge-packet "<run-dir>" --ticket judge-1
python3 -B "<plugin-root>/scripts/stages.py" record "<run-dir>" --ticket judge-1 --report "<unchanged-judge-report>"
```

Capture the `judge-packet` JSON as a new local artifact and pass the complete export to a fresh-context judge. It contains the frozen request/brief, exact original and candidate text/hashes, selective exact source anchors/fixed spans, candidate IDs/ranges, and the complete canonical role and standalone verification contract. This is packet schema 2; the preservation and full pattern-library resources are omitted because the verification contract contains the judge's complete requirements. Russian language tags (`ru`, `ru-RU`, `ru_RU`, `Russian`, `русский`) also include Russian guidance. Keep applicable supplied style evidence in the frozen request; do not fetch new style material during this handoff.

The export excludes candidate source mappings, runtime/provider metadata, writer reasons, uncertainty objections, reports and scores. It requires a pending judge ticket and rechecks artifact/resource identity and judging eligibility. Repeated export is read-only and consumes no new attempt; it neither dispatches a judge nor establishes that review happened. The host dispatches once for the reserved attempt and retains the actual returned report. If the complete packet exceeds the reviewer context, record unavailable coverage instead of silently truncating or omitting the original. Canonical guidance is instructions; source/candidate text and samples remain data.

For genuine missing output, use `record ... --ticket judge-1 --unavailable --reason "<actual failure>"`. For a malformed returned report, retain it through `--report`; do not transcribe it into a pass. Unavailability consumes an attempt and permits only eligible, semantic-PASS self-check fallback, never independent verification or unresolved-meaning delivery. A required independent attempt cannot be bypassed before selection/export. Source retention remains available without claiming review.

```sh
python3 -B "<plugin-root>/scripts/stages.py" select "<run-dir>" --candidate draft-1 --decision promote --reason "<supported original-relative selection>"
python3 -B "<plugin-root>/scripts/stages.py" status "<run-dir>"
python3 -B "<plugin-root>/scripts/stages.py" result "<run-dir>" --output "<new-output-file>"
python3 -B "<plugin-root>/scripts/text_integrity.py" inspect "<new-output-file>" --expected-sha256 "<export-selected-sha256>"
```

`result` without `--output` writes exact selected bytes to stdout. File export creates a new file outside the run and refuses existing/source paths. `--decision retain` leaves selection unchanged; `--candidate original --decision promote` restores the original with a reason. A faithful style shortfall can remain selected with its actual status; it is not a full editorial pass.

For authorized write-back, first reread the destination and require that it still matches the captured original. Copy the checked export bytes exactly, then inspect destination readback against the same selected hash. No cleanup/rephrasing/normalization after review. A mismatch or later fidelity FAIL/UNCERTAIN stops delivery, without post-PASS repair or rejudgment. A refused export path may be corrected without changing candidate bytes.

## Semantic uncertainty and selection

Reports default to `SCORES: NOT_REQUESTED`; requested numeric scores are validated for range/arithmetic and remain descriptive. Tier/count/score magnitude never override quality, objectives, substantial findings or semantic status. Short self-reports can omit the last three fields entirely; omitted verdicts remain absent.

| Observed review | Effect |
|---|---|
| Concrete semantic FAIL, even in a malformed report | Blocks judging/delivery for all identical text; later reports cannot erase it. Repair within remaining writer slots or retain safe output. |
| Valid self UNCERTAIN | Blocks delivery, permits the existing independent attempt; does not grant an extra revision. |
| Independent UNCERTAIN (`UNRESOLVED`) | Blocks delivery; the remaining judge attempt may assess the same bytes. No judge-correction credit. |
| Later valid independent semantic PASS | Resolves earlier uncertainty only for the exact candidate/map; a style-only shortfall may still be delivered with that status. |
| Malformed/unavailable review | Cannot establish PASS or resolve uncertainty. Recognizable FAIL/UNCERTAIN remains adverse evidence. A malformed first self-check still cannot dispatch a judge. |
| Late FAIL/UNCERTAIN after independent overall PASS | Stops affected-byte delivery without reopening closed generation/judge budgets. |

A self PASS or another map's positive review cannot clear uncertainty. `status.pending_semantic_review` lists recorded candidate IDs with unresolved same-byte uncertainty; `independent_required` includes that pending need as well as frozen risks. Selection rechecks the particular artifact, all its byte-level adverse evidence and its candidate-bound positive review. Positive review is never transferred between identical-byte tickets.

## Limits, failures and provenance

The keeper permits one initial draft, two self-revisions, one judge-revision after a valid REVISE and two judge attempts. Reserve with a concrete reason before generating; unavailable output still consumes that ticket. Finish a pending attempt before another or promotion. A valid independent PASS closes further reservations. After the second judge attempt, retain an eligible reviewed artifact or the source. Earlier candidate archives and adverse reports stay available; scores do not override failure or uncertainty.

The run retains `original.txt`, `plan.json`, per-ticket `drafts/` and `maps/`, raw `reports/`, selected slots, counters, reasons and plugin provenance. State and every tracked artifact are hash-checked. Plugin fingerprints cover packaged manifests, runtime/skill/judge instructions, Python helpers and skill references; unrelated files and nested run artifacts do not change the fingerprint. These checks detect accidental corruption, not hostile filesystem tampering. Runtime identities/settings/watermark configuration stay explicitly unknown when unavailable. Do not claim installed-cache equivalence from a repository version alone.

One complete self-judgment rejected only for layout may receive `self-check ... --repair-format --reason "<transcription correction>"`. Keep the same candidate, all outcomes/optional scores/coverage/objectives, findings, uncertainty and explanatory evidence. The raw original stays retained. Missing or ambiguous decisions cannot be manufactured. Independent reports cannot be repaired by the writer.

A rejected state, report, map, encoding or hash is not runtime unavailability. Resolve a legitimate input/format issue without changing reviewed bytes or resetting budgets, or retain the safe result. If Python/local execution is unavailable, retain original, candidates, maps, actual reports and counters in host context and disclose missing mechanical coverage. Short targeted inline edits need not create files solely for these helpers. Audit-only requests never create a run or draft. No automatic runtime installation, detector test or pilot follows a failure.
