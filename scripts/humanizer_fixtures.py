# ABOUTME: Supplies explicit synthetic plan and coverage fixtures for offline Humanizer protocol tests.

import hashlib
import json
from pathlib import Path


def plan_for(data):
    return {'schema_version': 2, 'source_sha256': hashlib.sha256(data).hexdigest(),
            'request': 'Synthetic protocol fixture; no claim of a real semantic review.',
            'brief': {'intensity': 'targeted', 'reader': 'fixture reader', 'genre': 'fixture',
                      'register': 'neutral', 'purpose': 'exercise retention mechanics', 'languages': ['en'],
                      'objectives': [{'id': 'fixture-objective', 'source_units': ['u1'],
                                      'issue': 'Synthetic transition fixture, not a real editorial judgment.',
                                      'action': 'Exercise the requested candidate transition.'}], 'no_change_reason': '',
                      'risks': [], 'judge_requested': False},
            'units': [{'id': 'u1', 'start': 0, 'end': len(data), 'section': 's1', 'links': []}],
            'anchors': [],
            'fixed': [], 'runtime': dict.fromkeys(('writer', 'judge', 'settings', 'watermark'), 'unknown')}


def mapping_for(source, candidate):
    return {'source_sha256': hashlib.sha256(source).hexdigest(),
            'candidate_sha256': hashlib.sha256(candidate).hexdigest(),
            'units': [{'id': 'c1', 'start': 0, 'end': len(candidate), 'source_units': ['u1']}], 'fixed': []}


def keeper_args(args):
    """Supply explicit synthetic plans and maps for CLI transition tests."""
    args = list(args)
    if args[0] == 'init' and '--plan' not in args:
        source = Path(args[args.index('--original') + 1])
        path = Path(str(args[1]) + '.fixture-plan.json')
        path.write_text(json.dumps(plan_for(source.read_bytes())))
        args += ['--plan', path]
    elif args[0] == 'record' and '--text' in args and '--mapping' not in args:
        candidate = Path(args[args.index('--text') + 1])
        path = Path(str(candidate) + '.fixture-map.json')
        path.write_text(json.dumps(mapping_for((Path(args[1]) / 'original.txt').read_bytes(), candidate.read_bytes())))
        args += ['--mapping', path]
    return args


OBJECTIVE_LINE = 'OBJECTIVES: [{"id":"fixture-objective","status":"achieved","evidence":"Synthetic protocol assertion; no model review executed."}]'
REVIEW_METADATA = ('COVERAGE: {"source":["u1"],"candidate":["c1"],"fixed":[]}\n' +
                   OBJECTIVE_LINE + '\nQUALITY_CHECK: PASS\n')


def integrity_report():
    return ('PRESERVATION_CHECK: PASS\nSynthetic preservation assertion for protocol testing.\n'
            'HALLUCINATION_CHECK: PASS\nSynthetic source-support assertion for protocol testing.\n' + REVIEW_METADATA)
