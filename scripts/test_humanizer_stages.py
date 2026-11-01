#!/usr/bin/env python3
# ABOUTME: Exercises Humanizer artifact selection, review recovery and revision limits through its local CLI.

import hashlib
import json
import re
from humanizer_fixtures import keeper_args, REVIEW_METADATA, integrity_report
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'plugins/humanizer/scripts/stages.py'


def report(preservation='PASS', hallucination='PASS', score=8, total=None,
           verdict='PASS', findings=None, count=None, quality='PASS'):
    findings = findings or []
    # Historical fixture phrases become explicit JSON metadata; quoted evidence stays data.
    records = []
    for finding in findings:
        if isinstance(finding, dict):
            records.append(json.dumps(finding))
        else:
            match = re.match(r'Tier ([12]) (minor|substantial) (.*)', finding)
            records.append(json.dumps({'tier': int(match[1]), 'severity': match[2],
                                       'pattern': 'fixture', 'quote': match[3], 'reason': match[3]}) if match else finding)
    findings = records
    if total is None and score is not None:
        total = score * 5
    if count is None:
        count = len(findings)
    return '\n'.join([
        'PRESERVATION_CHECK: ' + preservation,
        'Source qualifications, protected content and scope were checked.',
        '',
        'HALLUCINATION_CHECK: ' + hallucination,
        'Output claims were compared with the complete original.',
        '',
        REVIEW_METADATA.rstrip().replace('QUALITY_CHECK: PASS', 'QUALITY_CHECK: ' + quality),
        'AI_PATTERNS_FOUND: ' + str(count),
        *(findings or ['None']),
        '',
        *(['SCORES: NOT_REQUESTED'] if score is None else [
            'SCORES:',
            '- Directness: {}/10'.format(score),
            '- Rhythm: {}/10'.format(score),
            '- Trust: {}/10'.format(score),
            '- Authenticity: {}/10'.format(score),
            '- Preservation: {}/10'.format(score),
            '- Total: {}/50'.format(total)]),
        '',
        'VERDICT: ' + verdict,
        '',
    ])


class HumanizerStages(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='humanizer stage tests ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'source with spaces.txt'
        self.source_bytes = 'Срок — 30 секунд.\r\n\r\nThe team may test again.\r\n'.encode('utf-8')
        self.source.write_bytes(self.source_bytes)
        self.run = self.base / 'run with spaces'
        self.serial = 0
        self.call('init', self.run, '--original', self.source)

    def file(self, data, suffix='.txt'):
        self.serial += 1
        path = self.base / ('fixture {}{}'.format(self.serial, suffix))
        path.write_bytes(data.encode('utf-8') if isinstance(data, str) else data)
        return path

    def call(self, *args, status=0, raw=False):
        args = keeper_args(args)
        result = subprocess.run([sys.executable, '-B', str(HELPER), *map(str, args)],
                                cwd=self.base, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, status,
                         result.stdout.decode('utf-8', errors='replace') +
                         result.stderr.decode('utf-8', errors='replace'))
        if status:
            self.assertIn(b'error:', result.stderr)
            return result
        if raw:
            return result.stdout
        return json.loads(result.stdout)

    def reserve(self, kind, candidate=None):
        args = ['reserve', self.run, '--kind', kind, '--reason', 'Apply the source-supported fixture correction.']
        if candidate is not None:
            args += ['--candidate', candidate]
        return self.call(*args)['ticket']

    def candidate(self, data=b'A faithful fixture candidate.\n', kind='initial'):
        ticket = self.reserve(kind)
        self.call('record', self.run, '--ticket', ticket, '--text', self.file(data))
        return ticket

    def self_review(self, candidate, body=None):
        if body is None:
            existing = [row for row in self.state()['reviews'] if row['id'] == 'self-' + candidate]
            if existing:
                return existing[0]
        return self.call('self-check', self.run, '--candidate', candidate,
                         '--report', self.file(report() if body is None else body))

    def repair_review(self, candidate, body, status=0):
        return self.call('self-check', self.run, '--candidate', candidate,
                         '--report', self.file(body), '--repair-format', '--reason',
                         'Repair report layout only; keep the same checks and candidate.', status=status)

    def judge_review(self, candidate, body=None):
        if not any(row['kind'] == 'self' and row['candidate'] == candidate for row in self.state()['reviews']):
            self.self_review(candidate)
        ticket = self.reserve('judge', candidate)
        return self.call('record', self.run, '--ticket', ticket,
                         '--report', self.file(report() if body is None else body))

    def select(self, candidate, decision='promote', status=0):
        return self.call('select', self.run, '--candidate', candidate,
                         '--decision', decision, '--reason',
                         ('Keep the earlier selection because this candidate must not replace it.'
                          if decision == 'retain' else
                          'Select the supported correction with its actual review status.'), status=status)

    def result(self):
        return self.call('result', self.run, raw=True)

    def state(self):
        return self.call('status', self.run)

    def test_unreviewed_candidate_cannot_replace_original(self):
        candidate = self.candidate()
        self.select(candidate, status=2)
        self.assertEqual(self.result(), self.source_bytes)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_rejected_candidate_does_not_overwrite_selected_bytes(self):
        accepted_bytes = 'Срок — 30 секунд.\r\nThe team may test again.\r\n'.encode('utf-8')
        accepted = self.candidate(accepted_bytes)
        self.self_review(accepted)
        self.select(accepted)
        rejected = self.candidate(b'The team tested again.\n', kind='self-revision')
        self.self_review(rejected, report(preservation='FAIL', score=10, verdict='REVISE'))
        self.select(rejected, decision='retain')
        self.assertEqual(self.result(), accepted_bytes)
        self.select(rejected, status=2)
        self.assertEqual(self.result(), accepted_bytes)
        self.assertEqual(self.state()['selected']['candidate'], accepted)

    def test_higher_score_cannot_override_scope_or_invention_failure(self):
        for hard_check in ('preservation', 'hallucination'):
            with self.subTest(hard_check=hard_check):
                if hard_check == 'hallucination':
                    self.run = self.base / 'second run'
                    self.call('init', self.run, '--original', self.source)
                candidate = self.candidate(b'A rewritten protected quote and invented certainty.\n')
                kwargs = {hard_check: 'FAIL', 'score': 10, 'verdict': 'REVISE'}
                self.self_review(candidate, report(**kwargs))
                self.select(candidate, status=2)
                self.assertEqual(self.result(), self.source_bytes)

    def test_malformed_independent_report_allows_labeled_self_check_recovery(self):
        candidate_bytes = b'The team may test again after thirty seconds.\n'
        candidate = self.candidate(candidate_bytes)
        self.judge_review(candidate, 'PRESERVATION_CHECK: PASS\nVERDICT: PASS\n')
        self.self_review(candidate)
        self.select(candidate)
        state = self.state()
        self.assertEqual(self.result(), candidate_bytes)
        self.assertIn('self', json.dumps(state['selected']).lower())
        self.assertTrue(any(review['analysis']['available'] is False for review in state['reviews']))

    def test_unavailable_judgment_does_not_erase_explicit_hard_failure(self):
        candidate = self.candidate(b'The team will test again.\n')
        self.judge_review(candidate, 'PRESERVATION_CHECK: FAIL\n"may" was replaced with "will".\n')
        self.self_review(candidate)
        self.select(candidate, status=2)
        self.assertEqual(self.result(), self.source_bytes)

    def test_malformed_case_or_markup_cannot_hide_an_explicit_hard_failure(self):
        failures = (
            'preservation_check: fail',
            'PRESERVATION_CHECK: **FAIL**',
            '**PRESERVATION_CHECK**: FAIL',
            '**PRESERVATION_CHECK:** **FAIL**',
            '- **HALLUCINATION_CHECK**: **FAIL**',
            '*PRESERVATION_CHECK*: *FAIL*',
            '`HALLUCINATION_CHECK`: `FAIL`',
        )
        for index, failure in enumerate(failures):
            with self.subTest(failure=failure):
                self.run = self.base / ('malformed hard failure {}'.format(index))
                self.call('init', self.run, '--original', self.source)
                candidate = self.candidate()
                review = self.judge_review(candidate, failure + '\nA concrete source qualification was removed.\n')
                self.assertFalse(review['analysis']['available'])
                self.assertTrue(review['analysis']['hard_fail'])
                self.self_review(candidate)
                self.select(candidate, status=2)
                self.assertEqual(self.result(), self.source_bytes)

    def test_identical_bytes_keep_hard_failure_evidence_across_ticket_names(self):
        data = b'The team will test again.\n'
        candidate = self.candidate(data)
        self.judge_review(candidate, report(preservation='FAIL', verdict='REVISE'))
        same_bytes = self.candidate(data, kind='self-revision')
        self.self_review(same_bytes)
        self.select(same_bytes, status=2)
        self.assertEqual(self.result(), self.source_bytes)

    def test_short_integrity_report_cannot_contradict_its_own_adverse_evidence(self):
        candidate = self.candidate()
        review = self.self_review(candidate, 'PRESERVATION_CHECK: PASS\n'
                                  'HALLUCINATION_CHECK: PASS\n'
                                  '**PRESERVATION_CHECK**: FAIL\n'
                                  'A concrete source qualification was removed.\n')
        self.assertFalse(review['analysis']['available'])
        self.assertTrue(review['analysis']['hard_fail'])
        self.select(candidate, status=2)
        self.assertEqual(self.result(), self.source_bytes)

    def test_inline_code_quotations_do_not_create_adverse_review_outcomes(self):
        quotations = ('`PRESERVATION_CHECK: FAIL`', '``HALLUCINATION_CHECK: FAIL``',
                      '`**PRESERVATION_CHECK**: FAIL`')
        for index, quotation in enumerate(quotations):
            with self.subTest(quotation=quotation):
                self.run = self.base / ('inline code quotation {}'.format(index))
                self.call('init', self.run, '--original', self.source)
                candidate = self.candidate()
                body = report() + 'The following source example is unchanged:\n' + quotation + '\n'
                review = self.judge_review(candidate, body)
                self.assertTrue(review['analysis']['available'])
                self.assertFalse(review['analysis']['hard_fail'])
                self.select(candidate)
                self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_labeled_source_example_fences_are_literal_inside_a_complete_review(self):
        quotations = (
            'Source example:\n```text\nPRESERVATION_CHECK: FAIL\n```\n',
            'Protected source example:\n```text\n**PRESERVATION_CHECK**: FAIL\n```\n',
            '```source-example\nHALLUCINATION_CHECK: FAIL\n```\n',
            'Quoted source example:\n~~~text\n**HALLUCINATION_CHECK**: FAIL\n~~~\n',
        )
        for index, quotation in enumerate(quotations):
            with self.subTest(quotation=quotation):
                self.run = self.base / ('source example fence {}'.format(index))
                self.call('init', self.run, '--original', self.source)
                candidate = self.candidate()
                body = (report() + quotation if index % 2 == 0 else
                        report().replace('Source qualifications, protected content and scope were checked.',
                                         'The protected example is unchanged.\n' + quotation))
                review = self.judge_review(candidate, body)
                self.assertTrue(review['analysis']['available'])
                self.assertFalse(review['analysis']['hard_fail'])
                self.assertEqual((self.run / review['path']).read_bytes(), body.encode('utf-8'))
                self.select(candidate)
                self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_entire_fenced_adverse_reports_cannot_be_disguised_as_source_examples(self):
        failures = (
            ('```text\n**PRESERVATION_CHECK**: FAIL\nA qualification was removed.\n```\n', False),
            ('Source example:\n```source-example\n`HALLUCINATION_CHECK`: FAIL\nA claim was invented.\n```\n', False),
            ('Source example:\n```source-example\n' + report(preservation='FAIL', verdict='REVISE') + '```\n', True),
        )
        for index, (body, available) in enumerate(failures):
            with self.subTest(body=body):
                self.run = self.base / ('entire fenced report {}'.format(index))
                self.call('init', self.run, '--original', self.source)
                candidate = self.candidate()
                review = self.judge_review(candidate, body)
                self.assertEqual(review['analysis']['available'], available)
                self.assertTrue(review['analysis']['hard_fail'])
                self.self_review(candidate)
                self.select(candidate, status=2)
                self.assertEqual(self.result(), self.source_bytes)

    def test_ambiguous_fenced_failure_is_not_silently_exempted(self):
        candidate = self.candidate()
        body = report() + '```text\n**PRESERVATION_CHECK**: FAIL\n```\n'
        review = self.judge_review(candidate, body)
        self.assertFalse(review['analysis']['available'])
        self.assertTrue(review['analysis']['hard_fail'])
        self.self_review(candidate)
        self.select(candidate, status=2)
        self.assertEqual(self.result(), self.source_bytes)

    def test_incomplete_or_misplaced_source_examples_do_not_relax_the_schema(self):
        quotation = 'Source example:\n```text\n**PRESERVATION_CHECK**: FAIL\n```\n'
        bodies = (
            report() + quotation.rsplit('```', 1)[0],
            report().replace('AI_PATTERNS_FOUND: 0\nNone', 'AI_PATTERNS_FOUND: 0\nNone\n' + quotation),
            report().replace('SCORES:\n', 'SCORES:\n' + quotation),
            integrity_report() + quotation,
        )
        for index, body in enumerate(bodies):
            with self.subTest(index=index):
                self.run = self.base / ('unavailable source example {}'.format(index))
                self.call('init', self.run, '--original', self.source)
                candidate = self.candidate()
                review = self.judge_review(candidate, body)
                self.assertFalse(review['analysis']['available'])
                self.assertTrue(review['analysis']['hard_fail'])
                self.self_review(candidate)
                self.select(candidate, status=2)
                self.assertEqual(self.result(), self.source_bytes)

    def test_integrity_only_review_retains_literal_examples_without_inventing_scores(self):
        candidate = self.candidate()
        body = (integrity_report() +
                'Source example:\n```text\nPRESERVATION_CHECK: FAIL\n```\n')
        review = self.self_review(candidate, body)
        self.assertTrue(review['analysis']['available'])
        self.assertFalse(review['analysis']['hard_fail'])
        selected = self.select(candidate)['selected']
        self.assertEqual(selected['editorial_status'], 'unscored')
        self.assertIsNone(selected['total'])
        self.assertEqual((self.run / review['path']).read_bytes(), body.encode('utf-8'))
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_format_repair_retains_literal_source_examples_without_inventing_failure(self):
        candidate = self.candidate()
        quotation = 'Source example:\n```text\nPRESERVATION_CHECK: FAIL\n```\n'
        valid = report() + quotation
        malformed = valid.replace('\n- ', '\n')
        prior = self.self_review(candidate, malformed)
        self.assertFalse(prior['analysis']['available'])
        self.assertFalse(prior['analysis']['hard_fail'])
        before = self.state()
        self.repair_review(candidate, report(), status=2)
        self.assertEqual(self.state(), before)
        repaired = self.repair_review(candidate, valid)
        self.assertTrue(repaired['analysis']['available'])
        self.assertFalse(repaired['analysis']['hard_fail'])
        self.assertEqual((self.run / prior['path']).read_bytes(), malformed.encode('utf-8'))
        self.assertEqual((self.run / repaired['path']).read_bytes(), valid.encode('utf-8'))
        self.select(candidate)
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_format_repair_keeps_actual_decorated_failure_binding(self):
        candidate = self.candidate()
        valid = report(verdict='REVISE') + '**PRESERVATION_CHECK**: FAIL\nA qualification was removed.\n'
        prior = self.self_review(candidate, valid.replace('\n- ', '\n'))
        self.assertTrue(prior['analysis']['hard_fail'])
        before = self.state()
        self.repair_review(candidate, report(), status=2)
        self.assertEqual(self.state(), before)
        repaired = self.repair_review(candidate, valid)
        self.assertTrue(repaired['analysis']['available'])
        self.assertTrue(repaired['analysis']['hard_fail'])
        self.select(candidate, status=2)
        self.assertEqual(self.result(), self.source_bytes)

    def test_missing_judge_output_consumes_attempt_and_keeps_labeled_self_recovery(self):
        candidate = self.candidate()
        self.self_review(candidate)
        ticket = self.reserve('judge', candidate)
        self.call('record', self.run, '--ticket', ticket, '--unavailable',
                  '--reason', 'The host returned no independent report.')
        self.select(candidate)
        state = self.state()
        self.assertEqual(state['counts']['judge'], 1)
        self.assertEqual(state['selected']['independent_status'], 'unavailable')
        self.assertIn('self', state['selected']['verification'])
        self.call('record', self.run, '--ticket', ticket, '--unavailable',
                  '--reason', 'The same attempt must not be reset.', status=2)

    def test_missing_writer_output_consumes_initial_attempt_and_retains_source(self):
        ticket = self.reserve('initial')
        self.call('record', self.run, '--ticket', ticket, '--unavailable',
                  '--reason', 'The host returned no writer artifact.')
        self.assertEqual(self.result(), self.source_bytes)
        self.assertEqual(self.state()['counts']['initial'], 1)
        self.call('reserve', self.run, '--kind', 'initial', '--reason',
                  'An unavailable draft must not reset the initial attempt.', status=2)

    def test_score_and_finding_inconsistencies_are_unavailable(self):
        fixtures = [
            report(total=41),
            report(score=11),
            report(count=1),
            report(findings=['A location is mentioned without a tier or severity.']),
            report().replace('PRESERVATION_CHECK: PASS', 'PRESERVATION_CHECK: PASS\nPRESERVATION_CHECK: FAIL'),
        ]
        for index, body in enumerate(fixtures):
            with self.subTest(index=index):
                self.run = self.base / ('invalid review run {}'.format(index))
                self.call('init', self.run, '--original', self.source)
                candidate = self.candidate()
                self.self_review(candidate, body)
                state = self.state()
                self.assertTrue(any(review['analysis']['available'] is False for review in state['reviews']))
                self.select(candidate, status=2)
                self.assertEqual(self.result(), self.source_bytes)

    def test_format_repair_retains_raw_reports_provenance_and_candidate_bytes(self):
        candidate_bytes = b'A source-faithful candidate with a deliberately retained repeat.\r\n'
        candidate = self.candidate(candidate_bytes)
        explanation = 'None. The retained repeat serves a separate checklist entry point.'
        malformed = report().replace('None\n', explanation + '\n')
        self.self_review(candidate, malformed)
        before = self.state()
        original_review = before['reviews'][-1]
        self.assertFalse(original_review['analysis']['available'])
        self.select(candidate, status=2)
        repaired = report() + '\n' + explanation + '\n'
        self.repair_review(candidate, repaired)
        after = self.state()
        self.assertEqual(after['counts'], before['counts'])
        self.assertEqual(len(after['reviews']), len(before['reviews']) + 1)
        self.assertEqual((self.run / original_review['path']).read_bytes(), malformed.encode('utf-8'))
        repair = after['reviews'][-1]
        self.assertEqual((self.run / repair['path']).read_bytes(), repaired.encode('utf-8'))
        self.assertEqual(repair['format_repair_of'], original_review['id'])
        self.assertTrue(repair['format_repair_reason'])
        self.assertTrue(repair['analysis']['available'])
        self.assertEqual(repair['candidate'], candidate)
        self.assertEqual(repair['candidate_sha256'], original_review['candidate_sha256'])
        self.select(candidate)
        self.assertEqual(self.result(), candidate_bytes)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)
        self.assertIn('self', self.state()['selected']['verification'])
        self.assertEqual(self.state()['selected']['total'], 40)

    def test_format_repair_accepts_explicit_zero_tier_totals_and_missing_score_bullets(self):
        candidate = self.candidate()
        malformed = report().replace('AI_PATTERNS_FOUND: 0\nNone',
                                     'AI_PATTERNS_FOUND:\nTier 1: 0\nTier 2: 0\nNone')
        malformed = malformed.replace('\n- ', '\n')
        self.self_review(candidate, malformed)
        self.assertFalse(self.state()['reviews'][-1]['analysis']['available'])
        repaired = report() + '\nTier 1: 0\nTier 2: 0\n'
        self.repair_review(candidate, repaired)
        self.select(candidate)
        state = self.state()
        self.assertEqual(state['selected']['verdict'], 'PASS')
        self.assertEqual(state['selected']['total'], 40)
        self.assertEqual(state['counts']['self_revision'], 0)
        self.assertEqual(state['counts']['judge'], 0)

    def test_format_repair_preserves_a_real_minor_finding(self):
        finding = 'Tier 2 minor Pattern 17: "very" adds empty emphasis.'
        canonical = report(findings=[finding])
        candidate = self.candidate()
        self.self_review(candidate, canonical.replace('\n- ', '\n'))
        self.assertFalse(self.state()['reviews'][-1]['analysis']['available'])
        self.repair_review(candidate, canonical)
        self.select(candidate)
        state = self.state()
        self.assertEqual(state['selected']['total'], 40)
        self.assertIn(json.dumps(finding.split('minor ', 1)[1]), (self.run / state['reviews'][-1]['path']).read_text())

    def test_only_one_successful_format_repair_is_available(self):
        candidate = self.candidate()
        self.self_review(candidate, report().replace('\n- ', '\n'))
        self.repair_review(candidate, report())
        self.select(candidate)
        before = self.state()
        self.repair_review(candidate, report(), status=2)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_format_repair_needs_a_valid_layout_and_explicit_reason(self):
        candidate = self.candidate()
        malformed = report().replace('\n- ', '\n')
        self.self_review(candidate, malformed)
        before = self.state()
        self.repair_review(candidate, malformed, status=2)
        self.assertEqual(self.state(), before)
        for reason in (None, ''):
            with self.subTest(reason=reason):
                args = ['self-check', self.run, '--candidate', candidate,
                        '--report', self.file(report()), '--repair-format']
                if reason is not None:
                    args += ['--reason', reason]
                self.call(*args, status=2)
                self.assertEqual(self.state(), before)
                self.assertEqual(self.result(), self.source_bytes)
        self.repair_review(candidate, report())
        self.select(candidate)
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_format_repair_cannot_replace_an_available_self_review(self):
        candidate = self.candidate()
        self.self_review(candidate)
        self.select(candidate)
        before = self.state()
        self.repair_review(candidate, report(), status=2)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_format_repair_cannot_launder_an_explicit_hard_failure(self):
        candidate = self.candidate()
        failed = report(preservation='FAIL', verdict='REVISE')
        self.self_review(candidate, failed.replace('\n- ', '\n'))
        before = self.state()
        self.repair_review(candidate, report(), status=2)
        self.assertEqual(self.state(), before)
        self.select(candidate, status=2)
        self.assertEqual(self.result(), self.source_bytes)
        self.repair_review(candidate, failed)
        self.assertTrue(self.state()['reviews'][-1]['analysis']['available'])
        self.select(candidate, status=2)
        self.assertEqual(self.result(), self.source_bytes)

    def test_format_repair_cannot_change_scores_outcome_or_findings(self):
        finding = 'Tier 2 minor Pattern 17: "very" adds empty emphasis.'
        canonical = report(findings=[finding])
        alterations = [
            report(score=9, findings=[finding]),
            report(score=6, verdict='REVISE', findings=[finding]),
            report(),
            report(findings=['Tier 2 minor Pattern 17: finding evidence omitted.']),
            report(findings=['Tier 2 minor Pattern 17: "slightly" adds empty emphasis.']),
        ]
        for index, altered in enumerate(alterations):
            with self.subTest(index=index):
                self.run = self.base / ('forbidden review change {}'.format(index))
                self.call('init', self.run, '--original', self.source)
                candidate = self.candidate()
                self.self_review(candidate, canonical.replace('\n- ', '\n'))
                before = self.state()
                self.repair_review(candidate, altered, status=2)
                self.assertEqual(self.state(), before)
                self.select(candidate, status=2)
                self.assertEqual(self.result(), self.source_bytes)

    def test_format_repair_cannot_manufacture_missing_or_ambiguous_decisions(self):
        valid = report()
        invalid = [
            valid.replace('VERDICT: PASS\n', ''),
            valid.replace('- Total: 40/50\n', ''),
            valid.replace('PRESERVATION_CHECK: PASS\n', ''),
            valid.replace('AI_PATTERNS_FOUND: 0\nNone', 'AI_PATTERNS_FOUND:\nNone'),
            valid.replace('PRESERVATION_CHECK: PASS',
                          'PRESERVATION_CHECK: PASS\nPRESERVATION_CHECK: FAIL'),
            valid.replace('VERDICT: PASS', 'VERDICT: PASS\nVERDICT: REVISE'),
        ]
        for index, malformed in enumerate(invalid):
            with self.subTest(index=index):
                self.run = self.base / ('missing review decision {}'.format(index))
                self.call('init', self.run, '--original', self.source)
                candidate = self.candidate()
                self.self_review(candidate, malformed)
                before = self.state()
                self.assertFalse(before['reviews'][-1]['analysis']['available'])
                self.repair_review(candidate, valid, status=2)
                self.assertEqual(self.state(), before)
                self.assertEqual(self.result(), self.source_bytes)

    def test_failed_format_repair_keeps_the_selected_result_usable(self):
        accepted_bytes = b'A faithful previously selected result.\n'
        accepted = self.candidate(accepted_bytes)
        self.self_review(accepted)
        self.select(accepted)
        pending = self.candidate(b'A checked but malformed-report candidate.\n', kind='self-revision')
        self.self_review(pending, report().replace('\n- ', '\n'))
        before = self.state()
        self.repair_review(pending, report(score=9), status=2)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.result(), accepted_bytes)
        self.assertEqual(self.state()['selected']['candidate'], accepted)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_valid_independent_review_is_retained_as_independent(self):
        candidate_bytes = b'A complete independently reviewed fixture.\n'
        candidate = self.candidate(candidate_bytes)
        self.judge_review(candidate)
        self.select(candidate)
        self.assertEqual(self.result(), candidate_bytes)
        self.assertIn('independent', json.dumps(self.state()['selected']).lower())

    def test_crlf_review_is_valid_and_raw_review_bytes_are_retained(self):
        candidate = self.candidate()
        raw_report = report().replace('\n', '\r\n').encode('utf-8')
        self.judge_review(candidate, raw_report)
        self.select(candidate)
        state = self.state()
        self.assertIn('independent', state['selected']['verification'])
        review = state['reviews'][-1]
        self.assertTrue(review['analysis']['available'])
        self.assertEqual((self.run / review['path']).read_bytes(), raw_report)
        self.assertEqual(review['candidate'], candidate)

    def test_failed_promotion_leaves_previous_state_usable_for_supported_recovery(self):
        accepted_bytes = b'A retained checked draft.\n'
        accepted = self.candidate(accepted_bytes)
        self.self_review(accepted)
        self.select(accepted)
        candidate_bytes = b'A new draft awaiting its actual review.\n'
        candidate = self.candidate(candidate_bytes, kind='self-revision')
        self.select(candidate, status=2)
        self.assertEqual(self.result(), accepted_bytes)
        state = self.state()
        self.assertTrue(state['selected']['eligible'])
        self.assertEqual(state['selected']['candidate'], accepted)
        self.self_review(candidate)
        self.select(candidate)
        self.assertEqual(self.result(), candidate_bytes)

    def test_style_only_shortfall_remains_returnable_with_actual_status(self):
        candidate_bytes = b'A faithful draft with a disclosed style shortfall.\n'
        candidate = self.candidate(candidate_bytes)
        self.self_review(candidate, report(score=6, quality='FAIL', verdict='REVISE'))
        self.select(candidate)
        self.assertEqual(self.result(), candidate_bytes)
        selected = json.dumps(self.state()['selected']).lower()
        self.assertTrue('revise' in selected or 'below' in selected or 'shortfall' in selected, selected)

    def test_short_text_integrity_only_recovery_does_not_invent_a_score(self):
        candidate = self.candidate()
        self.self_review(candidate, integrity_report())
        self.select(candidate)
        selected = self.state()['selected']
        self.assertEqual(selected['editorial_status'], 'unscored')
        self.assertIsNone(selected['total'])
        self.assertIn('self', selected['verification'])

    def test_shortening_candidate_cannot_skip_scoring_required_by_source_length(self):
        long_source = self.file(('The source claim may remain qualified.\n' * 25).encode('utf-8'))
        self.run = self.base / 'long source run'
        self.call('init', self.run, '--original', long_source)
        candidate = self.candidate(b'Short candidate.\n')
        self.self_review(candidate, integrity_report())
        self.select(candidate, status=2)
        self.assertEqual(self.result(), long_source.read_bytes())

    def test_later_hard_failure_requires_explicit_recovery_before_output(self):
        candidate = self.candidate()
        self.self_review(candidate)
        self.select(candidate)
        self.judge_review(candidate, report(preservation='FAIL', verdict='REVISE'))
        self.call('result', self.run, status=2)
        self.select('original')
        self.assertEqual(self.result(), self.source_bytes)

    def test_self_revision_budget_is_shared_and_cannot_be_reset(self):
        self.candidate()
        self.candidate(b'First supported revision.\n', kind='self-revision')
        self.candidate(b'Second supported revision.\n', kind='self-revision')
        self.call('reserve', self.run, '--kind', 'self-revision', '--reason', 'Third revision.', status=2)
        self.call('init', self.run, '--original', self.source, status=2)
        self.call('reserve', self.run, '--kind', 'initial', '--reason', 'Reset as another initial draft.', status=2)
        counts = self.state()['counts']
        self.assertEqual(counts['initial'], 1)
        self.assertEqual(counts['self_revision'], 2)

    def test_judge_and_judge_revision_budgets_are_bounded(self):
        first = self.candidate()
        self.judge_review(first, report(preservation='FAIL', score=6, verdict='REVISE'))
        revised = self.candidate(b'A correction addressing the requested review.\n', kind='judge-revision')
        self.judge_review(revised)
        self.call('reserve', self.run, '--kind', 'judge', '--candidate', revised,
                  '--reason', 'Third independent assessment.', status=2)
        self.call('reserve', self.run, '--kind', 'judge-revision',
                  '--reason', 'Second judge correction.', status=2)
        counts = self.state()['counts']
        self.assertEqual(counts['judge'], 2)
        self.assertEqual(counts['judge_revision'], 1)
        self.assertEqual(counts['self_revision'], 0)

    def test_judge_revision_needs_an_actual_revision_request(self):
        candidate = self.candidate()
        self.judge_review(candidate)
        self.call('reserve', self.run, '--kind', 'judge-revision',
                  '--reason', 'No reviewer requested a correction.', status=2)
        self.assertEqual(self.state()['counts']['judge_revision'], 0)

    def test_valid_independent_pass_closes_all_reservations_without_mutation(self):
        candidate = self.candidate()
        self.self_review(candidate)
        self.judge_review(candidate)
        self.select(candidate)
        before = {str(path.relative_to(self.run)): path.read_bytes()
                  for path in self.run.rglob('*') if path.is_file()}
        for kind in ('initial', 'self-revision', 'judge-revision', 'judge'):
            with self.subTest(kind=kind):
                arguments = ['reserve', self.run, '--kind', kind,
                             '--reason', 'A valid independent PASS must close this run.']
                if kind == 'judge':
                    arguments += ['--candidate', candidate]
                failure = self.call(*arguments, status=2)
                self.assertIn(b'valid independent PASS closes further reservations', failure.stderr)
                self.assertEqual({str(path.relative_to(self.run)): path.read_bytes()
                                  for path in self.run.rglob('*') if path.is_file()}, before)
        self.assertEqual(self.state()['counts'], {'initial': 1, 'self_revision': 0,
                                               'judge_revision': 0, 'judge': 1})
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_known_hard_failure_bytes_cannot_gain_a_judge_correction_allowance(self):
        failures = (report(preservation='FAIL', verdict='REVISE'),
                    '**HALLUCINATION_CHECK**: FAIL\nThe candidate added unsupported certainty.\n')
        for index, body in enumerate(failures):
            with self.subTest(index=index):
                self.run = self.base / ('known failure gate {}'.format(index))
                self.call('init', self.run, '--original', self.source)
                bad_bytes = b'The team will test again.\n'
                initial = self.candidate(bad_bytes)
                adverse = self.self_review(initial, body)
                self.assertTrue(adverse['analysis']['hard_fail'])
                same_bytes = self.candidate(bad_bytes, kind='self-revision')
                self.self_review(same_bytes)
                before = (self.run / 'state.json').read_bytes()
                for candidate in (initial, same_bytes):
                    failure = self.call('reserve', self.run, '--kind', 'judge',
                                        '--candidate', candidate, '--reason',
                                        'Known hard failures must be repaired before judging.', status=2)
                    self.assertIn(b'known hard-failure bytes cannot be sent to a judge', failure.stderr)
                    self.assertEqual((self.run / 'state.json').read_bytes(), before)
                self.call('reserve', self.run, '--kind', 'judge-revision', '--reason',
                          'No actual independent REVISE exists.', status=2)
                self.assertEqual((self.run / 'state.json').read_bytes(), before)
                self.assertEqual(self.state()['counts']['judge'], 0)
                self.assertEqual(self.state()['counts']['judge_revision'], 0)
                corrected_bytes = b'The team may test again.\n'
                corrected = self.candidate(corrected_bytes, kind='self-revision')
                self.self_review(corrected)
                self.judge_review(corrected)
                self.select(corrected)
                self.assertEqual(self.result(), corrected_bytes)
                self.assertEqual((self.run / adverse['path']).read_bytes(), body.encode('utf-8'))
                self.assertEqual((self.run / 'drafts' / (initial + '.txt')).read_bytes(), bad_bytes)
                self.assertEqual((self.run / 'drafts' / (same_bytes + '.txt')).read_bytes(), bad_bytes)
                self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_pending_attempt_blocks_new_reservations_and_promotion_without_mutation(self):
        candidate = self.candidate()
        self.self_review(candidate)
        self.select(candidate)
        ticket = self.reserve('self-revision')
        before = (self.run / 'state.json').read_bytes()
        self.call('reserve', self.run, '--kind', 'judge', '--candidate', candidate,
                  '--reason', 'A pending writer attempt must finish first.', status=2)
        self.select(candidate, status=2)
        self.assertEqual((self.run / 'state.json').read_bytes(), before)
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')
        self.call('record', self.run, '--ticket', ticket, '--unavailable',
                  '--reason', 'The reserved writer returned no artifact.')
        self.assertEqual(self.state()['counts']['self_revision'], 1)
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_existing_lock_refuses_commands_without_removing_the_lock(self):
        lock = self.run / '.lock'
        lock.write_bytes(b'Another command owns this lock.\n')
        before = (self.run / 'state.json').read_bytes()
        self.call('status', self.run, status=2)
        self.call('reserve', self.run, '--kind', 'initial', '--reason',
                  'This attempt must not bypass an active lock.', status=2)
        self.assertEqual(lock.read_bytes(), b'Another command owns this lock.\n')
        self.assertEqual((self.run / 'state.json').read_bytes(), before)
        lock.unlink()
        self.assertEqual(self.state()['counts']['initial'], 0)
        self.assertEqual(self.result(), self.source_bytes)

    def test_checksum_damage_stops_the_run_and_preserves_the_source(self):
        for name in ('state.json', 'state.sha256'):
            with self.subTest(name=name):
                path = self.run / name
                before = path.read_bytes()
                path.write_bytes(before + b'corruption')
                failure = self.call('result', self.run, status=2)
                self.assertIn(b'state checksum mismatch', failure.stderr)
                self.assertFalse((self.run / '.lock').exists())
                self.assertEqual(self.source.read_bytes(), self.source_bytes)
                path.write_bytes(before)
        self.assertEqual(self.result(), self.source_bytes)

    def test_corrupt_state_content_fails_cleanly_even_with_a_matching_checksum(self):
        state_path = self.run / 'state.json'
        checksum_path = self.run / 'state.sha256'
        original_state = state_path.read_bytes()
        original_checksum = checksum_path.read_bytes()
        wrong_shape = json.loads(original_state)
        wrong_shape['reviews'] = None
        fixtures = (b'{', b'{"version":1,"version":1}', json.dumps(wrong_shape).encode('utf-8'))
        for index, data in enumerate(fixtures):
            with self.subTest(index=index):
                state_path.write_bytes(data)
                checksum_path.write_text(hashlib.sha256(data).hexdigest() + '\n')
                failure = self.call('result', self.run, status=2)
                self.assertNotIn(b'Traceback', failure.stderr)
                self.assertFalse((self.run / '.lock').exists())
                self.assertEqual(self.source.read_bytes(), self.source_bytes)
        state_path.write_bytes(original_state)
        checksum_path.write_bytes(original_checksum)
        self.assertEqual(self.result(), self.source_bytes)

    def test_score_disagreement_is_descriptive_without_downgrading_judge_pass(self):
        for index, self_score in enumerate((4, 6)):
            with self.subTest(self_score=self_score):
                self.run = self.base / ('score disagreement {}'.format(index))
                self.call('init', self.run, '--original', self.source)
                candidate = self.candidate()
                self.self_review(candidate, report(score=self_score))
                self.judge_review(candidate, report(score=8))
                selected = self.select(candidate)['selected']
                self.assertEqual(selected['self_total'], self_score * 5)
                self.assertEqual(selected['independent_total'], 40)
                self.assertEqual(selected['review_total'], 40)
                self.assertEqual(selected['review_verdict'], 'PASS')
                self.assertEqual(selected['verification'], 'independent')
                self.assertEqual(selected['total'], 40)
                self.assertEqual(selected['editorial_status'], 'passed')
                self.assertEqual(selected['verdict'], 'PASS')
                self.assertNotIn('score_basis', selected)

    def test_recorded_revisions_remain_selectable_with_their_own_reviews(self):
        initial = self.candidate()
        self.self_review(initial)
        self.select(initial)
        middle = self.candidate(b'A first supported revision.\n', kind='self-revision')
        self.self_review(middle)
        current = self.candidate(b'A second supported revision.\n', kind='self-revision')
        self.self_review(current)
        self.assertEqual(self.state()['selected']['candidate'], initial)
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')
        stored = json.loads((self.run / 'state.json').read_bytes())
        for identifier, expected in ((initial, b'A faithful fixture candidate.\n'),
                                     (middle, b'A first supported revision.\n'),
                                     (current, b'A second supported revision.\n')):
            relative = 'drafts/' + identifier + '.txt'
            self.assertEqual((self.run / relative).read_bytes(), expected)
            self.assertEqual(stored['files'][relative], hashlib.sha256(expected).hexdigest())
        self.assertEqual(len(stored['reviews']), 3)
        selected = self.select(middle)['selected']
        self.assertEqual(selected['review'], 'self-' + middle)
        self.assertEqual(Path(selected['path']), self.run.resolve() / 'drafts' / (middle + '.txt'))
        self.assertEqual(self.result(), b'A first supported revision.\n')
        self.select(current)
        self.assertEqual(self.result(), b'A second supported revision.\n')
        self.select(initial)
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_prior_state_versions_are_rejected_without_reset_or_migration(self):
        path = self.run / 'state.json'
        state = json.loads(path.read_bytes())
        for version in (1, 2):
            state['version'] = version
            data = json.dumps(state).encode()
            path.write_bytes(data)
            (self.run / 'state.sha256').write_text(hashlib.sha256(data).hexdigest())
            failure = self.call('status', self.run, status=2)
            self.assertIn(b'unsupported state version', failure.stderr)
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_unselected_archive_tampering_blocks_output_without_slot_fallback(self):
        initial = self.candidate()
        self.self_review(initial)
        self.select(initial)
        middle = self.candidate(b'A separately retained revision.\n', kind='self-revision')
        self.self_review(middle)
        self.candidate(b'The current candidate has different bytes.\n', kind='self-revision')
        archive = self.run / 'drafts' / (middle + '.txt')
        archive.write_bytes(b'Altered archived evidence.\n')
        failure = self.call('result', self.run, status=2)
        self.assertIn(b'artifact checksum mismatch: drafts/', failure.stderr)
        self.assertEqual((self.run / 'accepted.txt').read_bytes(), b'A faithful fixture candidate.\n')
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_recording_cannot_overwrite_an_existing_candidate_archive(self):
        ticket = self.reserve('initial')
        directory = self.run / 'drafts'
        directory.mkdir()
        archive = directory / (ticket + '.txt')
        retained = b'Preexisting candidate evidence must remain intact.\n'
        archive.write_bytes(retained)
        before = (self.run / 'state.json').read_bytes()
        failure = self.call('record', self.run, '--ticket', ticket,
                            '--text', self.file(b'Different supplied candidate.\n'), status=2)
        self.assertIn(b'candidate archive already exists', failure.stderr)
        self.assertEqual(archive.read_bytes(), retained)
        self.assertEqual((self.run / 'state.json').read_bytes(), before)
        self.assertFalse((self.run / 'candidate.txt').exists())
        self.assertEqual(self.state()['counts']['initial'], 1)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_report_tampering_blocks_output_instead_of_reusing_saved_analysis(self):
        candidate = self.candidate()
        self.self_review(candidate)
        self.select(candidate)
        review_path = self.run / self.state()['reviews'][0]['path']
        review_path.write_bytes(review_path.read_bytes() + b'Changed retained evidence.\n')
        failure = self.call('result', self.run, status=2)
        self.assertIn(b'artifact checksum mismatch', failure.stderr)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_candidate_ticket_cannot_be_reused_to_replace_recorded_text(self):
        candidate = self.candidate()
        self.call('record', self.run, '--ticket', candidate,
                  '--text', self.file(b'Different unreviewed bytes.\n'), status=2)
        self.self_review(candidate)
        self.select(candidate)
        self.assertEqual(self.result(), b'A faithful fixture candidate.\n')

    def test_tampered_original_snapshot_is_not_returned_as_valid_output(self):
        snapshot = Path(self.state()['original']['path'])
        self.assertNotEqual(snapshot, self.source)
        snapshot.write_bytes(b'Altered retained original.\n')
        self.call('result', self.run, status=2)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_tampered_selected_snapshot_is_not_silently_returned(self):
        candidate = self.candidate()
        self.self_review(candidate)
        self.select(candidate)
        snapshot = Path(self.state()['selected']['path'])
        snapshot.write_bytes(b'Altered accepted artifact.\n')
        self.call('result', self.run, status=2)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_export_preserves_exact_bytes_and_refuses_existing_files(self):
        candidate_bytes = 'Русский текст — без нормализации.\r\n\r\nA caveat may apply.\r\n'.encode('utf-8')
        candidate = self.candidate(candidate_bytes)
        self.self_review(candidate)
        self.select(candidate)
        output = self.base / 'result with spaces.txt'
        self.call('result', self.run, '--output', output)
        self.assertEqual(output.read_bytes(), candidate_bytes)
        self.assertEqual(self.result(), candidate_bytes)
        self.call('result', self.run, '--output', self.source, status=2)
        self.call('result', self.run, '--output', output, status=2)
        before = self.state()
        inside = self.run / 'export.txt'
        rejected = self.call('result', self.run, '--output', inside, status=2)
        self.assertIn(b'export destination must be outside the run directory', rejected.stderr)
        self.assertFalse(inside.exists())
        self.assertEqual(self.state(), before)
        self.assertEqual(self.result(), candidate_bytes)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)
        self.assertEqual(output.read_bytes(), candidate_bytes)


if __name__ == '__main__':
    unittest.main(verbosity=2)
