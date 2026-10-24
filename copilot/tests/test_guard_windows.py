"""Run the Windows hook in a real shell; risky commands are input strings only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PKG = Path(__file__).resolve().parents[1] / 'aml'


class WindowsGuard(unittest.TestCase):
    def test_configuration(self):
        hook = json.loads((PKG / 'hooks.json').read_text(encoding='utf-8'))['hooks']['preToolUse'][0]
        self.assertIn('aml-guard.ps1', hook.get('powershell', ''))
        self.assertIn('$env:PLUGIN_ROOT', hook['powershell'])
        self.assertNotIn('bash', hook['powershell'])

    def exercise(self, shell):
        with tempfile.TemporaryDirectory(prefix='aml 한글 ') as tmp:
            root = Path(tmp)
            pkg = root / '패키지 공백'
            shutil.copytree(PKG, pkg)
            project = root / '프로젝트'
            project.mkdir()
            for name in ('spec.md', 'task.md'):
                (project / name).touch()
            env = os.environ.copy()
            # No Bash or Store aliases in PATH: try python after python3 fails.
            bins = root / 'bin'
            bins.mkdir()
            (bins / 'python3.cmd').write_text('@exit /b 1\n')
            (bins / 'python.cmd').write_text('@"' + sys.executable + '" %*\n')
            env['PATH'] = str(bins)
            env['PLUGIN_ROOT'] = str(pkg)
            hook = json.loads((pkg / 'hooks.json').read_text(encoding='utf-8'))['hooks']['preToolUse'][0]['powershell']

            def run(data, want):
                raw = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
                p = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', hook], input=raw.encode('utf-8'), capture_output=True, env=env, cwd=root, timeout=15)
                self.assertEqual(p.returncode, want, p.stderr.decode('utf-8', errors='replace'))
                if want == 2:
                    d = json.loads(p.stdout.decode('utf-8-sig'))
                    self.assertEqual(d['permissionDecision'], 'deny')
                    self.assertIn('→', d['permissionDecisionReason'])
                else:
                    self.assertEqual(p.stdout.strip(), b'')

            def payload(command):
                return dict(cwd=str(project), toolName='powershell', toolArgs={'command': command})

            for command, want in [('Get-ChildItem', 0), ('git status', 0), ('git push --force', 2), ('git reset --hard', 2), ('echo x > .env', 2), ('git add .env', 2), ('rm -rf .', 2), ('git push --force-with-lease', 0), ('rm -rf build', 0)]:
                run(payload(command), want)
            run('', 0)
            run('broken json', 0)
            run({'cwd': str(project), 'toolName': 'skill', 'toolArgs': {'name': 'doctor'}}, 0)
            data = payload('git reset --hard')
            data['toolArgs'] = json.dumps(data['toolArgs'])
            run(data, 2)
            data['cwd'] = str(root)
            run(data, 0)
            (project / '.aml').mkdir()
            (project / '.aml/FIXING').touch()
            run(dict(cwd=str(project), toolName='edit', toolArgs={'path': str(project / 'tests/test_app.py')}), 2)
            (project / '.aml/config.yaml').write_text('guard: "off"\n')
            run(payload('git reset --hard'), 0)
            (project / '.aml/config.yaml').unlink()
            # Do not block tools when every Python candidate fails.
            for name in ('python3', 'python', 'py'):
                (bins / (name + '.cmd')).write_text('@exit /b 1\n')
            run(payload('git reset --hard'), 0)
            # Also support environments where only py -3 works.
            (bins / 'py.cmd').write_text('@"' + sys.executable + '" %2 %3 %4 %5 %6 %7 %8 %9\n')
            run(payload('git reset --hard'), 2)

    @unittest.skipUnless(os.name == 'nt', 'Windows only')
    def test_windows_powershell(self):
        self.exercise(str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'))

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell 7 is not installed')
    def test_powershell_7(self):
        self.exercise(shutil.which('pwsh'))


if __name__ == '__main__':
    unittest.main()
