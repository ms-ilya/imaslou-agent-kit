#!/usr/bin/env python3
# ABOUTME: Inspects UTF-8 bytes and applies explicit original-bound edits with local integrity receipts.

"""Read-only inspection is integrated with Humanizer; explicit editing remains standalone.

Version 1 edits only the exact captured original. Scope, source-unit labels,
authorization and boundary intent are caller assertions, not semantic judgments.
No normalization, implicit deletion, language parser or watermark detector runs.
"""

import argparse
from collections import Counter
import hashlib
import heapq
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata


POLICY = 'explicit-spans-v1'


class IntegrityError(ValueError):
    """An explicit edit or byte-integrity precondition was not satisfied."""


def require(condition, message):
    if not condition:
        raise IntegrityError(message)


def digest(data):
    """Return the SHA-256 identity of exact bytes."""
    return hashlib.sha256(data).hexdigest()


def canonical_json(value):
    """Encode stable receipts without emitting literal terminal controls."""
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('ascii')


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'duplicate JSON key: ' + key)
        value[key] = item
    return value


def fields(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected), 'invalid fields: ' + label)


def text_bytes(data):
    require(isinstance(data, bytes), 'input must be bytes')
    try:
        text = data.decode('utf-8', errors='strict')
    except UnicodeDecodeError as error:
        raise IntegrityError('input is not strict UTF-8') from error
    require('\x00' not in text, 'NUL/binary input is unsupported')
    return text


def scalar_offsets(text):
    offsets = [0]
    for character in text:
        offsets.append(offsets[-1] + len(character.encode('utf-8')))
    return offsets


def codepoints(text):
    return ['U+{:04X}'.format(ord(character)) for character in text]


def inspect_bytes(data, full_inventory=False):
    """Summarize exact scalars with bounded diagnostic examples; never normalize."""
    text = text_bytes(data)
    offsets = scalar_offsets(text)
    observations = []
    examples = []
    categories = Counter()
    scripts = Counter()
    interesting = 0
    for index, character in enumerate(text):
        category = unicodedata.category(character)
        categories[category] += 1
        name = unicodedata.name(character, 'UNNAMED')
        script = next((label for label in ('LATIN', 'CYRILLIC', 'GREEK', 'ARABIC', 'HEBREW', 'HIRAGANA', 'KATAKANA', 'HANGUL', 'CJK') if label in name), 'other')
        scripts[script] += 1
        diagnostic = ((category.startswith(('C', 'M')) and character not in '\r\n\t') or
                      (category.startswith('Z') and character != ' ') or
                      ord(character) in (0xFFFD, 0xFE0E, 0xFE0F))
        interesting += diagnostic
        if not (full_inventory and (ord(character) >= 128 or category.startswith('C')) or diagnostic):
            continue
        priority = 0 if category.startswith('C') else 1 if ord(character) == 0xFFFD else 2
        if not full_inventory and len(examples) == 32 and (-priority, -index) <= examples[0][:2]:
            continue
        observation = {
            'byte_start': offsets[index], 'byte_end': offsets[index + 1],
            'scalar_start': index, 'scalar_end': index + 1,
            'codepoint': 'U+{:04X}'.format(ord(character)),
            'name': name, 'category': category,
            'bidi': unicodedata.bidirectional(character),
            'combining': unicodedata.combining(character),
            'utf8_hex': character.encode('utf-8').hex(),
            'before': codepoints(text[max(0, index - 2):index]),
            'after': codepoints(text[index + 1:index + 3]),
            'disposition': 'preserve-or-flag',
        }
        if full_inventory:
            observations.append(observation)
        else:
            heapq.heappush(examples, (-priority, -index, observation))
            if len(examples) > 32:
                heapq.heappop(examples)
    if not full_inventory:
        observations = sorted((item[2] for item in examples), key=lambda item: item['scalar_start'])
    return {
        'schema_version': 2, 'policy': POLICY, 'unicode_version': unicodedata.unidata_version,
        'encoding': 'UTF-8', 'input_sha256': digest(data), 'utf8_bytes': len(data),
        'unicode_scalars': len(text), 'observations': observations, 'edits': [],
        'inventory': 'full' if full_inventory else 'summary',
        'category_counts': dict(categories), 'script_name_counts': dict(scripts),
        'interesting_scalars': interesting,
        'omitted_examples': max(0, interesting - len(observations)) if not full_inventory else 0,
        'fidelity_editorial': 'not-assessed',
        'statistical_watermark': 'unavailable/unverified', 'generic_detector': 'not-attempted',
    }


def hash_value(value, label):
    require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None,
            'invalid SHA-256: ' + label)
    return value


def hex_bytes(value, label):
    require(isinstance(value, str) and re.fullmatch(r'(?:[0-9a-f]{2})*', value) is not None,
            'invalid lowercase byte hex: ' + label)
    return bytes.fromhex(value)


def nonempty_string(value, label):
    require(isinstance(value, str) and bool(value.strip()), 'missing ' + label)


def span(start, end, boundaries, label):
    require(type(start) is int and type(end) is int and 0 <= start < end <= max(boundaries),
            'invalid range: ' + label)
    require(start in boundaries and end in boundaries, 'range splits UTF-8 scalar: ' + label)
    return start, end


def ranges(value, boundaries, label):
    require(isinstance(value, list), 'invalid ranges: ' + label)
    result = []
    for pair in value:
        require(isinstance(pair, list) and len(pair) == 2, 'invalid range pair: ' + label)
        start, end = span(pair[0], pair[1], boundaries, label)
        require(not result or result[-1][1] <= start, 'overlapping/unsorted ranges: ' + label)
        result.append((start, end))
    return result


def in_range(start, end, spans):
    return any(left <= start and end <= right for left, right in spans)


def validate_scope(scope, boundaries, size):
    fields(scope, ('editable', 'protected', 'locks'), 'scope')
    editable = ranges(scope['editable'], boundaries, 'editable')
    protected = ranges(scope['protected'], boundaries, 'protected')
    locks = ranges(scope['locks'], boundaries, 'locks')
    cursor = 0
    for start, end in sorted(editable + protected):
        require(start == cursor, 'editable/protected scope must partition input exactly')
        cursor = end
    require(cursor == size, 'scope does not cover input')
    require(all(in_range(start, end, protected) for start, end in locks),
            'locks must lie inside protected ranges')
    return editable, protected


def validate_boundary(boundary, data, text, start, end, scalar_start, scalar_end, replacement):
    fields(boundary, ('left_hex', 'right_hex', 'result_hex', 'intent'), 'boundary')
    left = hex_bytes(boundary['left_hex'], 'left context')
    right = hex_bytes(boundary['right_hex'], 'right context')
    result = hex_bytes(boundary['result_hex'], 'boundary result')
    left_text, right_text = text_bytes(left), text_bytes(right)
    require(len(left) <= start and data[start - len(left):start] == left, 'left context mismatch')
    require(data[end:end + len(right)] == right, 'right context mismatch')
    require((start == 0 or left_text) and (end == len(data) or right_text),
            'boundary requires immediate neighbor context')
    require(result == left + replacement + right, 'boundary result mismatch')
    intent = boundary['intent']
    require(intent in ('restore-known-word', 'preserve-separation', 'preserve-format'),
            'unknown boundary intent')
    before = text[scalar_start - 1] if scalar_start else ''
    after = text[scalar_end] if scalar_end < len(text) else ''
    if intent == 'restore-known-word':
        removed = text[scalar_start:scalar_end]
        require(not replacement and before.isalnum() and after.isalnum() and
                all(unicodedata.category(character) in ('Cf', 'Co') for character in removed),
                'word restoration requires inserted format/private-use bytes between word characters')
    elif intent == 'preserve-separation':
        replacement_text = text_bytes(replacement)
        require(bool(replacement_text) and all(character.isspace() for character in replacement_text),
                'separation requires a nonempty whitespace replacement')
    else:
        require(not (before.isalnum() and after.isalnum()),
                'format edit between word characters requires an explicit word/separation intent')
    return left, right, result


def apply_edits(original, data, plan):
    """Apply only explicit original-bound spans; return bytes and a stable byte receipt.

    This validates caller-supplied boundary assertions, not linguistic meaning.
    Rewritten inputs are refused until frozen original-protection mapping exists.
    """
    original_text = text_bytes(original)
    text = text_bytes(data)
    fields(plan, ('schema_version', 'original_sha256', 'input_sha256', 'scope', 'edits'), 'plan')
    require(type(plan['schema_version']) is int and plan['schema_version'] == 1, 'unsupported plan version')
    require(hash_value(plan['original_sha256'], 'original') == digest(original), 'original hash mismatch')
    require(hash_value(plan['input_sha256'], 'input') == digest(data), 'input hash mismatch')
    require(original == data, 'v1 requires edit input identical to captured original; rewritten input unsupported')
    offsets = scalar_offsets(text)
    boundaries = {position: index for index, position in enumerate(offsets)}
    original_boundaries = set(scalar_offsets(original_text))
    editable, protected = validate_scope(plan['scope'], boundaries, len(data))
    require(isinstance(plan['edits'], list), 'edits must be a list')
    edits = []
    preserved = []
    pieces = []
    cursor = output_size = output_scalars = 0
    for item in plan['edits']:
        fields(item, ('byte_start', 'byte_end', 'scalar_start', 'scalar_end', 'expected_hex',
                      'replacement_hex', 'reason', 'authorization', 'source_anchor', 'boundary'), 'edit')
        start, end = span(item['byte_start'], item['byte_end'], boundaries, 'edit')
        require(start >= cursor, 'overlapping/unsorted edits')
        require(in_range(start, end, editable), 'edit intersects protected/out-of-scope bytes')
        scalar_start, scalar_end = boundaries[start], boundaries[end]
        require(type(item['scalar_start']) is int and type(item['scalar_end']) is int and
                item['scalar_start'] == scalar_start and item['scalar_end'] == scalar_end,
                'scalar/byte coordinates mismatch')
        expected = hex_bytes(item['expected_hex'], 'expected')
        replacement = hex_bytes(item['replacement_hex'], 'replacement')
        require(expected == data[start:end], 'expected input bytes mismatch')
        require(expected != replacement, 'no-op edit must use an empty edit list')
        replacement_text = text_bytes(replacement)
        nonempty_string(item['reason'], 'edit reason')
        nonempty_string(item['authorization'], 'authorization reference')
        anchor = item['source_anchor']
        fields(anchor, ('unit_id', 'byte_start', 'byte_end', 'expected_hex'), 'source anchor')
        nonempty_string(anchor['unit_id'], 'source unit label')
        anchor_start, anchor_end = span(anchor['byte_start'], anchor['byte_end'], original_boundaries, 'source anchor')
        require(anchor_start <= start and end <= anchor_end, 'source anchor does not contain edit')
        require(hex_bytes(anchor['expected_hex'], 'source anchor') == original[anchor_start:anchor_end],
                'original source anchor bytes mismatch')
        left, right, boundary_result = validate_boundary(item['boundary'], data, text, start, end,
                                                        scalar_start, scalar_end, replacement)
        unchanged = data[cursor:start]
        if unchanged:
            preserved.append({'input_start': cursor, 'input_end': start, 'output_start': output_size,
                              'output_end': output_size + len(unchanged), 'sha256': digest(unchanged)})
        pieces.extend((unchanged, replacement))
        output_size += len(unchanged)
        output_scalars += scalar_start - boundaries[cursor]
        edits.append(dict(item, source_anchor=dict(anchor), boundary=dict(item['boundary']),
                          output_byte_start=output_size, output_byte_end=output_size + len(replacement),
                          output_scalar_start=output_scalars, output_scalar_end=output_scalars + len(replacement_text),
                          original_codepoints=codepoints(expected.decode('utf-8')),
                          replacement_codepoints=codepoints(replacement_text)))
        output_size += len(replacement)
        output_scalars += len(replacement_text)
        cursor = end
    tail = data[cursor:]
    if tail:
        preserved.append({'input_start': cursor, 'input_end': len(data), 'output_start': output_size,
                          'output_end': output_size + len(tail), 'sha256': digest(tail)})
    pieces.append(tail)
    output = b''.join(pieces)
    for item in edits:
        boundary = item['boundary']
        left, right = bytes.fromhex(boundary['left_hex']), bytes.fromhex(boundary['right_hex'])
        start, end = item['output_byte_start'], item['output_byte_end']
        require(start >= len(left) and output[start - len(left):end + len(right)] == bytes.fromhex(boundary['result_hex']),
                'other edits invalidate declared output boundary')

    def project(position):
        return position + sum(len(bytes.fromhex(item['replacement_hex'])) - (item['byte_end'] - item['byte_start'])
                              for item in edits if item['byte_end'] <= position)

    protected_receipts = []
    for start, end in protected:
        out_start, out_end = project(start), project(end)
        require(output[out_start:out_end] == data[start:end], 'protected byte continuity failed')
        protected_receipts.append({'input_start': start, 'input_end': end, 'output_start': out_start,
                                   'output_end': out_end, 'sha256': digest(data[start:end])})
    receipt = {
        'schema_version': 1, 'policy': POLICY, 'unicode_version': unicodedata.unidata_version, 'encoding': 'UTF-8',
        'original_sha256': digest(original), 'input_sha256': digest(data), 'output_sha256': digest(output),
        'plan_sha256': digest(canonical_json(plan)), 'scope_sha256': digest(canonical_json(plan['scope'])),
        'edits': edits, 'preserved_ranges': preserved, 'protected_ranges': protected_receipts,
        'observations_before': inspect_bytes(data, full_inventory=True)['observations'],
        'observations_after': inspect_bytes(output, full_inventory=True)['observations'],
        'fidelity_editorial': 'not-assessed', 'statistical_watermark': 'unavailable/unverified',
        'generic_detector': 'not-attempted',
    }
    return output, receipt


def load_stages():
    spec = importlib.util.spec_from_file_location('humanizer_integrity_stages', Path(__file__).with_name('stages.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_new(path, data):
    with path.open('xb') as stream:
        os.chmod(str(path), 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def publish_output(path, data):
    # Link a complete private temporary inode, never the retained audit snapshot.
    # Exclusive linking preserves a concurrently created destination unchanged.
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '.integrity-', dir=str(path.parent))
    temporary = Path(temporary)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(str(temporary), str(path))
    finally:
        temporary.unlink()


def apply_files(args):
    stages = load_stages()
    run = Path(args.run).resolve(strict=True)
    try:
        with stages.locked(run):
            return apply_locked(args, stages, run)
    except stages.StageError as error:
        raise IntegrityError(str(error)) from error


def apply_locked(args, stages, run):
    state = stages.load(run)
    ticket = stages.attempt(state, args.ticket)
    require(ticket['kind'] in ('initial', 'self-revision', 'judge-revision'), 'ticket is not a writer reservation')
    require(ticket['status'] == 'reserved', 'writer ticket is not pending')
    require(not any(review['kind'] == 'judge' and review['analysis']['available'] and
                    review['analysis']['verdict'] == 'PASS' for review in state['reviews']),
            'valid independent PASS forbids cleanup mutation')
    source_path = Path(state['original']['source_path']).resolve()
    input_path = Path(args.input).resolve(strict=True)
    plan_path = Path(args.plan).resolve(strict=True)
    output_path = Path(args.output).absolute()
    audit_root = Path(str(run) + '.text-integrity')
    require(not audit_root.is_symlink(), 'audit root is a symlink')
    resolved_output = output_path.resolve()
    require(resolved_output not in (source_path, input_path, plan_path), 'output aliases source/input/plan')
    require(resolved_output != run and run not in resolved_output.parents, 'output must be outside keeper directory')
    require(resolved_output != audit_root and audit_root not in resolved_output.parents,
            'output must be outside audit directory')
    require(not os.path.lexists(str(output_path)), 'output already exists')
    original = (run / 'original.txt').read_bytes()
    require(source_path.read_bytes() == original, 'source changed since capture')
    data = input_path.read_bytes()
    plan = json.loads(plan_path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    output, receipt = apply_edits(original, data, plan)
    receipt.update(run=str(run), ticket=args.ticket, output_path=str(output_path))
    audit_root.mkdir(mode=0o700, exist_ok=True)
    evidence = audit_root / args.ticket
    require(evidence.parent == audit_root and re.fullmatch(r'draft-[1-4]', args.ticket) is not None,
            'invalid writer ticket path')
    evidence.mkdir(mode=0o700)
    try:
        for name, content in (('input.txt', data), ('output.txt', output),
                              ('plan.json', canonical_json(plan)), ('receipt.json', canonical_json(receipt))):
            write_new(evidence / name, content)
        publish_output(output_path, output)
        require(output_path.read_bytes() == output, 'published output readback mismatch')
        write_new(evidence / 'complete.json', canonical_json({
            'run': str(run), 'ticket': args.ticket, 'receipt_sha256': digest(canonical_json(receipt)),
            'output_sha256': digest(output),
        }))
    except (OSError, ValueError, TypeError) as error:
        # A partial sidecar is retained and blocks this ticket; no successful
        # receipt is returned. The host still records the reserved failure.
        try:
            write_new(evidence / 'failure.json', canonical_json({'status': 'incomplete', 'error': str(error)}))
        except OSError as retention_error:
            raise IntegrityError('{}; failure evidence could not be retained: {}'.format(error, retention_error)) from error
        raise
    return receipt


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('inspect', help='Read-only exact UTF-8 inventory; no watermark assessment')
    inspect.add_argument('input')
    inspect.add_argument('--expected-sha256')
    inspect.add_argument('--full-inventory', action='store_true', help='Emit all non-ASCII/control observations; keep large inventories outside model context')
    apply = commands.add_parser('apply-edits', help='Explicit original-only edits under an existing writer reservation')
    apply.add_argument('input')
    for option in ('plan', 'run', 'ticket', 'output'):
        apply.add_argument('--' + option, required=True)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'inspect':
            result = inspect_bytes(Path(args.input).read_bytes(), full_inventory=args.full_inventory)
            if args.expected_sha256 is not None:
                require(hash_value(args.expected_sha256, 'expected') == result['input_sha256'], 'expected hash mismatch')
        else:
            result = apply_files(args)
        sys.stdout.buffer.write(canonical_json(result))
        return 0
    except (IntegrityError, OSError, ValueError, KeyError, TypeError, IndexError, RuntimeError) as error:
        print('error: ' + json.dumps(str(error), ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
