#!/usr/bin/env python3
# ABOUTME: Exercises relocated plugin helpers without host variables or changes to the user's project.

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from sync_metadata import ROOT


class PackagedHelpers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agent kit packaging ')
        self.base = Path(self.temp.name)
        self.project = self.base / 'project with spaces'
        self.project.mkdir()
        self.env = dict(os.environ)
        self.env.pop('CLAUDE_PLUGIN_ROOT', None)
        self.env.pop('CLAUDE_SKILL_DIR', None)

    def tearDown(self):
        self.temp.cleanup()

    def package(self, name):
        target = self.base / 'plugin cache' / name
        shutil.copytree(ROOT / 'plugins' / name, target,
                        ignore=shutil.ignore_patterns('__pycache__', 'evals'))
        return target

    def run_script(self, script, *args, status=0, env=None):
        result = subprocess.run(['bash', str(script), *map(str, args)], cwd=self.project,
                                env=env or self.env, text=True, capture_output=True, timeout=90)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result.stdout

    def test_feature_validators_after_relocation(self):
        package = self.package('feature-spec')
        output = self.run_script(package / 'scripts/test-checks.sh')
        self.assertRegex(output, r'ALL \d+ CHECKS BEHAVE AS DOCUMENTED')

    def test_auditor_catalog_and_findings_after_relocation(self):
        package = self.package('appstore-guideline-auditor')
        output = self.run_script(package / 'scripts/check-catalogue.sh')
        self.assertIn('CATALOGUE OK', output)
        findings = self.project / 'findings legal.json'
        findings.write_text(json.dumps({'category': 'legal', 'status': 'completed',
                                       'findings': [], 'checklist': []}))
        self.assertIn('0 finding(s)', self.run_script(package / 'scripts/validate-findings.sh', findings))
        findings.write_text('{"category": "made-up-category"}')
        self.assertIn('does not match', self.run_script(package / 'scripts/validate-findings.sh', findings, status=1))

    def test_auditor_does_not_modify_project(self):
        package = self.package('appstore-guideline-auditor')
        source = self.project / 'notes.txt'
        source.write_text('Existing project content\n')
        scratch = self.base / 'audit scratch'
        self.run_script(package / 'scripts/collect-context.sh', self.project, scratch)
        context = json.loads((scratch / 'context.json').read_text())
        self.assertFalse(context['in_scope'])
        self.assertEqual(context['out_of_scope_reason'], 'no-xcode-project')
        self.assertIn('UNTOUCHED', self.run_script(package / 'scripts/check-untouched.sh', self.project, scratch))
        self.assertEqual(source.read_text(), 'Existing project content\n')
        self.assertEqual(sorted(p.name for p in self.project.iterdir()), ['notes.txt'])

    @unittest.skipUnless(shutil.which('jq'), 'jq is required for comprehensive review')
    def test_review_extraction_without_host_variables(self):
        package = self.package('ios-comprehensive-review')
        env = dict(self.env)
        # Read the existing repository history; this test never creates a commit.
        git_dir = subprocess.check_output(['git', 'rev-parse', '--absolute-git-dir'], cwd=ROOT, text=True).strip()
        env.update(GIT_DIR=git_dir, GIT_WORK_TREE=str(ROOT))
        self.run_script(package / 'scripts/extract-pr-context.sh', '--base', 'HEAD', '--branch', 'HEAD', env=env)
        context = json.loads((self.project / '.ios-review-temp/pr-context.json').read_text())
        self.assertEqual(context['changed_files'], [])
        self.assertEqual(context['signature_changes'], [])

    @unittest.skipUnless(shutil.which('jq'), 'jq is required for comprehensive review')
    def test_review_preserves_unverified_findings(self):
        package = self.package('ios-comprehensive-review')
        work = self.project / '.ios-review-temp'
        work.mkdir()
        (work / 'pr-context.json').write_text(json.dumps({
            'pr_number': 0, 'title': 'Packaging fixture', 'author': 'Fixture',
            'head_branch': 'feature', 'base_branch': 'main',
            'changed_files': [{'path': 'Source.swift', 'change_type': 'modified'}],
        }))
        (work / 'review-Source.json').write_text(json.dumps({
            'agent': 'file-analyzer', 'findings': [{
                'severity': 'warning', 'file': 'Source.swift', 'line': 1,
                'category': 'Correctness', 'issue': 'Fixture needs verification', 'evidence': 'fixture',
            }],
        }))
        output = self.run_script(package / 'scripts/findings-worklist.sh')
        finding_id = json.loads(output)['id']
        summary = self.run_script(package / 'scripts/build-report.sh')
        self.assertIn('Warning: 1', summary)
        self.assertIn('Unverified: 1', summary)
        self.assertIn('(unverified)', (work / 'ios-review-report.md').read_text())
        (work / 'verdicts-1.json').write_text(json.dumps({
            'agent': 'finding-verifier', 'status': 'completed',
            'verdicts': [{'id': finding_id, 'verdict': 'confirmed', 'reason': 'Fixture confirmed'}],
        }))
        self.assertEqual(self.run_script(package / 'scripts/findings-worklist.sh'), '')
        self.assertIn('Unverified: 0', self.run_script(package / 'scripts/build-report.sh'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
