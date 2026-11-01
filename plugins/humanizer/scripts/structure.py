#!/usr/bin/env python3
# ABOUTME: Describes English/Russian prose structure and repeated phrasing without assigning authorship or quality scores.

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys


WORDS = re.compile(r"(?:[^\W\d_]|[\u0300-\u036f])+(?:['’\-](?:[^\W\d_]|[\u0300-\u036f])+)*|\d+(?:[.,]\d+)*")
ABBREVIATIONS = re.compile(r'\b(?:Mr|Mrs|Ms|Dr|Prof|etc|e\.g|i\.e|т\.\s*е|т\.\s*д|г|ул|им|стр)\.', re.I)


def sentences(text):
    # Mask only segmentation positions; reported text and offsets stay unchanged.
    masked = list(text)
    for match in ABBREVIATIONS.finditer(text):
        for index in range(match.start(), match.end()):
            if masked[index] == '.':
                masked[index] = '·'
    for match in re.finditer(r'(?<=\d)\.(?=\d)|\b[A-ZА-ЯЁ]\.(?=\s*[A-ZА-ЯЁ])', text):
        for index in range(match.start(), match.end()):
            if masked[index] == '.':
                masked[index] = '·'
    starts, result = 0, []
    for match in re.finditer(r'[.!?…]+[”"»\)\]]*(?=\s+|$)', ''.join(masked)):
        result.append(text[starts:match.end()].strip())
        starts = match.end()
    if text[starts:].strip():
        result.append(text[starts:].strip())
    return [item for item in result if WORDS.search(item)]


def distribution(values):
    if not values:
        return None
    ordered = sorted(values)
    return {'count': len(values), 'min': min(values), 'median': statistics.median(values),
            'max': max(values), 'mean': round(statistics.mean(values), 3),
            'stdev': round(statistics.pstdev(values), 3), 'p90': ordered[math.ceil(.9 * len(values)) - 1]}


def profile(data, language):
    text = data.decode('utf-8')
    if '\x00' in text:
        raise ValueError('NUL/binary input is unsupported')
    counts = Counter()
    paragraphs, pending = [], []
    fenced, frontmatter, html = None, None, False
    table = False
    container = None
    section = 'document'

    def flush():
        if pending:
            paragraphs.append({'line': pending[0][0], 'section': section,
                               'text': ' '.join(value.strip() for _, value in pending)})
            pending.clear()

    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        kind = None
        if number == 1 and stripped in ('---', '+++'):
            frontmatter = stripped
            kind = 'data'
        elif frontmatter:
            kind = 'data'
            if stripped == frontmatter:
                frontmatter = None
        elif fenced:
            kind = 'code'
            if re.fullmatch(re.escape(fenced[0]) + '{' + str(len(fenced)) + r',}\s*', stripped):
                fenced = None
        elif re.match(r'(`{3,}|~{3,})', stripped):
            fenced = re.match(r'(`{3,}|~{3,})', stripped).group(1)
            kind = 'code'
        elif html or stripped.startswith('<'):
            html = bool(stripped)
            kind = 'html'
        elif not stripped:
            kind = 'blank'
        elif line.startswith(('    ', '\t')):
            kind = 'code'
        elif re.match(r'#{1,6}\s', stripped) or (number < len(lines) and re.fullmatch(r'\s*(?:={3,}|-{3,})\s*', lines[number])):
            kind = 'headings'
        elif re.fullmatch(r'(?:={3,}|-{3,}|\*{3,})', stripped):
            kind = 'separator'
        elif '|' in stripped and (table or stripped.startswith('|') or number < len(lines) and re.match(r'\s*\|?\s*:?-{3,}', lines[number])):
            kind = 'tables'
        elif re.match(r'(?:[-+*]|\d+[.)])\s', stripped):
            kind = 'lists'
        elif stripped.startswith('>'):
            kind = 'quotes'
        elif re.match(r'\[[^]]+\]:', stripped):
            kind = 'references'
        elif container:
            kind = container
        table = kind == 'tables'
        container = kind if kind in ('lists', 'quotes') else None
        if kind:
            flush()
            counts[kind] += 1
            if kind == 'headings':
                section = 'line-' + str(number)
        else:
            pending.append((number, line))
    flush()
    eligible = language in ('en', 'ru')
    rows = []
    excluded_inline = 0
    for paragraph in paragraphs:
        clean, removed = re.subn(r'(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)', ' ', paragraph['text'])
        excluded_inline += removed
        # Link destinations are metadata; retain only the reader-visible label.
        clean = re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', clean)
        rows.append(dict(paragraph, text=clean, sentences=sentences(clean), words=WORDS.findall(clean)))
    all_sentences = [(sentence, row['line'], row['section']) for row in rows for sentence in row['sentences']]
    sentence_lengths = [len(WORDS.findall(sentence)) for sentence, _, _ in all_sentences]
    repeats = defaultdict(list)
    for kind, items in (('sentence-opening', all_sentences),
                        ('paragraph-opening', [(row['text'], row['line'], row['section']) for row in rows]),
                        ('paragraph-closing', [(row['text'], row['line'], row['section']) for row in rows])):
        for value, line, sec in items:
            tokens = [word.lower() for word in WORDS.findall(value)]
            phrase = tokens[-3:] if kind.endswith('closing') else tokens[:3]
            if len(phrase) == 3:
                repeats[(kind, ' '.join(phrase))].append({'line': line, 'section': sec})
    sections = defaultdict(list)
    for row in rows:
        sections[row['section']].append(row)
    for sec, members in sections.items():
        for kind, row, tail in (('section-opening', members[0], False), ('section-closing', members[-1], True)):
            tokens = [word.lower() for word in row['words']]
            if len(tokens) >= 3:
                repeats[(kind, ' '.join(tokens[-3:] if tail else tokens[:3]))].append({'line': row['line'], 'section': sec})
    local = []
    for row in rows:
        tokens = [word.lower() for word in row['words']]
        phrases = Counter(' '.join(tokens[index:index + 3]) for index in range(len(tokens) - 2))
        terms = Counter(word for word in tokens if len(word) >= 4)
        for kind, values in (('phrase', phrases), ('term', terms)):
            for value, count in sorted(values.items(), key=lambda pair: (-pair[1], pair[0])):
                if count > 1:
                    local.append({'kind': kind, 'text': value, 'count': count, 'line': row['line']})
    enough = eligible and len(all_sentences) >= 5 and len(rows) >= 3
    repeated = [{'kind': kind, 'text': phrase, 'count': len(locations), 'locations': locations[:5]}
                for (kind, phrase), locations in sorted(repeats.items()) if len(locations) > 1]
    return {'schema_version': 1, 'sha256': hashlib.sha256(data).hexdigest(), 'language': language,
            'eligibility': 'descriptive' if enough else 'insufficient-prose' if eligible else 'unsupported-or-mixed-language',
            'limitations': ['Heuristic Markdown and English/Russian segmentation; quotations, abbreviations and list continuations may be ambiguous.',
                            'Five sentences and three paragraphs are a reporting floor, not a human-writing target.',
                            'Repetition and regularity may be intentional; no quality, authorship, detector or watermark conclusion.'],
            'excluded_lines': dict(counts), 'inline_code_spans': excluded_inline,
            'prose_paragraphs': len(rows), 'prose_sentences': len(all_sentences),
            'sentence_words': distribution(sentence_lengths) if enough else None,
            'paragraph_words': distribution([len(row['words']) for row in rows]) if enough else None,
            'single_sentence_paragraph_fraction': round(sum(len(row['sentences']) == 1 for row in rows) / len(rows), 3) if enough else None,
            'repeated_boundaries': repeated[:20] if eligible else [],
            'local_repetition': local[:20] if eligible else [],
            'omitted_repetition_records': max(0, len(repeated) - 20) + max(0, len(local) - 20) if eligible else 0}


def main():
    parser = argparse.ArgumentParser(description='Read-only structure descriptions; no target scores or network calls.')
    parser.add_argument('source')
    parser.add_argument('--candidate')
    parser.add_argument('--sample')
    parser.add_argument('--language', choices=('en', 'ru', 'mixed', 'unknown'), required=True)
    args = parser.parse_args()
    try:
        result = {name: profile(Path(path).read_bytes(), args.language) for name, path in
                  (('source', args.source), ('candidate', args.candidate), ('style_sample', args.sample)) if path}
        print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print('error: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
