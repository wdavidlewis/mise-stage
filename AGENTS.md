# AGENTS.md

Instructions for AI coding agents working in this repository.

## Work against a GitHub issue

Work in this repo is tracked against GitHub issues (`wdavidlewis/mise-stage`).

- If you start work and no issue has been given, offer to create one with
  `gh issue create` before starting. Show the proposed title and body first.
- The maintainer may decline an issue for small changes. That's fine; proceed
  without one, but still on a branch (see below).
- When there is an issue, reference it in the branch name, commit messages, and
  the PR description (for example, `Closes #12`).

## Branches and merging

- Never commit to `main`. All work happens on a branch.
- Name the branch after its issue: `<issue-number>-<short-slug>`, for example
  `12-add-login-form`.
- If issue creation was declined, the work still happens on a branch. Pick a
  reasonable short descriptive name, for example `fix-readme-typo`.
- Push the branch to GitHub and open a pull request. Changes reach `main` only
  by merging that PR on GitHub.

## After a merge

- Switch to `main` and pull: `git switch main && git pull --prune`.
- Delete the local branch. PRs are squash-merged, so `git branch -d` refuses;
  first confirm the PR shows as merged (`gh pr view <n> --json state`), then
  use `git branch -D <branch>`.
- GitHub deletes the remote branch automatically on merge (the repo has
  "Automatically delete head branches" on). If it is still there, delete it
  with `git push origin --delete <branch>`.
