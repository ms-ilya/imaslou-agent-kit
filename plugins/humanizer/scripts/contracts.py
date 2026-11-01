#!/usr/bin/env python3
# ABOUTME: Validates frozen source plans, candidate byte maps and declared review coverage without inferring meaning.

import hashlib
import json
from pathlib import Path


RISKS = ('structural-recomposition', 'dense-relationships', 'mixed-language', 'protected-boundaries')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fields(value, names, label):
    require(isinstance(value, dict) and set(value) == set(names), 'invalid fields: ' + label)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def boundaries(data):
    text = data.decode('utf-8')
    require(bool(text) and '\x00' not in text, 'empty or NUL-containing text')
    offsets = {0}
    cursor = 0
    for char in text:
        cursor += len(char.encode('utf-8'))
        offsets.add(cursor)
    return offsets


def span(row, offsets):
    start, end = row['start'], row['end']
    require(type(start) is int and type(end) is int and start < end and
            start in offsets and end in offsets, 'invalid UTF-8 byte range')
    return start, end


def partition(rows, data):
    require(isinstance(rows, list) and rows, 'missing complete unit partition')
    offsets, cursor = boundaries(data), 0
    for row in rows:
        start, end = span(row, offsets)
        require(start == cursor, 'units must partition all bytes in order without gaps or overlaps')
        cursor = end
    require(cursor == len(data), 'units do not cover all bytes')


def ids(rows):
    values = [row['id'] for row in rows]
    require(all(nonempty(value) for value in values) and len(values) == len(set(values)), 'invalid/duplicate IDs')
    return set(values)


def index_text(data, prefix):
    """Locate physical blocks without assigning meaning, scope or source mappings."""
    boundaries(data)
    require(prefix in ('u', 'c'), 'index prefix must be u or c')
    rows, start, cursor, after_blank = [], 0, 0, False
    for line in data.decode('utf-8').splitlines(keepends=True):
        if after_blank and line.strip():
            rows.append({'id': prefix + str(len(rows) + 1), 'start': start, 'end': cursor})
            start = cursor
        cursor += len(line.encode('utf-8'))
        after_blank = not line.strip()
    if cursor > start:
        rows.append({'id': prefix + str(len(rows) + 1), 'start': start, 'end': cursor})
    partition(rows, data)
    return {'sha256': sha(data), 'offset_unit': 'UTF-8 bytes, half-open', 'units': rows,
            'largest_block_bytes': max(row['end'] - row['start'] for row in rows)}


def source_anchors(plan, source):
    """Derive quotations from captured bytes, never from preparatory paraphrases."""
    return [{'id': anchor['id'], 'question': anchor['question'],
             'spans': [dict(row, text=source[row['start']:row['end']].decode('utf-8'),
                            source_units=[unit['id'] for unit in plan['units']
                                          if unit['start'] < row['end'] and row['start'] < unit['end']])
                       for row in anchor['spans']]}
            for anchor in plan['anchors']]


def validate_plan(plan, source):
    fields(plan, ('schema_version', 'source_sha256', 'request', 'brief', 'units', 'anchors', 'fixed', 'runtime'), 'plan')
    require(plan['schema_version'] == 2 and plan['source_sha256'] == sha(source), 'plan source identity/version mismatch')
    require(nonempty(plan['request']), 'missing actual request')
    brief = plan['brief']
    fields(brief, ('intensity', 'reader', 'genre', 'register', 'purpose', 'languages', 'objectives',
                   'no_change_reason', 'risks', 'judge_requested'), 'brief')
    require(brief['intensity'] in ('targeted', 'full', 'unchanged'), 'invalid editing intensity')
    require(all(nonempty(brief[key]) for key in ('reader', 'genre', 'register', 'purpose')), 'incomplete rewrite brief')
    require(isinstance(brief['languages'], list) and brief['languages'] and
            all(nonempty(lang) for lang in brief['languages']), 'missing languages')
    require(isinstance(brief['risks'], list) and len(set(brief['risks'])) == len(brief['risks']) and
            set(brief['risks']) <= set(RISKS), 'invalid review risks')
    require(type(brief['judge_requested']) is bool, 'judge_requested must be boolean')
    partition(plan['units'], source)
    unit_ids = ids(plan['units'])
    for unit in plan['units']:
        fields(unit, ('id', 'start', 'end', 'section', 'links'), 'source unit')
        require(nonempty(unit['section']), 'missing source section')
        require(isinstance(unit['links'], list) and set(unit['links']) <= unit_ids, 'unknown cross-unit relationship')
    require(isinstance(plan['anchors'], list), 'invalid source anchors')
    ids(plan['anchors'])
    offsets = boundaries(source)
    for anchor in plan['anchors']:
        fields(anchor, ('id', 'spans', 'question'), 'source anchor')
        require(nonempty(anchor['question']), 'missing source question')
        require(isinstance(anchor['spans'], list) and anchor['spans'], 'source anchor needs exact ranges')
        end = 0
        for row in anchor['spans']:
            fields(row, ('start', 'end'), 'anchor span')
            start, stop = span(row, offsets)
            require(start >= end, 'anchor spans must be sorted and nonoverlapping')
            end = stop
    objectives = brief['objectives']
    require(isinstance(objectives, list), 'invalid objectives')
    ids(objectives)
    for objective in objectives:
        fields(objective, ('id', 'source_units', 'issue', 'action'), 'objective')
        require(isinstance(objective['source_units'], list) and objective['source_units'] and
                set(objective['source_units']) <= unit_ids, 'objective needs source locations')
        require(nonempty(objective['issue']) and nonempty(objective['action']), 'objective needs reader impact and intended change')
    require(isinstance(brief['no_change_reason'], str), 'invalid no-change reason')
    require(bool(objectives) != bool(brief['no_change_reason'].strip()), 'supply objectives or a justified no-change reason')
    require(brief['intensity'] != 'unchanged' or not objectives, 'unchanged plan cannot promise edits')
    require(isinstance(plan['fixed'], list), 'invalid fixed spans')
    ids(plan['fixed'])
    offsets, end = boundaries(source), 0
    for fixed in plan['fixed']:
        fields(fixed, ('id', 'start', 'end', 'kind'), 'fixed span')
        start, stop = span(fixed, offsets)
        require(start >= end, 'fixed spans must be sorted and nonoverlapping')
        require(fixed['kind'] in ('protected', 'out-of-scope', 'verbatim'), 'invalid fixed-span kind')
        end = stop
    runtime = plan['runtime']
    fields(runtime, ('writer', 'judge', 'settings', 'watermark'), 'runtime')
    require(all(nonempty(runtime[key]) for key in runtime), 'use unknown for unavailable runtime metadata')
    return plan


def mapping_errors(plan, source, candidate, mapping):
    """Return mechanical failures while retaining the actual rejected candidate."""
    try:
        fields(mapping, ('source_sha256', 'candidate_sha256', 'units', 'fixed'), 'candidate map')
        require(plan['brief']['intensity'] != 'unchanged' or candidate == source,
                'unchanged intensity requires original bytes')
        require(plan['brief']['objectives'] or candidate == source,
                'a plan with no rewrite objectives requires original bytes')
        require(mapping['source_sha256'] == sha(source) and mapping['candidate_sha256'] == sha(candidate),
                'candidate map identity mismatch')
        partition(mapping['units'], candidate)
        candidate_ids = ids(mapping['units'])
        require(candidate_ids, 'missing candidate units')
        covered = set()
        for unit in mapping['units']:
            fields(unit, ('id', 'start', 'end', 'source_units'), 'candidate unit')
            require(isinstance(unit['source_units'], list) and unit['source_units'], 'candidate unit needs source anchors')
            covered.update(unit['source_units'])
        require(covered == ids(plan['units']), 'candidate map must account for every source unit, without unknown anchors')
        require(isinstance(mapping['fixed'], list), 'invalid candidate fixed spans')
        require(ids(mapping['fixed']) == ids(plan['fixed']), 'candidate map omits/adds fixed spans')
        require([row['id'] for row in mapping['fixed']] == [row['id'] for row in plan['fixed']], 'fixed spans changed order')
        offsets, end, prior_source_end = boundaries(candidate), 0, None
        for before, after in zip(plan['fixed'], mapping['fixed']):
            fields(after, ('id', 'start', 'end'), 'candidate fixed span')
            start, stop = span(after, offsets)
            require(start >= end, 'candidate fixed spans overlap or are unsorted')
            require(source[before['start']:before['end']] == candidate[start:stop],
                    'fixed bytes changed: ' + before['id'])
            if before['kind'] == 'out-of-scope':
                require(before['start'] != 0 or start == 0, 'insertion before out-of-scope prefix')
                require(before['end'] != len(source) or stop == len(candidate), 'insertion after out-of-scope suffix')
            require(prior_source_end != before['start'] or start == end,
                    'insertion between adjacent fixed spans')
            end = stop
            prior_source_end = before['end']
        return []
    except (ValueError, KeyError, TypeError) as error:
        return [str(error)]


def review_errors(analysis, plan, mapping):
    errors = []
    coverage = analysis.get('coverage')
    expected = {'source': ids(plan['units']), 'candidate': ids(mapping['units']), 'fixed': ids(plan['fixed'])}
    if not isinstance(coverage, dict) or set(coverage) != set(expected):
        errors.append('missing bidirectional/fixed review coverage')
    else:
        for key, values in expected.items():
            actual = coverage[key]
            if not isinstance(actual, list) or not all(isinstance(value, str) for value in actual) or len(actual) != len(set(actual)) or set(actual) != values:
                errors.append('incomplete/unknown review coverage: ' + key)
    outcomes = analysis.get('objectives')
    if not isinstance(outcomes, list) or {item['id'] for item in outcomes} != ids(plan['brief']['objectives']):
        errors.append('objective review does not cover the frozen brief')
    return errors


def judge_required(plan, words):
    brief = plan['brief']
    return words > 2000 or brief['judge_requested'] or bool(brief['risks']) or len(set(brief['languages'])) > 1


def provenance(root):
    """Record installed resources and declared versions, not guessed model settings."""
    root = Path(root)
    # Hash only packaged execution resources; runtime evidence may live below root.
    paths = [root / '.claude-plugin/plugin.json', root / '.codex-plugin/plugin.json',
             root / 'references/runtime.md', root / 'agents/judge.md',
             root / 'skills/humanizer/SKILL.md', root / 'skills/humanizer/agents/openai.yaml']
    paths += list((root / 'scripts').glob('*.py'))
    paths += list((root / 'skills/humanizer/references').glob('*.md'))
    paths = sorted(paths)
    hashes = {str(path.relative_to(root)): sha(path.read_bytes()) for path in paths}
    versions = {str(path.relative_to(root)): json.loads(path.read_text())['version']
                for path in paths if path.name == 'plugin.json'}
    return {'versions': versions, 'resource_sha256': hashes}
