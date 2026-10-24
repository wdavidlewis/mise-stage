# AGENTS.md

Instructions for AI coding agents working in this repository.

## Work against a GitHub issue

Work in this repo is tracked against GitHub issues (`wdavidlewis/mise-stage`).

- If you start work and no issue has been given, offer to create one with
  `gh issue create` before starting. Show the proposed title and body first.
- The maintainer may decline an issue for small changes. That's fine; proceed
  without one.
- When there is an issue, reference it in the branch name, commit messages, and
  the PR description (for example, `Closes #12`).

## Branches and merging

- Never commit to `main`. All work happens on a branch.
- Name the branch after its issue: `<issue-number>-<short-slug>`, for example
  `12-add-login-form`. For work with no issue, use a short descriptive slug.
- Push the branch to GitHub and open a pull request. Changes reach `main` only
  by merging that PR on GitHub.
