# Checking the done criteria — independent check and self-check

Used after /aml:go finishes all tasks, or when the user says "check it".

## What to look at

- The "Done criteria" list in `spec.md` (as is, leaving none out)
- The "How to check" commands in `AGENTS.md`

For each item, actually run it or look at the screen, and write one of three.

- **Works** — what you ran and what you saw
- **Not working** — short steps to try it again, and what you actually saw
- **Couldn't check** — why not (no tool, no environment, etc.) and how the user can check it themselves

Just reading the code is never "works". Don't change code or tests while checking — send what you find back to /aml:go's fixing step. All the checkboxes being ticked is not by itself proof that it's done.

## Independent check (default)

Call the `verifier` agent that comes with this plugin (`agents/verifier.agent.md`) as a subagent and hand it the check. Type `/env` in the Copilot conversation and `verifier` shows up in the Custom Agents section.

Hand the helper only the project location, the done criteria list, the How to check commands, and one line on what was built — don't hand over the conclusion "it's done". The helper reads the files and runs things itself.

Only when you actually called it and a verdict came back, write `Check type: independent check (verifier agent)`.

## Self-check (when the helper can't be called)

If verifier can't be called (the plugin is off, the subagent failed, etc.) or no result comes back, then in the same session set aside the builder's conclusions and run everything again from the start with only the two things above. Write `Check type: self-check (<why it couldn't be called>)` in the record, and don't write "independent check done".

## After fixing

If anything was fixed, run the related checks again. Leave done criteria you couldn't check unticked, and write down in plain words what is still uncertain because of that.
