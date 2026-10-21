#!/usr/bin/env python3
# ABOUTME: Checks both host catalogs, skill metadata, packaged resources and helper syntax.

import ast
import json
from pathlib import Path
import re
import subprocess
import sys

from sync_metadata import ROOT, generated_files

# Reuse the kit's YAML reader (PyYAML, or macOS Ruby's YAML parser).
sys.path.insert(0, str(ROOT / 'plugins/feature-spec/scripts/lib'))
from check_frontmatter import load_yaml

# Dispatch examples can override the host even when frontmatter omits a model.
# Match YAML, JSON and keyword-argument selectors, not model_reasoning_effort.
MODEL_ASSIGNMENT = re.compile(r'''(?<![\w-])["']?model["']?\s*[:=]''')


def check(root=ROOT):
    errors = []

    def require(condition, path, message):
        if not condition:
            errors.append(f'{path.relative_to(root)}: {message}')

    def frontmatter(path):
        text = path.read_text()
        match = re.match(r'^---\n(.*?)\n---\n', text, re.S)
        require(match is not None, path, 'missing frontmatter')
        if not match:
            return {}, text
        try:
            meta = load_yaml(match.group(1))
        except (ValueError, LookupError) as exc:
            require(False, path, f'YAML could not be checked: {exc}')
            return {}, text[match.end():]
        require(isinstance(meta, dict), path, 'frontmatter must be a mapping')
        return meta if isinstance(meta, dict) else {}, text[match.end():]

    for path, expected in generated_files(root):
        require(path.is_file() and path.read_text() == expected, path,
                'generated content differs; run python3 scripts/sync_metadata.py')

    catalog_path = root / '.claude-plugin/marketplace.json'
    catalog = json.loads(catalog_path.read_text())
    entries = catalog['plugins']
    names = [e['name'] for e in entries]
    require(len(names) == len(set(names)), catalog_path, 'duplicate plugin name')
    actual = {p.name for p in (root / 'plugins').iterdir() if p.is_dir()}
    require(set(names) == actual, catalog_path, 'catalog does not match plugin directories')
    skill_count = agent_count = 0
    for entry in entries:
        plugin = root / entry['source']
        require(entry['source'] == f'./plugins/{entry["name"]}', catalog_path,
                f'{entry["name"]}: source must point at its packaged directory')
        manifest_path = plugin / '.claude-plugin/plugin.json'
        manifest = json.loads(manifest_path.read_text())
        require(manifest['name'] == entry['name'], manifest_path, 'name differs from catalog')
        require(bool(re.fullmatch(r'\d+\.\d+\.\d+', manifest['version'])), manifest_path,
                'expected a semantic release version')
        require(bool(manifest.get('description')) and bool(manifest.get('author', {}).get('name')),
                manifest_path, 'description and author.name are required')
        skills = list((plugin / 'skills').glob('*/SKILL.md'))
        require(bool(skills), manifest_path, 'plugin has no skills')
        for path in skills:
            skill_count += 1
            meta, body = frontmatter(path)
            require('model' not in meta, path,
                    'omit model metadata so user and host configuration select it')
            name, desc = meta.get('name', ''), meta.get('description', '')
            require(name == path.parent.name and bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name)),
                    path, 'name must match its kebab-case folder')
            require(isinstance(desc, str) and 0 < len(desc) <= 1024, path,
                    'description must contain 1–1024 characters')
            require('CLAUDE_PLUGIN_ROOT' not in body and 'CLAUDE_SKILL_DIR' not in body,
                    path, 'Claude path substitution in shared instructions')
            require(not re.search(r'(?<![`\w])!`[^`]+`', body), path,
                    'dynamic shell injection requires Claude; run the command explicitly')
            require('(../../references/runtime.md)' in body, path, 'runtime guidance is not linked')
            policy_path = path.parent / 'agents/openai.yaml'
            policy = load_yaml(policy_path.read_text())['policy']['allow_implicit_invocation']
            require(policy is (not meta.get('disable-model-invocation', False)), policy_path,
                    'Codex invocation policy differs from Claude policy')
            # Claude grants and portable script calls must still name the same helpers.
            grants = set(re.findall(r'Bash\(bash \$\{CLAUDE_PLUGIN_ROOT\}/scripts/([\w.-]+\.sh)',
                                    path.read_text().split('---', 2)[1]))
            used = set(re.findall(r'<plugin-root>/scripts/([\w.-]+\.sh)', body))
            require(grants == used, path, f'script grants differ: granted={sorted(grants)}, used={sorted(used)}')
            for agent_plugin, role in re.findall(r'subagent_type[:=]\s*"([\w-]+):([\w-]+)"', body):
                require(agent_plugin == plugin.name and (plugin / 'agents' / f'{role}.md').is_file(),
                        path, f'agent role not bundled: {agent_plugin}:{role}')
        for path in (plugin / 'agents').glob('*.md'):
            agent_count += 1
            meta, _ = frontmatter(path)
            require(meta.get('name') == path.stem, path, 'agent name differs from filename')
            require('model' not in meta, path,
                    'omit model metadata, including inherit, to preserve user subagent defaults')
        for path in plugin.rglob('*.md'):
            if 'evals' in path.parts:
                continue
            text = path.read_text()
            body = re.sub(r'^---\n.*?\n---\n', '', text, count=1, flags=re.S)
            require(not MODEL_ASSIGNMENT.search(body), path,
                    'omit model assignments in workflow instructions; follow the runtime model policy')
            if path.name == 'runtime.md':
                continue
            skill_dir = next((parent for parent in path.parents if (parent / 'SKILL.md').is_file()), None)
            for token, resource in re.findall(r'(<plugin-root>|<skill-dir>)/([\w./-]+\.(?:md|sh|json|py))', text):
                base = plugin if token == '<plugin-root>' else skill_dir
                require(base is not None and (base / resource).is_file(), path,
                        f'missing packaged resource: {token}/{resource}')
            for target in re.findall(r'\[[^\]\n]+\]\(([^)\s]+)\)', text):
                if ':' in target or target.startswith(('#', '/', '<')) or '<' in target:
                    continue
                require((path.parent / target.split('#')[0]).exists(), path, f'broken relative link: {target}')
        readme = plugin / 'README.md'
        require('Claude Code' in readme.read_text() and 'Codex' in readme.read_text(), readme,
                'both hosts must be documented')
        for path in plugin.rglob('*.json'):
            json.loads(path.read_text())

    # Validate user-facing invocation examples against the installed skill names.
    commands = {
        f'{entry["name"]}:{path.parent.name}'
        for entry in entries
        for path in (root / entry['source'] / 'skills').glob('*/SKILL.md')
    }
    for path in [root / 'README.md', *root.glob('plugins/*/README.md')]:
        for command in re.findall(r'/([a-z0-9-]+:[a-z0-9:-]+)', path.read_text()):
            if command.split(':')[0] in names:
                require(command in commands, path, f'unknown skill invocation: /{command}')

    # Syntax checks run without executing helper behavior or creating bytecode files.
    for path in [*root.glob('scripts/*.py'), *root.glob('plugins/*/scripts/**/*.py')]:
        try:
            ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as exc:
            require(False, path, str(exc))
    for path in root.glob('plugins/*/scripts/*.sh'):
        result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
        require(result.returncode == 0, path, result.stderr.strip())
    if errors:
        print('\n'.join(f'FAIL {error}' for error in errors))
        return 1
    print(f'Compatibility checks passed: {len(entries)} plugins, {skill_count} skills, {agent_count} agent roles')
    return 0


if __name__ == '__main__':
    sys.exit(check())
