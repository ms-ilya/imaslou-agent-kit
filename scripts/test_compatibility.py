#!/usr/bin/env python3
# ABOUTME: Checks that packaged workflows leave model selection to user and host configuration.

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from check_compatibility import check
from sync_metadata import generated_files


class ModelSelectionPolicy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agent kit policy ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plugin = self.root / 'plugins/example'
        self.skill = self.plugin / 'skills/inspect/SKILL.md'
        self.agent = self.plugin / 'agents/reviewer.md'
        self.write(self.root / '.claude-plugin/marketplace.json', json.dumps({
            'name': 'test-kit', 'plugins': [{
                'name': 'example', 'source': './plugins/example',
                'description': 'Inspect a fixture.',
            }],
        }))
        self.write(self.plugin / '.claude-plugin/plugin.json', json.dumps({
            'name': 'example', 'version': '1.0.0',
            'description': 'Inspect a fixture.', 'author': {'name': 'Fixture'},
        }))
        self.write(self.root / 'README.md', 'Claude Code and Codex: /example:inspect\n')
        self.write(self.plugin / 'README.md', 'Claude Code and Codex: /example:inspect\n')
        self.write(self.root / 'docs/runtime.md', 'Leave model selection to the host.\n')
        self.write(self.skill, '''---
name: inspect
description: Inspect a fixture. Use when testing the package checker.
disable-model-invocation: true
effort: high
---

Read [runtime conventions](../../references/runtime.md).
Use a fresh context and return evidence.
''')
        self.write(self.agent, '''---
name: reviewer
description: Inspect only the assigned files.
tools: Read
maxTurns: 6
effort: high
---

Read the assigned input and report evidence without editing it.
''')
        for path, content in generated_files(self.root):
            self.write(path, content)

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def result(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = check(self.root)
        return status, output.getvalue()

    def assert_rejected(self, path):
        status, output = self.result()
        self.assertEqual(status, 1, output)
        self.assertIn(str(path.relative_to(self.root)), output)
        self.assertIn('model', output)

    def test_host_selection_preserves_effort_and_turn_limits(self):
        status, output = self.result()
        self.assertEqual(status, 0, output)
        self.assertIn('1 plugins, 1 skills, 1 agent roles', output)

    def test_python_helper_requires_matching_host_grant(self):
        helper = self.plugin / 'scripts/retain.py'
        self.write(helper, '# ABOUTME: Retains a packaging fixture.\n')
        original = self.skill.read_text()
        invocation = '\nRun `python3 -B "<plugin-root>/scripts/retain.py"`.\n'
        self.skill.write_text(original + invocation)
        status, output = self.result()
        self.assertEqual(status, 1, output)
        self.assertIn('script grants differ', output)
        self.skill.write_text(original.replace('effort: high', '''effort: high
allowed-tools:
  - Bash(python3 -B ${CLAUDE_PLUGIN_ROOT}/scripts/retain.py *)''') + invocation)
        status, output = self.result()
        self.assertEqual(status, 0, output)

    def test_integrity_inspect_grant_is_accepted(self):
        self.write(self.plugin / 'scripts/text_integrity.py', '# ABOUTME: Inspects a synthetic fixture.\n')
        original = self.skill.read_text()
        invocation = '\nRun `python3 -B "<plugin-root>/scripts/text_integrity.py" inspect INPUT`.\n'
        grant = 'Bash(python3 -B ${CLAUDE_PLUGIN_ROOT}/scripts/text_integrity.py inspect *)'
        for metadata in (f'allowed-tools:\n  - Read\n  - {grant}', f'allowed-tools: Read, {grant}'):
            with self.subTest(metadata=metadata):
                self.skill.write_text(original.replace('effort: high', 'effort: high\n' + metadata) + invocation)
                status, output = self.result()
                self.assertEqual(status, 0, output)

    def test_integrity_broad_mutating_and_missing_grants_are_rejected(self):
        self.write(self.plugin / 'scripts/text_integrity.py', '# ABOUTME: Inspects a synthetic fixture.\n')
        original = self.skill.read_text()
        invocation = '\nRun `python3 -B "<plugin-root>/scripts/text_integrity.py" inspect INPUT`.\n'
        prefix = 'Bash(python3 -B ${CLAUDE_PLUGIN_ROOT}/scripts/text_integrity.py '
        grants = [prefix + '*)', prefix + 'apply-edits *)',
                  prefix + 'inspect:*)', prefix + 'inspect *)\n  - ' + prefix + 'apply-edits *)',
                  prefix + 'inspect *)\n  - Bash(*)', prefix + 'inspect *)\n  - Bash', 'Read']
        for grant in grants:
            with self.subTest(grant=grant):
                metadata = 'allowed-tools:\n  - ' + grant
                self.skill.write_text(original.replace('effort: high', 'effort: high\n' + metadata) + invocation)
                status, output = self.result()
                self.assertEqual(status, 1, output)
                self.assertIn('text_integrity.py requires exactly its inspect-only grant', output)

    def test_agent_cannot_select_a_model_or_force_inheritance(self):
        original = self.agent.read_text()
        for value in ('sonnet', 'inherit', 'provider/model-name', 'null'):
            with self.subTest(value=value):
                self.agent.write_text(original.replace('tools: Read', f'model: {value}\ntools: Read'))
                self.assert_rejected(self.agent)

    def test_skill_cannot_select_a_model(self):
        self.skill.write_text(self.skill.read_text().replace('effort: high', 'model: sonnet\neffort: high'))
        self.assert_rejected(self.skill)

    def test_inline_dispatch_cannot_select_a_model(self):
        self.skill.write_text(self.skill.read_text() + '\nFor a quick search, use `model: haiku`.\n')
        self.assert_rejected(self.skill)

    def test_json_dispatch_cannot_select_a_model(self):
        self.skill.write_text(self.skill.read_text() + '\nspawn_agent({"model": "provider/model-name"})\n')
        self.assert_rejected(self.skill)

    def test_reference_cannot_override_model_on_continuation(self):
        reference = self.skill.parent / 'references/retry.md'
        self.write(reference, 'Agent(resume="worker-id", model="provider/model-name")\n')
        self.assert_rejected(reference)

    def test_model_discussion_and_other_settings_are_not_selectors(self):
        self.skill.write_text(self.skill.read_text() + '''
Leave the model to the host, unless the user explicitly requests one.
Reasoning effort is separate: `model_reasoning_effort = "high"`.
A source variable such as `view_model = "example"` is not a model override.
''')
        status, output = self.result()
        self.assertEqual(status, 0, output)


if __name__ == '__main__':
    unittest.main(verbosity=2)
