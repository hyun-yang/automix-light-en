# Handing work over and blocking risky actions

When deciding how much work to hand to Claude, weigh the risk of the change, whether it can be undone, and how it can be checked.

## When it's fine to let it run on its own

If all four of these conditions are met, you can cut down the check-ins along the way and review the result once it's finished.

1. **The risk is low.** In `task.md`, "Risk" for that section is marked "low".
2. **Changes can be undone.** It's a Git repository, and the state before the work is committed.
3. **The result can be checked.** A way to check it, such as tests or looking at a screen, is written under "Proof" in `task.md`.
4. **The blocking feature is on.** `/aml:doctor` showed "Safety net on".

If the conditions aren't met, split the work and check it step by step. For actions that affect the outside world or are hard to undo — payments, sending email, deploying to a server — the user confirms before they run.

To hand work over, you can tell `/aml:go` "please carry this section through to the end". You can also change the edit-approval mode with `Shift+Tab` in the Claude Code input box. Even if you chose to let it run, review the changes and the check results once it's finished.

## What aml blocks

The blocking hook works in folders that have `spec.md` and `task.md`.

| Blocked action | Why | What to do |
|---|---|---|
| Committing a `.env` file | Passwords and API keys can stay in the Git history even after the file is deleted. | Add `.env` to `.gitignore`, and keep sensitive values in a local file that Git ignores. |
| Changing test files while fixing a bug | Changing a test to make the error pass may leave the real bug unfixed. | Only if the test itself is wrong, confirm it needs changing, then lift the block with `rm .aml/FIXING`. |
| Force push, hard reset, mass file deletion | Work or history can disappear and be hard to recover. | Check what the action will affect, then the user runs it directly in the terminal. |

When an action is blocked, the reason and what to do are shown together.

To turn it off, set this in `.aml/config.yaml`:

```yaml
guard: "off"
```

To prevent leaking sensitive information or losing work, we recommend keeping the default, on.

## Rule cards vs. the blocking hook

- **Rule cards** (`.claude/skills/`) are guidance Claude refers to while working. Use them to explain judgment calls that depend on the situation or multi-step procedures.
- **The blocking hook** is a script that checks set conditions before a tool runs. Use it to block matching actions automatically.

Explain important rules as guidance, and for violations that can be detected automatically, also check them with a hook. What a hook blocks depends on the check conditions written in the script.

## Adding project-specific blocking rules

Register a hook in `.claude/settings.json`, and write the script so it returns exit code `2` when it should block an action.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command",
            "command": "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/my-guard.sh" }
        ]
      }
    ]
  }
}
```

Here is an example that blocks a command containing `deploy --prod`.

```bash
#!/usr/bin/env bash
# .claude/hooks/my-guard.sh — ask the user to run production deploys themselves
CMD=$(cat | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)
if echo "$CMD" | grep -q "deploy --prod"; then
  echo "Please check what will be deployed to production, then run it yourself." >&2
  exit 2      # Block the action. This message is passed to Claude.
fi
exit 0
```

In this example, **exit code `0` means pass and `2` means block**. Put the reason and the next step in the block message. The example lets the action through if reading the input fails. Whether to let things through or block them when an error happens should be decided by what the project needs.

For detailed settings, see the official [hooks guide](https://code.claude.com/docs/en/hooks-guide) and [settings](https://code.claude.com/docs/en/settings).
