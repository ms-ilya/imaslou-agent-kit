#!/usr/bin/env python3
# ABOUTME: Exercises Humanizer text-integrity inspection, explicit edits and failure gates against frozen byte fixtures.

from collections import Counter
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import io
import json
from humanizer_fixtures import REVIEW_METADATA, integrity_report, plan_for, mapping_for
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import unicodedata
import urllib.request


def u8(text):
    return text.encode('utf-8')


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    identity: str


@dataclass(frozen=True)
class SelectedEdit:
    start: int
    end: int
    before: bytes
    after: bytes
    output_start: int
    output_end: int
    boundary_start: int
    boundary: bytes
    reason: str


@dataclass(frozen=True)
class FrozenFixture:
    name: str
    family: str
    original: bytes
    source: bytes
    expected: bytes
    editable: tuple
    protected: tuple
    locks: tuple
    edits: tuple
    observed_codepoints: tuple
    provenance: str


def injected(name, source, expected, prefix, artifact, replacement, boundary_start,
             boundary, reason):
    data = u8(source)
    start = len(u8(prefix))
    old, new = u8(artifact), u8(replacement)
    edit = SelectedEdit(start, start + len(old), old, new, start,
                        start + len(new), len(u8(boundary_start)), u8(boundary), reason)
    return FrozenFixture(name, 'injected', data, data, u8(expected),
                         (Span(0, len(data), 'editable-document'),), (), (), (edit,),
                         tuple(ord(ch) for ch in artifact),
                         'Synthetic insertion into the independently stated clean parent.')


def unchanged(name, family, source, observed_codepoints):
    data = u8(source)
    return FrozenFixture(name, family, data, data, u8(source),
                         (Span(0, len(data), 'editable-document'),), (), (), (),
                         observed_codepoints,
                         'Synthetic legitimate content; no artifact removal is authorized.')


def protected_case(name, prefix, protected, suffix, expected, observed_codepoints,
                   edit_prefix=None, artifact=None, replacement=None,
                   boundary_start=None, boundary=None):
    source = u8(prefix + protected + suffix)
    protected_start = len(u8(prefix))
    protected_end = protected_start + len(u8(protected))
    guard = Span(protected_start, protected_end, 'protected-' + name)
    editable = tuple(span for span in (
        Span(0, protected_start, 'editable-prefix'),
        Span(protected_end, len(source), 'editable-suffix'),
    ) if span.start < span.end)
    edits = ()
    if edit_prefix is not None:
        start = len(u8(edit_prefix))
        old, new = u8(artifact), u8(replacement)
        edits = (SelectedEdit(start, start + len(old), old, new, start,
                              start + len(new), len(u8(boundary_start)), u8(boundary),
                              'Known synthetic injection only in the declared editable span.'),)
    return FrozenFixture(name, 'protected', source, source, u8(expected), editable,
                         (guard,), (guard,), edits, observed_codepoints,
                         'Synthetic protected content and independently stated output oracle.')


# Source and output literals, including boundary oracles, are frozen independently
# of the editor under test. These fixtures never contain historical evaluation prose.
FIXTURES = (
    injected('zwsp-within-word', 'Say he\u200bllo.', 'Say hello.', 'Say he',
             '\u200b', '', 'Say ', 'hello', 'Remove known insertion inside the word hello.'),
    injected('zwsp-between-words', 'red\u200bblue', 'red blue', 'red', '\u200b',
             ' ', '', 'red blue', 'Restore the known space between red and blue.'),
    injected('word-joiner-injection', 'A co\u2060lor sample.', 'A color sample.',
             'A co', '\u2060', '', 'A ', 'color', 'Remove known insertion inside color.'),
    injected('soft-hyphen-injection', 'Use co\u00adoperate.', 'Use cooperate.',
             'Use co', '\u00ad', '', 'Use ', 'cooperate',
             'Remove explicitly injected conditional hyphen inside cooperate.'),
    injected('misplaced-bom-injection', 'A sa\ufeffmple.', 'A sample.', 'A sa',
             '\ufeff', '', 'A ', 'sample', 'Remove known embedded BOM inside sample.'),
    injected('direction-mark-injection', 'The ca\u200et sleeps.', 'The cat sleeps.',
             'The ca', '\u200e', '', 'The ', 'cat',
             'Remove known stray direction mark inside the synthetic word cat.'),
    injected('private-use-interface-residue', 'Ready.\ue123', 'Ready.', 'Ready.',
             '\ue123', '', '', 'Ready.', 'Remove the selected synthetic UI residue.'),
    injected('selected-ui-label', 'Answer.\n[Copy response]', 'Answer.\n', 'Answer.\n',
             '[Copy response]', '', '', 'Answer.\n',
             'Remove this selected interface label outside the document.'),

    unchanged('persian-zwnj', 'legitimate', 'می\u200cروم', (0x200C,)),
    unchanged('arabic-joining-control', 'legitimate', 'ب\u200dب', (0x200D,)),
    unchanged('indic-joining-control', 'legitimate', 'क्\u200dष', (0x200D,)),
    unchanged('emoji-zwj', 'legitimate', 'Family: 👩\u200d👩\u200d👧\u200d👦.', (0x200D,)),
    unchanged('text-variation-selector', 'legitimate', 'Text heart: ❤\ufe0e.', (0xFE0E,)),
    unchanged('emoji-variation-selector', 'legitimate', 'Emoji heart: ❤\ufe0f.', (0xFE0F,)),
    unchanged('emoji-tag-flag', 'legitimate',
              'Flag: 🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f.',
              (0xE0067, 0xE0062, 0xE0065, 0xE006E, 0xE007F)),
    unchanged('decomposed-accent', 'legitimate', 'A cafe\u0301 closes.', (0x0301,)),
    unchanged('non-latin-combining-mark', 'legitimate', 'שָׁלוֹם', (0x05B8, 0x05C1, 0x05B9)),
    unchanged('rtl-mark', 'legitimate', 'עברית\u200f 12', (0x200F,)),
    unchanged('bidi-isolate', 'legitimate', 'Name: \u2067علي\u2069.', (0x2067, 0x2069)),
    unchanged('bidi-embedding', 'legitimate', 'Name: \u202bعلي\u202c.', (0x202B, 0x202C)),
    unchanged('nbsp-typography', 'legitimate', 'Mr.\u00a0Lee arrives.', (0x00A0,)),
    unchanged('narrow-nbsp-number-unit', 'legitimate', 'Mass: 12\u202fkg.', (0x202F,)),
    unchanged('cjk-space', 'legitimate', '東京\u3000大阪', (0x3000,)),
    unchanged('legitimate-soft-hyphen', 'legitimate', 'Print co\u00adoperate here.', (0x00AD,)),
    unchanged('invisible-math-operator', 'legitimate', 'Formula: 2\u2062x.', (0x2062,)),
    unchanged('mixed-script-name', 'legitimate', 'Name: Mаria.', (0x0430,)),
    unchanged('agreed-private-use-glyph', 'legitimate', 'Logo glyph: \ue123.', (0xE123,)),
    unchanged('leading-utf8-bom', 'legitimate', '\ufeffDocument starts here.', (0xFEFF,)),

    protected_case('fenced-code', '', '```text\nhe\u200bllo\n```\n', 'Say he\u200bllo.\n',
                   '```text\nhe\u200bllo\n```\nSay hello.\n', (0x200B,),
                   '```text\nhe\u200bllo\n```\nSay he', '\u200b', '',
                   '```text\nhe\u200bllo\n```\nSay ', 'hello'),
    protected_case('indented-code', 'Prose.\n', '    he\u200bllo\r\n', 'Tail.\r\n',
                   'Prose.\n    he\u200bllo\r\nTail.\r\n', (0x200B,)),
    protected_case('inline-code', 'Say he\u200bllo; keep ', '`he\u200bllo`', '.',
                   'Say hello; keep `he\u200bllo`.', (0x200B,),
                   'Say he', '\u200b', '', 'Say ', 'hello'),
    protected_case('structured-json', 'Data:\n', '{"key":"he\u200bllo","n":12}\n',
                   'End.\n', 'Data:\n{"key":"he\u200bllo","n":12}\nEnd.\n', (0x200B,)),
    protected_case('frontmatter', '', '---\r\nlabel: he\u200bllo\r\n---\r\n',
                   'Body he\u200bllo.\r\n',
                   '---\r\nlabel: he\u200bllo\r\n---\r\nBody hello.\r\n', (0x200B,),
                   '---\r\nlabel: he\u200bllo\r\n---\r\nBody he', '\u200b', '',
                   '---\r\nlabel: he\u200bllo\r\n---\r\nBody ', 'hello'),
    protected_case('html', 'Keep ', '<span data-id="a\u200bb">x\u00a0y</span>', '.',
                   'Keep <span data-id="a\u200bb">x\u00a0y</span>.', (0x200B, 0x00A0)),
    protected_case('quotation', 'Say he\u200bllo; quotation: ', '“he\u200bllo”', '.',
                   'Say hello; quotation: “he\u200bllo”.', (0x200B,),
                   'Say he', '\u200b', '', 'Say ', 'hello'),
    protected_case('citation', 'Claim ', '[ref\u200b1, p. 2]', ' remains.',
                   'Claim [ref\u200b1, p. 2] remains.', (0x200B,)),
    protected_case('url-query', 'Say he\u200bllo; URL ',
                   'https://example.test/a\u200bb?utm_source=x&n=12#frag', '.',
                   'Say hello; URL https://example.test/a\u200bb?utm_source=x&n=12#frag.',
                   (0x200B,), 'Say he', '\u200b', '', 'Say ', 'hello'),
    protected_case('math', 'Keep ', '$2\u2062x + y\u200b = 3$', '.',
                   'Keep $2\u2062x + y\u200b = 3$.', (0x2062, 0x200B)),
    protected_case('identifier', 'Identifier ', 'Mаria_\u200dID', ' is literal.',
                   'Identifier Mаria_\u200dID is literal.', (0x0430, 0x200D)),
    FrozenFixture('section-boundary-repeated', 'protected',
                  u8('he\u200bllo\r\nBEGIN\r\nhe\u200bllo\r\nEND\r\nhe\u200bllo\r\n'),
                  u8('he\u200bllo\r\nBEGIN\r\nhe\u200bllo\r\nEND\r\nhe\u200bllo\r\n'),
                  u8('he\u200bllo\r\nBEGIN\r\nhello\r\nEND\r\nhe\u200bllo\r\n'),
                  (Span(17, 27, 'editable-section'),),
                  (Span(0, 17, 'protected-prefix'), Span(27, 42, 'protected-suffix')),
                  (Span(0, 17, 'protected-prefix'), Span(27, 42, 'protected-suffix')),
                  (SelectedEdit(19, 22, u8('\u200b'), b'', 19, 19, 17, b'hello',
                                'Known insertion only inside the selected middle section.'),),
                  (0x200B,), 'Synthetic repeated text; both surrounding sections are locked.'),

    unchanged('clean-ascii', 'clean', 'A plain sentence.', ()),
    unchanged('clean-curly-punctuation', 'clean', '“It’s ready”—she said.',
              (0x201C, 0x2019, 0x201D, 0x2014)),
    unchanged('clean-multilingual', 'clean', 'Hello. Привет. 東京。', (0x041F, 0x6771)),
    unchanged('clean-tabs-crlf', 'clean', 'One\tTwo\r\nThree\r\n', (0x0009, 0x000D, 0x000A)),
    unchanged('clean-trailing-whitespace', 'clean', 'Line.  \t\r\nTail. \n', (0x0009, 0x000D, 0x000A)),
    unchanged('clean-blank-final-newlines', 'clean', '\n\nFirst.\n\nLast.\n\n', (0x000A,)),
    unchanged('clean-bom-mixed-content', 'clean', '\ufeff`id` and <b>text</b>.\r\n', (0xFEFF, 0x000D, 0x000A)),
    unchanged('clean-empty', 'clean', '', ()),
)


def fixture_bytes():
    def encode(value):
        if isinstance(value, bytes):
            return {'utf8_hex': value.hex()}
        if isinstance(value, tuple):
            return [encode(item) for item in value]
        if isinstance(value, dict):
            return {key: encode(item) for key, item in value.items()}
        return value
    return json.dumps([encode(asdict(item)) for item in FIXTURES],
                      ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('ascii')


def validate_fixture_oracles():
    expected_counts = {'injected': 8, 'legitimate': 20, 'protected': 12, 'clean': 8}
    assert dict(Counter(item.family for item in FIXTURES)) == expected_counts
    assert len({item.name for item in FIXTURES}) == 48
    for item in FIXTURES:
        assert item.original == item.source
        text = item.source.decode('utf-8', errors='strict')
        item.expected.decode('utf-8', errors='strict')
        boundaries = {len(text[:index].encode('utf-8')) for index in range(len(text) + 1)}
        for span in item.editable + item.protected + item.locks:
            assert 0 <= span.start <= span.end <= len(item.source), item.name
            assert span.start in boundaries and span.end in boundaries, item.name
        for left in item.editable:
            for right in item.protected + item.locks:
                assert left.end <= right.start or right.end <= left.start, item.name
        previous_end = 0
        parts = []
        for edit in item.edits:
            assert previous_end <= edit.start < edit.end <= len(item.source), item.name
            assert edit.start in boundaries and edit.end in boundaries, item.name
            assert item.source[edit.start:edit.end] == edit.before, item.name
            assert any(scope.start <= edit.start and edit.end <= scope.end
                       for scope in item.editable), item.name
            assert item.expected[edit.output_start:edit.output_end] == edit.after, item.name
            assert item.expected[edit.boundary_start:edit.boundary_start + len(edit.boundary)] == edit.boundary, item.name
            assert edit.before not in edit.boundary, item.name
            parts.extend((item.source[previous_end:edit.start], edit.after))
            previous_end = edit.end
        parts.append(item.source[previous_end:])
        assert b''.join(parts) == item.expected, item.name
        for codepoint in item.observed_codepoints:
            assert chr(codepoint) in text, (item.name, codepoint)
    return expected_counts


FROZEN_FIXTURE_SHA256 = '5df0b15860c79653695e964cded03126c40baa92ec3152a090067a9eebda7cd8'
ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'plugins/humanizer/scripts/text_integrity.py'
REGRESSION_EVIDENCE = {'fixture_sha256': FROZEN_FIXTURE_SHA256, 'fixtures': {}, 'probes': {}}


def load_local_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def make_plan(item):
    edits = []
    for selected in item.edits:
        output_end = selected.boundary_start + len(selected.boundary)
        left = item.expected[selected.boundary_start:selected.output_start]
        right = item.expected[selected.output_end:output_end]
        if selected.after and selected.after.decode('utf-8').isspace():
            intent = 'preserve-separation'
        elif not selected.after and left and right and (
                left.decode('utf-8')[-1].isalnum() and right.decode('utf-8')[0].isalnum()):
            intent = 'restore-known-word'
        else:
            intent = 'preserve-format'
        edits.append({
            'byte_start': selected.start, 'byte_end': selected.end,
            'scalar_start': len(item.source[:selected.start].decode('utf-8')),
            'scalar_end': len(item.source[:selected.end].decode('utf-8')),
            'expected_hex': selected.before.hex(), 'replacement_hex': selected.after.hex(),
            'reason': selected.reason, 'authorization': 'frozen-fixture:' + item.name,
            'source_anchor': {'unit_id': item.name, 'byte_start': selected.start,
                              'byte_end': selected.end, 'expected_hex': selected.before.hex()},
            'boundary': {'left_hex': left.hex(), 'right_hex': right.hex(),
                         'result_hex': selected.boundary.hex(), 'intent': intent},
        })
    return {
        'schema_version': 1,
        'original_sha256': hashlib.sha256(item.original).hexdigest(),
        'input_sha256': hashlib.sha256(item.source).hexdigest(),
        'scope': {key: [[span.start, span.end] for span in ranges if span.start < span.end]
                  for key, ranges in (('editable', item.editable), ('protected', item.protected),
                                      ('locks', item.locks))},
        'edits': edits,
    }


class HumanizerTextIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        validate_fixture_oracles()
        assert hashlib.sha256(fixture_bytes()).hexdigest() == FROZEN_FIXTURE_SHA256
        cls.helper = load_local_module(HELPER, 'humanizer_text_integrity_under_test')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='humanizer integrity regression ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def deny_external_calls(self):
        stack = ExitStack()
        for owner, name in ((socket, 'socket'), (socket, 'create_connection'),
                            (urllib.request, 'urlopen'), (subprocess, 'run'),
                            (subprocess, 'Popen')):
            stack.enter_context(mock.patch.object(owner, name,
                side_effect=AssertionError('Text-integrity helper attempted external I/O.')))
        return stack

    def assert_observations(self, data, observations):
        expected = []
        byte_start = 0
        for scalar, ch in enumerate(data.decode('utf-8')):
            encoded = ch.encode('utf-8')
            category = unicodedata.category(ch)
            if ((category.startswith(('C', 'M')) and ch not in '\r\n\t') or
                    (category.startswith('Z') and ch != ' ') or ord(ch) in (0xFFFD, 0xFE0E, 0xFE0F)):
                expected.append((byte_start, byte_start + len(encoded), scalar, scalar + 1,
                                 'U+{:04X}'.format(ord(ch)), encoded.hex()))
            byte_start += len(encoded)
        actual = [(row['byte_start'], row['byte_end'], row['scalar_start'], row['scalar_end'],
                   row['codepoint'], row['utf8_hex']) for row in observations]
        self.assertEqual(actual, expected[:32])
        self.assertTrue(all(row['disposition'] == 'preserve-or-flag' for row in observations))
        for row in observations:
            self.assertIn('name', row)
            self.assertIn('category', row)
            self.assertIn('bidi', row)
            self.assertIn('combining', row)

    def exercise_fixture(self, item):
        plan = make_plan(item)
        untouched_plan = copy.deepcopy(plan)
        source_path = self.base / 'inspected original with spaces.txt'
        source_path.write_bytes(item.source)
        inspection_arguments = ('inspect', source_path, '--expected-sha256',
                                hashlib.sha256(item.source).hexdigest())
        inspected_cli = self.cli(*inspection_arguments)
        inspected_cli_twice = self.cli(*inspection_arguments)
        self.assertEqual(inspected_cli.returncode, 0, inspected_cli.stderr)
        self.assertEqual(inspected_cli_twice.returncode, 0, inspected_cli_twice.stderr)
        self.assertEqual(inspected_cli.stdout, inspected_cli_twice.stdout)
        self.assertEqual(source_path.read_bytes(), item.source)
        with self.deny_external_calls():
            before = self.helper.inspect_bytes(item.source)
            self.assertEqual(before, self.helper.inspect_bytes(item.source))
            actual, receipt = self.helper.apply_edits(item.original, item.source, plan)
            self.assertEqual((actual, receipt),
                             self.helper.apply_edits(item.original, item.source, plan))
            after = self.helper.inspect_bytes(actual)
            self.assertEqual(after, self.helper.inspect_bytes(actual))
        self.assertEqual(plan, untouched_plan)
        self.assertEqual(json.loads(inspected_cli.stdout), before)
        self.assertEqual(actual, item.expected)
        self.assertEqual(before['input_sha256'], hashlib.sha256(item.source).hexdigest())
        self.assertEqual(before['utf8_bytes'], len(item.source))
        self.assertEqual(before['unicode_scalars'], len(item.source.decode('utf-8')))
        self.assertEqual(before['edits'], [])
        self.assert_observations(item.source, before['observations'])
        self.assert_observations(actual, after['observations'])
        for report in (before, after, receipt):
            self.assertEqual(report['schema_version'], 1 if report is receipt else 2)
            self.assertEqual(report['policy'], 'explicit-spans-v1')
            self.assertEqual(report['unicode_version'], unicodedata.unidata_version)
            self.assertEqual(report['encoding'], 'UTF-8')
            self.assertEqual(report['fidelity_editorial'], 'not-assessed')
            self.assertEqual(report['statistical_watermark'], 'unavailable/unverified')
            self.assertEqual(report['generic_detector'], 'not-attempted')
        self.assertEqual(receipt['original_sha256'], hashlib.sha256(item.original).hexdigest())
        self.assertEqual(receipt['input_sha256'], hashlib.sha256(item.source).hexdigest())
        self.assertEqual(receipt['output_sha256'], hashlib.sha256(actual).hexdigest())
        self.assertEqual(receipt['plan_sha256'],
                         hashlib.sha256(self.helper.canonical_json(plan)).hexdigest())
        self.assertEqual(receipt['scope_sha256'],
                         hashlib.sha256(self.helper.canonical_json(plan['scope'])).hexdigest())
        self.assertEqual(receipt['observations_before'], self.helper.inspect_bytes(item.source, full_inventory=True)['observations'])
        self.assertEqual(receipt['observations_after'], self.helper.inspect_bytes(actual, full_inventory=True)['observations'])
        self.assertEqual(len(receipt['edits']), len(item.edits))
        for selected, requested, recorded in zip(item.edits, plan['edits'], receipt['edits']):
            for key in ('byte_start', 'byte_end', 'scalar_start', 'scalar_end', 'expected_hex',
                        'replacement_hex', 'reason', 'authorization', 'source_anchor', 'boundary'):
                self.assertEqual(recorded[key], requested[key])
            self.assertEqual(recorded['output_byte_start'], selected.output_start)
            self.assertEqual(recorded['output_byte_end'], selected.output_end)
            self.assertEqual(recorded['output_scalar_start'],
                             len(actual[:selected.output_start].decode('utf-8')))
            self.assertEqual(recorded['output_scalar_end'],
                             len(actual[:selected.output_end].decode('utf-8')))
            self.assertEqual(recorded['original_codepoints'],
                             ['U+{:04X}'.format(ord(ch)) for ch in selected.before.decode('utf-8')])
            self.assertEqual(recorded['replacement_codepoints'],
                             ['U+{:04X}'.format(ord(ch)) for ch in selected.after.decode('utf-8')])
            observed_boundary = actual[selected.boundary_start:selected.boundary_start + len(selected.boundary)]
            self.assertEqual(observed_boundary, selected.boundary)
            self.assertNotIn(selected.before, observed_boundary)
        for row in receipt['preserved_ranges'] + receipt['protected_ranges']:
            source_slice = item.source[row['input_start']:row['input_end']]
            self.assertEqual(source_slice, actual[row['output_start']:row['output_end']])
            self.assertEqual(row['sha256'], hashlib.sha256(source_slice).hexdigest())
        self.assertEqual([(row['input_start'], row['input_end'])
                          for row in receipt['protected_ranges']],
                         [(span.start, span.end) for span in item.protected])
        preserved = receipt['preserved_ranges']
        expected_unchanged = []
        cursor = 0
        for edit in item.edits:
            if cursor < edit.start:
                expected_unchanged.append((cursor, edit.start))
            cursor = edit.end
        if cursor < len(item.source):
            expected_unchanged.append((cursor, len(item.source)))
        self.assertEqual([(row['input_start'], row['input_end']) for row in preserved],
                         expected_unchanged)
        # Resolution is fixture-bound: no targeted injected bytes remain at the
        # independent clean-parent boundaries; an unrelated protected copy may remain.
        for selected in item.edits:
            self.assertNotIn(selected.before,
                             item.expected[selected.boundary_start:selected.boundary_start + len(selected.boundary)])
        resolved = {'schema_version': 1,
                    'original_sha256': hashlib.sha256(actual).hexdigest(),
                    'input_sha256': hashlib.sha256(actual).hexdigest(),
                    'scope': {'editable': [[0, len(actual)]] if actual else [],
                              'protected': [], 'locks': []}, 'edits': []}
        with self.deny_external_calls():
            twice, repeated = self.helper.apply_edits(actual, actual, resolved)
        self.assertEqual(twice, actual)
        self.assertEqual(repeated['edits'], [])
        if item.edits:
            with self.assertRaises(self.helper.IntegrityError):
                self.helper.apply_edits(item.original, actual, plan)
        REGRESSION_EVIDENCE['fixtures'][item.name] = {
            'family': item.family, 'input_sha256': before['input_sha256'],
            'expected_output_hex': item.expected.hex(), 'actual_output_hex': actual.hex(),
            'inspection_before': before, 'inspection_after': after,
            'cli_inspection_repeated_identically': True,
            'plan': plan, 'receipt': receipt, 'resolved_receipt': repeated,
            'target_boundaries_verified': len(item.edits), 'status': 'passed',
        }

    def invalid_plan(self, probe, mutate, item=None, original=None, data=None):
        item = item or FIXTURES[0]
        plan = make_plan(item)
        mutate(plan)
        with self.deny_external_calls(), self.assertRaises(self.helper.IntegrityError) as caught:
            self.helper.apply_edits(item.original if original is None else original,
                                    item.source if data is None else data, plan)
        result = REGRESSION_EVIDENCE['probes'].setdefault(probe, {'status': 'passed', 'checks': []})
        result['checks'].append({'outcome': 'rejected', 'error': str(caught.exception)})

    def synthetic_run(self, item=None, status='reserved', kind='initial', prior_pass=False):
        item = item or FIXTURES[0]
        source = self.base / 'original source with spaces.txt'
        source.write_bytes(item.source)
        run = self.base / 'synthetic keeper with spaces'
        run.mkdir()
        (run / 'original.txt').write_bytes(item.source)
        identity = hashlib.sha256(item.source).hexdigest()
        state = {
            'version': 1,
            'original': {'source_path': str(source), 'sha256': identity,
                         'words': len(item.source.decode('utf-8').split())},
            'files': {'original.txt': identity},
            'attempts': [{'id': 'draft-1', 'kind': kind, 'reason': 'Synthetic offline gate fixture.',
                          'candidate': None, 'status': status}],
            'reviews': [], 'selected': {'candidate': 'original', 'reason': 'Synthetic source.'},
            'decisions': [],
        }
        ticket = 'draft-1'
        if kind == 'judge' or prior_pass:
            (run / 'candidate.txt').write_bytes(item.source)
            (run / 'initial.txt').write_bytes(item.source)
            state['files'].update({'candidate.txt': identity, 'initial.txt': identity})
            state['attempts'] = [
                {'id': 'draft-1', 'kind': 'initial', 'reason': 'Synthetic recorded byte fixture.',
                 'candidate': None, 'status': 'recorded', 'sha256': identity},
                {'id': 'judge-1', 'kind': 'judge', 'reason': 'Synthetic gate record; no judge executed.',
                 'candidate': 'draft-1', 'status': 'reserved'},
            ]
            ticket = 'judge-1'
        if prior_pass:
            stages = load_local_module(ROOT / 'plugins/humanizer/scripts/stages.py',
                                       'humanizer_synthetic_stage_fixture')
            report = (integrity_report().encode() +
                      b'AI_PATTERNS_FOUND: 0\nNone\nSCORES:\n'
                      b'- Directness: 8/10\n- Rhythm: 8/10\n- Trust: 8/10\n'
                      b'- Authenticity: 8/10\n- Preservation: 8/10\n- Total: 40/50\n'
                      b'VERDICT: PASS\n')
            analysis = stages.parse_report(report, 'judge', True)
            self.assertTrue(analysis['available'])
            reports = run / 'reports'
            reports.mkdir()
            (reports / 'judge-1.txt').write_bytes(report)
            state['files']['reports/judge-1.txt'] = hashlib.sha256(report).hexdigest()
            state['attempts'][-1]['status'] = 'recorded'
            state['reviews'] = [{'id': 'judge-1', 'kind': 'judge', 'candidate': 'draft-1',
                                 'candidate_sha256': identity, 'path': 'reports/judge-1.txt',
                                 'analysis': analysis}]
            state['attempts'].append({'id': 'draft-2', 'kind': 'self-revision',
                'reason': 'Synthetic later pending reservation tests post-PASS refusal.',
                'candidate': None, 'status': 'reserved'})
            ticket = 'draft-2'
        stages = load_local_module(ROOT / 'plugins/humanizer/scripts/stages.py', 'fixture_contracts')
        state['version'] = 3
        state['plan'] = plan_for(item.source)
        state['provenance'] = stages.contracts.provenance(ROOT / 'plugins/humanizer')
        encoded_plan = json.dumps(state['plan']).encode()
        (run / 'plan.json').write_bytes(encoded_plan)
        state['files']['plan.json'] = hashlib.sha256(encoded_plan).hexdigest()
        for writer in state['attempts']:
            if writer['kind'] != 'judge' and writer['status'] == 'recorded':
                mapping = mapping_for(item.source, item.source)
                writer.update(mapping=mapping, mechanical_errors=[], sha256=identity)
                for relative, data in (('drafts/' + writer['id'] + '.txt', item.source),
                                       ('maps/' + writer['id'] + '.json', json.dumps(mapping).encode())):
                    (run / relative).parent.mkdir(exist_ok=True)
                    (run / relative).write_bytes(data)
                    state['files'][relative] = hashlib.sha256(data).hexdigest()
        self.write_state(run, state)
        plan = self.base / 'explicit plan with spaces.json'
        plan.write_bytes(self.helper.canonical_json(make_plan(item)))
        output = self.base / 'exact output with spaces.txt'
        return source, plan, run, ticket, output

    def write_state(self, run, state):
        encoded = (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
        (run / 'state.json').write_bytes(encoded)
        (run / 'state.sha256').write_text(hashlib.sha256(encoded).hexdigest() + '\n', encoding='ascii')

    def cli_arguments(self, source, plan, run, ticket, output):
        return ['apply-edits', str(source), '--plan', str(plan), '--run', str(run),
                '--ticket', ticket, '--output', str(output)]

    def cli(self, *arguments):
        return subprocess.run([sys.executable, '-B', str(HELPER), *map(str, arguments)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def assert_cli_refusal(self, probe, args, paths):
        snapshots = {Path(path): Path(path).read_bytes() if Path(path).is_file() else None
                     for path in paths}
        result = self.cli(*args)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout, b'')
        self.assertTrue(result.stderr.strip())
        for path, expected in snapshots.items():
            if expected is None:
                self.assertFalse(path.exists(), str(path))
            else:
                self.assertEqual(path.read_bytes(), expected)
        evidence = REGRESSION_EVIDENCE['probes'].setdefault(probe, {'status': 'passed', 'checks': []})
        evidence['checks'].append({'outcome': 'rejected', 'exit_code': result.returncode,
                                   'stderr': result.stderr.decode('utf-8')})

    def test_probe_01_wrong_input_hash(self):
        self.invalid_plan('01-wrong-input-hash', lambda plan: plan.update(input_sha256='0' * 64))

    def test_probe_02_wrong_original_hash(self):
        self.invalid_plan('02-wrong-original-hash', lambda plan: plan.update(original_sha256='0' * 64))
        altered = b'A distinct original.'
        self.invalid_plan('02-wrong-original-hash',
                          lambda plan: plan.update(original_sha256=hashlib.sha256(altered).hexdigest()),
                          original=altered)

    def test_probe_03_stale_scalar_byte_coordinates(self):
        self.invalid_plan('03-stale-coordinates', lambda plan: plan['edits'][0].update(scalar_start=0))

    def test_probe_04_split_utf8(self):
        self.invalid_plan('04-split-utf8', lambda plan: plan['edits'][0].update(byte_start=7))

    def test_probe_05_overlapping_edits(self):
        self.invalid_plan('05-overlap', lambda plan: plan['edits'].append(copy.deepcopy(plan['edits'][0])))

    def test_probe_06_protected_intersection(self):
        def mutate(plan):
            plan['scope'] = {'editable': [], 'protected': [[0, len(FIXTURES[0].source)]],
                             'locks': [[0, len(FIXTURES[0].source)]]}
        self.invalid_plan('06-protected-intersection', mutate)

    def test_probe_07_inconsistent_scope_lock_map(self):
        self.invalid_plan('07-scope-lock-map', lambda plan: plan['scope'].update(locks=[[0, 1]]))

    def test_probe_08_unexpected_matched_bytes(self):
        self.invalid_plan('08-unexpected-bytes', lambda plan: plan['edits'][0].update(expected_hex='7a7a7a'))

    def test_probe_09_ambiguous_character_preserved(self):
        item = next(row for row in FIXTURES if row.name == 'persian-zwnj')
        with self.deny_external_calls():
            output, receipt = self.helper.apply_edits(item.original, item.source, make_plan(item))
            observations = self.helper.inspect_bytes(output)['observations']
        self.assertEqual(output, item.source)
        self.assertEqual(receipt['edits'], [])
        self.assertTrue(any(row['codepoint'] == 'U+200C' and
                            row['disposition'] == 'preserve-or-flag' for row in observations))
        REGRESSION_EVIDENCE['probes']['09-ambiguous-character'] = {
            'status': 'passed', 'outcome': 'preserved-and-flagged', 'output_sha256': hashlib.sha256(output).hexdigest()}

    def test_probe_10_separator_boundary_violation(self):
        def mutate(plan):
            plan['edits'][0]['replacement_hex'] = ''
            plan['edits'][0]['boundary']['result_hex'] = b'redblue'.hex()
        self.invalid_plan('10-separator-boundary', mutate, item=FIXTURES[1])
        for replacement in ('', '\u2060', '\u0301'):
            def bypass(plan, value=replacement):
                plan['edits'][0]['replacement_hex'] = value.encode('utf-8').hex()
                plan['edits'][0]['boundary'].update(
                    intent='preserve-format', result_hex=u8('red' + value + 'blue').hex())
            self.invalid_plan('10-separator-boundary', bypass, item=FIXTURES[1])

    def test_probe_11_invalid_utf8_binary(self):
        errors = []
        for data in (b'bad\xff', b'bad\x00text'):
            with self.deny_external_calls(), self.assertRaises(self.helper.IntegrityError) as caught:
                self.helper.inspect_bytes(data)
            errors.append(str(caught.exception))
            plan = {'schema_version': 1, 'original_sha256': hashlib.sha256(data).hexdigest(),
                    'input_sha256': hashlib.sha256(data).hexdigest(),
                    'scope': {'editable': [[0, len(data)]], 'protected': [], 'locks': []}, 'edits': []}
            with self.assertRaises(self.helper.IntegrityError):
                self.helper.apply_edits(data, data, plan)
        REGRESSION_EVIDENCE['probes']['11-invalid-encoding-binary'] = {
            'status': 'passed', 'outcome': 'rejected', 'errors': errors}

    def test_probe_12_existing_destination(self):
        source, plan, run, ticket, output = self.synthetic_run()
        output.write_bytes(b'Existing destination must survive.\r\n')
        self.assert_cli_refusal('12-existing-destination',
            self.cli_arguments(source, plan, run, ticket, output),
            (source, plan, run / 'state.json', run / 'state.sha256', output))

    def test_probe_13_source_or_alias_destination(self):
        source, plan, run, ticket, _output = self.synthetic_run()
        alias = self.base / 'source alias.txt'
        alias.symlink_to(source)
        for destination in (source, alias, plan, run / 'new.txt',
                            Path(str(run) + '.text-integrity') / 'new.txt'):
            with self.subTest(destination=destination.name):
                self.assert_cli_refusal('13-source-alias-destination',
                    self.cli_arguments(source, plan, run, ticket, destination),
                    (source, plan, run / 'state.json', run / 'state.sha256', destination))

    def test_probe_14_malformed_unknown_fields(self):
        for mutate in (
                lambda plan: plan.update(unrecognized=True),
                lambda plan: plan['scope'].update(unrecognized=[]),
                lambda plan: plan['edits'][0].update(unrecognized=True),
                lambda plan: plan['edits'][0]['source_anchor'].update(unrecognized=True),
                lambda plan: plan['edits'][0]['boundary'].update(unrecognized=True),
                lambda plan: plan['edits'][0].update(byte_start=True)):
            self.invalid_plan('14-malformed-plan', mutate)
        source, plan, run, ticket, output = self.synthetic_run()
        encoded = plan.read_bytes()
        plan.write_bytes(b'{"schema_version":1,' + encoded[1:])
        self.assert_cli_refusal('14-malformed-plan', self.cli_arguments(source, plan, run, ticket, output),
                                (source, plan, run / 'state.json', run / 'state.sha256', output))

    def test_probe_15_out_of_range_coordinates(self):
        self.invalid_plan('15-out-of-range', lambda plan: plan['edits'][0].update(byte_end=10000))

    def test_probe_16_concurrent_destination(self):
        source, plan, run, ticket, output = self.synthetic_run()
        state_before = {name: (run / name).read_bytes() for name in ('state.json', 'state.sha256')}
        sentinel = b'Concurrent writer wins intact.\r\n'
        real_link = self.helper.os.link
        raced = []
        def race_link(source_path, destination, *args, **kwargs):
            if Path(destination) == output:
                output.write_bytes(sentinel)
                raced.append(True)
            return real_link(source_path, destination, *args, **kwargs)
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(self.helper.os, 'link', side_effect=race_link), \
                mock.patch.object(sys, 'argv', [str(HELPER), *self.cli_arguments(source, plan, run, ticket, output)]), \
                redirect_stdout(stdout), redirect_stderr(stderr), self.deny_external_calls():
            result = self.helper.main()
        self.assertTrue(raced)
        self.assertNotEqual(result, 0)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(output.read_bytes(), sentinel)
        self.assertEqual(source.read_bytes(), FIXTURES[0].source)
        state_after = {name: (run / name).read_bytes() for name in ('state.json', 'state.sha256')}
        self.assertEqual(state_after, state_before)
        evidence = Path(str(run) + '.text-integrity') / ticket
        self.assertFalse((evidence / 'complete.json').exists())
        audit_files = {path.name: path.read_bytes().hex() for path in evidence.iterdir() if path.is_file()}
        self.assertIn('failure.json', audit_files)
        self.assertEqual(bytes.fromhex(audit_files['input.txt']), FIXTURES[0].source)
        self.assertEqual(bytes.fromhex(audit_files['output.txt']), FIXTURES[0].expected)
        REGRESSION_EVIDENCE['probes']['16-concurrent-destination'] = {
            'status': 'passed', 'outcome': 'rejected-with-concurrent-bytes-preserved',
            'exit_code': result, 'stdout': stdout.getvalue(), 'stderr': stderr.getvalue(),
            'destination_hex': output.read_bytes().hex(), 'source_hex': source.read_bytes().hex(),
            'audit_files_hex': audit_files,
            'state_before_hex': {name: data.hex() for name, data in state_before.items()},
            'state_after_hex': {name: data.hex() for name, data in state_after.items()}}

    def test_probe_17_missing_unreserved_ticket(self):
        source, plan, run, ticket, output = self.synthetic_run()
        args = self.cli_arguments(source, plan, run, 'draft-99', output)
        self.assert_cli_refusal('17-missing-unreserved-ticket', args,
                                (source, plan, run / 'state.json', run / 'state.sha256', output))
        args = self.cli_arguments(source, plan, run, ticket, output)
        del args[args.index('--ticket'):args.index('--ticket') + 2]
        self.assert_cli_refusal('17-missing-unreserved-ticket', args,
                                (source, plan, run / 'state.json', run / 'state.sha256', output))

    def test_probe_18_already_recorded_ticket(self):
        source, plan, run, ticket, output = self.synthetic_run(status='recorded')
        self.assert_cli_refusal('18-recorded-ticket', self.cli_arguments(source, plan, run, ticket, output),
                                (source, plan, run / 'state.json', run / 'state.sha256', output))

    def test_probe_19_judge_ticket(self):
        source, plan, run, ticket, output = self.synthetic_run(kind='judge')
        self.assert_cli_refusal('19-judge-ticket', self.cli_arguments(source, plan, run, ticket, output),
                                (source, plan, run / 'state.json', run / 'state.sha256', output))

    def test_probe_20_prior_valid_pass(self):
        source, plan, run, ticket, output = self.synthetic_run(prior_pass=True)
        self.assert_cli_refusal('20-prior-valid-pass', self.cli_arguments(source, plan, run, ticket, output),
                                (source, plan, run / 'state.json', run / 'state.sha256',
                                 run / 'reports/judge-1.txt', output))

    def test_cli_exact_export_and_audit_once(self):
        item = next(row for row in FIXTURES if row.name == 'section-boundary-repeated')
        source, plan, run, ticket, output = self.synthetic_run(item)
        before = {path: path.read_bytes() for path in (source, plan, run / 'state.json', run / 'state.sha256')}
        inspect = self.cli('inspect', source, '--expected-sha256', hashlib.sha256(item.source).hexdigest())
        self.assertEqual(inspect.returncode, 0, inspect.stderr)
        self.assertEqual(json.loads(inspect.stdout), self.helper.inspect_bytes(item.source))
        mismatched_inspect = self.cli('inspect', source, '--expected-sha256', '0' * 64)
        self.assertNotEqual(mismatched_inspect.returncode, 0)
        self.assertEqual(mismatched_inspect.stdout, b'')
        self.assertTrue(mismatched_inspect.stderr.strip())
        self.assertEqual(source.read_bytes(), item.source)
        arguments = self.cli_arguments(source, plan, run, ticket, output)
        result = self.cli(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes(), item.expected)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['run'], str(run.resolve()))
        self.assertEqual(receipt['ticket'], ticket)
        audit = Path(str(run) + '.text-integrity') / ticket
        self.assertEqual((audit / 'input.txt').read_bytes(), item.source)
        self.assertEqual((audit / 'output.txt').read_bytes(), item.expected)
        self.assertEqual(json.loads((audit / 'plan.json').read_bytes()), make_plan(item))
        self.assertEqual(json.loads((audit / 'receipt.json').read_bytes()), receipt)
        self.assertTrue((audit / 'complete.json').is_file())
        audit_files = {path.name: path.read_bytes().hex() for path in audit.iterdir() if path.is_file()}
        self.assertEqual(set(audit_files), {'input.txt', 'output.txt', 'plan.json', 'receipt.json', 'complete.json'})
        for path, expected in before.items():
            self.assertEqual(path.read_bytes(), expected)
        second_output = self.base / 'second-output.txt'
        retry = self.cli(*self.cli_arguments(source, plan, run, ticket, second_output))
        self.assertNotEqual(retry.returncode, 0)
        self.assertEqual(retry.stdout, b'')
        self.assertFalse(second_output.exists())
        self.assertEqual(output.read_bytes(), item.expected)
        self.assertEqual(json.loads((audit / 'receipt.json').read_bytes()), receipt)
        self.assertEqual({path.name: path.read_bytes().hex() for path in audit.iterdir() if path.is_file()},
                         audit_files)
        state_after = {name: (run / name).read_bytes() for name in ('state.json', 'state.sha256')}
        self.assertEqual(state_after, {path.name: data for path, data in before.items()
                                      if path.name in ('state.json', 'state.sha256')})
        REGRESSION_EVIDENCE['cli'] = {
            'status': 'passed', 'receipt': receipt,
            'exit_code': result.returncode, 'stdout_hex': result.stdout.hex(),
            'stderr': result.stderr.decode('utf-8'), 'audit_files_hex': audit_files,
            'output_hex': output.read_bytes().hex(), 'source_hex': source.read_bytes().hex(),
            'state_before_hex': {path.name: data.hex() for path, data in before.items()
                                 if path.name in ('state.json', 'state.sha256')},
            'state_after_hex': {name: data.hex() for name, data in state_after.items()},
            'single_ticket_reuse': {
                'outcome': 'rejected', 'exit_code': retry.returncode,
                'stdout_hex': retry.stdout.hex(), 'stderr': retry.stderr.decode('utf-8')},
            'expected_hash_mismatch': {
                'outcome': 'rejected', 'exit_code': mismatched_inspect.returncode,
                'stdout_hex': mismatched_inspect.stdout.hex(),
                'stderr': mismatched_inspect.stderr.decode('utf-8')},
            'state_bytes_unchanged': True,
        }


for _fixture in FIXTURES:
    def _exercise(self, item=_fixture):
        self.exercise_fixture(item)
    setattr(HumanizerTextIntegrity, 'test_fixture_' + _fixture.name.replace('-', '_'), _exercise)


if __name__ == '__main__':
    unittest.main()
