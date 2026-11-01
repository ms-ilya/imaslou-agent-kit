# ABOUTME: Tests descriptive scoring, semantic uncertainty and compact source anchors with synthetic offline judgments.

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from humanizer_fixtures import integrity_report, plan_for
from test_humanizer_contracts import module, ROOT
import test_humanizer_stages as stage_tests


report = stage_tests.report


class AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stages = module('stages')

    def parse(self, body, kind='judge', short=False):
        return self.stages.parse_report(body.encode(), kind, short)

    def test_valid_tier_scores_and_minor_count_do_not_control_acceptance(self):
        for pattern, tier in (('6', 1), ('17', 2), ('Russian collocation', 2)):
            for score in (None, 0, 3, 6, 10):
                for count in (1, 4):
                    with self.subTest(pattern=pattern, score=score, count=count):
                        findings = [dict(pattern=pattern, tier=tier, severity='minor',
                                         quote='Fixture passage ' + str(n), reason='Synthetic minor complaint.')
                                    for n in range(count)]
                        parsed = self.parse(report(score=score, findings=findings))
                        self.assertTrue(parsed['available'], parsed)
                        self.assertEqual(parsed['verdict'], 'PASS')

    def test_substantial_findings_block_pass_in_every_tier_with_any_score(self):
        for pattern, tier in (('6', 1), ('17', 2)):
            for score in (None, 10):
                finding = dict(pattern=pattern, tier=tier, severity='substantial',
                               quote='Fixture passage.', reason='Synthetic substantial reader problem.')
                self.assertFalse(self.parse(report(score=score, findings=[finding]))['available'])
                self.assertTrue(self.parse(report(score=score, findings=[finding], verdict='REVISE'))['available'])

    def test_maximum_scores_cannot_rescue_quality_objectives_or_semantics(self):
        failures = [report(score=10, quality='FAIL', verdict='REVISE'),
                    report(score=10, preservation='FAIL', verdict='REVISE'),
                    report(score=10, hallucination='FAIL', verdict='REVISE'),
                    report(score=10, verdict='REVISE').replace('"status":"achieved"',
                                                              '"status":"unresolved"')]
        for body in failures:
            result = self.parse(body)
            self.assertTrue(result['available'], result)
            self.assertEqual(result['total'], 50)
            self.assertFalse(self.parse(body.replace('VERDICT: REVISE', 'VERDICT: PASS'))['available'])

    def test_optional_scores_are_explicit_and_cannot_hide_supplied_numbers(self):
        body = report(score=None)
        parsed = self.parse(body)
        self.assertTrue(parsed['available'])
        self.assertIsNone(parsed['scores'])
        self.assertIsNone(parsed['total'])
        for changed in (body.replace('NOT_REQUESTED', 'UNKNOWN'),
                        body.replace('NOT_REQUESTED', 'NOT_REQUESTED\n- Total: 40/50'),
                        body.replace('SCORES: NOT_REQUESTED', '')):
            self.assertFalse(self.parse(changed)['available'])

    def test_uncertainty_in_either_direction_requires_unresolved_verdict(self):
        for header in ('preservation', 'hallucination'):
            body = report(**{header: 'UNCERTAIN'}, score=None, verdict='UNRESOLVED')
            result = self.parse(body)
            self.assertTrue(result['available'], result)
            self.assertTrue(result['text_uncertain'])
            self.assertFalse(result['text_hard_fail'])
            self.assertEqual(result['semantic_status'], 'uncertain')
            for verdict in ('PASS', 'REVISE'):
                self.assertFalse(self.parse(body.replace('VERDICT: UNRESOLVED', 'VERDICT: ' + verdict))['available'])

    def test_fail_takes_precedence_without_erasing_uncertainty(self):
        result = self.parse(report(preservation='FAIL', hallucination='UNCERTAIN', verdict='REVISE'))
        self.assertTrue(result['available'])
        self.assertTrue(result['text_hard_fail'])
        self.assertTrue(result['text_uncertain'])
        self.assertEqual(result['semantic_status'], 'fail')

    def test_short_self_uncertainty_does_not_invent_verdict_or_scores(self):
        body = integrity_report().replace('PRESERVATION_CHECK: PASS', 'PRESERVATION_CHECK: UNCERTAIN')
        result = self.parse(body, 'self', True)
        self.assertTrue(result['available'])
        self.assertEqual(result['semantic_status'], 'uncertain')
        self.assertEqual(result['editorial_status'], 'unresolved')
        self.assertIsNone(result['verdict'])
        self.assertIsNone(result['scores'])

    def test_quoted_uncertainty_is_data_but_an_entire_report_is_not_exempt(self):
        quotation = 'Source example:\n```source-example\nPRESERVATION_CHECK: UNCERTAIN\n```\n'
        for body, kind, short in ((report(score=None) + quotation, 'judge', False),
                                  (integrity_report() + quotation, 'self', True)):
            result = self.parse(body, kind, short)
            self.assertTrue(result['available'], result)
            self.assertFalse(result['text_uncertain'])
        entire = '```source-example\n' + report(preservation='UNCERTAIN', verdict='UNRESOLVED') + '```\n'
        self.assertTrue(self.parse(entire)['text_uncertain'])

    def test_malformed_and_decorated_uncertainty_remains_visible(self):
        for body in ('**PRESERVATION_CHECK**: UNCERTAIN\nUnresolved interpretation.\n',
                     '`HALLUCINATION_CHECK`: UNCERTAIN\nUnresolved support.\n',
                     report().replace('PRESERVATION_CHECK: PASS',
                                      'PRESERVATION_CHECK: PASS\nPRESERVATION_CHECK: UNCERTAIN')):
            result = self.parse(body)
            self.assertFalse(result['available'])
            self.assertTrue(result['text_uncertain'])
        quoted = report(score=None) + '`PRESERVATION_CHECK: UNCERTAIN` is source text.\n'
        self.assertFalse(self.parse(quoted)['text_uncertain'])

    def test_format_repair_keeps_uncertainty_and_optional_score_mode(self):
        explanation = 'None. Synthetic explanatory text retained exactly.'
        body = report(preservation='UNCERTAIN', score=None, verdict='UNRESOLVED')
        malformed = body.replace('None\n', explanation + '\n')
        repaired = body + explanation + '\n'
        result = self.stages.validate_format_repair(malformed.encode(), repaired.encode(), False)
        self.assertTrue(result['text_uncertain'])
        for changed in (repaired.replace('PRESERVATION_CHECK: UNCERTAIN', 'PRESERVATION_CHECK: PASS')
                                .replace('VERDICT: UNRESOLVED', 'VERDICT: PASS'),
                        repaired.replace('SCORES: NOT_REQUESTED', 'SCORES:\n- Total: 0/50')):
            with self.assertRaises(self.stages.StageError):
                self.stages.validate_format_repair(malformed.encode(), changed.encode(), False)

    def test_short_format_repair_cannot_manufacture_missing_coverage_or_resolve_doubt(self):
        body = integrity_report().replace('PRESERVATION_CHECK: PASS', 'PRESERVATION_CHECK: UNCERTAIN')
        missing = '\n'.join(line for line in body.splitlines() if not line.startswith('COVERAGE:'))
        for repaired in (body, integrity_report()):
            with self.assertRaises(self.stages.StageError):
                self.stages.validate_format_repair(missing.encode(), repaired.encode(), True)


class UncertaintyTransitions(unittest.TestCase):
    def setUp(self):
        # Reuse the CLI harness without inheriting and rerunning its unrelated test cases.
        self.k = stage_tests.HumanizerStages(methodName='runTest')
        self.k.setUp()
        self.addCleanup(self.k.doCleanups)

    def uncertain(self, short=False):
        return (integrity_report().replace('PRESERVATION_CHECK: PASS', 'PRESERVATION_CHECK: UNCERTAIN')
                if short else report(preservation='UNCERTAIN', score=None, verdict='UNRESOLVED'))

    def test_short_self_uncertainty_requires_independent_resolution_then_closes(self):
        k = self.k
        candidate = k.candidate()
        k.self_review(candidate, self.uncertain(short=True))
        k.select(candidate, status=2)
        self.assertTrue(k.state()['independent_required'])
        self.assertEqual(k.state()['pending_semantic_review'], [candidate])
        k.judge_review(candidate, report(score=None))
        selected = k.select(candidate)['selected']
        self.assertEqual(selected['verification'], 'independent')
        self.assertIsNone(selected['total'])
        self.assertEqual(k.result(), b'A faithful fixture candidate.\n')
        self.assertEqual(k.state()['pending_semantic_review'], [])
        k.call('reserve', k.run, '--kind', 'self-revision', '--reason', 'Closed run.', status=2)

    def test_independent_uncertainty_has_only_existing_retry_no_revision_credit(self):
        k = self.k
        candidate = k.candidate()
        k.self_review(candidate)
        k.select(candidate)
        k.judge_review(candidate, self.uncertain())
        k.call('result', k.run, status=2)
        k.call('reserve', k.run, '--kind', 'judge-revision', '--reason', 'Uncertainty is not a correction.', status=2)
        k.judge_review(candidate, report(score=None))
        k.select(candidate)
        self.assertEqual(k.state()['counts']['judge'], 2)
        self.assertEqual(k.result(), b'A faithful fixture candidate.\n')

    def test_independent_semantic_pass_resolves_doubt_with_disclosed_style_shortfall(self):
        k = self.k
        candidate = k.candidate()
        k.self_review(candidate, self.uncertain())
        k.judge_review(candidate, report(score=None, quality='FAIL', verdict='REVISE'))
        selected = k.select(candidate)['selected']
        self.assertEqual(selected['verification'], 'independent')
        self.assertEqual(selected['editorial_status'], 'style-shortfall')
        self.assertEqual(selected['verdict'], 'REVISE')
        self.assertEqual(k.state()['pending_semantic_review'], [])
        self.assertEqual(k.result(), b'A faithful fixture candidate.\n')

    def test_unavailable_judge_cannot_fall_back_to_uncertain_self_report(self):
        k = self.k
        candidate = k.candidate()
        k.self_review(candidate, self.uncertain())
        ticket = k.reserve('judge', candidate)
        k.call('record', k.run, '--ticket', ticket, '--unavailable', '--reason', 'Synthetic unavailable output.')
        k.select(candidate, status=2)
        self.assertEqual(k.result(), k.source_bytes)

    def test_two_uncertain_judges_exhaust_budget_without_authorizing_delivery(self):
        k = self.k
        candidate = k.candidate()
        k.self_review(candidate, self.uncertain())
        k.judge_review(candidate, self.uncertain())
        k.judge_review(candidate, self.uncertain())
        k.select(candidate, status=2)
        k.call('reserve', k.run, '--kind', 'judge', '--candidate', candidate, '--reason', 'No extra attempt.', status=2)
        self.assertEqual(k.result(), k.source_bytes)

    def test_same_bytes_cannot_launder_doubt_or_borrow_another_maps_resolution(self):
        k = self.k
        first = k.candidate()
        k.self_review(first, self.uncertain())
        second = k.candidate(kind='self-revision')
        k.self_review(second)
        k.select(second, status=2)
        k.judge_review(second)
        k.select(second)
        k.select(first, status=2)
        self.assertEqual(k.state()['pending_semantic_review'], [first])

    def test_late_same_byte_uncertainty_invalidates_delivery_without_reopening(self):
        k = self.k
        first = k.candidate()
        second = k.candidate(kind='self-revision')
        k.self_review(first)
        k.judge_review(first)
        k.select(first)
        k.self_review(second, self.uncertain())
        k.call('result', k.run, status=2)
        for kind in ('judge', 'self-revision'):
            args = ['reserve', k.run, '--kind', kind, '--reason', 'Closure remains binding.']
            if kind == 'judge':
                args += ['--candidate', first]
            k.call(*args, status=2)
        k.select('original')
        self.assertEqual(k.result(), k.source_bytes)

    def test_malformed_self_uncertainty_cannot_bypass_valid_self_prerequisite(self):
        k = self.k
        candidate = k.candidate()
        body = self.uncertain().replace('COVERAGE:', 'MISSING_COVERAGE:')
        k.self_review(candidate, body)
        k.call('reserve', k.run, '--kind', 'judge', '--candidate', candidate, '--reason', 'Missing coverage.', status=2)
        k.repair_review(candidate, self.uncertain(), status=2)
        k.select(candidate, status=2)

    def test_malformed_independent_uncertainty_cannot_fall_back_to_previous_pass_checks(self):
        k = self.k
        candidate = k.candidate()
        k.judge_review(candidate, report(quality='FAIL', verdict='REVISE'))
        k.judge_review(candidate, '**HALLUCINATION_CHECK**: UNCERTAIN\nUnresolved source support.\n')
        k.select(candidate, status=2)
        self.assertTrue(k.state()['reviews'][-1]['analysis']['text_uncertain'])
        self.assertEqual(k.result(), k.source_bytes)

    def test_concrete_failure_cannot_be_reclassified_for_adjudication(self):
        k = self.k
        candidate = k.candidate()
        k.self_review(candidate, report(preservation='FAIL', hallucination='UNCERTAIN', verdict='REVISE'))
        k.call('reserve', k.run, '--kind', 'judge', '--candidate', candidate, '--reason', 'Known FAIL.', status=2)
        k.repair_review(candidate, self.uncertain(), status=2)
        k.select(candidate, status=2)

    def test_uncertainty_does_not_poison_different_candidate_bytes(self):
        k = self.k
        first = k.candidate()
        k.self_review(first, self.uncertain())
        second = k.candidate(b'A different synthetic candidate.\n', kind='self-revision')
        k.self_review(second, report(score=None))
        k.select(second)
        self.assertEqual(k.result(), b'A different synthetic candidate.\n')


class CompactPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contracts = module('contracts')

    def test_index_preserves_every_byte_and_reports_physical_blocks_only(self):
        for source in ('\ufeffА е́.\r\n\r\nLast.\r\n', '\n\nРусский\u2028\u2028English',
                       '\r\n\r\n', 'x' * 12000):
            data = source.encode()
            indexed = self.contracts.index_text(data, 'u')
            rows = indexed['units']
            self.assertEqual(b''.join(data[row['start']:row['end']] for row in rows), data)
            self.assertEqual(indexed['sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(indexed['largest_block_bytes'], max(row['end'] - row['start'] for row in rows))
            for n, row in enumerate(rows, 1):
                self.assertEqual(row['id'], 'u' + str(n))
                self.assertEqual(set(row), {'id', 'start', 'end'})
                data[row['start']:row['end']].decode()

    def test_index_cli_is_read_only_and_needs_no_run(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.txt'
            source.write_bytes('Русский.\r\n\r\nEnglish.\n'.encode())
            before = source.read_bytes()
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/stages.py'), 'index',
                                     '--text', str(source), '--prefix', 'c'], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['units'][0]['id'], 'c1')
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(list(Path(folder).iterdir()), [source])

    def test_index_rejects_empty_nul_invalid_utf8_and_invalid_prefix(self):
        for data, prefix in ((b'', 'u'), (b'a\0b', 'u'), (b'\xff', 'u'), (b'valid', 'other')):
            with self.assertRaises(ValueError):
                self.contracts.index_text(data, prefix)

    def test_source_anchors_are_exact_and_span_cross_unit_relationships(self):
        source = 'А.\r\n\r\nА позже.'.encode()
        plan = plan_for(source)
        split = len('А.\r\n\r\n'.encode())
        plan['units'] = [dict(plan['units'][0], end=split, links=['u2']),
                         dict(plan['units'][0], id='u2', start=split, links=['u1'])]
        plan['anchors'] = [{'id': 'a1', 'spans': [{'start': 0, 'end': 2},
                                                {'start': split, 'end': len(source)}],
                            'question': 'Which time relationship connects these passages?'}]
        self.contracts.validate_plan(plan, source)
        anchor = self.contracts.source_anchors(plan, source)[0]
        self.assertEqual([row['text'] for row in anchor['spans']], ['А', 'А позже.'])
        self.assertEqual([row['source_units'] for row in anchor['spans']], [['u1'], ['u2']])
        self.assertEqual(set(anchor), {'id', 'question', 'spans'})

    def test_anchor_schema_rejects_unbound_text_invalid_ranges_and_duplicate_ids(self):
        source = 'А. Later.'.encode()
        base = plan_for(source)
        anchor = {'id': 'a1', 'spans': [{'start': 0, 'end': len(source)}], 'question': 'What is qualified?'}
        invalid = [dict(anchor, question=''), dict(anchor, spans=[]), dict(anchor, text='invented'),
                   dict(anchor, spans=[{'start': 1, 'end': 2}]),
                   dict(anchor, spans=[{'start': 0, 'end': 2}, {'start': 0, 'end': 3}])]
        for item in invalid:
            plan = copy.deepcopy(base)
            plan['anchors'] = [item]
            with self.assertRaises(ValueError):
                self.contracts.validate_plan(plan, source)
        base['anchors'] = [anchor, anchor]
        with self.assertRaises(ValueError):
            self.contracts.validate_plan(base, source)

    def test_empty_anchors_are_valid_but_old_meaning_schema_is_not(self):
        source = b'Complete source.'
        plan = plan_for(source)
        self.contracts.validate_plan(plan, source)
        plan['units'][0]['meaning'] = 'An unvalidated paraphrase.'
        with self.assertRaises(ValueError):
            self.contracts.validate_plan(plan, source)
        del plan['units'][0]['meaning']
        plan['schema_version'] = 1
        with self.assertRaises(ValueError):
            self.contracts.validate_plan(plan, source)


if __name__ == '__main__':
    unittest.main()
