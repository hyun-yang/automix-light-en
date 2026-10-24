#!/usr/bin/env python3
"""Shared Copilot safety-net decisions. Never execute input commands."""
import fnmatch
import json
import os
from pathlib import Path
import re
import sys


def project_path(value):
    if os.name == 'nt' and isinstance(value, str):
        if re.match(r'^/[a-zA-Z]/', value):
            value = value[1] + ':' + value[2:]
        elif value.startswith('/tmp/'):
            value = str(Path(os.environ.get('AML_GUARD_TEMP_ROOT', os.environ.get('TEMP', '.'))) / value[5:])
    return Path(value)


def reason(data):
    root = project_path(data.get('cwd') or os.getcwd())
    if not root.is_dir():
        root = Path.cwd()
    if not all((root / name).is_file() for name in ('spec.md', 'task.md')):
        return None
    config = root / '.aml/config.yaml'
    if config.is_file() and re.search(r'^\s*guard:\s*"?off"?\s*$', config.read_text(encoding='utf-8'), re.M):
        return None
    name = data.get('toolName') or data.get('tool_name') or ''
    args = data.get('toolArgs', data.get('tool_input'))
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = {'command': args}
    if not isinstance(args, dict):
        args = {}
    if name not in ('bash', 'Bash', 'powershell'):
        if not (root / '.aml/FIXING').is_file():
            return None
        paths = [args[k] for k in ('path', 'file_path', 'filePath') if isinstance(args.get(k), str)]
        for value in args.values():
            if isinstance(value, str):
                paths.extend(re.findall(r'^\*\*\* (?:Update|Add|Delete) File: (.+)$', value, re.M))
        patterns = ('*/tests/*', '*/test/*', '*/__tests__/*', 'tests/*', 'test/*', '__tests__/*', '*test_*.py', '*_test.py', '*_test.go', '*_test.rb', '*_spec.rb', '*_test.dart', '*.test.js', '*.test.jsx', '*.test.ts', '*.test.tsx', '*.spec.js', '*.spec.jsx', '*.spec.ts', '*.spec.tsx', '*.spec.dart', '*Test.java', '*Tests.cs')
        if any(fnmatch.fnmatchcase(p.strip().replace('\\', '/'), pattern) for p in paths for pattern in patterns):
            return "a bug is being fixed right now (.aml/FIXING).\n   Changing a test file doesn't make the bug go away; it makes the check that catches the bug go away.\n   → Leave the test as it is and fix the code until it passes.\n   → Only if the test itself is written wrong: remove the marker with rm .aml/FIXING and try again."
        return None
    cmd = args.get('command') or ''
    if not isinstance(cmd, str):
        return None
    if re.search(r'(>|>>)\s*[^\s]*\.env', cmd) or re.search(r'git\s+add\s[^;&|]*\.env', cmd):
        return 'a secret key could get into the repository.\n   Files like .env hold passwords and API keys. Once they get into the repository,\n   they stay in the history even if you delete them later.\n   → Don\'t put .env in the repository; list it in .gitignore.\n   → If a value needs changing, tell Copilot "put this value in .env" and check it with your own eyes.'
    if re.search(r'git\s+push[^;&|]*--force(\s|$)', cmd) and not re.search(r'git\s+push[^;&|]*--force-with-lease', cmd):
        return "a force push overwrites history that's already been pushed.\n   → If you really need it, use --force-with-lease. It stops on its own if it would overwrite someone else's work."
    if re.search(r'git\s+reset[^;&|]*--hard', cmd):
        return 'a hard reset deletes unsaved work for good.\n   → To set it aside for a while: git stash  (bring it back later with git stash pop)\n   → To go back to a specific commit: git revert <commit>  (undoes without erasing history)\n   → If it really has to be thrown away, the user should run it directly in the terminal.'
    if re.search(r'(^|[\s;&|(])rm\s+(-[^\s]*[rR][^\s]*\s+)+(/|~|\.|\*|\./\*|/\*|\$HOME)(\s|$)', cmd):
        return "this command wipes a whole folder, and it can't be undone.\n   → Name exactly what to delete (e.g. rm -rf build).\n   → If it really has to be deleted like this, the user should run it directly in the terminal."
    return None


def main():
    try:
        sys.stdin.reconfigure(encoding='utf-8-sig')
        sys.stdout.reconfigure(encoding='utf-8', newline='\n')
        sys.stderr.reconfigure(encoding='utf-8', newline='\n')
        message = reason(json.load(sys.stdin))
        if message:
            message = '❌ Blocked by the aml safety net — ' + message
            print(json.dumps({'permissionDecision': 'deny', 'permissionDecisionReason': message}, ensure_ascii=False))
            print(message, file=sys.stderr)
            return 2
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
