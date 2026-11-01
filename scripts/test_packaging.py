#!/usr/bin/env python3
# ABOUTME: Exercises relocated plugin helpers without host variables or changes to the user's project.

import json
from humanizer_fixtures import keeper_args, REVIEW_METADATA, integrity_report, plan_for, mapping_for
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from sync_metadata import ROOT


class PackagedHelpers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agent kit packaging ')
        self.base = Path(self.temp.name)
        self.project = self.base / 'project with spaces'
        self.project.mkdir()
        self.env = dict(os.environ)
        self.env.pop('CLAUDE_PLUGIN_ROOT', None)
        self.env.pop('CLAUDE_SKILL_DIR', None)

    def tearDown(self):
        self.temp.cleanup()

    def package(self, name):
        target = self.base / 'plugin cache' / name
        shutil.copytree(ROOT / 'plugins' / name, target,
                        ignore=shutil.ignore_patterns('__pycache__', 'evals'))
        return target

    def run_script(self, script, *args, status=0, env=None):
        result = subprocess.run(['bash', str(script), *map(str, args)], cwd=self.project,
                                env=env or self.env, text=True, capture_output=True, timeout=90)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result.stdout

    def test_feature_validators_after_relocation(self):
        package = self.package('feature-spec')
        output = self.run_script(package / 'scripts/test-checks.sh')
        self.assertRegex(output, r'ALL \d+ CHECKS BEHAVE AS DOCUMENTED')

    def test_humanizer_selected_bytes_after_relocation(self):
        package = self.package('humanizer')
        helper = package / 'scripts/stages.py'
        original = self.project / 'original newsletter.txt'
        source_bytes = 'Библиотека может повторить проверку.\r\n'.encode('utf-8')
        original.write_bytes(source_bytes)
        candidate = self.project / 'candidate newsletter.txt'
        selected_bytes = 'Библиотека, возможно, повторит проверку.\r\n'.encode('utf-8')
        candidate.write_bytes(selected_bytes)
        review = self.project / 'review.txt'
        review.write_text(integrity_report())
        run = self.base / 'stage run'

        def call(*args, raw=False):
            args = keeper_args(args)
            result = subprocess.run([sys.executable, '-B', str(helper), *map(str, args)],
                                    cwd=self.project, env=self.env, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout if raw else json.loads(result.stdout)

        call('init', run, '--original', original)
        ticket = call('reserve', run, '--kind', 'initial', '--reason', 'Requested full rewrite.')['ticket']
        call('record', run, '--ticket', ticket, '--text', candidate)
        call('self-check', run, '--candidate', ticket, '--report', review)
        call('select', run, '--candidate', ticket, '--decision', 'promote',
             '--reason', 'Source possibility and actor preserved; short input is unscored.')
        self.assertEqual(call('result', run, raw=True), selected_bytes)
        self.assertEqual(original.read_bytes(), source_bytes)
        self.assertTrue((package / 'skills/humanizer/references/stages.md').is_file())

    def test_humanizer_structure_and_frozen_resources_after_relocation(self):
        package = self.package('humanizer')
        source = self.project / 'source prose.txt'
        data = b'First idea matters. Another idea follows.\n\nFirst idea matters. Details follow.\n\nLast thought remains.\n'
        source.write_bytes(data)
        result = subprocess.run([sys.executable, '-B', str(package / 'scripts/structure.py'),
                                 str(source), '--candidate', str(source), '--sample', str(source), '--language', 'en'],
                                cwd=self.project, env=self.env, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        profiles = json.loads(result.stdout)
        self.assertEqual(profiles['source'], profiles['candidate'])
        self.assertEqual(profiles['source'], profiles['style_sample'])
        self.assertEqual(profiles['source']['prose_sentences'], 5)
        self.assertEqual(source.read_bytes(), data)
        run = self.base / 'resource-bound run'
        initialized = subprocess.run([sys.executable, '-B', str(package / 'scripts/stages.py'),
                                      *map(str, keeper_args(('init', run, '--original', source)))],
                                     cwd=self.project, env=self.env, capture_output=True, timeout=15)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        state = (run / 'state.json').read_bytes()
        contract = package / 'skills/humanizer/references/verification.md'
        contract.write_bytes(contract.read_bytes() + b'\nChanged fixture contract.\n')
        refused = subprocess.run([sys.executable, '-B', str(package / 'scripts/stages.py'),
                                  'reserve', str(run), '--kind', 'initial', '--reason', 'Fixture.'],
                                 cwd=self.project, env=self.env, capture_output=True, timeout=15)
        self.assertEqual(refused.returncode, 2)
        self.assertIn(b'installed plugin resources changed', refused.stderr)
        self.assertEqual((run / 'state.json').read_bytes(), state)
        self.assertEqual(source.read_bytes(), data)

    def test_humanizer_text_integrity_after_relocation(self):
        import hashlib

        package = self.package('humanizer')
        helper = package / 'scripts/text_integrity.py'
        keeper = package / 'scripts/stages.py'
        source = self.project / 'synthetic unicode input.txt'
        source_bytes = 'A\u200bB\r\nCafé\r\n'.encode('utf-8')
        expected_bytes = 'AB\r\nCafé\r\n'.encode('utf-8')
        source.write_bytes(source_bytes)
        identity = hashlib.sha256(source_bytes).hexdigest()
        plan = {
            'schema_version': 1, 'original_sha256': identity, 'input_sha256': identity,
            'scope': {'editable': [[0, 5]], 'protected': [[5, len(source_bytes)]],
                      'locks': [[7, 12]]},
            'edits': [{
                'byte_start': 1, 'byte_end': 4, 'scalar_start': 1, 'scalar_end': 2,
                'expected_hex': 'e2808b', 'replacement_hex': '',
                'reason': 'Remove the explicitly injected fixture artifact.',
                'authorization': 'Synthetic packaging fixture authorizes this exact deletion.',
                'source_anchor': {'unit_id': 'packaging-unit', 'byte_start': 0,
                                  'byte_end': 5, 'expected_hex': source_bytes[:5].hex()},
                'boundary': {'left_hex': '41', 'right_hex': '42', 'result_hex': '4142',
                             'intent': 'restore-known-word'},
            }],
        }
        plan_bytes = (json.dumps(plan, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8')
        plan_path = self.project / 'explicit edit plan.json'
        plan_path.write_bytes(plan_bytes)
        run = self.base / 'integrity stage run'
        output = self.project / 'synthetic exact output.txt'
        sidecar = Path(str(run) + '.text-integrity')

        def call(script, *args, status=0):
            if script.name == 'stages.py':
                args = keeper_args(args)
            result = subprocess.run([sys.executable, '-B', str(script), *map(str, args)],
                                    cwd=self.project, env=self.env, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, status, result.stdout + result.stderr)
            if status:
                self.assertEqual(result.stdout, b'')
                return None
            return json.loads(result.stdout)

        def run_files():
            return {str(p.relative_to(run)): p.read_bytes() for p in run.rglob('*') if p.is_file()}

        self.assertNotIn('CLAUDE_PLUGIN_ROOT', self.env)
        self.assertNotIn('CLAUDE_SKILL_DIR', self.env)
        inspected = call(helper, 'inspect', source, '--expected-sha256', identity)
        self.assertEqual(inspected['input_sha256'], identity)
        self.assertEqual(inspected['utf8_bytes'], len(source_bytes))
        self.assertEqual(inspected['unicode_scalars'], len(source_bytes.decode('utf-8')))
        self.assertTrue(any(item['name'] == 'ZERO WIDTH SPACE' for item in inspected['observations']))
        self.assertEqual(source.read_bytes(), source_bytes)
        self.assertEqual(sorted(p.name for p in self.project.iterdir()), [plan_path.name, source.name])
        self.assertFalse(sidecar.exists())

        call(keeper, 'init', run, '--original', source)
        initial_state = run_files()
        call(helper, 'apply-edits', source, '--plan', plan_path, '--run', run,
             '--ticket', 'draft-1', '--output', output, status=2)
        self.assertEqual(run_files(), initial_state)
        self.assertFalse(output.exists())
        ticket = call(keeper, 'reserve', run, '--kind', 'initial',
                      '--reason', 'Synthetic deterministic edit fixture; no model generation.')['ticket']
        reserved_state = run_files()
        receipt = call(helper, 'apply-edits', source, '--plan', plan_path, '--run', run,
                       '--ticket', ticket, '--output', output)
        self.assertEqual(output.read_bytes(), expected_bytes)
        self.assertEqual(source.read_bytes(), source_bytes)
        self.assertEqual(plan_path.read_bytes(), plan_bytes)
        self.assertEqual(run_files(), reserved_state)
        self.assertEqual(receipt['original_sha256'], identity)
        self.assertEqual(receipt['input_sha256'], identity)
        self.assertEqual(receipt['output_sha256'], hashlib.sha256(expected_bytes).hexdigest())
        self.assertEqual(receipt['plan_sha256'], hashlib.sha256(plan_bytes).hexdigest())
        self.assertEqual(receipt['ticket'], ticket)
        self.assertEqual(receipt['run'], str(run.resolve()))
        self.assertEqual(len(receipt['edits']), 1)
        self.assertEqual(receipt['edits'][0]['expected_hex'], 'e2808b')
        self.assertEqual(receipt['edits'][0]['replacement_hex'], '')
        self.assertEqual(receipt['edits'][0]['output_byte_start'], 1)
        self.assertEqual(receipt['edits'][0]['output_byte_end'], 1)
        self.assertEqual(receipt['fidelity_editorial'], 'not-assessed')
        self.assertEqual(receipt['statistical_watermark'], 'unavailable/unverified')
        self.assertEqual(receipt['generic_detector'], 'not-attempted')
        evidence = sidecar / ticket
        self.assertEqual(sorted(p.name for p in evidence.iterdir()),
                         ['complete.json', 'input.txt', 'output.txt', 'plan.json', 'receipt.json'])
        self.assertEqual((evidence / 'input.txt').read_bytes(), source_bytes)
        self.assertEqual((evidence / 'output.txt').read_bytes(), expected_bytes)
        self.assertEqual((evidence / 'plan.json').read_bytes(), plan_bytes)
        self.assertEqual(json.loads((evidence / 'receipt.json').read_bytes()), receipt)
        self.assertIsInstance(json.loads((evidence / 'complete.json').read_bytes()), dict)

    def test_humanizer_readonly_inspection_before_draft_and_after_export(self):
        import hashlib
        import importlib.util

        package = self.package('humanizer')
        inspector = package / 'scripts/text_integrity.py'
        keeper = package / 'scripts/stages.py'
        original = self.project / 'untouched original with spaces.txt'
        original_bytes = '\ufeffCafe\u0301 memo.\r\nKeep می\u200cروم and 12\u202fkg.\r\n'.encode('utf-8')
        selected_bytes = '\ufeffCafe\u0301 memo.\r\nKeep می\u200cروم; mass: 12\u202fkg.\r\n'.encode('utf-8')
        original.write_bytes(original_bytes)
        original_hash = hashlib.sha256(original_bytes).hexdigest()
        selected_hash = hashlib.sha256(selected_bytes).hexdigest()
        run = self.base / 'synthetic readonly keeper with spaces'
        sidecar = Path(str(run) + '.text-integrity')

        def call(script, *args, status=0):
            if script.name == 'stages.py':
                args = keeper_args(args)
            result = subprocess.run([sys.executable, '-B', str(script), *map(str, args)],
                                    cwd=self.project, env=self.env, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, status, result.stdout + result.stderr)
            if status:
                self.assertEqual(result.stdout, b'')
                self.assertTrue(result.stderr.strip())
                return result
            return json.loads(result.stdout)

        def run_files():
            return {str(path.relative_to(run)): path.read_bytes()
                    for path in run.rglob('*') if path.is_file()}

        self.assertNotIn('CLAUDE_PLUGIN_ROOT', self.env)
        self.assertNotIn('CLAUDE_SKILL_DIR', self.env)
        self.assertFalse(run.exists())
        before_draft = call(inspector, 'inspect', original, '--expected-sha256', original_hash)
        self.assertEqual(before_draft,
                         call(inspector, 'inspect', original, '--expected-sha256', original_hash))
        self.assertEqual(original.read_bytes(), original_bytes)
        self.assertEqual(before_draft['input_sha256'], original_hash)
        self.assertFalse(run.exists())
        self.assertFalse(sidecar.exists())
        self.assertEqual(sorted(path.name for path in self.project.iterdir()), [original.name])

        # Static byte/report records exercise packaging and readback only. No
        # writer, semantic evaluator or independent model is invoked by this fixture.
        spec = importlib.util.spec_from_file_location('relocated_readonly_keeper_fixture', keeper)
        stages = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stages)
        report = (integrity_report().encode() + b'' +
                  b'AI_PATTERNS_FOUND: 0\nNone\nSCORES: NOT_REQUESTED\n'
                  b'VERDICT: PASS\n')
        parsed_report = stages.parse_report(report, 'judge', True)
        self.assertTrue(parsed_report['available'])
        draft_path = self.project / 'static candidate.txt'
        report_path = self.project / 'static report.txt'
        draft_path.write_bytes(selected_bytes)
        report_path.write_bytes(report)
        call(keeper, 'init', run, '--original', original)
        call(keeper, 'reserve', run, '--kind', 'initial', '--reason', 'Static byte fixture.')
        call(keeper, 'record', run, '--ticket', 'draft-1', '--text', draft_path)
        call(keeper, 'self-check', run, '--candidate', 'draft-1', '--report', report_path)
        call(keeper, 'reserve', run, '--kind', 'judge', '--candidate', 'draft-1', '--reason', 'Static report fixture.')
        call(keeper, 'record', run, '--ticket', 'judge-1', '--report', report_path)
        call(keeper, 'select', run, '--candidate', 'draft-1', '--decision', 'promote', '--reason', 'Static selection fixture.')
        retained_before = run_files()
        status_before = call(keeper, 'status', run)
        self.assertEqual(status_before['selected']['sha256'], selected_hash)
        self.assertEqual(status_before['selected']['verification'], 'independent')
        self.assertEqual(status_before['counts'],
                         {'initial': 1, 'self_revision': 0, 'judge_revision': 0, 'judge': 1})
        export = self.project / 'exact exported candidate with spaces.txt'
        exported = call(keeper, 'result', run, '--output', export)
        self.assertEqual(export.read_bytes(), selected_bytes)
        self.assertEqual(exported['sha256'], selected_hash)
        self.assertEqual(exported['selected']['sha256'], selected_hash)
        after_export = call(inspector, 'inspect', export, '--expected-sha256',
                            exported['selected']['sha256'])
        self.assertEqual(after_export, call(inspector, 'inspect', export, '--expected-sha256',
                                           exported['selected']['sha256']))
        self.assertEqual(after_export['input_sha256'], selected_hash)
        for inspection in (before_draft, after_export):
            self.assertEqual(inspection['edits'], [])
            self.assertEqual(inspection['fidelity_editorial'], 'not-assessed')
            self.assertEqual(inspection['statistical_watermark'], 'unavailable/unverified')
            self.assertEqual(inspection['generic_detector'], 'not-attempted')
            observed = {row['codepoint'] for row in inspection['observations']}
            self.assertTrue({'U+FEFF', 'U+0301', 'U+200C', 'U+202F'} <= observed)
            self.assertGreater(inspection['category_counts']['Cc'], 0)
            self.assertTrue(all(row['disposition'] == 'preserve-or-flag'
                                for row in inspection['observations']))
        self.assertEqual(run_files(), retained_before)
        self.assertEqual(call(keeper, 'status', run), status_before)
        self.assertEqual(original.read_bytes(), original_bytes)
        self.assertEqual(export.read_bytes(), selected_bytes)
        self.assertFalse(sidecar.exists())

        # The requested writeback copies the already checked export verbatim;
        # the keeper's captured original and review bindings remain immutable.
        original.write_bytes(export.read_bytes())
        written_back = call(inspector, 'inspect', original, '--expected-sha256',
                            exported['selected']['sha256'])
        self.assertEqual(written_back, after_export)
        self.assertEqual(original.read_bytes(), selected_bytes)
        self.assertEqual(run_files(), retained_before)
        self.assertEqual(call(keeper, 'status', run), status_before)
        call(inspector, 'inspect', original, '--expected-sha256', original_hash, status=2)
        self.assertEqual(original.read_bytes(), selected_bytes)
        self.assertEqual(export.read_bytes(), selected_bytes)
        self.assertEqual(run_files(), retained_before)
        self.assertEqual(call(keeper, 'status', run), status_before)
        self.assertFalse(sidecar.exists())

        tampered_bytes = selected_bytes + b'\t'
        export.write_bytes(tampered_bytes)
        call(inspector, 'inspect', export, '--expected-sha256',
             exported['selected']['sha256'], status=2)
        self.assertEqual(export.read_bytes(), tampered_bytes)
        self.assertEqual(original.read_bytes(), selected_bytes)
        self.assertEqual(run_files(), retained_before)
        self.assertEqual(call(keeper, 'status', run), status_before)
        self.assertFalse(sidecar.exists())

    def test_humanizer_retention_and_dispatch_gates_after_relocation(self):
        import hashlib

        package = self.package('humanizer')
        keeper = package / 'scripts/stages.py'
        inspector = package / 'scripts/text_integrity.py'
        original_bytes = '\ufeffA fixed synthetic source: cafe\u0301.\r\n'.encode('utf-8')
        candidate_bytes = (
            '\ufeffFirst fixed byte fixture: cafe\u0301.\r\n'.encode('utf-8'),
            '\ufeffSecond fixed byte fixture: cafe\u0301.\r\n'.encode('utf-8'),
            '\ufeffThird fixed byte fixture: cafe\u0301.\r\n'.encode('utf-8'),
        )
        integrity_pass = integrity_report().encode()
        integrity_fail = (b'PRESERVATION_CHECK: FAIL\nSynthetic adverse gate evidence.\n'
                          b'HALLUCINATION_CHECK: PASS\n')
        judge_pass = (integrity_report().encode() + b'' +
                      b'AI_PATTERNS_FOUND: 0\nNone\nSCORES: NOT_REQUESTED\n'
                      b'VERDICT: PASS\n')

        def call(script, *args, status=0):
            if script.name == 'stages.py':
                args = keeper_args(args)
            result = subprocess.run([sys.executable, '-B', str(script), *map(str, args)],
                                    cwd=self.project, env=self.env, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, status, result.stdout + result.stderr)
            if status:
                self.assertEqual(result.stdout, b'')
                self.assertTrue(result.stderr.strip())
                return result
            return json.loads(result.stdout)

        def run_files(run):
            return {str(path.relative_to(run)): path.read_bytes()
                    for path in run.rglob('*') if path.is_file()}

        def new_run(label):
            source = self.project / (label + ' original with spaces.txt')
            source.write_bytes(original_bytes)
            run = self.base / (label + ' run with spaces')
            call(keeper, 'init', run, '--original', source)
            return source, run

        def static_writer(run, label, body, kind, report_body=integrity_pass):
            # These fixed local byte/report fixtures exercise transitions only;
            # recording them never invokes a writer or semantic reviewer.
            draft = self.project / (label + ' candidate with spaces.txt')
            draft.write_bytes(body)
            report = self.project / (label + ' static self report.txt')
            report.write_bytes(report_body)
            ticket = call(keeper, 'reserve', run, '--kind', kind,
                          '--reason', 'Fixed synthetic transition fixture; no model generation.')['ticket']
            call(keeper, 'record', run, '--ticket', ticket, '--text', draft)
            call(keeper, 'self-check', run, '--candidate', ticket, '--report', report)
            return ticket

        source, retained_run = new_run('retention')
        tickets = []
        for index, body in enumerate(candidate_bytes):
            ticket = static_writer(retained_run, 'retention ' + str(index), body,
                                   'initial' if index == 0 else 'self-revision')
            tickets.append(ticket)
            call(keeper, 'select', retained_run, '--candidate', ticket,
                 '--decision', 'promote' if index == 0 else 'retain',
                 '--reason', 'Synthetic explicit selection; keep the first while later fixtures are recorded.')
        before_selection = call(keeper, 'status', retained_run)
        self.assertEqual(before_selection['counts'],
                         {'initial': 1, 'self_revision': 2, 'judge_revision': 0, 'judge': 0})
        for ticket, body in zip(tickets, candidate_bytes):
            relative = 'drafts/' + ticket + '.txt'
            self.assertEqual(before_selection['attempts'][tickets.index(ticket)]['sha256'],
                             hashlib.sha256(body).hexdigest())
            self.assertEqual((retained_run / relative).read_bytes(), body)
            saved_state = json.loads((retained_run / 'state.json').read_bytes())
            self.assertEqual(saved_state['files'][relative], hashlib.sha256(body).hexdigest())
        selected = call(keeper, 'select', retained_run, '--candidate', tickets[1],
                        '--decision', 'promote',
                        '--reason', 'Export the older unselected fixture after the later candidate.')
        self.assertEqual(selected['selected']['candidate'], tickets[1])
        self.assertTrue(selected['selected']['eligible'])
        retained_before_export = run_files(retained_run)
        export = self.project / 'older retained export with spaces.txt'
        exported = call(keeper, 'result', retained_run, '--output', export)
        self.assertEqual(export.read_bytes(), candidate_bytes[1])
        observed = call(inspector, 'inspect', export, '--expected-sha256', exported['selected']['sha256'])
        self.assertEqual(observed,
                         call(inspector, 'inspect', export, '--expected-sha256', exported['selected']['sha256']))
        self.assertEqual(observed['input_sha256'], hashlib.sha256(candidate_bytes[1]).hexdigest())
        self.assertEqual(observed['edits'], [])
        self.assertEqual(observed['statistical_watermark'], 'unavailable/unverified')
        self.assertEqual(observed['generic_detector'], 'not-attempted')
        self.assertEqual(run_files(retained_run), retained_before_export)
        self.assertEqual(call(keeper, 'status', retained_run), selected)
        self.assertEqual(source.read_bytes(), original_bytes)
        self.assertEqual(len(selected['reviews']), 3)
        self.assertFalse(Path(str(retained_run) + '.text-integrity').exists())

        failed_source, failed_run = new_run('hard failure')
        failed_ticket = static_writer(failed_run, 'hard failure', candidate_bytes[0],
                                      'initial', integrity_fail)
        failed_state = call(keeper, 'status', failed_run)
        self.assertTrue(failed_state['reviews'][0]['analysis']['hard_fail'])
        failed_files = run_files(failed_run)
        refused = call(keeper, 'reserve', failed_run, '--kind', 'judge', '--candidate', failed_ticket,
                       '--reason', 'Probe known failure dispatch refusal.', status=2)
        self.assertIn(b'hard', refused.stderr.lower())
        self.assertEqual(call(keeper, 'status', failed_run), failed_state)
        self.assertEqual(run_files(failed_run), failed_files)
        self.assertEqual(failed_source.read_bytes(), original_bytes)

        passed_source, passed_run = new_run('valid PASS')
        passed_ticket = static_writer(passed_run, 'valid PASS', candidate_bytes[0], 'initial')
        static_report = self.project / 'static independent PASS fixture.txt'
        static_report.write_bytes(judge_pass)
        judge_ticket = call(keeper, 'reserve', passed_run, '--kind', 'judge', '--candidate', passed_ticket,
                            '--reason', 'Static parser/gate fixture; no independent model dispatched.')['ticket']
        call(keeper, 'record', passed_run, '--ticket', judge_ticket, '--report', static_report)
        passed_state = call(keeper, 'status', passed_run)
        self.assertTrue(passed_state['reviews'][-1]['analysis']['available'])
        self.assertEqual(passed_state['reviews'][-1]['analysis']['verdict'], 'PASS')
        passed_files = run_files(passed_run)
        for kind in ('self-revision', 'judge-revision', 'judge'):
            args = ['reserve', passed_run, '--kind', kind,
                    '--reason', 'Probe that a valid PASS closes future reservations.']
            if kind == 'judge':
                args.extend(['--candidate', passed_ticket])
            refused = call(keeper, *args, status=2)
            self.assertIn(b'pass', refused.stderr.lower())
            self.assertEqual(call(keeper, 'status', passed_run), passed_state)
            self.assertEqual(run_files(passed_run), passed_files)
        self.assertEqual(passed_source.read_bytes(), original_bytes)

    def test_auditor_catalog_and_findings_after_relocation(self):
        package = self.package('appstore-guideline-auditor')
        output = self.run_script(package / 'scripts/check-catalogue.sh')
        self.assertIn('CATALOGUE OK', output)
        findings = self.project / 'findings legal.json'
        findings.write_text(json.dumps({'category': 'legal', 'status': 'completed',
                                       'findings': [], 'checklist': []}))
        self.assertIn('0 finding(s)', self.run_script(package / 'scripts/validate-findings.sh', findings))
        findings.write_text('{"category": "made-up-category"}')
        self.assertIn('does not match', self.run_script(package / 'scripts/validate-findings.sh', findings, status=1))

    def test_auditor_does_not_modify_project(self):
        package = self.package('appstore-guideline-auditor')
        source = self.project / 'notes.txt'
        source.write_text('Existing project content\n')
        scratch = self.base / 'audit scratch'
        self.run_script(package / 'scripts/collect-context.sh', self.project, scratch)
        context = json.loads((scratch / 'context.json').read_text())
        self.assertFalse(context['in_scope'])
        self.assertEqual(context['out_of_scope_reason'], 'no-xcode-project')
        self.assertIn('UNTOUCHED', self.run_script(package / 'scripts/check-untouched.sh', self.project, scratch))
        self.assertEqual(source.read_text(), 'Existing project content\n')
        self.assertEqual(sorted(p.name for p in self.project.iterdir()), ['notes.txt'])

    @unittest.skipUnless(shutil.which('jq'), 'jq is required for comprehensive review')
    def test_review_extraction_without_host_variables(self):
        package = self.package('ios-comprehensive-review')
        env = dict(self.env)
        # Read the existing repository history; this test never creates a commit.
        git_dir = subprocess.check_output(['git', 'rev-parse', '--absolute-git-dir'], cwd=ROOT, text=True).strip()
        env.update(GIT_DIR=git_dir, GIT_WORK_TREE=str(ROOT))
        self.run_script(package / 'scripts/extract-pr-context.sh', '--base', 'HEAD', '--branch', 'HEAD', env=env)
        context = json.loads((self.project / '.ios-review-temp/pr-context.json').read_text())
        self.assertEqual(context['changed_files'], [])
        self.assertEqual(context['signature_changes'], [])

    @unittest.skipUnless(shutil.which('jq'), 'jq is required for comprehensive review')
    def test_review_preserves_unverified_findings(self):
        package = self.package('ios-comprehensive-review')
        work = self.project / '.ios-review-temp'
        work.mkdir()
        (work / 'pr-context.json').write_text(json.dumps({
            'pr_number': 0, 'title': 'Packaging fixture', 'author': 'Fixture',
            'head_branch': 'feature', 'base_branch': 'main',
            'changed_files': [{'path': 'Source.swift', 'change_type': 'modified'}],
        }))
        (work / 'review-Source.json').write_text(json.dumps({
            'agent': 'file-analyzer', 'findings': [{
                'severity': 'warning', 'file': 'Source.swift', 'line': 1,
                'category': 'Correctness', 'issue': 'Fixture needs verification', 'evidence': 'fixture',
            }],
        }))
        output = self.run_script(package / 'scripts/findings-worklist.sh')
        finding_id = json.loads(output)['id']
        summary = self.run_script(package / 'scripts/build-report.sh')
        self.assertIn('Warning: 1', summary)
        self.assertIn('Unverified: 1', summary)
        self.assertIn('(unverified)', (work / 'ios-review-report.md').read_text())
        (work / 'verdicts-1.json').write_text(json.dumps({
            'agent': 'finding-verifier', 'status': 'completed',
            'verdicts': [{'id': finding_id, 'verdict': 'confirmed', 'reason': 'Fixture confirmed'}],
        }))
        self.assertEqual(self.run_script(package / 'scripts/findings-worklist.sh'), '')
        self.assertIn('Unverified: 0', self.run_script(package / 'scripts/build-report.sh'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
