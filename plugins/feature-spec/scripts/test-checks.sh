#!/usr/bin/env bash
# ABOUTME: Self-test for every checker, generator and the hook, plus skill frontmatter, script grants and
# ABOUTME: rule tables — asserts the shipped skeletons pass, then mutates one rule at a time and asserts its failure fires.
#
# A checker that stops enforcing a rule keeps printing OK, so the rule dies silently.
# This is the only thing standing between a regex tweak and a plugin that validates nothing.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REFS="$HERE/../skills/feature-spec/references"
TREE_CHECK="$HERE/check-tree.sh"
SPEC_CHECK="$HERE/check-spec.sh"

command -v python3 >/dev/null 2>&1 || { echo "FAIL  python3 not found — test-checks.sh cannot run"; exit 2; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/docs/specs" "$WORK/docs/adr"

pass=0; fail=0; skipped=0

# expect <name> <exit-code> <pattern-that-must-appear> -- <command...>
expect() {
  local name="$1" want="$2" pat="$3"; shift 4
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$rc" -ne "$want" ]; then
    echo "FAIL  $name"
    echo "      exit $rc, wanted $want"
    printf '%s\n' "$out" | tail -4 | while IFS= read -r l; do echo "      | $l"; done
    fail=$((fail+1)); return
  fi
  if [ -n "$pat" ] && ! printf '%s\n' "$out" | grep -qi -- "$pat"; then
    echo "FAIL  $name"
    echo "      exit code right, but no output matched: $pat"
    printf '%s\n' "$out" | grep -i 'FAIL' | head -3 | while IFS= read -r l; do echo "      | $l"; done
    fail=$((fail+1)); return
  fi
  echo "ok    $name"
  pass=$((pass+1))
}

# ---------------------------------------------------------------- fixtures
# The design record fixture is the skeleton the plugin documents in
# tree-format.md. Testing against the shipped example is what stops the
# format and its checker drifting apart.
python3 - "$REFS/tree-format.md" "$WORK/tree.md" <<'PY'
import re,sys
src=open(sys.argv[1]).read()
m=re.search(r'```skeleton\n(.*?)\n```', src, re.S)
if not m:
    sys.stderr.write("no ```skeleton block in tree-format.md\n"); sys.exit(2)
open(sys.argv[2],'w').write(m.group(1)+"\n")
PY
[ -s "$WORK/tree.md" ] || { echo "FAIL  could not extract the tree skeleton"; exit 2; }

# The files the skeleton's ## Reads names, so the resolution check has something real.
: > "$WORK/docs/specs/GLOSSARY.md"
cat > "$WORK/docs/adr/0004-checkpoint-file-over-database.md" <<'EOF'
# Checkpoint file over a database for retry state

Status: Proposed

## Decision

Retry state lives in the existing JSON checkpoint file, not a new table.
EOF
: > "$WORK/AGENTS.md"
# The file the skeleton's first grounding fact cites, long enough to hold line 31.
mkdir -p "$WORK/cmd/ingest"
for n in $(seq 1 40); do echo "// line $n"; done > "$WORK/cmd/ingest/state.go"

# A spec whose every tag resolves against that record: Q1, Q2, grounding fact 1,
# the chosen strategy and ADR-0004 all exist in the skeleton above.
cat > "$WORK/spec.md" <<'EOF'
# Retry uploads

Batch imports restart from zero after a crash.

## User stories

P1 · Resume an interrupted import

## Requirements

FR-001  The importer resumes from the last checkpoint on restart.
        ← Settled Q1
FR-002  The importer retries a failed row at most 5 times over 24 hours.
        ← Settled Q2
FR-003  Retry state is written to the existing checkpoint file.
        ← Grounding fact 1

## Success criteria

SC-001  An import interrupted at row 10000 resumes within 2 seconds.
        ← Strategy (chosen)
SC-002  A row that has failed 5 times appears in the reject file with its line number.
        ← ADR-0004

## Acceptance scenarios

FR-001  Given a checkpoint exists, when the importer starts, then it resumes from it.
FR-002  Given 5 attempts have been made, when a 6th is due, then the row is rejected.
FR-003  Given a retry is scheduled, when state is written, then it lands in the checkpoint file.

## Out of scope

- An external retry queue. ← Strategy (chosen)

## Open questions

- [NEEDS CLARIFICATION: Q12 — per-source overrides, low impact, deferred to post-launch]
EOF

mut() { # mut <dest> <sed-expr> [src]
  sed "$2" "${3:-$WORK/tree.md}" > "$WORK/$1"
}

echo "── check-tree.sh ─────────────────────────────────────────────"

expect "shipped skeleton passes" 0 "TREE OK" -- \
  bash "$TREE_CHECK" "$WORK/tree.md" --repo-root "$WORK"

mut ghost.md 's|docs/adr/0004-checkpoint-file-over-database.md|docs/adr/9999-invented.md|'
expect "ghost ## Reads entry is caught" 1 "does not exist" -- \
  bash "$TREE_CHECK" "$WORK/ghost.md" --repo-root "$WORK"

mut state.md 's/| Verification | Missing |/| Verification | Done |/'
expect "illegal coverage state is caught" 1 "illegal state" -- \
  bash "$TREE_CHECK" "$WORK/state.md" --repo-root "$WORK"

mut clearstar.md 's/Clear\* (1 deferred)/Clear*/'
expect "Clear* without a count is caught" 1 "deferral count" -- \
  bash "$TREE_CHECK" "$WORK/clearstar.md" --repo-root "$WORK"

mut na.md 's|N/A — no user-facing surface|N/A|'
expect "N/A without a reason is caught" 1 "no stated reason" -- \
  bash "$TREE_CHECK" "$WORK/na.md" --repo-root "$WORK"

mut rename.md 's/| Problem \& outcome |/| Problem and outcomes |/'
expect "paraphrased category name is caught" 1 "coverage" -- \
  bash "$TREE_CHECK" "$WORK/rename.md" --repo-root "$WORK"

mut noround.md 's/(r1)$//'
expect "settled answer missing its round is caught" 1 "round tag" -- \
  bash "$TREE_CHECK" "$WORK/noround.md" --repo-root "$WORK"

mut nowhy.md 's/^  \*Why:\* one source of truth.*$/  one source of truth./'
expect "settled answer missing its rationale is caught" 1 "rationale" -- \
  bash "$TREE_CHECK" "$WORK/nowhy.md" --repo-root "$WORK"

mut dupq.md 's/\*\*Q2 Attempt ceiling\*\*/**Q1 Attempt ceiling**/'
expect "reused question id is caught" 1 "reused" -- \
  bash "$TREE_CHECK" "$WORK/dupq.md" --repo-root "$WORK"

mut orphan.md 's/deps: Q7/deps: Q12/'
expect "blocked question behind a deferred parent is caught" 1 "transitive" -- \
  bash "$TREE_CHECK" "$WORK/orphan.md" --repo-root "$WORK"

mut round99.md 's/Round: 1 of 2/Round: 3 of 2/'
expect "a round past its declared cap is caught" 1 "past the declared cap" -- \
  bash "$TREE_CHECK" "$WORK/round99.md" --repo-root "$WORK"

mut nophase.md 's/Next phase: 2/Next phase: 12/'
expect "out-of-range next phase is caught" 1 "phases 0 through 7" -- \
  bash "$TREE_CHECK" "$WORK/nophase.md" --repo-root "$WORK"

mut noprob.md '/^## Problem$/,/^## Protocol$/{/^## /!d;}'
expect "empty problem statement is caught" 1 "Problem is empty" -- \
  bash "$TREE_CHECK" "$WORK/noprob.md" --repo-root "$WORK"

expect "missing file is not a pass" 2 "no such file" -- \
  bash "$TREE_CHECK" "$WORK/nope.md"

# --- an entry is checked as an entry, not as a count ----------------------
# Two rationales on Q1 used to cover for none on Q2.
python3 - "$WORK/tree.md" "$WORK/why-elsewhere.md" <<'WHYEOF'
import sys
src=open(sys.argv[1]).read()
a="  *Why:* survives a workday outage, bounds file growth. (r1)\n"
b="  *Why:* one source of truth, and replay already reads it. Stated in the request. (r0)\n"
assert a in src and b in src
open(sys.argv[2],'w').write(src.replace(a,"").replace(b, b+"  *Why:* a second reason on the wrong entry. (r1)\n"))
WHYEOF
expect "a rationale on another entry does not cover for a missing one" 1 "settled with no rationale: Q2" -- \
  bash "$TREE_CHECK" "$WORK/why-elsewhere.md" --repo-root "$WORK"
mut noanswer.md 's/^- \*\*Q2 Attempt ceiling\*\* → .*$/- **Q2 Attempt ceiling** → /'
expect "a settled entry with no answer is caught" 1 "settled with no answer: Q2" -- \
  bash "$TREE_CHECK" "$WORK/noanswer.md" --repo-root "$WORK"
mut colon-entry.md 's/^- \*\*Q2 Attempt ceiling\*\* → /- **Q2 Attempt ceiling**: /'
expect "a settled entry no tool can read is caught" 1 "under ## Settled cannot be read" -- \
  bash "$TREE_CHECK" "$WORK/colon-entry.md" --repo-root "$WORK"
mut plain-deferred.md 's/^- \*\*Q12 Per-source overrides\*\*/- Q12 Per-source overrides/'
expect "a deferred entry no tool can read is caught" 1 "under ## Deferred cannot be read" -- \
  bash "$TREE_CHECK" "$WORK/plain-deferred.md" --repo-root "$WORK"
mut deferred-noreason.md 's/^- \*\*Q12 Per-source overrides\*\* — .*$/- **Q12 Per-source overrides** (r1)/'
expect "a deferral with no reason is caught" 1 "Q12 is deferred with no reason" -- \
  bash "$TREE_CHECK" "$WORK/deferred-noreason.md" --repo-root "$WORK"
mut round-words.md 's/Round: 1 of 2   Next phase: 2/Round: one of two   Next phase: drafting/'
expect "a round and phase that are not numbers are caught" 1 "Round is not written as" -- \
  bash "$TREE_CHECK" "$WORK/round-words.md" --repo-root "$WORK"
mut overcount.md 's/Clear\* (1 deferred)/Clear* (3 deferred)/'
expect "a Clear* count that ## Deferred does not back is caught" 1 "counts 3 deferred question(s)" -- \
  bash "$TREE_CHECK" "$WORK/overcount.md" --repo-root "$WORK"

# --- a decision taken from a document keeps the document's wording ---------
# The (r0) entry is what every requirement citing it is compared with, and
# nothing downstream has the document, so a paraphrase is caught here or never.
mkdir -p "$WORK/docs/briefs"
cat > "$WORK/docs/briefs/retry.md" <<'EOF'
# Brief: retry uploads

## Decided
- Retry state lives in the existing checkpoint file, not in a new table — one source of truth — decided by the user
EOF
python3 - "$WORK/tree.md" "$WORK" <<'R0EOF'
import sys
src=open(sys.argv[1]).read()
reads="- AGENTS.md   (principles)\n"
entry=("- **Q1 Where retry state lives** → in the existing checkpoint file. [P1]\n"
       "  *Why:* one source of truth, and replay already reads it. Stated in the request. (r0)\n")
assert reads in src and entry in src
def variant(name, answer, why):
    out=src.replace(reads, reads+"- docs/briefs/retry.md   (the input brief)\n")
    out=out.replace(entry, f"- **Q1 Where retry state lives** → {answer} [P1]\n  *Why:* {why} (r0)\n")
    open(f"{sys.argv[2]}/{name}","w").write(out)
variant("r0-copied.md", "Retry state lives in the existing checkpoint file, not in a new table.",
        'one source of truth. From docs/briefs/retry.md, "Decided".')
variant("r0-paraphrased.md", "Failed uploads are remembered by reusing whatever storage the importer already has.",
        'one source of truth. From docs/briefs/retry.md, "Decided".')
variant("r0-unsourced.md", "Retry state lives in the existing checkpoint file, not in a new table.",
        "one source of truth. Decided in the brief.")
R0EOF
expect "a decision copied from the brief passes" 0 "taken from an input document keep its wording" -- \
  bash "$TREE_CHECK" "$WORK/r0-copied.md" --repo-root "$WORK"
expect "a decision paraphrased from the brief is caught" 1 "of its answer is that document's wording" -- \
  bash "$TREE_CHECK" "$WORK/r0-paraphrased.md" --repo-root "$WORK"
expect "and it is caught on the write that makes it" 1 "of its answer is that document's wording" -- \
  bash "$TREE_CHECK" "$WORK/r0-paraphrased.md" --repo-root "$WORK" --closed-world
expect "an intake decision that names no source is caught" 1 "without saying where the decision came from: Q1" -- \
  bash "$TREE_CHECK" "$WORK/r0-unsourced.md" --repo-root "$WORK"

# --- grounding facts cite lines that exist --------------------------------
# Every requirement citing a fact inherits what is wrong with it, and nothing
# downstream opens the file again.
mut fact-ghost.md 's|cmd/ingest/state.go:31|cmd/ingest/no_such_file.go:9|'
expect "a grounding fact citing a file that is not there is caught" 1 "no such file exists" -- \
  bash "$TREE_CHECK" "$WORK/fact-ghost.md" --repo-root "$WORK"
expect "and it is caught on every write" 1 "no such file exists" -- \
  bash "$TREE_CHECK" "$WORK/fact-ghost.md" --repo-root "$WORK" --closed-world
mut fact-line.md 's|cmd/ingest/state.go:31|cmd/ingest/state.go:9999|'
expect "a grounding fact citing a line past the end of the file is caught" 1 "line 9999 of cmd/ingest/state.go, which has 40 lines" -- \
  bash "$TREE_CHECK" "$WORK/fact-line.md" --repo-root "$WORK"
mut fact-refuted.md 's|^1\. Ingest state is a JSON checkpoint at `cmd/ingest/state.go:31`|1. "State lives in `cmd/ingest/store.go:12`" — contradicted: no such file, searched cmd/ingest|'
expect "a contradicted claim may name the file that is not there" 0 "TREE OK" -- \
  bash "$TREE_CHECK" "$WORK/fact-refuted.md" --repo-root "$WORK"
mut fact-image.md 's|^2\. Nearest analogous feature: `--replay`|2. The compose file pins `ghcr.io/acme/api:3` and listens on `localhost:8080`|'
expect "an image tag and a host are not read as file citations" 0 "TREE OK" -- \
  bash "$TREE_CHECK" "$WORK/fact-image.md" --repo-root "$WORK"
mut fact-nosource.md 's|^2\. Nearest analogous feature.*$|2. Something nobody looked up|'
expect "a grounding fact with no source is caught" 1 "grounding fact 2 does not say where it came from" -- \
  bash "$TREE_CHECK" "$WORK/fact-nosource.md" --repo-root "$WORK"
mut fact-dup.md 's|^2\. Nearest analogous feature|1. Nearest analogous feature|'
expect "a grounding fact number used twice is caught" 1 "grounding fact number used twice: 1" -- \
  bash "$TREE_CHECK" "$WORK/fact-dup.md" --repo-root "$WORK"
# A fact from an earlier session describes the code as it was then.
sed -e 's/Round: 1 of 2/Round: 2 of 4/' -e 's|cmd/ingest/state.go:31|cmd/ingest/state.go:9999|' \
  "$WORK/tree.md" > "$WORK/fact-stale.md"
expect "a stale citation from an earlier session is reported, not failed" 0 "it may have changed since" -- \
  bash "$TREE_CHECK" "$WORK/fact-stale.md" --repo-root "$WORK"

# A crash exits 1, as a finding list does. Only the result line tells them apart.
printf '# Design tree: x\n\n## Problem\n\xff\xfe broken bytes\n' > "$WORK/badbytes.md"
expect "a checker that crashed is not read as findings" 2 "did not reach a verdict" -- \
  bash "$TREE_CHECK" "$WORK/badbytes.md" --repo-root "$WORK"

# --- principles files that live outside the repo --------------------------
# This machine keeps its only AGENTS.md in ~. Rejecting the path on shape made
# a real, readable file report as invented.
sed 's|- AGENTS.md   (principles)|- ~/.claude/definitely-not-here-9f3a.md   (principles)|' \
  "$WORK/tree.md" > "$WORK/tree-ext-ghost.md"
expect "an external path that does not exist is still a ghost" 1 "does not exist" -- \
  bash "$TREE_CHECK" "$WORK/tree-ext-ghost.md" --repo-root "$WORK"

sed "s|- AGENTS.md   (principles)|- $WORK/AGENTS.md   (principles)|" \
  "$WORK/tree.md" > "$WORK/tree-ext-ok.md"
expect "an external path that exists resolves" 0 "outside the repo" -- \
  bash "$TREE_CHECK" "$WORK/tree-ext-ok.md" --repo-root "$WORK"

# --- a run that asked nothing --------------------------------------------
# Input that already covers every category gets no clarifying round, so a
# record at Round 0 whose every decision is tagged (r0) is a finished record.
sed -e 's/Round: 1 of 2/Round: 0 of 2/' -e 's/bounds file growth\. (r1)$/bounds file growth. Stated in the request. (r0)/' \
  -e 's/(r1)$/(r0)/' "$WORK/tree.md" > "$WORK/tree-noround.md"
expect "a record with no clarifying round passes the gate" 0 "TREE OK" -- \
  bash "$TREE_CHECK" "$WORK/tree-noround.md" --repo-root "$WORK"

mut ahead.md 's/Round: 1 of 2/Round: 0 of 2/'
expect "an answer tagged past the recorded round is caught" 1 "Round says 0" -- \
  bash "$TREE_CHECK" "$WORK/ahead.md" --repo-root "$WORK"

# --- a record written by an earlier version ------------------------------
# Its Protocol block carries Mode, Counters and Guard lines and its own cap.
# Those fields are no longer read, and the record must still resume and amend.
python3 - "$WORK/tree.md" "$WORK/tree-v1.md" <<'V1EOF'
import sys
src=open(sys.argv[1]).read()
old="Round: 1 of 2   Next phase: 2\n"
assert old in src
new=("Round: 3 of 3   4th round unlocked: no   Next phase: 5\n"
     "Counters: questions 14 · fact-finders 2 · references 4 · orchestrator reads 5 · lines read 340 · critic passes 0\n"
     "Largest single read: 180 lines\n"
     "Guard: not tripped\n"
     "Mode: default\n")
open(sys.argv[2],'w').write(src.replace(old,new))
V1EOF
expect "a record from an earlier version still passes" 0 "TREE OK" -- \
  bash "$TREE_CHECK" "$WORK/tree-v1.md" --repo-root "$WORK"

echo
echo "── check-spec.sh ─────────────────────────────────────────────"

expect "valid spec passes" 0 "SPEC OK" -- \
  bash "$SPEC_CHECK" "$WORK/spec.md" --tree "$WORK/tree.md"

expect "refuses to run without the design record" 2 "--tree is required" -- \
  bash "$SPEC_CHECK" "$WORK/spec.md"

expect "unreadable design record is not a pass" 2 "not found" -- \
  bash "$SPEC_CHECK" "$WORK/spec.md" --tree "$WORK/nope.md"

smut() { sed "$2" "$WORK/spec.md" > "$WORK/$1"; }

smut fake-q.md 's/← Settled Q1/← Settled Q99/'
expect "fabricated Settled id is caught" 1 "fabricated citation" -- \
  bash "$SPEC_CHECK" "$WORK/fake-q.md" --tree "$WORK/tree.md"

smut fake-fact.md 's/← Grounding fact 1/← Grounding fact 42/'
expect "fabricated grounding fact is caught" 1 "fabricated citation" -- \
  bash "$SPEC_CHECK" "$WORK/fake-fact.md" --tree "$WORK/tree.md"

smut fake-adr.md 's/← ADR-0004/← ADR-9999/'
expect "fabricated ADR is caught" 1 "fabricated citation" -- \
  bash "$SPEC_CHECK" "$WORK/fake-adr.md" --tree "$WORK/tree.md"

smut fake-md.md 's|← Settled Q2|← docs/invented.md|'
expect "citation of a file not in ## Reads is caught" 1 "fabricated citation" -- \
  bash "$SPEC_CHECK" "$WORK/fake-md.md" --tree "$WORK/tree.md"

smut untagged.md '/← Settled Q2/d'
expect "missing source tag is caught" 1 "no source tag" -- \
  bash "$SPEC_CHECK" "$WORK/untagged.md" --tree "$WORK/tree.md"

smut adj.md 's/resumes within 2 seconds/resumes quickly/'
expect "unquantified adjective is caught" 1 "unquantified adjective" -- \
  bash "$SPEC_CHECK" "$WORK/adj.md" --tree "$WORK/tree.md"

smut noscen.md '/^FR-002  Given 5 attempts/d'
expect "requirement with no acceptance scenario is caught" 1 "no acceptance scenario" -- \
  bash "$SPEC_CHECK" "$WORK/noscen.md" --tree "$WORK/tree.md"

smut bare.md 's/\[NEEDS CLARIFICATION: Q12[^]]*\]/[NEEDS CLARIFICATION]/'
expect "bare clarification marker is caught" 1 "bare \[NEEDS CLARIFICATION\]" -- \
  bash "$SPEC_CHECK" "$WORK/bare.md" --tree "$WORK/tree.md"

# An out-of-scope line and an implementation constraint are decisions too: each
# carries a tag, and the tag is resolved like any other.
expect "a tag on an out-of-scope line resolves" 0 "cited outside the requirement sections resolve" -- \
  bash "$SPEC_CHECK" "$WORK/spec.md" --tree "$WORK/tree.md"
smut scope-fake.md 's/^- An external retry queue\. ← Strategy (chosen)/- An external retry queue. ← Settled Q99/'
expect "a fabricated tag on an out-of-scope line is caught" 1 "fabricated citation" -- \
  bash "$SPEC_CHECK" "$WORK/scope-fake.md" --tree "$WORK/tree.md"
smut scope-untagged.md 's/^- An external retry queue\. ← Strategy (chosen)/- An external retry queue./'
expect "an untagged out-of-scope line is caught" 1 "under ## Out of scope has no source tag" -- \
  bash "$SPEC_CHECK" "$WORK/scope-untagged.md" --tree "$WORK/tree.md"
printf '\n## Implementation constraints\n\n- Must use Kafka and store state in Postgres.\n' \
  | cat "$WORK/spec.md" - > "$WORK/constraint-untagged.md"
expect "an untagged implementation constraint is caught" 1 "under ## Implementation constraints has no source tag" -- \
  bash "$SPEC_CHECK" "$WORK/constraint-untagged.md" --tree "$WORK/tree.md"

# One deferred question is one marker. Marked inline and again under Open
# questions, it is counted twice here and carried into a plan as two.
expect "a deferred question marked once passes" 0 "1 clarification marker" -- \
  bash "$SPEC_CHECK" "$WORK/spec.md" --tree "$WORK/tree.md"
smut marker-twice.md 's/^- An external retry queue\./& [NEEDS CLARIFICATION: Q12 — also marked here]/'
expect "a deferred question marked twice is caught" 1 "more than once" -- \
  bash "$SPEC_CHECK" "$WORK/marker-twice.md" --tree "$WORK/tree.md"
smut marker-inline.md 's/^FR-002  The importer retries a failed row at most 5 times over 24 hours\.$/& [NEEDS CLARIFICATION: the ceiling per source is open]/'
expect "a tagged requirement with an inline marker is caught" 1 "both a source tag and an inline marker" -- \
  bash "$SPEC_CHECK" "$WORK/marker-inline.md" --tree "$WORK/tree.md"
smut marker-anon.md 's/NEEDS CLARIFICATION: Q12 — /NEEDS CLARIFICATION: /'
expect "an open question that names no question id is caught" 1 "name no question id" -- \
  bash "$SPEC_CHECK" "$WORK/marker-anon.md" --tree "$WORK/tree.md"

# The markers and the record's ## Deferred list are the same set of questions.
smut marker-dropped.md '/NEEDS CLARIFICATION: Q12/d'
expect "a deferred question the spec does not carry is caught" 1 "not carried under ## Open questions: Q12" -- \
  bash "$SPEC_CHECK" "$WORK/marker-dropped.md" --tree "$WORK/tree.md"
smut marker-settled.md 's/NEEDS CLARIFICATION: Q12 — /NEEDS CLARIFICATION: Q2 — /'
expect "a marker for a question the record settled is caught" 1 "which the record does not defer — the record settled it" -- \
  bash "$SPEC_CHECK" "$WORK/marker-settled.md" --tree "$WORK/tree.md"

# --- a statement nobody can see -------------------------------------------
# A bullet with no identifier, a section the template does not define and a
# line after a tag all assert something no tag covers and no critic is shown.
smut stray.md 's/^## Requirements$/&\
\
- The importer must also delete every checkpoint older than 30 days./'
expect "a statement with no identifier in ## Requirements is caught" 1 "belongs to no identifier" -- \
  bash "$SPEC_CHECK" "$WORK/stray.md" --tree "$WORK/tree.md"
expect "and it is caught on a draft mid-write too" 1 "belongs to no identifier" -- \
  bash "$SPEC_CHECK" "$WORK/stray.md" --tree "$WORK/tree.md" --closed-world
printf '\n## Non-functional requirements\n\nNFR-001  All retry state is encrypted at rest.\n' \
  | cat "$WORK/spec.md" - > "$WORK/unknown-section.md"
expect "a section the template does not define is caught" 1 "not a section of the spec template" -- \
  bash "$SPEC_CHECK" "$WORK/unknown-section.md" --tree "$WORK/tree.md"
printf '\n## Out of scope\n\n- A second boundary. ← Settled Q1\n' \
  | cat "$WORK/spec.md" - > "$WORK/twice-scope.md"
expect "the same section twice is caught" 1 "more than one 'out of scope' section" -- \
  bash "$SPEC_CHECK" "$WORK/twice-scope.md" --tree "$WORK/tree.md"
smut bold-id.md 's/^FR-003  Retry state is written/**FR-003:** Retry state is written/'
expect "a bolded identifier is still a definition" 0 "found 3 requirements" -- \
  bash "$SPEC_CHECK" "$WORK/bold-id.md" --tree "$WORK/tree.md"

# "withdrawn" as an ordinary word does not exempt a requirement from its tag.
sed -e 's/^FR-002  The importer retries a failed row at most 5 times over 24 hours\.$/FR-002  A row withdrawn by the operator is retried at most 5 times over 24 hours./' \
    -e '/← Settled Q2$/d' "$WORK/spec.md" > "$WORK/withdrawn-word.md"
expect "the word withdrawn in a sentence exempts nothing" 1 "FR-002 (line [0-9]*) has no source tag" -- \
  bash "$SPEC_CHECK" "$WORK/withdrawn-word.md" --tree "$WORK/tree.md"

# A scenario is keyed by the identifier that opens its line.
smut scen-mention.md 's/^FR-002  Given 5 attempts.*$/Scenarios for FR-002 are still to be written./'
expect "a requirement only mentioned among the scenarios has none" 1 "no acceptance scenario: FR-002" -- \
  bash "$SPEC_CHECK" "$WORK/scen-mention.md" --tree "$WORK/tree.md"
smut scen-ghost.md 's/^FR-003  Given a retry is scheduled/FR-0030  Given a retry is scheduled/'
expect "a scenario keyed to an undefined requirement is caught" 1 "keyed to FR-0030, which the spec does not define" -- \
  bash "$SPEC_CHECK" "$WORK/scen-ghost.md" --tree "$WORK/tree.md"

# A claim the fact-finder graded unverifiable is not a fact to build on.
mut tree-unverifiable.md 's|^1\. Ingest state is a JSON checkpoint.*$|1. "Ingest state is meant to move to a database" — unverifiable: about intent, nothing in the code says (fact-finder, r0, low)|'
expect "a requirement resting on an unverifiable claim is caught" 1 "grades that claim unverifiable" -- \
  bash "$SPEC_CHECK" "$WORK/spec.md" --tree "$WORK/tree-unverifiable.md"

# A file is where a decision came from, not a decision. Citing one would let a
# requirement skip the record entirely, with nothing for a critic to compare.
smut file-tag.md 's|← Settled Q2$|← docs/specs/GLOSSARY.md|'
expect "a file cited as a source is caught" 1 "a file is not a source" -- \
  bash "$SPEC_CHECK" "$WORK/file-tag.md" --tree "$WORK/tree.md"
smut principle-loose.md 's|← Settled Q2$|← Principle: md|'
expect "a principle tag has to name the file" 1 "md is not in ## Principles in force" -- \
  bash "$SPEC_CHECK" "$WORK/principle-loose.md" --tree "$WORK/tree.md"
smut principle-ok.md 's|← Settled Q2$|← Principle: AGENTS.md|'
expect "a principle tag naming a read file resolves" 0 "SPEC OK" -- \
  bash "$SPEC_CHECK" "$WORK/principle-ok.md" --tree "$WORK/tree.md"
# An ADR is citable when its file is among the record's reads; a title is not a file.
sed 's|^- ADR-0004 Checkpoint file.*$|&\
- ADR-0009 Use an external queue — Proposed|' "$WORK/tree.md" > "$WORK/tree-adr-title.md"
smut adr-title.md 's/← ADR-0004/← ADR-0009/'
expect "an ADR with a title and no file is not a source" 1 "names no ADR file with the id 0009" -- \
  bash "$SPEC_CHECK" "$WORK/adr-title.md" --tree "$WORK/tree-adr-title.md"

printf '\n## Clarifications\n\n- Q1 (r0) — Where retry state lives → in the existing checkpoint file.\n- Q99 (r1) — Invented → never asked.\n' \
  | cat "$WORK/spec.md" - > "$WORK/clar-ghost.md"
expect "a clarification the record never settled is caught" 1 "Clarifications lists Q99" -- \
  bash "$SPEC_CHECK" "$WORK/clar-ghost.md" --tree "$WORK/tree.md"

smut dupid.md 's/^FR-003  Retry state/FR-001  Retry state/'
expect "duplicate identifier is caught" 1 "defined 2x" -- \
  bash "$SPEC_CHECK" "$WORK/dupid.md" --tree "$WORK/tree.md"

# --- amendment: identifier stability -------------------------------------
expect "an unchanged spec is stable against itself" 0 "identifiers stable against the previous spec" -- \
  bash "$SPEC_CHECK" "$WORK/spec.md" --tree "$WORK/tree.md" --prev "$WORK/spec.md"
smut reworded-late.md 's/at most 5 times over 24 hours/at most 500 times over 24 days/'
expect "a change late in a statement is still a reword" 1 "text changed under existing identifiers: FR-002" -- \
  bash "$SPEC_CHECK" "$WORK/reworded-late.md" --tree "$WORK/tree.md" --prev "$WORK/spec.md"
sed -e 's/^FR-001  The importer resumes from the last checkpoint on restart\.$/FR-001  SWAP/' \
    -e 's/^FR-002  The importer retries a failed row at most 5 times over 24 hours\.$/FR-002  The importer resumes from the last checkpoint on restart./' \
    -e 's/^FR-001  SWAP$/FR-001  The importer retries a failed row at most 5 times over 24 hours./' \
    "$WORK/spec.md" > "$WORK/renumbered.md"
expect "a renumber fails even when rewording is allowed" 1 "identifiers were renumbered" -- \
  bash "$SPEC_CHECK" "$WORK/renumbered.md" --tree "$WORK/tree.md" --prev "$WORK/spec.md" --allow-reword
smut reworded.md 's/The importer resumes from the last checkpoint on restart./The importer restarts the whole import from row zero./'
expect "reword under a stable id fails by default" 1 "text changed under existing identifiers" -- \
  bash "$SPEC_CHECK" "$WORK/reworded.md" --tree "$WORK/tree.md" --prev "$WORK/spec.md"

expect "reword is accepted when acknowledged" 0 "allow-reword" -- \
  bash "$SPEC_CHECK" "$WORK/reworded.md" --tree "$WORK/tree.md" --prev "$WORK/spec.md" --allow-reword

smut vanished.md '/^FR-003  Retry state/,+1d'
expect "vanished identifier is caught" 1 "vanished" -- \
  bash "$SPEC_CHECK" "$WORK/vanished.md" --tree "$WORK/tree.md" --prev "$WORK/spec.md"

expect "unreadable --prev is not a pass" 2 "previous spec not found" -- \
  bash "$SPEC_CHECK" "$WORK/spec.md" --tree "$WORK/tree.md" --prev "$WORK/nope.md"

# --- a tag may name several sources, and all of them are citations ---------
# Resolving only the first is the check the second one passes. It let a
# `Deferred Q<n>` — not a source form at all — into a shipped spec behind a
# valid `Settled Q<n>`, and cost a real answer its traceability row.

smut multi-ok.md 's/← Grounding fact 1/← Settled Q1 (r1), Grounding fact 1/'
expect "a tag naming two valid sources passes" 0 "SPEC OK" -- \
  bash "$SPEC_CHECK" "$WORK/multi-ok.md" --tree "$WORK/tree.md"

smut multi-bad.md 's/← Settled Q1$/← Settled Q1 (r1), Deferred Q12 (r2)/'
expect "an invalid second source is caught" 1 "Deferred Q12" -- \
  bash "$SPEC_CHECK" "$WORK/multi-bad.md" --tree "$WORK/tree.md"

smut multi-fake.md 's/← Settled Q1$/← Settled Q1, Settled Q99/'
expect "a fabricated second Settled id is caught" 1 "fabricated citation" -- \
  bash "$SPEC_CHECK" "$WORK/multi-fake.md" --tree "$WORK/tree.md"

smut plural.md 's/← Grounding fact 1/← Grounding facts 1, 2/'
expect "the plural Grounding facts form resolves" 0 "SPEC OK" -- \
  bash "$SPEC_CHECK" "$WORK/plural.md" --tree "$WORK/tree.md"

# --- ## Strategy tolerates the decoration a drafter reaches for ------------
# `- **Chosen (structure): C — …**` named no chosen approach to a literal
# `Chosen:` match, and the failure was reported against the spec.
sed 's/^- Chosen: B — sweep.*$/- **Chosen (structure): B — sweep the checkpoint on a timer.**\n- **Chosen (matte): A — composite in the existing pass.**/' \
  "$WORK/tree.md" > "$WORK/tree-decorated.md"
expect "a decorated per-axis Chosen resolves" 0 "SPEC OK" -- \
  bash "$SPEC_CHECK" "$WORK/spec.md" --tree "$WORK/tree-decorated.md"

sed '/^- Chosen:/d' "$WORK/tree.md" > "$WORK/tree-nochosen.md"
expect "a genuinely absent Chosen names the record, not the spec" 1 "design record" -- \
  bash "$SPEC_CHECK" "$WORK/spec.md" --tree "$WORK/tree-nochosen.md"

# --- criteria are written with digits --------------------------------------
smut worded.md 's/An import interrupted at row 10000 resumes within 2 seconds./An import resumes in all three cases./'
expect "a number spelled as a word is flagged" 0 "as a word" -- \
  bash "$SPEC_CHECK" "$WORK/worded.md" --tree "$WORK/tree.md"

echo
echo "── closed-world: incomplete is not wrong ─────────────────────"

# The hook fires on every write, and a document under construction is
# legitimately incomplete. An open-world check calls that broken, which does not
# teach the writer to comply — it teaches the writer to evade, by buffering
# everything into one giant Write or dodging the filename. Closed-world checks
# are true at every stage: a fabricated citation is wrong at write three of nine
# exactly as it is wrong at the end.

# A record as Phase 1 legitimately leaves it: four sections, no coverage table.
cat > "$WORK/phase1.md" <<'EOF'
# Design tree: retry uploads

## Problem
Batch imports restart from zero after a crash.

## Protocol
Slug: 2026-08-24-retry   Started: 2026-08-24
Round: 0 of 2   Next phase: 2

## Reads
- AGENTS.md   (principles)

## Principles in force
- From AGENTS.md: "smallest reasonable change"

## Grounding facts
1. Ingest state is a JSON checkpoint at `state.go:31` (fact-finder, r0, high)
EOF

expect "a Phase 1 record passes closed-world" 0 "TREE OK (closed-world)" -- \
  bash "$TREE_CHECK" "$WORK/phase1.md" --closed-world --repo-root "$WORK"
expect "the same record still fails the full gate" 1 "missing sections" -- \
  bash "$TREE_CHECK" "$WORK/phase1.md" --repo-root "$WORK"

# A corrupt value is wrong at any stage and must survive closed-world.
sed 's/Round: 0 of 2/Round: 99 of 2/' "$WORK/phase1.md" > "$WORK/phase1-bad.md"
expect "a round past its cap still fires in closed-world" 1 "past the declared cap" -- \
  bash "$TREE_CHECK" "$WORK/phase1-bad.md" --closed-world --repo-root "$WORK"
sed 's|- AGENTS.md   (principles)|- docs/nope.md|' "$WORK/phase1.md" > "$WORK/phase1-ghost.md"
expect "a ghost read still fires in closed-world" 1 "does not exist" -- \
  bash "$TREE_CHECK" "$WORK/phase1-ghost.md" --closed-world --repo-root "$WORK"

# A draft mid-write: one requirement, no acceptance scenarios yet.
cat > "$WORK/partial.md" <<'EOF'
# Retry uploads

## Requirements

FR-001  The importer resumes from the last checkpoint on restart.
        ← Settled Q1
EOF

expect "a partial draft passes closed-world" 0 "SPEC OK (closed-world)" -- \
  bash "$SPEC_CHECK" "$WORK/partial.md" --tree "$WORK/tree.md" --closed-world
expect "the same draft still fails the full gate" 1 "acceptance scenario" -- \
  bash "$SPEC_CHECK" "$WORK/partial.md" --tree "$WORK/tree.md"

sed 's/← Settled Q1/← Settled Q99/' "$WORK/partial.md" > "$WORK/partial-fake.md"
expect "a fabricated citation still fires in closed-world" 1 "fabricated citation" -- \
  bash "$SPEC_CHECK" "$WORK/partial-fake.md" --tree "$WORK/tree.md" --closed-world
sed 's/on restart\./quickly./' "$WORK/partial.md" > "$WORK/partial-adj.md"
expect "an unquantified adjective still fires in closed-world" 1 "unquantified adjective" -- \
  bash "$SPEC_CHECK" "$WORK/partial-adj.md" --tree "$WORK/tree.md" --closed-world

# An empty stub is the very first write of a draft.
printf '# Retry uploads\n\nBatch imports restart from zero.\n' > "$WORK/stub.md"
expect "an empty stub passes closed-world" 0 "SPEC OK (closed-world)" -- \
  bash "$SPEC_CHECK" "$WORK/stub.md" --tree "$WORK/tree.md" --closed-world

# A finding printed on a partial draft is still a finding.
printf '# Retry uploads\n\n## Requirements\n\n| FR-001 | resumes | ← Settled Q99 |\n' > "$WORK/table.md"
expect "an unreadable requirement does not end in SPEC OK" 1 "belongs to no identifier" -- \
  bash "$SPEC_CHECK" "$WORK/table.md" --tree "$WORK/tree.md" --closed-world

echo
echo "── the hook: silent on incomplete, loud on wrong ─────────────"

HOOK="$HERE/hook-validate.sh"
hookrun() { echo "{\"tool_input\":{\"file_path\":\"$1\"}}" | bash "$HOOK"; }

cp "$WORK/tree.md" "$WORK/docs/specs/tree.md"
expect "hook is silent on a complete record" 0 "" -- hookrun "$WORK/docs/specs/tree.md"
cp "$WORK/phase1.md" "$WORK/docs/specs/tree.md"
expect "hook is silent on a Phase 1 record" 0 "" -- hookrun "$WORK/docs/specs/tree.md"
cp "$WORK/phase1-bad.md" "$WORK/docs/specs/tree.md"
expect "hook fires on a round past its cap" 2 "past the declared cap" -- hookrun "$WORK/docs/specs/tree.md"

cp "$WORK/tree.md" "$WORK/docs/specs/tree.md"
cp "$WORK/partial.md" "$WORK/docs/specs/spec.draft.md"
expect "hook is silent on a partial draft" 0 "" -- hookrun "$WORK/docs/specs/spec.draft.md"
cp "$WORK/partial-fake.md" "$WORK/docs/specs/spec.draft.md"
expect "hook fires on a fabricated citation" 2 "fabricated citation" -- \
  hookrun "$WORK/docs/specs/spec.draft.md"
printf '# Retry uploads\n\n## Functional Requirements\n\nFR-001  The importer resumes.\n        ← Settled Q99\n' \
  > "$WORK/docs/specs/spec.draft.md"
expect "hook fires whatever the requirement heading is called" 2 "fabricated citation" -- \
  hookrun "$WORK/docs/specs/spec.draft.md"
expect "hook ignores an unrelated file" 0 "" -- hookrun "$WORK/AGENTS.md"

echo
echo "── check-tree.sh --doctor ────────────────────────────────────"

expect "healthy record needs no repair" 0 "Nothing structurally wrong" -- \
  bash "$TREE_CHECK" "$WORK/tree.md" --doctor

sed '/^## Sessions/,$d' "$WORK/tree.md" > "$WORK/nosessions.md"
expect "names the missing section" 1 "required section" -- \
  bash "$TREE_CHECK" "$WORK/nosessions.md" --doctor
expect "prints the heading to restore" 1 "── add ── Sessions" -- \
  bash "$TREE_CHECK" "$WORK/nosessions.md" --doctor
# The skeleton's body is an example about another feature. Printed as a repair,
# it becomes decisions nobody made in a record every tag resolves against.
sed '/^## Settled/,/^## Frontier/{/^## Frontier/!d;}' "$WORK/tree.md" > "$WORK/nosettled.md"
if bash "$TREE_CHECK" "$WORK/nosettled.md" --doctor | grep -q "Where retry state lives"; then
  echo "FAIL  the doctor offers the skeleton's example decisions as a repair"
  fail=$((fail+1))
else
  echo "ok    the doctor restores a heading, never the example's content"
  pass=$((pass+1))
fi
expect "offers the canonical coverage table" 1 "Problem & outcome" -- \
  bash "$TREE_CHECK" "$WORK/rename.md" --doctor

echo
echo "── generators ────────────────────────────────────────────────"

expect "traceability joins requirement to rationale" 0 "one source of truth" -- \
  bash "$HERE/make-traceability.sh" "$WORK/spec.md" --tree "$WORK/tree.md" --out -
expect "traceability lists deferred items" 0 "Deferred, and therefore untraced" -- \
  bash "$HERE/make-traceability.sh" "$WORK/spec.md" --tree "$WORK/tree.md" --out -
expect "traceability reports an unresolvable tag" 1 "Not traceable" -- \
  bash "$HERE/make-traceability.sh" "$WORK/fake-q.md" --tree "$WORK/tree.md" --out -
expect "generators refuse without the record" 2 "--tree is required" -- \
  bash "$HERE/make-traceability.sh" "$WORK/spec.md"

# An answer cited in second position is still cited. Reading only the first
# listed it under "answered but not traced" — a section the operator is told to
# read before reporting, so a false entry there costs attention.
sed -e 's/^FR-002  The importer retries.*$/FR-002  The importer retries a failed row at most 5 times over 24 hours./' \
    -e 's|← Settled Q2$|← Grounding fact 1, Settled Q2 (r1)|' \
    "$WORK/spec.md" > "$WORK/spec-second.md"
expect "a second-position source is traced" 0 "Q2 Attempt ceiling" -- \
  bash "$HERE/make-traceability.sh" "$WORK/spec-second.md" --tree "$WORK/tree.md" --out -
if bash "$HERE/make-traceability.sh" "$WORK/spec-second.md" --tree "$WORK/tree.md" --out - \
   | grep -q "Decided but cited nowhere"; then
  echo "FAIL  a second-position source is still reported as an unused answer"
  fail=$((fail+1))
else
  echo "ok    a second-position source is not reported as unused"
  pass=$((pass+1))
fi

# A scope boundary reaches the spec as an out-of-scope line, not as a
# requirement. Cited there, the decision is traced; cited nowhere, it is named.
sed 's|← Settled Q2$|← Grounding fact 2|' "$WORK/spec.md" > "$WORK/spec-noq2.md"
expect "a decision no line cites is named" 0 "Decided but cited nowhere" -- \
  bash "$HERE/make-traceability.sh" "$WORK/spec-noq2.md" --tree "$WORK/tree.md" --out -
sed 's|^- An external retry queue\. ← Strategy (chosen)$|- An external retry queue. ← Settled Q2|' \
  "$WORK/spec-noq2.md" > "$WORK/spec-scope-tag.md"
expect "a decision cited by an out-of-scope line is traced" 0 "Decisions cited outside the requirements" -- \
  bash "$HERE/make-traceability.sh" "$WORK/spec-scope-tag.md" --tree "$WORK/tree.md" --out -
if bash "$HERE/make-traceability.sh" "$WORK/spec-scope-tag.md" --tree "$WORK/tree.md" --out - \
   | grep -q "Decided but cited nowhere"; then
  echo "FAIL  a decision cited by an out-of-scope line is still reported as uncited"
  fail=$((fail+1))
else
  echo "ok    a decision cited by an out-of-scope line is not reported as uncited"
  pass=$((pass+1))
fi

# The template leaves two statements untagged on purpose, and the generator
# must not call either untraceable.
sed -e 's/^FR-003  Retry state is written to the existing checkpoint file\.$/FR-003  Retry state is written to the existing checkpoint file. (withdrawn)/' \
    -e '/← Grounding fact 1$/d' "$WORK/spec.md" > "$WORK/spec-withdrawn.md"
expect "a withdrawn requirement is not reported as untraceable" 0 "0 untraceable" -- \
  bash "$HERE/make-traceability.sh" "$WORK/spec-withdrawn.md" --tree "$WORK/tree.md" --out "$WORK/trace-w.md"

echo
echo "── make-packet.sh ────────────────────────────────────────────"

# A lens declared a blind spot caused by a hand-rolled sed range, not by
# anything in the spec. Phase 6 is the phase most sensitive to input shape and
# was the only one assembling its input by hand.
PACKET="$HERE/make-packet.sh"

expect "packet carries the statements with their tags" 0 "← Settled Q1" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
expect "packet carries the coverage table with Clear* intact" 0 "Clear\* (1 deferred)" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
# A tag alone says where a statement came from, not what the source says. The
# critic cannot open the record, so the cited text has to travel with the tag.
expect "packet carries the text of a cited decision" 0 "Settled Q2 Attempt ceiling\*\* → at most 5 attempts" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
expect "packet carries the text of a cited grounding fact" 0 "Grounding fact 1\*\* — Ingest state is a JSON checkpoint" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
expect "packet carries what the record holds and no statement cites" 0 "Grounding fact 2\*\* — Nearest analogous feature" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
printf '\n## Implementation constraints\n\n- Standard library only; no new dependency. ← Settled Q1\n' \
  | cat "$WORK/spec.md" - > "$WORK/spec-constraint.md"
expect "packet carries the user's implementation constraints" 0 "Standard library only" -- \
  bash "$PACKET" "$WORK/spec-constraint.md" --tree "$WORK/tree.md"
expect "packet carries the deferred list" 0 "Q12 Per-source overrides" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
expect "packet carries the principles verbatim" 0 "smallest reasonable change" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
expect "packet carries the scope boundary, not just its heading" 0 "An external retry queue" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
expect "packet names what a promoted ADR decided" 0 "Decision: Retry state lives" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
expect "packet inlines the rubric" 0 "anti-rubber-stamp" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
# A check the rubric asks for needs its input in the packet, or the critic
# reports a blind spot, or reports the check as passed.
expect "packet carries the opening paragraph" 0 "Batch imports restart from zero after a crash" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
expect "packet carries the user stories the P1 check reads" 0 "P1 · Resume an interrupted import" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
printf '\n## Principle deviations\n\n| "no backward-compat shims" | the old checkpoint has to stay readable | a one-off migration |\n' \
  | cat "$WORK/spec.md" - > "$WORK/spec-deviation.md"
expect "packet carries a declared principle deviation" 0 "the old checkpoint has to stay readable" -- \
  bash "$PACKET" "$WORK/spec-deviation.md" --tree "$WORK/tree.md"
printf '# Glossary\n\n## Batch\n\nThe rows read from one source file in one run.\n\n- Decided: Q1 (r0)\n' \
  > "$WORK/docs/specs/GLOSSARY.md"
expect "packet carries a glossary term with its definition" 0 "\*\*Batch\*\* — The rows read from one source file" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
expect "packet says when a listed term has no glossary entry" 0 "\*\*Checkpoint\*\* — _the record lists this term" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
# A requirement that runs over indented lines reaches the critic whole.
smut multiline.md 's/^FR-002  The importer retries a failed row at most 5 times over 24 hours\.$/FR-002  The importer retries a failed row:\
          at most 5 times, spread over 24 hours./'
expect "a requirement written over several lines is one statement" 0 "SPEC OK" -- \
  bash "$SPEC_CHECK" "$WORK/multiline.md" --tree "$WORK/tree.md"
expect "and the packet carries all of it" 0 "retries a failed row: at most 5 times, spread over 24 hours" -- \
  bash "$PACKET" "$WORK/multiline.md" --tree "$WORK/tree.md"
# Where the ADR's decision is read from must not depend on the caller's cwd.
expect "packet finds the ADR from any working directory" 0 "Decision: Retry state lives" -- \
  env -C / bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md"
expect "packet is written to a file when asked" 0 "wrote $WORK/.work/critic-packet.md" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md" --out "$WORK/.work/critic-packet.md"
if [ "$(cat "$WORK/.work/.gitignore" 2>/dev/null)" = "*" ]; then
  echo "ok    the working directory keeps itself out of version control"; pass=$((pass+1))
else
  echo "FAIL  .work/ was created without its ignore file"; fail=$((fail+1))
fi

# An empty section must say it is empty. A lens cannot tell a section with
# nothing in it from a section the extraction dropped, and it reports the
# second as a blind spot — which is exactly what happened.
sed '/^## Out of scope$/,$d' "$WORK/spec.md" > "$WORK/spec-noscope.md"
expect "an absent section says so rather than arriving blank" 0 "states no scope boundary" -- \
  bash "$PACKET" "$WORK/spec-noscope.md" --tree "$WORK/tree.md"

expect "packet refuses without the record" 2 "--tree is required" -- \
  bash "$PACKET" "$WORK/spec.md"

echo
echo "── spec-diff.sh ──────────────────────────────────────────────"

DIFF="$HERE/spec-diff.sh"
sed -e 's/at most 5 times over 24 hours/at most 10 times over 48 hours/' \
    -e 's/^FR-001  The importer resumes from the last checkpoint on restart\./FR-001  The importer resumes from the last checkpoint on restart. (withdrawn)/' \
    "$WORK/spec.md" > "$WORK/spec-amended.md"

expect "reports a reword under a stable id" 0 "Reworded under a stable identifier" -- \
  bash "$DIFF" "$WORK/spec.md" "$WORK/spec-amended.md"
expect "shows the changed words, not the whole line" 0 "\*\*10\*\*" -- \
  bash "$DIFF" "$WORK/spec.md" "$WORK/spec-amended.md"
expect "counts a marked withdrawal as correct" 0 "Withdrawn, correctly" -- \
  bash "$DIFF" "$WORK/spec.md" "$WORK/spec-amended.md"

sed '/^SC-002/,+1d' "$WORK/spec.md" > "$WORK/spec-vanished.md"
expect "a vanished identifier fails" 1 "Vanished" -- \
  bash "$DIFF" "$WORK/spec.md" "$WORK/spec-vanished.md"

expect "identical specs report no change" 0 "Nothing changed" -- \
  bash "$DIFF" "$WORK/spec.md" "$WORK/spec.md"

# A requirement that gains a second citation has been retagged. Comparing only
# the first source called that "unchanged".
sed 's|← Settled Q1$|← Settled Q1 (r1), Grounding fact 2|' "$WORK/spec.md" > "$WORK/spec-retag.md"
expect "a second citation counts as a retag" 0 "Same text, different source" -- \
  bash "$DIFF" "$WORK/spec.md" "$WORK/spec-retag.md"
expect "the retag names both sources" 0 "Settled Q1, Grounding fact 2" -- \
  bash "$DIFF" "$WORK/spec.md" "$WORK/spec-retag.md"
expect "missing file is not a pass" 2 "no such file" -- \
  bash "$DIFF" "$WORK/spec.md" "$WORK/nope.md"

echo
echo "── check-critique.sh ─────────────────────────────────────────"

cat > "$WORK/c1.txt" <<'EOF'
VERDICT: fix-first
CONFIDENCE: high — every check ran against text in the packet
BLIND SPOT: cannot confirm the file format without reading source

BLOCKING
- B1 [completeness] SC-001 — no number that would prove it
  QUOTE: "resumes within 2 seconds"
  WHY: no settled answer gives that budget
  FIX: cite the settled answer, or mark it [NEEDS CLARIFICATION]
- B2 [consistency] FR-002 — contradicts the chosen strategy
  QUOTE: "at most 5 times over 24 hours"
  WHY: strategy B sweeps on a timer
  FIX: state the interaction with the sweep interval
EOF
cat > "$WORK/c2.txt" <<'EOF'
VERDICT: fix-first
CONFIDENCE: moderate — one check depended on a summarised section
BLIND SPOT: same as pass 1

RECONCILIATION
- B1 fixed
- B2 not fixed — the sweep interval is still unstated
EOF

expect "a well-formed first pass validates" 0 "CRITIQUE OK" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" --single
expect "reconciliation accounts for every id" 0 "accounts for all 2" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" "$WORK/c2.txt"
expect "unresolved findings are reported, not hidden" 0 "ship unresolved" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" "$WORK/c2.txt"

grep -v 'B2' "$WORK/c2.txt" > "$WORK/c2-dropped.txt"
expect "a dropped finding is caught" 1 "does not account for B2" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" "$WORK/c2-dropped.txt"

grep -v 'FIX:' "$WORK/c1.txt" > "$WORK/c1-nofix.txt"
expect "a finding with no FIX is caught" 1 "no FIX:" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1-nofix.txt" --single

cat > "$WORK/c-stamp.txt" <<'EOF'
VERDICT: ship
CONFIDENCE: high — everything checked out
BLIND SPOT: none
EOF
expect "a rubber stamp is caught" 1 "CHECKED AND SOUND" -- \
  bash "$HERE/check-critique.sh" "$WORK/c-stamp.txt" --single
printf '\nCHECKED AND SOUND\n- Looks good.\n- Great work.\n' | cat "$WORK/c-stamp.txt" - > "$WORK/c-stamp2.txt"
expect "a sound section that names nothing it checked is caught" 1 "0 item(s) that name what was checked" -- \
  bash "$HERE/check-critique.sh" "$WORK/c-stamp2.txt" --single
cat > "$WORK/c-sound.txt" <<'EOF'
VERDICT: ship
CONFIDENCE: high — every check ran against text in the packet
BLIND SPOT: none

CHECKED AND SOUND
- FR-002 "at most 5 times over 24 hours" says what Settled Q2 says, "at most 5 attempts spread over 24h"
- SC-001 names its number, 2 seconds
EOF
expect "a clean pass that names what it checked validates" 0 "anti-rubber-stamp satisfied" -- \
  bash "$HERE/check-critique.sh" "$WORK/c-sound.txt" --single --packet "$WORK/.work/critic-packet.md"

# --- a quote is text the critic was shown ---------------------------------
# A finding about words that are not in the draft sends the orchestrator to
# edit a spec that was right.
expect "quotes found in the packet pass" 0 "quote(s) compared against the packet" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" --single --packet "$WORK/.work/critic-packet.md"
sed 's/QUOTE: "at most 5 times over 24 hours"/QUOTE: "retries are attempted without any upper bound"/' \
  "$WORK/c1.txt" > "$WORK/c1-invented.txt"
expect "a quote the packet does not contain is caught" 1 "B2 quotes text the packet does not contain" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1-invented.txt" --single --packet "$WORK/.work/critic-packet.md"
sed 's/QUOTE: "at most 5 times over 24 hours"/QUOTE: "The importer retries … at most 5 times over 24 hours"/' \
  "$WORK/c1.txt" > "$WORK/c1-elided.txt"
expect "an elided quote is compared piece by piece" 0 "CRITIQUE OK" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1-elided.txt" --single --packet "$WORK/.work/critic-packet.md"
expect "a packet that cannot be read is not a pass" 2 "packet not found" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" --single --packet "$WORK/nope.md"
sed 's/^  QUOTE: "resumes within 2 seconds"$/  QUOTE:/' "$WORK/c1.txt" > "$WORK/c1-emptyquote.txt"
expect "an empty QUOTE is caught" 1 "B1 carries no QUOTE" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1-emptyquote.txt" --single
sed 's/^VERDICT: fix-first$/VERDICT: ship/' "$WORK/c1.txt" > "$WORK/c1-ship.txt"
expect "ship with blocking findings is caught" 1 "VERDICT is ship with 2 blocking" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1-ship.txt" --single
cat > "$WORK/c-template.txt" <<'EOF'
VERDICT: ship | fix-first
CONFIDENCE: high | moderate | low — <one sentence saying why>
BLIND SPOT: <what this pass could not assess>

BLOCKING
- B1 [completeness] FR-004 — <finding>
  QUOTE: "<verbatim from the draft>"
  WHY: <one sentence>
  FIX: <the smallest edit that would clear this>
EOF
expect "the unfilled output template is caught" 1 "still carries the output template's placeholders" -- \
  bash "$HERE/check-critique.sh" "$WORK/c-template.txt" --single

# --- a disposition says fixed, or it does not ------------------------------
sed 's/^- B2 not fixed — .*$/- B2 could not be verified as fixed/' "$WORK/c2.txt" > "$WORK/c2-hedged.txt"
expect "a hedged disposition accounts for nothing" 1 "does not account for B2" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" "$WORK/c2-hedged.txt"
sed 's/^- B2 not fixed — .*$/B1 was fixed. Unlike B2, nothing new was found./' "$WORK/c2.txt" > "$WORK/c2-prose.txt"
expect "a finding mentioned in passing is not accounted for" 1 "does not account for B2" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" "$WORK/c2-prose.txt"
cat > "$WORK/c2-relisted.txt" <<'EOF'
VERDICT: fix-first
CONFIDENCE: high — every check ran against text in the packet
BLIND SPOT: none

RECONCILIATION
- B1 fixed

BLOCKING
- B2 [consistency] FR-002 — still contradicts the chosen strategy
  QUOTE: "at most 5 times over 24 hours"
  WHY: strategy B sweeps on a timer
  FIX: state the interaction with the sweep interval
EOF
expect "a finding listed as blocking again ships unresolved" 0 "1 finding(s) ship unresolved: B2" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" "$WORK/c2-relisted.txt"
sed 's/^VERDICT: fix-first$/VERDICT: ship/' "$WORK/c2.txt" > "$WORK/c2-ship.txt"
expect "a second pass that ships with a finding open is caught" 1 "VERDICT is ship with 1 finding(s) still open" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" "$WORK/c2-ship.txt"
# The second pass runs in fresh context, so the packet tells it what the first found.
expect "the second packet carries the first pass's blocking findings" 0 "contradicts the chosen strategy" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md" --pass1 "$WORK/c1.txt"
expect "and asks for a disposition per finding" 0 "RECONCILIATION" -- \
  bash "$PACKET" "$WORK/spec.md" --tree "$WORK/tree.md" --pass1 "$WORK/c1.txt"

echo
echo "── publish-spec.sh ───────────────────────────────────────────"

# The spec that ships is the draft that was checked: renamed, never retyped.
PUBLISH="$HERE/publish-spec.sh"
newdir() { rm -rf "$WORK/pub"; mkdir -p "$WORK/pub"; cp "$WORK/tree.md" "$WORK/pub/tree.md"; }

newdir; cp "$WORK/spec.md" "$WORK/pub/spec.draft.md"
expect "a clean draft is published" 0 "PUBLISHED" -- bash "$PUBLISH" "$WORK/pub"
if cmp -s "$WORK/spec.md" "$WORK/pub/spec.md" && [ ! -e "$WORK/pub/spec.draft.md" ] \
   && [ -s "$WORK/pub/traceability.md" ]; then
  echo "ok    the published spec is the draft byte for byte, and the draft is gone"
  pass=$((pass+1))
else
  echo "FAIL  publishing left the directory in the wrong state"
  ls "$WORK/pub" | sed 's/^/      | /'
  fail=$((fail+1))
fi
expect "nothing left to publish is not a pass" 2 "already there" -- bash "$PUBLISH" "$WORK/pub"

newdir; cp "$WORK/fake-q.md" "$WORK/pub/spec.draft.md"
expect "a draft with findings is not published" 1 "NOT PUBLISHED" -- bash "$PUBLISH" "$WORK/pub"
if [ -e "$WORK/pub/spec.draft.md" ] && [ ! -e "$WORK/pub/spec.md" ]; then
  echo "ok    a refused publish touches nothing"; pass=$((pass+1))
else
  echo "FAIL  a refused publish changed the directory"; fail=$((fail+1))
fi

# An amendment is checked against the spec it replaces, and says what changed.
newdir; cp "$WORK/spec.md" "$WORK/pub/spec.md"; cp "$WORK/reworded.md" "$WORK/pub/spec.draft.md"
expect "an amendment that rewords is refused until acknowledged" 1 "text changed under existing identifiers" -- \
  bash "$PUBLISH" "$WORK/pub"
expect "an acknowledged amendment prints what changed" 0 "Reworded under a stable identifier" -- \
  bash "$PUBLISH" "$WORK/pub" --allow-reword
newdir; cp "$WORK/spec.md" "$WORK/pub/spec.md"; cp "$WORK/renumbered.md" "$WORK/pub/spec.draft.md"
expect "a restart replaces the old spec without comparing" 0 "PUBLISHED" -- \
  bash "$PUBLISH" "$WORK/pub" --fresh

# --- severity is the section, not the id prefix ---------------------------
# Three parallel lenses MUST use distinct id prefixes or their ids collide, and
# every scheme that disambiguated them was invisible to a `B\d+` parser: two
# real blocking findings read as zero, and pass 2 then "accounted for all 0".
sed -e 's/- B1 /- BC1 /' -e 's/- B2 /- BC1f /' "$WORK/c1.txt" > "$WORK/c1-lens.txt"
expect "per-lens id prefixes are seen" 0 "2 blocking" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1-lens.txt" --single

sed -e 's/- B1 fixed/- BC1 fixed/' -e 's/- B2 not fixed/- BC1f not fixed/' \
  "$WORK/c2.txt" > "$WORK/c2-lens.txt"
expect "per-lens ids reconcile across passes" 0 "accounts for all 2" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1-lens.txt" "$WORK/c2-lens.txt"
grep -v 'BC1f' "$WORK/c2-lens.txt" > "$WORK/c2-lens-dropped.txt"
expect "a dropped per-lens finding is still caught" 1 "does not account for BC1f" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1-lens.txt" "$WORK/c2-lens-dropped.txt"

# A reconciliation is dispositions, not findings — counting them as
# unclassified would report a problem in every well-formed second pass.
expect "a reconciliation is not read as unclassified findings" 0 "CRITIQUE OK" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1.txt" "$WORK/c2.txt"

# A finding under no severity heading cannot be classified, and one this script
# cannot see ships as resolved.
sed '/^BLOCKING$/d' "$WORK/c1.txt" > "$WORK/c1-nosection.txt"
expect "findings under no severity heading are caught" 1 "no BLOCKING or ADVISORY heading" -- \
  bash "$HERE/check-critique.sh" "$WORK/c1-nosection.txt" --single

echo
echo "── check-plan.sh ─────────────────────────────────────────────"

PLAN_CHECK="$HERE/check-plan.sh"
PROGRESS="$HERE/make-progress.sh"

# The plan fixture is the skeleton the plugin documents in plan-template.md.
# Testing against the shipped example is what stops the format and its checker
# drifting apart — the same stance taken with the design record above.
# A real plan lives in a repository, and the hook has no --repo-root to pass —
# it discovers this the same way check-plan.sh does.
mkdir -p "$WORK/.git" "$WORK/plan/tasks" "$WORK/cmd/ingest"
: > "$WORK/cmd/ingest/replay.go"

python3 - "$REFS/plan-template.md" "$WORK/plan/plan.md" "$WORK/plan/tasks/T01.md" <<'PY'
import re,sys
src=open(sys.argv[1]).read()
for fence,dest in (('plan-skeleton',sys.argv[2]),('task-skeleton',sys.argv[3])):
    m=re.search(rf'```{fence}\n(.*?)\n```', src, re.S)
    if not m:
        sys.stderr.write(f"no ```{fence} block in plan-template.md\n"); sys.exit(2)
    open(dest,'w').write(m.group(1)+"\n")
PY
[ -s "$WORK/plan/plan.md" ] || { echo "FAIL  could not extract the plan skeleton"; exit 2; }
[ -s "$WORK/plan/tasks/T01.md" ] || { echo "FAIL  could not extract the task skeleton"; exit 2; }

# T02-T04 complete the graph the shipped plan skeleton declares. T01 is the
# format under test; these three exist so the backwards coverage check has a
# whole plan to run against.
cat > "$WORK/plan/tasks/T02.md" <<'EOF'
# T02 — Resume from the checkpoint on start

Covers: FR-001, SC-001
Depends on: T01
Milestone: M1
Status: Planned
Touches: cmd/ingest/replay.go

## Goal

An interrupted import continues from the row the checkpoint names.

## Why now

Completes M1: with T01's state on disk, this is the behaviour a user sees.

## Action items

- [ ] Read the checkpoint on startup instead of starting at row 0
- [ ] Skip rows the checkpoint marks as ingested

## Done when

- FR-001  Given a checkpoint exists, when the importer starts, then it resumes from it.
- SC-001  An import interrupted at row 10000 resumes within 2 seconds.

## Notes

## Execution summary
EOF

cat > "$WORK/plan/tasks/T03.md" <<'EOF'
# T03 — Enforce the attempt ceiling

Covers: FR-002
Depends on: T01
Milestone: M2
Status: Planned
Touches: cmd/ingest/state.go

## Goal

A row stops being retried once it has been attempted 5 times.

## Why now

First task of M2, and the reject file in T04 has nothing to write without it.

## Action items

- [ ] Compare the attempt count against the ceiling before scheduling a retry

## Done when

- FR-002  Given 5 attempts have been made, when a 6th is due, then the row is rejected.

## Notes

## Execution summary
EOF

cat > "$WORK/plan/tasks/T04.md" <<'EOF'
# T04 — Write rejected rows to the reject file

Covers: SC-002
Depends on: T03
Milestone: M2
Status: Planned
Touches: cmd/ingest/replay.go

## Goal

A row that exhausted its attempts appears in the reject file with its line number.

## Why now

Completes M2 — the operator-visible half of the ceiling.

## Action items

- [ ] Append the row and its line number to the reject file on exhaustion

## Done when

- SC-002  A row that has failed 5 times appears in the reject file with its line number.

## Notes

## Execution summary
EOF

expect "make-progress.sh generates the task graph" 0 "4 task" -- \
  bash "$PROGRESS" "$WORK/plan"

expect "shipped plan skeleton passes" 0 "PLAN OK" -- \
  bash "$PLAN_CHECK" "$WORK/plan" --spec "$WORK/spec.md" --repo-root "$WORK"

expect "refuses to run without the spec" 2 "--spec is required" -- \
  bash "$PLAN_CHECK" "$WORK/plan"

expect "unreadable spec is not a pass" 2 "not found" -- \
  bash "$PLAN_CHECK" "$WORK/plan" --spec "$WORK/nope.md"

# pmut <name> <sed-expr> <file-within-plan> — one mutation, on its own copy.
pmut() {
  rm -rf "$WORK/p-$1"; cp -R "$WORK/plan" "$WORK/p-$1"
  sed -i.bak "$2" "$WORK/p-$1/$3" && rm -f "$WORK/p-$1/$3.bak"
}
pcheck() { bash "$PLAN_CHECK" "$WORK/p-$1" --spec "${2:-$WORK/spec.md}" --repo-root "$WORK"; }

pmut fake-cov 's/^Covers: FR-003$/Covers: FR-042/' tasks/T01.md
expect "fabricated Covers identifier is caught" 1 "fabricated citation" -- pcheck fake-cov

pmut orphan 's/^Covers: SC-002$/Covers: FR-003/' tasks/T04.md
expect "requirement no task covers is caught" 1 "no task covers" -- pcheck orphan

pmut restated 's/^- FR-002  Given 5 attempts.*$/- FR-002  Attempts are capped correctly./' tasks/T03.md
expect "restated done-condition is caught" 1 "not in the spec" -- pcheck restated

pmut ghostdep 's/^Depends on: T01$/Depends on: T09/' tasks/T02.md
expect "dependency on a task with no file is caught" 1 "has no task file" -- pcheck ghostdep

pmut cycle 's/^Depends on: —$/Depends on: T04/' tasks/T01.md
expect "dependency cycle is caught" 1 "dependency cycle" -- pcheck cycle

pmut ghostpath 's|^Touches: cmd/ingest/state.go:31$|Touches: cmd/ingest/invented.go|' tasks/T01.md
expect "Touches path that does not exist is caught" 1 "does not exist" -- pcheck ghostpath

pmut badstatus 's/^Status: Planned$/Status: Nearly/' tasks/T01.md
expect "illegal task status is caught" 1 "is not one of" -- pcheck badstatus

pmut adjective 's/^- \[ \] Write it whenever a retry is scheduled$/- [ ] Write it quickly whenever a retry is scheduled/' tasks/T01.md
expect "unquantified adjective in an action item is caught" 1 "unquantified adjective" -- pcheck adjective

pmut blockedbare 's/^Status: Planned$/Status: Blocked/' tasks/T03.md
expect "Blocked task with no Blocked by is caught" 1 "Blocked by" -- pcheck blockedbare

pmut nocost 's/ — \*\*Reversing:\*\* a migration of every checkpoint written since M1\./\./' plan.md
expect "plan assumption with no reversal cost is caught" 1 "reversal cost" -- pcheck nocost

pmut untagged 's/^Covers: FR-003$/Covers: —/' tasks/T01.md
expect "task covering nothing and unlabelled is caught" 1 "Enabling work" -- pcheck untagged

pmut noreason 's|^- _nothing — every requirement and criterion is covered by a task_$|- FR-003|' plan.md
expect "not-planned entry with no reason is caught" 1 "no reason" -- pcheck noreason

pmut ghostseam 's|^- cmd/ingest/replay.go |- cmd/ingest/invented.go |' plan.md
expect "seam path that does not exist is caught" 1 "does not exist" -- pcheck ghostseam

pmut ghostms 's/^Milestone: M2$/Milestone: M9/' tasks/T03.md
expect "task in an undeclared milestone is caught" 1 "does not declare" -- pcheck ghostms

# The table is generated. A hand-edited status is a second copy, and a second
# copy is what falls behind — the failure make-progress.sh exists to prevent.
pmut stale 's/^Status: Planned$/Status: Done/' tasks/T02.md
expect "task graph that has fallen behind its task files is caught" 1 "fallen behind" -- pcheck stale
expect "make-progress.sh --check reports the same staleness" 1 "stale task graph" -- \
  bash "$PROGRESS" "$WORK/p-stale" --check
expect "make-progress.sh brings it current" 0 "wrote" -- bash "$PROGRESS" "$WORK/p-stale"
expect "regenerated plan passes" 0 "PLAN OK" -- pcheck stale

# A plan that adds a file names a path that does not exist yet. Making that
# sayable keeps the existence check strict everywhere else, where it catches an
# invented seam.
pmut newfile 's|^Touches: cmd/ingest/state.go:31$|Touches: cmd/ingest/retry.go (new)|' tasks/T01.md
expect "a path marked (new) is not required to exist" 0 "PLAN OK" -- pcheck newfile
pmut newfile-bare 's|^Touches: cmd/ingest/state.go:31$|Touches: cmd/ingest/retry.go|' tasks/T01.md
expect "the same path unmarked is still caught" 1 "does not exist" -- pcheck newfile-bare

# A row for a task file not yet written is an assertion about absence, so it
# belongs at the gate. A hook firing here would punish drafting plan.md first.
rm -rf "$WORK/p-mapfirst"; mkdir -p "$WORK/p-mapfirst/tasks"
cp "$WORK/plan/plan.md" "$WORK/p-mapfirst/plan.md"
cp "$WORK/plan/tasks/T01.md" "$WORK/p-mapfirst/tasks/T01.md"
expect "closed-world allows a map drafted before its tasks" 0 "PLAN OK" -- \
  bash "$PLAN_CHECK" "$WORK/p-mapfirst" --spec "$WORK/spec.md" --repo-root "$WORK" --closed-world
expect "the gate still catches the tasks that were never written" 1 "has no task file" -- \
  bash "$PLAN_CHECK" "$WORK/p-mapfirst" --spec "$WORK/spec.md" --repo-root "$WORK"

# A traceback exits 1, exactly as a finding list does. Without a trailer check
# a parser bug reads as "N problems found" — a checker that never reached a
# verdict reporting one.
sed 's|^spec = Spec.load(specpath)$|spec = Spec.load(specpath); raise RuntimeError("boom")|' \
  "$PLAN_CHECK" > "$WORK/check-plan-crash.sh"
expect "a crashed checker does not read as findings" 2 "did not reach a verdict" -- \
  bash "$WORK/check-plan-crash.sh" "$WORK/plan" --spec "$WORK/spec.md" --repo-root "$WORK"

# R20: a marker the spec carries and the plan drops is a question answered by
# stealth, which is the whole reason deferral is bounded in the interview.
sed 's|deferred to post-launch\]|deferred until the second release]|' \
    "$WORK/spec.md" > "$WORK/spec-marked.md"
expect "open marker the plan drops is caught" 1 "open question the plan does not" -- \
  pcheck stale "$WORK/spec-marked.md"

# Closed-world: a plan mid-write is legitimately incomplete, and a checker that
# calls that broken teaches evasion rather than compliance.
rm -rf "$WORK/p-partial"; mkdir -p "$WORK/p-partial/tasks"
cp "$WORK/plan/tasks/T01.md" "$WORK/p-partial/tasks/T01.md"
expect "closed-world is silent on a plan with no plan.md yet" 0 "PLAN OK" -- \
  bash "$PLAN_CHECK" "$WORK/p-partial" --spec "$WORK/spec.md" --repo-root "$WORK" --closed-world
expect "open-world fails on the same partial plan" 1 "no plan.md" -- \
  bash "$PLAN_CHECK" "$WORK/p-partial" --spec "$WORK/spec.md" --repo-root "$WORK"

sed -i.bak 's/^Covers: FR-003$/Covers: FR-042/' "$WORK/p-partial/tasks/T01.md"
rm -f "$WORK/p-partial/tasks/T01.md.bak"
expect "closed-world still fires on a fabricated Covers tag" 1 "fabricated citation" -- \
  bash "$PLAN_CHECK" "$WORK/p-partial" --spec "$WORK/spec.md" --repo-root "$WORK" --closed-world

# --- the hook, on plan files ----------------------------------------------
mkdir -p "$WORK/docs/specs/plan/tasks"
cp "$WORK/spec.md" "$WORK/docs/specs/spec.md"
cp "$WORK/plan/plan.md" "$WORK/docs/specs/plan/plan.md"
cp "$WORK"/plan/tasks/T0*.md "$WORK/docs/specs/plan/tasks/"
expect "hook is silent on a complete plan" 0 "" -- hookrun "$WORK/docs/specs/plan/plan.md"
expect "hook is silent on a valid task file" 0 "" -- hookrun "$WORK/docs/specs/plan/tasks/T01.md"
sed -i.bak 's/^Covers: FR-003$/Covers: FR-042/' "$WORK/docs/specs/plan/tasks/T01.md"
rm -f "$WORK/docs/specs/plan/tasks/T01.md.bak"
expect "hook fires on a fabricated Covers tag" 2 "fabricated citation" -- \
  hookrun "$WORK/docs/specs/plan/tasks/T01.md"

echo
echo "── make-plan-packet.sh ───────────────────────────────────────"

PPACKET="$HERE/make-plan-packet.sh"
ppacket() { bash "$PPACKET" "${1:-$WORK/plan}" --spec "$WORK/spec.md" --tree "$WORK/tree.md" "${@:2}"; }

expect "packet carries what the spec asked for" 0 "FR-001  The importer resumes" -- ppacket
expect "packet carries the priorities the milestones rest on" 0 "P1 · Resume an interrupted import" -- ppacket
expect "packet carries each task with what it covers" 0 "Covers: FR-003" -- ppacket
expect "packet carries the quoted done-conditions" 0 "Given a retry is scheduled" -- ppacket
expect "packet carries the plan assumptions with their cost" 0 "Reversing" -- ppacket
expect "packet carries the principles verbatim" 0 "smallest reasonable change" -- ppacket
expect "packet carries the chosen strategy the ordering assumes" 0 "sweep the checkpoint" -- ppacket
expect "packet inlines the rubric" 0 "anti-rubber-stamp" -- ppacket

# An empty section must say it is empty, and this one must say *why* an empty
# one is suspicious: the spec names no type or library by design, so a plan with
# no assumptions has invisible ones rather than none.
rm -rf "$WORK/p-noasm"; cp -R "$WORK/plan" "$WORK/p-noasm"
sed -i.bak 's|^- The attempt counter is a field.*$|- _none_|; /^  sidecar file\. \*\*Reversing:\*\*/d' \
  "$WORK/p-noasm/plan.md" && rm -f "$WORK/p-noasm/plan.md.bak"
expect "an empty assumptions section says why that is suspicious" 0 "invisible rather than absent" -- \
  ppacket "$WORK/p-noasm"

# Three parallel lenses all numbering findings B1 cannot be reconciled per id.
expect "a lens packet assigns that lens its own id prefix" 0 "\`BH1\`" -- \
  ppacket "$WORK/plan" --lens honesty
if ppacket "$WORK/plan" --lens honesty | grep -q "Lens 1 — Coverage"; then
  echo "FAIL  a lens packet carries another lens's rubric — duplicated judgement wastes the pass"
  fail=$((fail+1))
else
  echo "ok    a lens packet carries only its own lens"
  pass=$((pass+1))
fi

expect "refuses to build a packet without the spec" 2 "--spec is required" -- \
  bash "$PPACKET" "$WORK/plan" --tree "$WORK/tree.md"
expect "refuses to build a packet without the record" 2 "--tree is required" -- \
  bash "$PPACKET" "$WORK/plan" --spec "$WORK/spec.md"

echo
echo "── one parser for the record ────────────────────────────────"

# Every tool that reads tree.md reads it through record.py. A private tag parser
# is how the same first-match-only bug shipped in two scripts at once.
if grep -q 'from record import' "$HERE/check-spec.sh" \
   && grep -q 'from record import' "$HERE/check-tree.sh" \
   && grep -q 'from record import' "$HERE/make-traceability.sh" \
   && grep -q 'from record import' "$HERE/check-plan.sh" \
   && grep -q 'from record import' "$HERE/make-plan-packet.sh" \
   && grep -q 'from record import' "$HERE/make-progress.sh"; then
  echo "ok    every checker parses the record and the plan through lib/record.py"
  pass=$((pass+1))
else
  echo "FAIL  a checker has grown its own copy of the record parser"
  fail=$((fail+1))
fi

echo
echo "── skill frontmatter ─────────────────────────────────────────"

# Malformed frontmatter loads the skill with EMPTY metadata rather than failing,
# so a broken description is invisible until nobody can find the skill.
python3 "$HERE/lib/check_frontmatter.py" "$HERE/../skills"
case $? in
  0) pass=$((pass+1)) ;;
  3) skipped=$((skipped+1)) ;;
  *) fail=$((fail+1)) ;;
esac

echo
echo "── scripts a skill names are scripts it may run ──────────────"

# A skill that instructs `bash .../check-tree.sh` without granting it stops
# mid-run for a permission prompt. The grant and the instruction are two lists
# that must not drift.
grant_drift() {
  python3 - "$HERE/../skills" <<'PY'
import re, sys, os, glob
bad = 0
for path in sorted(glob.glob(os.path.join(sys.argv[1], '*', 'SKILL.md'))):
    name = os.path.basename(os.path.dirname(path))
    text = open(path).read()
    fm = text.split('---', 2)[1] if text.startswith('---') else ''
    granted = set(re.findall(r'Bash\(bash \$\{CLAUDE_PLUGIN_ROOT\}/scripts/([\w.-]+\.sh)', fm))
    body = text.split('---', 2)[2] if text.startswith('---') else text
    used = set(re.findall(r'(?:\$\{CLAUDE_PLUGIN_ROOT\}|<plugin-root>)/scripts/([\w.-]+\.sh)', body))
    missing = sorted(used - granted)
    unused = sorted(granted - used)
    if missing:
        print(f"FAIL  {name}: names {', '.join(missing)} but does not grant it in allowed-tools")
        bad += 1
    if unused:
        print(f"FAIL  {name}: grants {', '.join(unused)} but never names it — "
              f"a permission no instruction can reach")
        print(f"      expected: a row in the skill's Scripts table, or drop the grant")
        bad += 1
    if not missing and not unused:
        print(f"ok    {name}: grants exactly the {len(used)} script(s) it names")
sys.exit(1 if bad else 0)
PY
}
if grant_drift; then pass=$((pass+1)); else fail=$((fail+1)); fi

echo
echo "── rule-table drift ──────────────────────────────────────────"

# Each skill reproduces, verbatim, the rules its stage can act on, so one number
# means one rule everywhere. Two things can go wrong with copies: a row drifts
# from rules.md, or a rule ends up carried by no skill and so reaches nobody.
rule_drift() {
  python3 - "$REFS/rules.md" "$HERE/../skills" <<'PY'
import re,sys,os,glob
canon={}
for m in re.finditer(r'^\| \*\*(R\d+)\*\* \| (.*?) \|\s*$', open(sys.argv[1]).read(), re.M):
    canon[m.group(1)]=m.group(2)
if not canon:
    print("FAIL  rules.md defines no rule rows"); sys.exit(1)
bad=0
carried=set()
for path in sorted(glob.glob(os.path.join(sys.argv[2],'*','SKILL.md'))):
    name=os.path.basename(os.path.dirname(path))
    got={m.group(1):m.group(2) for m in
         re.finditer(r'^\| \*\*(R\d+)\*\* \| (.*?) \|\s*$', open(path).read(), re.M)}
    if not got:
        print(f"FAIL  {name}: no rule table found"); bad+=1; continue
    drifted=0
    for rid,text in sorted(got.items(), key=lambda kv:int(kv[0][1:])):
        if rid not in canon:
            print(f"FAIL  {name}: {rid} is not in rules.md"); bad+=1; drifted+=1
        elif text!=canon[rid]:
            print(f"FAIL  {name}: {rid} has drifted from rules.md")
            print(f"      canonical: {canon[rid][:72]}…")
            print(f"      in skill:  {text[:72]}…")
            bad+=1; drifted+=1
    carried|=set(got)
    if not drifted:
        print(f"ok    {name}: its {len(got)} rules are byte-identical to rules.md")
orphans=sorted(set(canon)-carried, key=lambda r:int(r[1:]))
if orphans:
    print(f"FAIL  no skill carries {', '.join(orphans)} — a rule in rules.md that reaches nobody")
    bad+=1
else:
    print(f"ok    all {len(canon)} rules in rules.md are carried by a skill")
sys.exit(1 if bad else 0)
PY
}
if rule_drift; then pass=$((pass+1)); else fail=$((fail+1)); fi

echo
echo "─────────────────────────────────────────────────────────────"
if [ "$fail" -eq 0 ] && [ "$skipped" -eq 0 ]; then
  echo "ALL $pass CHECKS BEHAVE AS DOCUMENTED"
  exit 0
fi
if [ "$fail" -eq 0 ]; then
  echo "$pass checks behave as documented — $skipped group(s) did not run, see the skip line(s) above"
  exit 0
fi
echo "$fail of $((pass+fail)) assertions failed"
exit 1
