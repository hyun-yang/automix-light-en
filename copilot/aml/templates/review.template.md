<!-- This file is the checklist for what the review step (review) looks at and how. Feel free to change it. -->
# Review checklist

## Look in three passes

1. **Bugs** — things that don't work, missed cases (empty values, cancel, double click, lost internet, very long input)
2. **Safety** — no passwords or API keys written into the code, no other people's data leaking onto the screen or into logs, input from the user isn't trusted as is
3. **Promises kept** — does it follow the "Done criteria" and "Decisions" in `spec.md`, and the plan in `task.md`? Was anything built differently without saying so?

Mark which pass each finding belongs to.

## What "major" means

Only things that break behavior · leak data · go against what spec.md decided are **major**.
Names, spacing, and matters of taste are all **minor**.

## Up to 5 minor findings

List only 5 and leave the rest as a count: "N more". When minor findings fill the screen, the major ones get lost.

## What not to look at

- Generated files (build output, lock files, folders like `node_modules/`)
- Things the tests already catch
- <add anything you want to leave out for this project here>
