# Growing the project and working as a team

As the app grows or more people work on it, you may need more tools. This document covers when to bring in parallel work, automatic checks, team rules, and so on, and how to start. Pick and apply what the current work needs first.

## 1. Working on several tasks at once

**When:** you have two or three tasks that change different files and can each go ahead on their own.

With `git worktree` you can make separate working folders of the same repository, so each terminal window works on a different branch.

```bash
git worktree add ../myapp-task2 -b task2
# open the new folder in a new terminal and run claude
```

Start with two or three, and adjust to what you can still review properly. Look at `task.md` and split off **tasks whose files don't overlap**. If they need to change the same file, do them in order.

## 2. Automatic checks (CI)

**When:** you start forgetting manual tests, or you're developing with other people.

CI runs tests and the like automatically when you push code or open a PR. For a GitHub repository, you can start by adding a setup like this to `.github/workflows/check.yml`. Below is an example for a project that uses npm.

```yaml
name: check
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test      # change to your project's install and test commands
```

For commands that fit the project, see "How to check" in `CLAUDE.md`. If needed, you can also run Claude non-interactively with `claude -p "..."` to summarize why a check failed.

It's also good to run the checks when you change `CLAUDE.md`, rule cards, or the blocking hook, because these settings affect how Claude works. `/aml:doctor` checks whether a check was run after settings changed.

See: [GitHub Actions for Claude Code](https://code.claude.com/docs/en/github-actions)

## 3. Regular code checks

**When:** about a month after development, or before releasing the app to other people.

Check all the code, including existing code, with `/aml:review all`. Add small fixes to `task.md`, and write up big changes in `intent.md` to carry on with planning and building.

To bring scheduled security scans into a company repository, check the terms and admin settings of tools such as Claude Security.

## 4. Sharing the team's review standards

**When:** other people start joining the project.

- Use `REVIEW.md` as the team's shared review standard. It cuts down on each reviewer checking different things.
- If needed, connect Claude reviews to PRs. You can look at managed Code Review or `claude-code-action`. Alongside the automatic review, people check the purpose of the change, design decisions, and risks.
- When the same finding comes up twice, write a development rule with `/aml:rule`. Team members can refer to the same standard and make fewer similar mistakes.

## 5. Applying organization-wide settings

**When:** a company repository needs shared rules that individuals can't turn off.

Settings deployed by an admin (managed settings) let you apply organization-level permissions and tool-use policies. Here is an example.

```json
{
  "permissions": {
    "deny": ["Read(.env*)", "Read(./secrets/**)", "Bash(curl *)"],
    "allow": ["Bash(git *)", "Bash(npm test)"]
  },
  "allowManagedHooksOnly": true,
  "allowManagedMcpServersOnly": true
}
```

- `deny` — blocks reading the listed files and running the listed commands. The example covers reading `.env*` and `./secrets/**`, and the `curl` command.
- `allow` — lets the listed commands run without approving them each time.
- `allowManagedHooksOnly` / `allowManagedMcpServersOnly` — limits hooks and MCP servers to the ones the admin allowed.

See: [settings](https://code.claude.com/docs/en/settings), [permissions](https://code.claude.com/docs/en/permissions), [sandboxing](https://code.claude.com/docs/en/sandboxing)

## 6. Considering Slack

**When:** bug reports and development requests mostly come in through Slack.

You can look at calling Claude from Slack to look into a reported problem and carry it on into a fix or a PR. Before bringing it in, check which integrations are available and the repository access permissions.

## 7. Seeing usage numbers on a dashboard

**When:** you want to compare model usage and cost across many tasks.

aml records numbers per task and shows the running totals in `/aml:status`. If you need a web dashboard, set up the [Langfuse integration](../README.md#langfuse-integration-optional).

To add up usage and cost for a whole organization, you can also look at sending data through OpenTelemetry. For setup, see the [usage monitoring docs](https://code.claude.com/docs/en/monitoring-usage).

## 8. Moving to automix (am)

**When:** you keep developing several features and need more task-management features.

`am` (automix) provides a separate check step, several agents working together, sharing development patterns across projects, budget caps, and an undo command. The basic flow — plan → task plan → build and check — is the same, so you can carry on with what you learned in aml.
