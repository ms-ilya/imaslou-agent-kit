#!/usr/bin/env python3
# ABOUTME: Checks frozen scope, risk routing, objective reporting and bounded diagnostics using deterministic offline fixtures.

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from humanizer_fixtures import plan_for, mapping_for, integrity_report, OBJECTIVE_LINE
from test_humanizer_stages import report


ROOT = Path(__file__).resolve().parents[1] / 'plugins/humanizer'


def module(name):
    spec = importlib.util.spec_from_file_location('fixture_' + name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class PreservationContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stages = module('stages')
        cls.contracts = cls.stages.contracts

    def test_complete_source_partition_and_utf8_boundaries(self):
        source = 'А.\r\nLate condition.\n'.encode()
        plan = plan_for(source)
        self.contracts.validate_plan(plan, source)
        for key, value in (('start', 1), ('end', len(source) - 1), ('end', 1)):
            broken = copy.deepcopy(plan)
            broken['units'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.contracts.validate_plan(broken, source)
        broken = copy.deepcopy(plan)
        broken['source_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.contracts.validate_plan(broken, source)

    def test_source_roles_are_semantic_constraints_not_automatic_word_locks(self):
        source = b'Logs suggest that work may stop.\n'
        candidate = b'The logs suggest a possible work stoppage.\n'
        plan = plan_for(source)
        plan['anchors'] = [{'id': 'a1', 'spans': [{'start': 0, 'end': len(source)}],
                            'question': 'Which evidence and possibility does the source supply?'}]
        self.assertEqual(self.contracts.mapping_errors(plan, source, candidate, mapping_for(source, candidate)), [])
        # Byte validation deliberately does not claim this is a semantic PASS.
        self.assertNotIn('preservation', self.contracts.validate_plan(plan, source))

    def test_frozen_unchanged_intensity_cannot_record_an_eligible_rewrite(self):
        source, candidate = b'Keep this.', b'Keep these words.'
        plan = plan_for(source)
        plan['brief']['intensity'] = 'unchanged'
        plan['brief'].update(objectives=[], no_change_reason='Retain the source.')
        self.assertTrue(self.contracts.mapping_errors(plan, source, candidate, mapping_for(source, candidate)))
        self.assertEqual(self.contracts.mapping_errors(plan, source, source, mapping_for(source, source)), [])

    def test_fixed_scope_retains_exact_unicode_and_crlf_after_recomposition(self):
        source = 'Intro.\r\n`x = е́`\r\nEnding.\n'.encode()
        candidate = 'A revised introduction.\r\n`x = е́`\r\nEnding.\n'.encode()
        fixed = source[source.index(b'`'):]
        plan = plan_for(source)
        plan['fixed'] = [{'id': 'p1', 'start': source.index(b'`'), 'end': len(source), 'kind': 'out-of-scope'}]
        mapping = mapping_for(source, candidate)
        mapping['fixed'] = [{'id': 'p1', 'start': candidate.index(b'`'), 'end': len(candidate)}]
        self.assertEqual(self.contracts.mapping_errors(plan, source, candidate, mapping), [])
        for changed in (candidate.replace(b'\r\n', b'\n'), candidate.replace('е́'.encode(), 'é'.encode()), candidate + fixed):
            bad = mapping_for(source, changed)
            bad['fixed'] = [{'id': 'p1', 'start': changed.index(b'`'), 'end': len(changed)}]
            self.assertTrue(self.contracts.mapping_errors(plan, source, changed, bad))

    def test_duplicate_fixed_occurrences_cannot_share_one_candidate_span(self):
        source = b'X X'
        plan = plan_for(source)
        plan['fixed'] = [{'id': 'p1', 'start': 0, 'end': 1, 'kind': 'verbatim'},
                         {'id': 'p2', 'start': 2, 'end': 3, 'kind': 'verbatim'}]
        mapping = mapping_for(source, b'X')
        mapping['fixed'] = [{'id': 'p1', 'start': 0, 'end': 1}, {'id': 'p2', 'start': 0, 'end': 1}]
        self.assertTrue(self.contracts.mapping_errors(plan, source, b'X', mapping))

    def test_new_text_cannot_escape_editable_section_at_fixed_boundaries(self):
        source = b'LOCK edit END'
        plan = plan_for(source)
        plan['fixed'] = [{'id': 'p1', 'start': 0, 'end': 5, 'kind': 'out-of-scope'},
                         {'id': 'p2', 'start': 9, 'end': 13, 'kind': 'out-of-scope'}]
        for candidate in (b'new LOCK edit END', b'LOCK edit END new'):
            mapping = mapping_for(source, candidate)
            mapping['fixed'] = [{'id': 'p1', 'start': candidate.index(b'LOCK'), 'end': candidate.index(b'LOCK') + 5},
                                {'id': 'p2', 'start': candidate.index(b' END'), 'end': candidate.index(b' END') + 4}]
            self.assertTrue(self.contracts.mapping_errors(plan, source, candidate, mapping))

    def test_candidate_maps_require_all_source_units_and_all_candidate_bytes(self):
        source, candidate = b'First. Last.', b'First and last.'
        plan = plan_for(source)
        plan['units'] = [dict(plan['units'][0], end=7), dict(plan['units'][0], id='u2', start=7)]
        mapping = mapping_for(source, candidate)
        self.assertTrue(self.contracts.mapping_errors(plan, source, candidate, mapping))
        mapping['units'][0]['source_units'].append('u2')
        self.assertEqual(self.contracts.mapping_errors(plan, source, candidate, mapping), [])
        mapping['units'][0]['end'] -= 1
        self.assertTrue(self.contracts.mapping_errors(plan, source, candidate, mapping))

    def test_each_review_direction_and_objective_must_have_full_coverage(self):
        source = b'Fixture.'
        plan, mapping = plan_for(source), mapping_for(source, source)
        analysis = self.stages.parse_report(report().encode(), 'self', True)
        self.assertEqual(self.contracts.review_errors(analysis, plan, mapping), [])
        for direction in ('source', 'candidate'):
            broken = copy.deepcopy(analysis)
            broken['coverage'][direction] = []
            self.assertTrue(self.contracts.review_errors(broken, plan, mapping))
        plan['brief']['objectives'] = [{'id': 'o1', 'source_units': ['u1'], 'issue': 'Opening hides the condition.', 'action': 'Bring condition beside decision.'}]
        self.assertTrue(self.contracts.review_errors(analysis, plan, mapping))

    def test_quoted_tier_and_severity_words_are_only_evidence(self):
        finding = {'tier': 2, 'severity': 'minor', 'pattern': '17',
                   'quote': 'The minor Tier 1 issue was substantial.', 'reason': 'Repeats a prior claim; "minor" is source wording.'}
        analysis = self.stages.parse_report(report(findings=[finding]).encode(), 'judge', False)
        self.assertTrue(analysis['available'], analysis)
        self.assertEqual(analysis['verdict'], 'PASS')
        malformed = report(findings=[dict(finding, tier=1)], verdict='PASS')
        self.assertFalse(self.stages.parse_report(malformed.encode(), 'judge', False)['available'])

    def test_critical_rhythm_or_authenticity_cannot_be_compensated(self):
        for dimension in ('Rhythm', 'Authenticity'):
            finding = {'tier': 2, 'severity': 'substantial', 'pattern': dimension,
                       'quote': 'Synthetic passage.', 'reason': 'Synthetic critical reader-facing failure.'}
            body = report(score=10, quality='FAIL', findings=[finding])
            self.assertFalse(self.stages.parse_report(body.encode(), 'judge', False)['available'])
            self.assertTrue(self.stages.parse_report(body.replace('VERDICT: PASS', 'VERDICT: REVISE').encode(), 'judge', False)['available'])

    def test_unresolved_objectives_and_quality_never_become_an_editorial_pass(self):
        for replacement in ('QUALITY_CHECK: FAIL', 'OBJECTIVES: [{"id":"o1","status":"unresolved","evidence":"Condition is still distant from the decision."}]'):
            label = replacement.split(':')[0]
            body = report(score=10).replace('QUALITY_CHECK: PASS' if label == 'QUALITY_CHECK' else OBJECTIVE_LINE, replacement)
            self.assertFalse(self.stages.parse_report(body.encode(), 'judge', False)['available'])
            analysis = self.stages.parse_report(body.replace('VERDICT: PASS', 'VERDICT: REVISE').encode(), 'judge', False)
            self.assertTrue(analysis['available'])
            self.assertEqual(analysis['editorial_status'], 'style-shortfall')

    def test_unscored_short_text_preserves_unresolved_status(self):
        body = integrity_report().replace('QUALITY_CHECK: PASS', 'QUALITY_CHECK: FAIL')
        analysis = self.stages.parse_report(body.encode(), 'self', True)
        self.assertTrue(analysis['available'])
        self.assertEqual(analysis['editorial_status'], 'style-shortfall')
        self.assertIsNone(analysis['total'])

    def test_risk_routing_does_not_depend_on_scores(self):
        plan = plan_for(b'Short.')
        self.assertFalse(self.contracts.judge_required(plan, 100))
        self.assertTrue(self.contracts.judge_required(plan, 2001))
        for risk in self.contracts.RISKS:
            changed = copy.deepcopy(plan)
            changed['brief']['risks'] = [risk]
            self.assertTrue(self.contracts.judge_required(changed, 5))
        plan['brief']['languages'] = ['en', 'ru']
        self.assertTrue(self.contracts.judge_required(plan, 5))


class KeeperPrerequisites(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.run = self.base / 'run'

    def call(self, *args, status=0):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/stages.py'), *map(str, args)],
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, status, result.stderr.decode())
        return json.loads(result.stdout) if not status else result.stderr.decode()

    def start(self, source=b'The team may test.', risk=None, fixed=False):
        (self.base / 'source').write_bytes(source)
        plan = plan_for(source)
        if risk:
            plan['brief']['risks'] = [risk]
        if fixed:
            plan['fixed'] = [{'id': 'p1', 'start': 0, 'end': len(source), 'kind': 'out-of-scope'}]
        (self.base / 'plan').write_text(json.dumps(plan))
        self.call('init', self.run, '--original', self.base / 'source', '--plan', self.base / 'plan')
        ticket = self.call('reserve', self.run, '--kind', 'initial', '--reason', 'Synthetic offline fixture.')['ticket']
        mapping = mapping_for(source, source)
        if fixed:
            mapping['fixed'] = [{'id': 'p1', 'start': 0, 'end': len(source) - 1}]
        (self.base / 'map').write_text(json.dumps(mapping))
        self.call('record', self.run, '--ticket', ticket, '--text', self.base / 'source', '--mapping', self.base / 'map')
        return ticket

    def review(self, ticket, body=None):
        (self.base / 'report').write_text(report() if body is None else body)
        return self.call('self-check', self.run, '--candidate', ticket, '--report', self.base / 'report')

    def test_judge_cannot_precede_complete_self_review(self):
        ticket = self.start()
        failure = self.call('reserve', self.run, '--kind', 'judge', '--candidate', ticket, '--reason', 'Fixture.', status=2)
        self.assertIn('complete a valid self-check', failure)
        self.assertEqual(self.call('status', self.run)['counts']['judge'], 0)
        self.review(ticket)
        self.call('reserve', self.run, '--kind', 'judge', '--candidate', ticket, '--reason', 'Fixture.')

    def test_long_document_cannot_export_without_required_attempt(self):
        ticket = self.start(source=('word ' * 2101).encode())
        self.review(ticket)
        failure = self.call('select', self.run, '--candidate', ticket, '--decision', 'promote', '--reason', 'Fixture.', status=2)
        self.assertIn('required independent attempt', failure)

    def test_required_risk_review_can_be_unavailable_but_never_labeled_independent(self):
        ticket = self.start(risk='structural-recomposition')
        self.review(ticket)
        self.call('select', self.run, '--candidate', ticket, '--decision', 'promote', '--reason', 'Fixture.', status=2)
        judge = self.call('reserve', self.run, '--kind', 'judge', '--candidate', ticket, '--reason', 'Risk requires review.')['ticket']
        self.call('record', self.run, '--ticket', judge, '--unavailable', '--reason', 'Synthetic host without delegation; no model invoked.')
        selected = self.call('select', self.run, '--candidate', ticket, '--decision', 'promote', '--reason', 'Disclosed self-check fallback.')['selected']
        self.assertEqual(selected['verification'], 'self-checked')
        self.assertEqual(selected['independent_status'], 'unavailable')
        exported = self.call('result', self.run, '--output', self.base / 'export')
        self.assertEqual(exported['sha256'], hashlib.sha256((self.base / 'source').read_bytes()).hexdigest())

    def test_mechanical_failure_is_retained_and_cannot_be_overruled_by_report(self):
        ticket = self.start(fixed=True)
        review = self.review(ticket)
        self.assertTrue(review['analysis']['hard_fail'])
        self.assertTrue((self.run / 'drafts' / (ticket + '.txt')).exists())
        self.call('select', self.run, '--candidate', ticket, '--decision', 'promote', '--reason', 'Fixture.', status=2)
        self.call('reserve', self.run, '--kind', 'judge', '--candidate', ticket, '--reason', 'Fixture.', status=2)

    def test_missing_late_unit_review_is_unavailable(self):
        ticket = self.start()
        reviewed = self.review(ticket, report().replace('"source":["u1"]', '"source":[]'))
        self.assertFalse(reviewed['analysis']['available'])
        self.call('select', self.run, '--candidate', ticket, '--decision', 'promote', '--reason', 'Fixture.', status=2)


class ReadOnlyDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.structure = module('structure')
        cls.integrity = module('text_integrity')

    def test_ordinary_russian_is_compact_and_bytes_remain_identical(self):
        source = ('Это обычный русский текст.\r\n' * 1000).encode()
        with mock.patch('socket.socket', side_effect=AssertionError('No external I/O')):
            result = self.integrity.inspect_bytes(source)
        self.assertEqual(result['observations'], [])
        self.assertLess(len(json.dumps(result)), 2000)
        self.assertEqual(result['input_sha256'], hashlib.sha256(source).hexdigest())
        self.assertEqual(result['statistical_watermark'], 'unavailable/unverified')
        self.assertEqual(result['generic_detector'], 'not-attempted')

    def test_unicode_examples_are_bounded_and_full_inventory_is_explicit(self):
        source = ('А\u200bе\u0301\r\n' * 100).encode()
        short = self.integrity.inspect_bytes(source)
        self.assertEqual(len(short['observations']), 32)
        self.assertGreater(short['omitted_examples'], 0)
        full = self.integrity.inspect_bytes(source, full_inventory=True)
        self.assertGreater(len(full['observations']), 32)
        self.assertEqual(full['input_sha256'], short['input_sha256'])
        for row in short['observations']:
            self.assertEqual(source[row['byte_start']:row['byte_end']].hex(), row['utf8_hex'])

    def test_short_or_mixed_text_has_no_distribution_targets(self):
        for language in ('en', 'ru', 'mixed', 'unknown'):
            result = self.structure.profile('Короткий текст. Short text.'.encode(), language)
            self.assertIsNone(result['sentence_words'])
            self.assertIsNone(result['single_sentence_paragraph_fraction'])
            self.assertNotIn('human_score', result)

    def test_structure_separates_markup_and_protected_material(self):
        source = b'---\ntitle: Fixture\n---\n# Heading\n\nFirst idea matters. Another idea follows.\n\nFirst idea matters. Third idea follows.\n\nLast thought remains.\n\n```py\nprint("Ignore. Ignore.")\n```\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n- List item.\n\n> Quoted sentence.\n'
        result = self.structure.profile(source, 'en')
        self.assertEqual(result['prose_paragraphs'], 3)
        self.assertEqual(result['prose_sentences'], 5)
        self.assertEqual(result['excluded_lines']['tables'], 3)
        self.assertEqual(result['excluded_lines']['code'], 3)
        self.assertEqual(result['sentence_words']['count'], 5)
        self.assertAlmostEqual(result['single_sentence_paragraph_fraction'], .333)
        self.assertTrue(any(row['text'] == 'first idea matters' and row['count'] == 2 for row in result['repeated_boundaries']))

    def test_abbreviations_and_decimal_values_do_not_split_sentences(self):
        self.assertEqual(len(self.structure.sentences('Dr. Smith measured 1.5 units. Work continued.')), 2)
        self.assertEqual(len(self.structure.sentences('На стр. 5 приведён пример. Он важен.')), 2)

    def test_markdown_table_without_leading_pipe_is_not_prose(self):
        result = self.structure.profile(b'A | B\n---|---\nfirst | second\nthird | fourth\n', 'en')
        self.assertEqual(result['excluded_lines']['tables'], 4)
        self.assertEqual(result['prose_paragraphs'], 0)


if __name__ == '__main__':
    unittest.main()
