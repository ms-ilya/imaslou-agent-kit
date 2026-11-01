#!/usr/bin/env python3
# ABOUTME: Retains Humanizer artifacts and enforces bounded local transitions from supplied reviews.

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import uuid

_spec = importlib.util.spec_from_file_location('humanizer_contracts', Path(__file__).with_name('contracts.py'))
contracts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contracts)


class StageError(Exception):
    pass


LIMITS = {'initial': 1, 'self-revision': 2, 'judge-revision': 1, 'judge': 2}
HEADERS = ('PRESERVATION_CHECK', 'HALLUCINATION_CHECK', 'COVERAGE', 'OBJECTIVES', 'QUALITY_CHECK', 'AI_PATTERNS_FOUND',
           'SCORES', 'VERDICT')
DIMENSIONS = ('Directness', 'Rhythm', 'Trust', 'Authenticity', 'Preservation')
ARTIFACT = re.compile(r'(?:original|initial|accepted|candidate)\.txt|plan\.json|maps/draft-[1-4]\.json|drafts/draft-[1-4]\.txt|reports/(?:self-draft-[1-4](?:-format-1)?|judge-[1-4])\.txt')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise StageError(message)


def read_text_file(path):
    data = Path(path).read_bytes()
    require(bool(data), 'text/report file is empty: {}'.format(path))
    try:
        require('\x00' not in data.decode('utf-8'), 'NUL-containing text is unsupported')
    except UnicodeDecodeError:
        raise StageError('text/report must be UTF-8: {}'.format(path))
    return data


def atomic_write(path, data):
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        with temporary.open('xb') as stream:
            os.chmod(str(temporary), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'duplicate state key: {}'.format(key))
        value[key] = item
    return value


def save(run, state):
    data = (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    atomic_write(run / 'state.json', data)
    atomic_write(run / 'state.sha256', (digest(data) + '\n').encode('ascii'))


def file_path(run, relative):
    require(isinstance(relative, str) and ARTIFACT.fullmatch(relative), 'invalid internal artifact path')
    path = run / relative
    require(not path.is_symlink() and not path.parent.is_symlink(), 'internal artifact is a symlink')
    return path


def store_file(run, state, relative, data):
    path = file_path(run, relative)
    path.parent.mkdir(mode=0o700, exist_ok=True)
    atomic_write(path, data)
    state['files'][relative] = digest(data)


def review_text(data, kind, short_source):
    # Positions stay aligned with retained prose so format repair cannot discard quoted evidence.
    text = '\n'.join(data.decode('utf-8').splitlines())
    fences = []
    opened = None
    previous = ''
    offset = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip('\n')
        if opened is not None:
            start, marker, quoted = opened
            if re.fullmatch(r'[ \t]*' + re.escape(marker[0]) + '{' + str(len(marker)) + r',}[ \t]*', content):
                fences.append((start, offset + len(line), quoted))
                opened = None
                previous = ''
        else:
            match = re.fullmatch(r'[ \t]*(`{3,}|~{3,})(.*)', content)
            if match:
                quoted = (match.group(2).strip().lower() == 'source-example' or
                          re.fullmatch(r'(?:(?:Protected|Quoted) source|Source) example:', previous, re.I) is not None)
                opened = (offset, match.group(1), quoted)
            elif content.strip():
                previous = content.strip()
        offset += len(line)
    if not any(quoted for _, _, quoted in fences):
        return text, text

    def masked(ranges):
        characters = list(text)
        for start, end, _ in ranges:
            characters[start:end] = ('\n' if char == '\n' else ' ' for char in text[start:end])
        return ''.join(characters)

    outside = masked(fences)
    fields = {label: list(re.finditer(r'^[ \t]*' + label + r':[ \t]*(.*)$', outside, re.M)) for label in HEADERS}
    integrity_only = kind == 'self' and short_source and not any(fields[label] for label in HEADERS[5:])
    expected = HEADERS[:5] if integrity_only else HEADERS
    if any(len(fields[label]) != 1 for label in expected):
        return text, text
    positions = [fields[label][0].start() for label in expected]
    if positions != sorted(positions):
        return text, text
    # Examples belong in prose, not the strict findings or score blocks. A whole
    # fenced report has no complete outside judgment and is never exempted.
    quoted = [item for item in fences if item[2] and
              (integrity_only or item[1] <= fields['AI_PATTERNS_FOUND'][0].start() or
               item[0] >= fields['VERDICT'][0].end())]
    return text, masked(quoted)


def finding_records(block):
    records = []
    for line in block.strip().splitlines():
        item = json.loads(line, object_pairs_hook=unique_object)
        require(isinstance(item, dict), 'finding must be a JSON object')
        fields = {'tier', 'severity', 'pattern', 'quote', 'reason'}
        missing, unexpected = fields - set(item), set(item) - fields
        problems = (['missing ' + ', '.join(sorted(missing))] if missing else [])
        problems += (['unexpected ' + ', '.join(sorted(unexpected))] if unexpected else [])
        require(not problems, 'finding fields: ' + '; '.join(problems))
        require(type(item['tier']) is int and item['tier'] in (1, 2) and
                item['severity'] in ('minor', 'substantial'), 'invalid finding metadata')
        require(all(contracts.nonempty(item[key]) for key in ('pattern', 'quote', 'reason')), 'missing finding evidence')
        pattern = item['pattern'].strip()
        if pattern.isdecimal():
            require(pattern in {str(number) for number in range(1, 24)}, 'unknown numbered pattern')
            require(item['tier'] == (1 if int(pattern) <= 8 else 2), 'pattern tier contradicts catalog')
        records.append(item)
    return records


def parse_report(data, kind, short_source):
    _, text = review_text(data, kind, short_source)
    errors = []
    values = {}
    positions = {}
    for label in HEADERS:
        matches = list(re.finditer(r'^[ \t]*' + label + r':[ \t]*(.*)$', text, re.M))
        if len(matches) == 1:
            values[label] = matches[0].group(1).strip()
            positions[label] = matches[0]
        elif len(matches) > 1:
            errors.append('duplicate ' + label)

    # Code around a label is decoration; code enclosing the whole judgment is a quotation.
    adverse = {match.group(2).upper() for match in re.finditer(
        r'^[ \t]*(?:[-*][ \t]+)?[*_]*(?:(`+)(?:PRESERVATION_CHECK|HALLUCINATION_CHECK)\1|'
        r'(?:PRESERVATION_CHECK|HALLUCINATION_CHECK))[*_]*[ \t]*:[ \t*_`]*(FAIL|UNCERTAIN)\b', text, re.M | re.I)}
    hard_fail, uncertain = 'FAIL' in adverse, 'UNCERTAIN' in adverse
    semantic_status = ('fail' if hard_fail else 'uncertain' if uncertain else
                       'pass' if all(values.get(label) == 'PASS' for label in HEADERS[:2]) else 'unavailable')
    for label in HEADERS[:2]:
        if values.get(label) not in ('PASS', 'FAIL', 'UNCERTAIN'):
            errors.append('missing/invalid ' + label)
    for label, following in zip(HEADERS[:2], HEADERS[1:3]):
        if label in positions and following in positions:
            evidence = text[positions[label].end():positions[following].start()].strip()
            if not evidence:
                errors.append('missing review evidence: ' + label)

    scored = any(label in positions for label in HEADERS[5:])
    integrity_only = kind == 'self' and short_source and not scored
    result = {'available': False, 'hard_fail': hard_fail, 'text_hard_fail': hard_fail, 'errors': errors,
              'text_uncertain': uncertain, 'semantic_status': semantic_status,
              'preservation': values.get('PRESERVATION_CHECK'),
              'hallucination': values.get('HALLUCINATION_CHECK'),
              'total': None, 'scores': None, 'verdict': None,
              'editorial_status': 'unavailable', 'coverage': None, 'objectives': None,
              'quality': values.get('QUALITY_CHECK'), 'improvement_status': 'unresolved'}
    for label in ('COVERAGE', 'OBJECTIVES'):
        try:
            result[label.lower()] = json.loads(values.get(label, ''), object_pairs_hook=unique_object)
        except (ValueError, StageError):
            errors.append('missing/invalid ' + label)
    objectives = result['objectives']
    try:
        require(isinstance(objectives, list), 'invalid objective outcomes')
        contracts.ids(objectives)
        for item in objectives:
            contracts.fields(item, ('id', 'status', 'evidence'), 'objective outcome')
            require(item['status'] in ('achieved', 'retained', 'unresolved') and contracts.nonempty(item['evidence']),
                    'invalid objective outcome')
        statuses = {item['status'] for item in objectives}
        result['improvement_status'] = ('unresolved' if 'unresolved' in statuses else
                                        'improved' if 'achieved' in statuses else 'no-justified-change')
    except (ValueError, TypeError, KeyError, StageError):
        errors.append('invalid objective outcomes')
    if result['quality'] not in ('PASS', 'FAIL'):
        errors.append('missing/invalid QUALITY_CHECK')
    if not isinstance(result['coverage'], dict) or set(result['coverage']) != {'source', 'candidate', 'fixed'}:
        errors.append('invalid COVERAGE')
    if integrity_only:
        if adverse and all(values.get(label) == 'PASS' for label in HEADERS[:2]):
            errors.append('hard checks contradict explicit adverse evidence')
        result['available'] = not errors
        order = [positions[label].start() for label in HEADERS[:5] if label in positions]
        if order != sorted(order):
            errors.append('fields are out of contract order')
        result['available'] = not errors
        result['editorial_status'] = ('unavailable' if errors or hard_fail else 'unresolved' if uncertain else
                                     'style-shortfall' if result['quality'] == 'FAIL' or
                                     result['improvement_status'] == 'unresolved' else 'unscored')
        return result

    for label in HEADERS[5:]:
        if label not in positions:
            errors.append('missing ' + label)
    order = [positions[label].start() for label in HEADERS if label in positions]
    if order != sorted(order):
        errors.append('fields are out of contract order')

    scores = {}
    if 'SCORES' in positions and 'VERDICT' in positions:
        block = text[positions['SCORES'].end():positions['VERDICT'].start()]
        not_requested = values['SCORES'] == 'NOT_REQUESTED'
        if not_requested and block.strip():
            errors.append('NOT_REQUESTED scores must have no numeric block')
        elif values['SCORES'] and not not_requested:
            errors.append('invalid SCORES mode')
        for name in (() if not_requested else DIMENSIONS + ('Total',)):
            scale = '50' if name == 'Total' else '10'
            found = re.findall(r'^[ \t]*-[ \t]*' + name + r':[ \t]*(\d+)/' + scale + r'[ \t]*$', block, re.M)
            if len(found) != 1:
                errors.append('missing/invalid score ' + name)
            else:
                scores[name] = int(found[0])
                if not 0 <= scores[name] <= int(scale):
                    errors.append('score out of range: ' + name)
        if len(scores) == 6 and sum(scores[name] for name in DIMENSIONS) != scores['Total']:
            errors.append('score total does not equal dimension sum')

    findings = []
    count_value = values.get('AI_PATTERNS_FOUND', '')
    if not re.fullmatch(r'\d+', count_value):
        errors.append('missing/invalid findings count')
    elif 'AI_PATTERNS_FOUND' in positions and 'SCORES' in positions:
        count = int(count_value)
        block = text[positions['AI_PATTERNS_FOUND'].end():positions['SCORES'].start()].strip()
        if count == 0:
            if block.lower() not in ('', 'none', 'none.'):
                errors.append('zero findings has nonempty findings evidence')
        else:
            try:
                findings = finding_records(block)
                require(len(findings) == count, 'findings count mismatch')
            except (ValueError, TypeError, KeyError, StageError) as error:
                errors.append('invalid JSON finding records/count: ' + str(error))
    verdict = values.get('VERDICT')
    if verdict not in ('PASS', 'REVISE', 'UNRESOLVED'):
        errors.append('missing/invalid VERDICT')
    if not errors:
        editorial_pass = (result['quality'] == 'PASS' and result['improvement_status'] != 'unresolved' and
                          all(item['severity'] == 'minor' for item in findings))
        expected = ('REVISE' if hard_fail else 'UNRESOLVED' if uncertain else
                    'PASS' if editorial_pass else 'REVISE')
        if verdict != expected:
            errors.append('VERDICT contradicts supplied gates')
    result.update(available=not errors, scores=scores or None,
                  total=scores.get('Total'), verdict=verdict,
                  editorial_status=('unresolved' if uncertain else 'passed' if verdict == 'PASS' else
                                    'style-shortfall') if not errors and not hard_fail else 'unavailable')
    return result


def repair_evidence(data, short_source):
    # This recognizes existing decision evidence, not a substitute review format.
    text, fields_text = review_text(data, 'self', short_source)
    labels = HEADERS[:5] if short_source and not any(
        re.search(r'^[ \t]*' + label + ':', fields_text, re.M) for label in HEADERS[5:]) else HEADERS
    fields = {}
    for label in labels:
        matches = list(re.finditer(r'^[ \t]*' + label + r':[ \t]*(.*)$', fields_text, re.M))
        require(len(matches) == 1, 'format repair requires one unambiguous ' + label)
        fields[label] = matches[0]
    require([fields[label].start() for label in labels] == sorted(fields[label].start() for label in labels),
            'format repair requires decision fields in contract order')
    values = {label: fields[label].group(1).strip() for label in labels}
    require(all(values[label] in ('PASS', 'FAIL', 'UNCERTAIN') for label in HEADERS[:2]),
            'format repair requires explicit original hard-check outcomes')
    blocks = {label: text[fields[label].end():fields[labels[index + 1]].start()]
              for index, label in enumerate(labels[:-1])}
    blocks[labels[-1]] = text[fields[labels[-1]].end():]
    blocks['prefix'] = text[:fields[HEADERS[0]].start()]

    def normalized(value):
        return ' '.join(re.sub(r'^[ \t]*[-*][ \t]+(?=Tier[ \t]+[12]\b)', '', value,
                               flags=re.M | re.I).split())

    if labels != HEADERS:
        facts = dict(values, scores=None, findings_count=None)
        return facts, {label: normalized(blocks.get(label, '')) for label in HEADERS + ('prefix',)}
    require(values['VERDICT'] in ('PASS', 'REVISE', 'UNRESOLVED'), 'format repair requires an explicit original VERDICT')
    require(values['SCORES'] in ('', 'NOT_REQUESTED'), 'format repair requires an explicit original SCORES mode')
    scores = {}
    score_block = blocks['SCORES']
    not_requested = values['SCORES'] == 'NOT_REQUESTED'
    require(not not_requested or not score_block.strip(), 'NOT_REQUESTED scores must have no numeric block')
    for name in (() if not_requested else DIMENSIONS + ('Total',)):
        scale = 50 if name == 'Total' else 10
        matches = list(re.finditer(r'^[ \t]*(?:-[ \t]*)?' + name + r':[ \t]*(.*)$', score_block, re.M))
        require(len(matches) == 1, 'format repair requires one original score for ' + name)
        value = re.fullmatch(r'(\d+)/' + str(scale), matches[0].group(1).strip())
        require(value is not None and 0 <= int(value.group(1)) <= scale,
                'format repair requires an unambiguous original score for ' + name)
        scores[name] = int(value.group(1))
    require(not_requested or sum(scores[name] for name in DIMENSIONS) == scores['Total'],
            'format repair cannot resolve inconsistent original scores')
    blocks['SCORES'] = re.sub(r'^[ \t]*(?:-[ \t]*)?(?:' + '|'.join(DIMENSIONS + ('Total',)) +
                              r'):[ \t]*\d+/(?:10|50)[ \t]*$', '', score_block, flags=re.M)
    count = values['AI_PATTERNS_FOUND']
    findings = blocks['AI_PATTERNS_FOUND']
    if not count:
        # Explicit zero tier totals can corroborate a supplied repaired count; no
        # report or decision value is generated when this evidence is absent.
        totals = list(re.finditer(r'^[ \t]*Tier[ \t]+([12]):[ \t]*(\d+)[ \t]*$', findings, re.M | re.I))
        require(len(totals) == 2 and sorted((int(item.group(1)), int(item.group(2))) for item in totals) == [(1, 0), (2, 0)],
                'format repair cannot infer an absent findings count without explicit zero tier totals')
        count = '0'
    require(re.fullmatch(r'\d+', count) is not None, 'format repair requires an unambiguous original findings count')
    count = int(count)
    if count:
        require(len(finding_records(findings)) == count, 'format repair requires complete original finding evidence')
    else:
        without_totals = re.sub(r'^[ \t]*Tier[ \t]+[12]:[ \t]*0[ \t]*$', '', findings, flags=re.M | re.I)
        require(re.search(r'\bTier[ \t]+[12]\b', without_totals, re.I) is None,
                'format repair cannot turn marked findings into zero findings')
        findings = re.sub(r'^[ \t]*(?:None\.?)[ \t]*$', '', findings, flags=re.M | re.I)
    blocks['AI_PATTERNS_FOUND'] = findings

    facts = {label: values[label] for label in HEADERS[:2] + ('VERDICT',)}
    facts.update({label: values[label] for label in ('COVERAGE', 'OBJECTIVES', 'QUALITY_CHECK')})
    facts.update(scores=scores, score_mode=values['SCORES'], findings_count=count)
    return facts, {label: normalized(value) for label, value in blocks.items()}


def validate_format_repair(original, repaired, short_source):
    prior = parse_report(original, 'self', short_source)
    require(not prior['available'], 'a valid self-check cannot receive a format repair')
    analysis = parse_report(repaired, 'self', short_source)
    require(analysis['available'], 'format repair must satisfy the unchanged strict review format')
    before, old_text = repair_evidence(original, short_source)
    after, new_text = repair_evidence(repaired, short_source)
    require(before == after and prior['hard_fail'] == analysis['hard_fail'] and
            prior['text_uncertain'] == analysis['text_uncertain'],
            'format repair cannot change decision facts, scores, outcomes or findings count')
    for label in ('prefix', 'PRESERVATION_CHECK', 'HALLUCINATION_CHECK', 'COVERAGE', 'OBJECTIVES', 'QUALITY_CHECK', 'SCORES'):
        require(old_text[label] == new_text[label], 'format repair must retain original ' + label + ' evidence')
    if before['findings_count'] is None:
        return analysis
    if before['findings_count']:
        require(old_text['AI_PATTERNS_FOUND'] == new_text['AI_PATTERNS_FOUND'],
                'format repair must retain original finding evidence')
        require(old_text['VERDICT'] == new_text['VERDICT'], 'format repair must retain original verdict explanation')
    else:
        explanation = old_text['AI_PATTERNS_FOUND']
        require(not new_text['AI_PATTERNS_FOUND'], 'zero findings explanation belongs after VERDICT')
        retained = new_text['VERDICT']
        if explanation:
            matches = [match for match in re.finditer(re.escape(explanation), retained)
                       if (match.start() == 0 or retained[match.start() - 1] == ' ') and
                       (match.end() == len(retained) or retained[match.end()] == ' ')]
            require(len(matches) == 1, 'format repair must retain the complete zero-findings explanation after VERDICT')
            match = matches[0]
            retained = ' '.join((retained[:match.start()] + ' ' + retained[match.end():]).split())
        require(retained == old_text['VERDICT'], 'format repair must retain original verdict explanation')
    return analysis


def counts(state):
    return {kind.replace('-', '_'): sum(item['kind'] == kind for item in state['attempts']) for kind in LIMITS}


def analyze(data, kind, state, candidate):
    analysis = parse_report(data, kind, state['original']['words'] < 100)
    item = attempt(state, candidate)
    if item.get('mechanical_errors'):
        analysis['hard_fail'] = True
        analysis['errors'] += item['mechanical_errors']
    if analysis['available'] and not item.get('mechanical_errors'):
        analysis['errors'] += contracts.review_errors(analysis, state['plan'], item['mapping'])
    analysis['available'] = not analysis['errors']
    if not analysis['available']:
        analysis['editorial_status'] = 'unavailable'
    return analysis


def decode_mapping(raw):
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object), []
    except (ValueError, StageError) as error:
        return None, ['invalid candidate map JSON: ' + str(error)]


def load(run):
    for name in ('state.json', 'state.sha256'):
        require(not (run / name).is_symlink(), 'state file is a symlink')
    data = (run / 'state.json').read_bytes()
    require(digest(data) == (run / 'state.sha256').read_text().strip(), 'state checksum mismatch; run is not safe to continue')
    state = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)
    require(isinstance(state, dict) and state.get('version') == 3, 'unsupported state version; do not migrate or reset an active run budget')
    require(set(state) == {'version', 'original', 'files', 'attempts', 'reviews', 'selected', 'decisions', 'plan', 'provenance'}, 'invalid state fields')
    require(isinstance(state['original'], dict) and set(state['original']) == {'source_path', 'sha256', 'words'}, 'invalid original metadata')
    require(isinstance(state['original']['source_path'], str) and Path(state['original']['source_path']).is_absolute(), 'invalid original source path')
    require(type(state['original']['words']) is int and state['original']['words'] >= 0, 'invalid original word count')
    require(isinstance(state['files'], dict) and all(isinstance(value, str) for value in state['files'].values()), 'invalid artifact identities')
    require(all(isinstance(state[name], list) for name in ('attempts', 'reviews', 'decisions')), 'invalid transition records')
    require(isinstance(state['selected'], dict) and set(state['selected']) == {'candidate', 'reason'}, 'invalid selected artifact')
    require(all(isinstance(value, str) for value in state['selected'].values()), 'invalid selection values')
    for decision in state['decisions']:
        require(isinstance(decision, dict) and set(decision) == {'candidate', 'decision', 'reason'}, 'invalid decision record')
        require(all(isinstance(value, str) for value in decision.values()) and decision['decision'] in ('promote', 'retain'), 'invalid selection decision')
    for relative, expected in state['files'].items():
        require(digest(file_path(run, relative).read_bytes()) == expected, 'artifact checksum mismatch: ' + relative)
    require(state['files'].get('original.txt') == state['original']['sha256'], 'original identity mismatch')
    original = file_path(run, 'original.txt').read_bytes()
    require(json.loads(file_path(run, 'plan.json').read_bytes(), object_pairs_hook=unique_object) == state['plan'], 'frozen plan mismatch')
    contracts.validate_plan(state['plan'], original)
    require(state['provenance'] == contracts.provenance(Path(__file__).resolve().parents[1]),
            'installed plugin resources changed; cannot mix contracts within this run')
    original_words = len(file_path(run, 'original.txt').read_bytes().decode('utf-8').split())
    require(original_words == state['original']['words'], 'original word-count mismatch')
    identifiers = set()
    pending = 0
    for item in state['attempts']:
        require(isinstance(item, dict) and {'id', 'kind', 'reason', 'candidate', 'status'} <= set(item), 'invalid attempt record')
        require(item['kind'] in LIMITS and item['id'] not in identifiers, 'invalid/duplicate attempt')
        identifiers.add(item['id'])
        require(item['status'] in ('reserved', 'recorded', 'unavailable'), 'invalid attempt status')
        pending += item['status'] == 'reserved'
        if item['kind'] != 'judge' and item['status'] == 'recorded':
            candidate = file_path(run, 'drafts/' + item['id'] + '.txt').read_bytes()
            mapping, parse_errors = decode_mapping(file_path(run, 'maps/' + item['id'] + '.json').read_bytes())
            require(item['mapping'] == mapping and item['sha256'] == digest(candidate), 'candidate map/archive identity mismatch')
            require(item['mechanical_errors'] == (parse_errors or contracts.mapping_errors(state['plan'], original, candidate, mapping)),
                    'mechanical preservation metadata mismatch')
    require(pending <= 1, 'multiple unfinished attempts')
    used = counts(state)
    for kind, limit in LIMITS.items():
        require(used[kind.replace('-', '_')] <= limit, 'attempt limit exceeded in state')
    reviewed = {}
    for review in state['reviews']:
        require(isinstance(review, dict) and {'id', 'kind', 'candidate', 'candidate_sha256', 'path', 'analysis'} <= set(review), 'invalid review record')
        require(review['kind'] in ('self', 'judge'), 'invalid review provenance')
        require(review['id'] not in reviewed, 'duplicate review record')
        require(review['candidate_sha256'] == artifact(state, review['candidate'])[1], 'review candidate identity mismatch')
        raw = file_path(run, review['path']).read_bytes()
        require(analyze(raw, review['kind'], state, review['candidate']) == review['analysis'], 'review metadata mismatch')
        if 'format_repair_of' in review or 'format_repair_reason' in review:
            prior = reviewed.get(review.get('format_repair_of'))
            require(prior is not None and prior['kind'] == review['kind'] == 'self' and
                    review['id'] == prior['id'] + '-format-1' and
                    review['path'] == 'reports/' + review['id'] + '.txt' and
                    review['candidate'] == prior['candidate'] and review['candidate_sha256'] == prior['candidate_sha256'],
                    'invalid format-repair provenance')
            require('format_repair_of' not in prior and isinstance(review.get('format_repair_reason'), str) and
                    review['format_repair_reason'].strip(), 'invalid format-repair reason or repeated repair')
            validate_format_repair(file_path(run, prior['path']).read_bytes(), raw, state['original']['words'] < 100)
        reviewed[review['id']] = review
    return state


@contextmanager
def locked(run):
    require(run.is_dir(), 'run directory does not exist; use init first')
    lock = run / '.lock'
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise StageError('run is locked; confirm no command is active before removing a stale .lock')
    try:
        os.close(descriptor)
        yield
    finally:
        lock.unlink()


def attempt(state, identifier):
    matches = [item for item in state['attempts'] if item['id'] == identifier]
    require(len(matches) == 1, 'unknown attempt: ' + identifier)
    return matches[0]


def artifact(state, identifier):
    if identifier == 'original':
        return 'original.txt', state['original']['sha256']
    item = attempt(state, identifier)
    require(item['kind'] != 'judge' and item['status'] == 'recorded', 'candidate is not a recorded writer attempt')
    archived = 'drafts/' + identifier + '.txt'
    if archived in state['files']:
        require(state['files'][archived] == item['sha256'], 'candidate archive identity mismatch: ' + identifier)
        return archived, item['sha256']
    raise StageError('candidate bytes are no longer retained: ' + identifier)


def unresolved_semantics(state, identifier):
    """Only a later independent judgment on this candidate/map resolves same-byte doubt."""
    _, identity = artifact(state, identifier)
    pending = False
    for review in state['reviews']:
        if review['candidate_sha256'] != identity:
            continue
        analysis = review['analysis']
        if analysis['text_uncertain']:
            pending = True
        elif (review['candidate'] == identifier and review['kind'] == 'judge' and
              analysis['available'] and analysis['semantic_status'] == 'pass'):
            pending = False
    return pending


def evaluation(state, identifier):
    relative, identity = artifact(state, identifier)
    info = {'candidate': identifier, 'path': relative, 'sha256': identity, 'total': None,
            'verification': 'source-retained', 'editorial_status': 'unscored', 'independent_status': 'not-attempted'}
    if identifier == 'original':
        info['improvement_status'] = 'source-retained'
        return info
    require(not attempt(state, identifier)['mechanical_errors'], 'mechanical preservation failure blocks this candidate')
    reviews = [item for item in state['reviews'] if item['candidate_sha256'] == identity]
    require(not any(item['analysis']['text_hard_fail'] for item in reviews), 'hard-failure evidence blocks this candidate; retain or restore another artifact')
    require(not unresolved_semantics(state, identifier),
            'unresolved semantic evidence blocks this candidate; independent resolution or source retention required')
    # Coverage belongs to a candidate's immutable map. Only adverse textual
    # evidence follows identical bytes across tickets, never another map's PASS.
    reviews = [item for item in reviews if item['candidate'] == identifier]
    judges = [item for item in reviews if item['kind'] == 'judge']
    self_checks = [item for item in reviews if item['kind'] == 'self' and item['analysis']['available']]
    valid_judges = [item for item in judges if item['analysis']['available']]
    require(self_checks, 'complete a valid self-check before selection')
    if contracts.judge_required(state['plan'], state['original']['words']):
        require(judges, 'required independent attempt is missing for these exact candidate bytes')
    info['independent_status'] = 'available' if valid_judges else ('unavailable' if judges else 'not-attempted')
    info['latest_independent_status'] = ('available' if judges[-1]['analysis']['available'] else 'unavailable') if judges else 'not-attempted'
    chosen = valid_judges[-1] if valid_judges else (self_checks[-1] if self_checks else None)
    require(chosen is not None, 'no available review; record a valid labeled self-check or independent review')
    report = chosen['analysis']
    require(report['preservation'] == report['hallucination'] == 'PASS', 'hard checks have not passed')
    info.update(verification='independent' if chosen['kind'] == 'judge' else 'self-checked',
                editorial_status=report['editorial_status'], total=report['total'], verdict=report['verdict'],
                review=chosen['id'], review_total=report['total'], review_verdict=report['verdict'],
                self_total=self_checks[-1]['analysis']['total'] if self_checks else None,
                independent_total=valid_judges[-1]['analysis']['total'] if valid_judges else None,
                improvement_status=report['improvement_status'])
    if identity == state['original']['sha256'] and info['improvement_status'] == 'improved':
        info['improvement_status'] = 'no-justified-change'
        info['improvement_basis'] = 'candidate bytes equal the original; raw objective assessment retained'
    return info


def public_status(run, state):
    selected = {'candidate': state['selected']['candidate'], 'reason': state['selected']['reason']}
    try:
        selected.update(evaluation(state, selected['candidate']))
        selected['path'] = str(run / selected['path'])
        selected['eligible'] = True
    except StageError as error:
        relative, identity = artifact(state, selected['candidate'])
        selected.update(path=str(run / relative), sha256=identity, eligible=False, error=str(error))
    original = dict(state['original'], path=str(run / 'original.txt'))
    pending_semantic_review = [item['id'] for item in state['attempts']
                               if item['kind'] != 'judge' and item['status'] == 'recorded' and
                               unresolved_semantics(state, item['id'])]
    return {'counts': counts(state), 'original': original, 'selected': selected,
            'plan': {'path': str(run / 'plan.json'), 'sha256': state['files']['plan.json'],
                     'source_units': len(state['plan']['units']), 'fixed_spans': len(state['plan']['fixed'])},
            'provenance': {'versions': state['provenance']['versions'], 'runtime': state['plan']['runtime'],
                           'resource_count': len(state['provenance']['resource_sha256'])},
            'independent_required': contracts.judge_required(state['plan'], state['original']['words']) or bool(pending_semantic_review),
            'pending_semantic_review': pending_semantic_review,
            'attempts': [{key: value for key, value in item.items() if key != 'mapping'} for item in state['attempts']],
            'reviews': state['reviews'], 'decisions': state['decisions']}


def initialize(args, run):
    original_path = Path(args.original).resolve(strict=True)
    data = read_text_file(original_path)
    plan_data = read_text_file(args.plan)
    plan = contracts.validate_plan(json.loads(plan_data, object_pairs_hook=unique_object), data)
    require(not run.exists(), 'run directory already exists; a run cannot be reset')
    run.mkdir(mode=0o700)
    state = {'version': 3, 'plan': plan, 'provenance': contracts.provenance(Path(__file__).resolve().parents[1]),
             'original': {'source_path': str(original_path), 'sha256': digest(data),
                                     'words': len(data.decode('utf-8').split())},
             'files': {}, 'attempts': [], 'reviews': [], 'decisions': [],
             'selected': {'candidate': 'original', 'reason': 'Source retained until an explicit eligible promotion.'}}
    store_file(run, state, 'original.txt', data)
    store_file(run, state, 'plan.json', plan_data)
    save(run, state)
    return public_status(run, state)


def judge_candidate(state, candidate):
    relative, identity = artifact(state, candidate)
    require(candidate != 'original', 'judge a writer candidate, not the retained original')
    require(not attempt(state, candidate)['mechanical_errors'], 'mechanical preservation failure blocks judging')
    require(not any(review['candidate_sha256'] == identity and review['analysis']['text_hard_fail']
                    for review in state['reviews']), 'known hard-failure bytes cannot be sent to a judge')
    require(any(review['candidate'] == candidate and review['candidate_sha256'] == identity and review['kind'] == 'self' and
                review['analysis']['available'] and review['analysis']['semantic_status'] in ('pass', 'uncertain')
                for review in state['reviews']),
            'complete a valid self-check before independent judging')
    return relative, identity


def judge_packet(args, run, state):
    """Export review inputs without exposing the writer's candidate interpretation."""
    item = attempt(state, args.ticket)
    require(item['kind'] == 'judge' and item['status'] == 'reserved', 'packet requires a pending judge ticket')
    relative, identity = judge_candidate(state, item['candidate'])
    original = file_path(run, 'original.txt').read_bytes()
    candidate = file_path(run, relative).read_bytes()
    require(digest(original) == state['original']['sha256'] and digest(candidate) == identity,
            'review input changed during packet export')
    root = Path(__file__).resolve().parents[1]
    paths = ['agents/judge.md', 'skills/humanizer/references/verification.md']
    languages = {language.lower().replace('_', '-').split('-')[0] for language in state['plan']['brief']['languages']}
    if languages & {'ru', 'russian', 'русский'}:
        paths.append('skills/humanizer/references/russian.md')
    resources = []
    for path in paths:
        data = (root / path).read_bytes()
        require(digest(data) == state['provenance']['resource_sha256'][path], 'review resource changed: ' + path)
        resources.append({'path': path, 'sha256': digest(data), 'text': data.decode('utf-8')})
    plan = state['plan']
    mapping = attempt(state, item['candidate'])['mapping']
    return {'schema_version': 2, 'ticket': item['id'], 'offset_unit': 'UTF-8 bytes, half-open',
            'resources': resources, 'request': plan['request'], 'brief': plan['brief'],
            'original': {'sha256': digest(original), 'text': original.decode('utf-8'),
                         'units': plan['units'], 'anchors': contracts.source_anchors(plan, original), 'fixed': plan['fixed']},
            'candidate': {'id': item['candidate'], 'sha256': identity, 'text': candidate.decode('utf-8'),
                          'units': [{key: unit[key] for key in ('id', 'start', 'end')} for unit in mapping['units']]}}


def reserve(args, state):
    require(args.reason.strip(), 'a nonempty supported reason is required')
    require(not any(item['status'] == 'reserved' for item in state['attempts']), 'record the pending attempt before reserving another')
    require(not any(review['kind'] == 'judge' and review['analysis']['available'] and
                    review['analysis']['verdict'] == 'PASS' for review in state['reviews']),
            'a valid independent PASS closes further reservations')
    used = counts(state)
    require(used[args.kind.replace('-', '_')] < LIMITS[args.kind], 'attempt limit reached for ' + args.kind)
    if args.kind == 'initial':
        require(not state['attempts'], 'initial drafting must be the first attempt')
    else:
        require(used['initial'] == 1 and state['attempts'][0]['status'] == 'recorded', 'record the initial draft first')
    if args.kind == 'judge':
        require(args.candidate is not None, 'judge reservation requires --candidate')
        judge_candidate(state, args.candidate)
    else:
        require(args.candidate is None, '--candidate is only used for judge reservations')
        require(used['judge'] < 2, 'the judge retry is exhausted; retain a checked artifact or restore the original')
    if args.kind == 'judge-revision':
        judges = [item for item in state['reviews'] if item['kind'] == 'judge']
        require(judges and judges[-1]['analysis']['available'] and judges[-1]['analysis']['verdict'] == 'REVISE',
                'judge-revision requires a completed valid REVISE and a supported correction')
    number = used['judge'] + 1 if args.kind == 'judge' else sum(item['kind'] != 'judge' for item in state['attempts']) + 1
    identifier = ('judge-' if args.kind == 'judge' else 'draft-') + str(number)
    state['attempts'].append({'id': identifier, 'kind': args.kind, 'reason': args.reason,
                              'candidate': args.candidate, 'status': 'reserved'})
    return {'ticket': identifier, 'kind': args.kind, 'counts': counts(state)}


def record_review(run, state, identifier, candidate, kind, data):
    _, identity = artifact(state, candidate)
    relative = 'reports/' + identifier + '.txt'
    store_file(run, state, relative, data)
    analysis = analyze(data, kind, state, candidate)
    review = {'id': identifier, 'kind': kind, 'candidate': candidate, 'candidate_sha256': identity,
              'path': relative, 'analysis': analysis}
    state['reviews'].append(review)
    return dict(review, available=analysis['available'])


def record(args, run, state):
    item = attempt(state, args.ticket)
    require(item['status'] == 'reserved', 'attempt was already recorded')
    if args.unavailable:
        require(args.reason is not None and args.reason.strip(), '--unavailable requires a concrete --reason')
        if item['kind'] == 'judge':
            result = record_review(run, state, item['id'], item['candidate'], 'judge', b'')
            result['reason'] = args.reason
            state['reviews'][-1]['unavailable_reason'] = args.reason
        else:
            result = {'candidate': item['id'], 'available': False, 'reason': args.reason}
        item.update(status='unavailable', unavailable_reason=args.reason)
        return result
    if item['kind'] == 'judge':
        require(args.report is not None and args.text is None, 'judge attempt requires --report')
        result = record_review(run, state, item['id'], item['candidate'], 'judge', read_text_file(args.report))
    else:
        require(args.text is not None and args.report is None and args.mapping is not None, 'writer attempt requires --text and --mapping')
        data = read_text_file(args.text)
        mapping_data = Path(args.mapping).read_bytes()
        mapping, parse_errors = decode_mapping(mapping_data)
        archived = 'drafts/' + item['id'] + '.txt'
        require(not file_path(run, archived).exists(), 'candidate archive already exists: ' + item['id'])
        store_file(run, state, archived, data)
        store_file(run, state, 'maps/' + item['id'] + '.json', mapping_data)
        store_file(run, state, 'candidate.txt', data)
        if item['kind'] == 'initial':
            store_file(run, state, 'initial.txt', data)
        item['sha256'] = digest(data)
        item['mapping'] = mapping
        item['mechanical_errors'] = parse_errors or contracts.mapping_errors(state['plan'], file_path(run, 'original.txt').read_bytes(), data, mapping)
        result = {'candidate': item['id'], 'sha256': item['sha256'], 'mechanical_errors': item['mechanical_errors']}
    item['status'] = 'recorded'
    return result


def self_check(args, run, state):
    require(args.candidate != 'original', 'self-check a writer candidate')
    identifier = 'self-' + args.candidate
    if args.repair_format:
        require(args.reason is not None and args.reason.strip(), '--repair-format requires a concrete --reason')
        previous = [item for item in state['reviews'] if item['id'] == identifier]
        require(len(previous) == 1 and previous[0]['kind'] == 'self', 'format repair requires the retained original self-check')
        prior = previous[0]
        repaired_id = identifier + '-format-1'
        require(not any(item['id'] == repaired_id for item in state['reviews']), 'format repair already recorded for this candidate')
        _, identity = artifact(state, args.candidate)
        require(identity == prior['candidate_sha256'], 'format repair requires the same candidate bytes')
        data = read_text_file(args.report)
        validate_format_repair(file_path(run, prior['path']).read_bytes(), data, state['original']['words'] < 100)
        require(not file_path(run, 'reports/' + repaired_id + '.txt').exists(), 'format-repair artifact already exists')
        result = record_review(run, state, repaired_id, args.candidate, 'self', data)
        metadata = {'format_repair_of': identifier, 'format_repair_reason': args.reason}
        state['reviews'][-1].update(metadata)
        result.update(metadata)
        return result
    require(args.reason is None, '--reason is only used with --repair-format for self-check')
    require(not any(item['id'] == identifier for item in state['reviews']), 'self-check already recorded for this candidate')
    return record_review(run, state, identifier, args.candidate, 'self', read_text_file(args.report))


def select(args, run, state):
    require(args.reason.strip(), 'a nonempty supported reason is required')
    relative, _ = artifact(state, args.candidate)
    if args.decision == 'promote':
        require(not any(item['status'] == 'reserved' for item in state['attempts']), 'complete the pending attempt before promotion')
        evaluation(state, args.candidate)
        if args.candidate != 'original':
            store_file(run, state, 'accepted.txt', file_path(run, relative).read_bytes())
        state['selected'] = {'candidate': args.candidate, 'reason': args.reason}
    state['decisions'] = [item for item in state['decisions']
                          if (item['candidate'], item['decision']) != (args.candidate, args.decision)]
    state['decisions'].append({'candidate': args.candidate, 'decision': args.decision, 'reason': args.reason})
    return public_status(run, state)


def result(args, run, state):
    selected = evaluation(state, state['selected']['candidate'])
    data = file_path(run, selected['path']).read_bytes()
    if args.output is None:
        sys.stdout.buffer.write(data)
        return None
    output = Path(args.output).absolute()
    require(output.resolve() != Path(state['original']['source_path']), 'export cannot overwrite the original source')
    require(run != output.resolve() and run not in output.resolve().parents,
            'export destination must be outside the run directory')
    with output.open('xb') as stream:
        stream.write(data)
    return {'output': str(output), 'sha256': digest(data), 'selected': selected}


def parser():
    root = argparse.ArgumentParser(description=__doc__ or 'Bounded Humanizer artifact retention; no model or network calls.')
    commands = root.add_subparsers(dest='command', required=True)
    index = commands.add_parser('index', help='Read-only UTF-8 block offsets; no semantic or scope inference')
    index.add_argument('--text', required=True)
    index.add_argument('--prefix', choices=('u', 'c'), required=True)
    for name in ('init', 'reserve', 'record', 'self-check', 'judge-packet', 'select', 'result', 'status'):
        command = commands.add_parser(name)
        command.add_argument('run', help='New directory for init; the same run directory afterward')
        if name == 'init':
            command.add_argument('--original', required=True)
            command.add_argument('--plan', required=True)
        elif name == 'reserve':
            command.add_argument('--kind', choices=tuple(LIMITS), required=True)
            command.add_argument('--reason', required=True)
            command.add_argument('--candidate')
        elif name == 'record':
            command.add_argument('--ticket', required=True)
            inputs = command.add_mutually_exclusive_group(required=True)
            inputs.add_argument('--text')
            inputs.add_argument('--report')
            inputs.add_argument('--unavailable', action='store_true')
            command.add_argument('--reason')
            command.add_argument('--mapping', help='Required original/candidate-bound byte map for writer records')
        elif name == 'self-check':
            command.add_argument('--candidate', required=True)
            command.add_argument('--report', required=True)
            command.add_argument('--repair-format', action='store_true')
            command.add_argument('--reason')
        elif name == 'judge-packet':
            command.add_argument('--ticket', required=True)
        elif name == 'select':
            command.add_argument('--candidate', required=True)
            command.add_argument('--decision', choices=('promote', 'retain'), required=True)
            command.add_argument('--reason', required=True)
        elif name == 'result':
            command.add_argument('--output')
    return root


def main():
    args = parser().parse_args()
    try:
        if args.command == 'index':
            print(json.dumps(contracts.index_text(read_text_file(args.text), args.prefix), ensure_ascii=False))
            return 0
        run = Path(args.run).resolve()
        if args.command == 'init':
            output = initialize(args, run)
        else:
            with locked(run):
                state = load(run)
                if args.command == 'status':
                    output = public_status(run, state)
                elif args.command == 'result':
                    output = result(args, run, state)
                elif args.command == 'judge-packet':
                    output = judge_packet(args, run, state)
                else:
                    handlers = {'reserve': lambda: reserve(args, state), 'record': lambda: record(args, run, state),
                                'self-check': lambda: self_check(args, run, state), 'select': lambda: select(args, run, state)}
                    output = handlers[args.command]()
                    save(run, state)
        if output is not None:
            print(json.dumps(output, ensure_ascii=False, sort_keys=args.command != 'judge-packet'))
        return 0
    except (StageError, OSError, ValueError, KeyError, TypeError, IndexError, RuntimeError) as error:
        print('error: {}'.format(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
