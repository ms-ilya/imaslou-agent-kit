#!/usr/bin/env python3
# ABOUTME: Reproduces review-binding, run-provenance and diagnostic edge cases found in the Humanizer follow-up audit.

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from humanizer_fixtures import plan_for, mapping_for
from test_humanizer_contracts import module, ROOT
from test_humanizer_stages import report


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.helper = ROOT / 'scripts/stages.py'
        self.run = self.base / 'run'
        self.source = b'The team may test again.\n'
        self.candidate = b'The team might test again.\n'
        self.serial = 0

    def file(self, data):
        self.serial += 1
        path = self.base / str(self.serial)
        path.write_bytes(data.encode() if isinstance(data, str) else data)
        return path

    def call(self, *args, status=0):
        result = subprocess.run([sys.executable, '-B', str(self.helper), *map(str, args)], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, status, result.stderr.decode())
        return json.loads(result.stdout) if status == 0 else result.stderr.decode()

    def start(self):
        self.call('init', self.run, '--original', self.file(self.source), '--plan', self.file(json.dumps(plan_for(self.source))))

    def draft(self, kind='initial', mapping=None):
        ticket = self.call('reserve', self.run, '--kind', kind, '--reason', 'Synthetic regression fixture.')['ticket']
        supplied = json.dumps(mapping_for(self.source, self.candidate)) if mapping is None else mapping
        self.call('record', self.run, '--ticket', ticket, '--text', self.file(self.candidate), '--mapping', self.file(supplied))
        return ticket

    def review(self, ticket):
        self.call('self-check', self.run, '--candidate', ticket, '--report', self.file(report()))

    def select(self, ticket, status=0):
        return self.call('select', self.run, '--candidate', ticket, '--decision', 'promote', '--reason', 'Fixture selection.', status=status)

    def test_no_objectives_plan_cannot_claim_a_supported_rewrite(self):
        contracts = module('contracts')
        plan = plan_for(self.source)
        plan['brief'].update(objectives=[], no_change_reason='The source already serves its reader.')
        self.assertTrue(contracts.mapping_errors(plan, self.source, self.candidate, mapping_for(self.source, self.candidate)))

    def test_identical_bytes_with_different_coverage_need_their_own_review(self):
        self.start()
        first = self.draft()
        self.review(first)
        changed_map = mapping_for(self.source, self.candidate)
        changed_map['units'][0]['id'] = 'different-candidate-unit'
        second = self.draft('self-revision', json.dumps(changed_map))
        self.assertIn('self-check', self.select(second, status=2))
        self.call('reserve', self.run, '--kind', 'judge', '--candidate', second, '--reason', 'Fixture.', status=2)

    def test_unchanged_bytes_cannot_be_reported_as_improved(self):
        self.candidate = self.source
        self.start()
        ticket = self.draft()
        self.review(ticket)
        self.assertEqual(self.select(ticket)['selected']['improvement_status'], 'no-justified-change')

    def test_no_change_plan_exports_exact_russian_bytes(self):
        # This checks the no-change path and byte identity, not the linguistic judgment.
        self.source = 'Заявления проверяют по средам.\r\nПроверяющий не указан.\r\n'.encode()
        self.candidate = self.source
        plan = plan_for(self.source)
        plan['brief'].update(intensity='unchanged', languages=['ru'], objectives=[],
                             no_change_reason='No reader problem identified in the supplied passage.')
        self.call('init', self.run, '--original', self.file(self.source), '--plan', self.file(json.dumps(plan)))
        ticket = self.draft()
        body = '\n'.join('OBJECTIVES: []' if line.startswith('OBJECTIVES:') else line
                         for line in report(score=None).splitlines()) + '\n'
        self.call('self-check', self.run, '--candidate', ticket, '--report', self.file(body))
        selected = self.select(ticket)['selected']
        self.assertTrue(selected['eligible'])
        self.assertEqual(selected['improvement_status'], 'no-justified-change')
        self.assertEqual(selected['verification'], 'self-checked')
        self.assertEqual(self.call('status', self.run)['counts']['judge'], 0)
        output = self.base / 'export.txt'
        self.call('result', self.run, '--output', output)
        self.assertEqual(output.read_bytes(), self.source)

    def test_invalid_json_map_retains_draft_and_consumes_ticket(self):
        self.start()
        ticket = self.draft(mapping='{bad json')
        state = self.call('status', self.run)
        self.assertTrue(state['attempts'][0]['mechanical_errors'])
        self.assertEqual((self.run / 'drafts' / (ticket + '.txt')).read_bytes(), self.candidate)
        self.assertEqual((self.run / 'maps' / (ticket + '.json')).read_bytes(), b'{bad json')
        self.call('record', self.run, '--ticket', ticket, '--text', self.file(self.candidate),
                  '--mapping', self.file(json.dumps(mapping_for(self.source, self.candidate))), status=2)

    def test_map_failure_does_not_poison_earlier_reviewed_identical_bytes(self):
        self.start()
        first = self.draft()
        self.review(first)
        self.select(first)
        broken_map = mapping_for(self.source, self.candidate)
        broken_map['candidate_sha256'] = '0' * 64
        second = self.draft('self-revision', json.dumps(broken_map))
        self.review(second)
        self.assertTrue(self.select(first)['selected']['eligible'])
        self.select(second, status=2)

    def test_nested_run_does_not_change_installed_resource_fingerprint(self):
        package = self.base / 'plugin'
        shutil.copytree(ROOT, package)
        self.helper = package / 'scripts/stages.py'
        self.run = package / 'temporary-run'
        self.start()
        before = self.call('status', self.run)['provenance']
        self.draft()
        after = self.call('status', self.run)['provenance']
        self.assertEqual(before, after)

    def test_control_after_many_combining_marks_remains_visible(self):
        text = ('е\u0301' * 40 + '\u202e').encode()
        result = module('text_integrity').inspect_bytes(text)
        self.assertIn('U+202E', {row['codepoint'] for row in result['observations']})
        self.assertLessEqual(len(result['observations']), 32)
        self.assertEqual(result['input_sha256'], hashlib.sha256(text).hexdigest())

    def test_nearest_rank_p90_is_not_the_maximum_for_ten_values(self):
        self.assertEqual(module('structure').distribution(list(range(1, 11)))['p90'], 9)

    def test_unicode_words_and_nested_backticks_do_not_distort_prose_counts(self):
        structure = module('structure')
        self.assertEqual(structure.WORDS.findall('A naïve café review.'), ['A', 'naïve', 'café', 'review'])
        result = structure.profile(b'First ``ignore `nested` words`` sentence.\n', 'en')
        self.assertEqual(result['inline_code_spans'], 1)

    def test_lazy_markdown_list_and_quote_continuations_are_not_prose(self):
        text = b'- First item\ncontinued here.\n\n> Quotation\ncontinued here.\n'
        result = module('structure').profile(text, 'en')
        self.assertEqual(result['prose_paragraphs'], 0)


if __name__ == '__main__':
    unittest.main()
