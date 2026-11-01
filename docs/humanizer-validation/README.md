# Humanizer 2.0.0 update readiness

**2.0.0 is prepared as an update candidate.** Both host manifests specify `2.0.0`, and the catalogs resolve to `plugins/humanizer/`. The [plugin README](../../plugins/humanizer/README.md#200-update-summary) summarizes the update and active-run compatibility. Offline checks cover the local workflow and packaging. They do not establish natural Russian prose, semantic equivalence or reliable model judgments. These working-tree changes have not been installed or promoted by this work.

## Verification

The [current offline check record](checks.json) lists exact commands and results. It covers source/candidate retention, protected bytes, review parsing, bounded attempts, export identity and package relocation, plus metadata and host compatibility. Tests use synthetic reports; passing them is not a semantic or writing-quality judgment.

Run from the repository root:

```sh
python3 -B -m unittest discover -s scripts -p 'test_humanizer*.py'
python3 -B -m unittest discover -s scripts -p 'test_packaging.py'
python3 -B -m unittest discover -s scripts -p 'test_compatibility.py'
python3 -B -m unittest discover -s scripts -p 'test_codex_smoke.py'
python3 -B scripts/sync_metadata.py --check
python3 -B scripts/check_compatibility.py
git diff --check
```

These commands make no model or detector calls and install nothing.

## Remaining release limitations

- Repeated fixed-pair reviews produced different semantic verdicts for identical Russian text. The role and Russian guide now use one contextual-meaning standard in the shared verification contract; its effect on model consistency remains unvalidated. A false semantic failure can still force unnecessary revision or source retention; the hard-failure policy has not changed.
- Blinded human assessment of writer naturalness, voice and source-relative fidelity remains pending. Initial drafts and selected controls do not validate the complete rewrite workflow.
- Later example corrections postdate the model evaluation. Offline coverage does not establish their effect on model behavior. Detector scores are not release gates or evidence of naturalness.
- The current candidate's complete rewrite workflow remains unvalidated end to end. Claude Code loading has static compatibility coverage; a live loading check was unavailable. See [host verification limits](../compatibility.md#humanizer-checks).

Runtime instructions and their required references ship in `plugins/humanizer/`. Regression tests and fixtures stay in `scripts/`. Detailed investigation reports, annotations, detector records and archive receipts are retained locally under ignored `.dev/`; they are not package dependencies. Back up that evidence separately when moving the checkout.
