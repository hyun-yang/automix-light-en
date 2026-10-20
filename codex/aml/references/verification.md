# Checking the done criteria — self-check and independent check

Used after $aml:go finishes all tasks, or when the user says "check it".

## What to look at

- The "Done criteria" list in `spec.md` (as is, leaving none out)
- The "How to check" commands in `AGENTS.md`

For each item, actually run it or look at the screen, and write one of three.

- **Works** — what you ran and what you saw
- **Not working** — short steps to try it again, and what you actually saw
- **Couldn't check** — why not (no tool, no environment, etc.) and how the user can check it themselves

Just reading the code is never "works". Don't change code or tests while checking — send what you find back to $aml:go's fixing step. All the checkboxes being ticked is not by itself proof that it's done.

## Self-check (default)

Done in the same session, but set aside the builder's conclusions and run everything again from the start with only the two things above. Write `Check type: self-check` in the record.

## Independent check (only when actually done)

Only when a separate helper (a subagent etc.) is available and the user or the project's guidance allows it. Hand the helper only the project location, the done criteria list, the How to check commands, and one line on what was built — don't hand over the conclusion "it's done". The helper must read the files and run things itself.

Only when it was actually done that way, write `Check type: independent check (<who/how>)`. If no helper is available, finish with a self-check and don't write "independent check done". aml can finish without an independent check.

## After fixing

If anything was fixed, run the related checks again. Leave done criteria you couldn't check unticked, and write down in plain words what is still uncertain because of that.
