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

## Where new code goes

Code lives under `python/mise_stage/` in three layers. Imports only point
downward; `.github/copilot-instructions.md` has the import rules per layer.

- `backends/<feature>/`: pure Python and data, no Maya or Qt.
- `dcc/`: thin adapters that call Maya and return backend records.
- `ui/<element>/`: Qt code, with a model, view and controller per element.

When brainstorming, grilling or planning a new feature, settle its location
before the requirements are final, and ask the maintainer if it is not obvious:

- Name the layer and package path for each part of the feature. A feature that
  spans layers lists the part for each layer.
- Name where its tests go (`tests/test_<feature>*.py`).
- Record these in the requirements or plan itself (for example as a
  requirement or key decision), not only in implementation notes.

## Code style

All Python in `python/mise_stage/` and `tests/` follows these rules.

- Use Google-style docstrings on every module, public class and public function.
  Include `Args`, `Returns` and `Raises` sections when they apply.
- Put type hints on every function signature, including return types. Use
  `-> None` for functions that return nothing.
- Test methods and test modules are exempt from docstrings. A test module may
  have a one-line docstring, and test method names should say what they check.
  Type hints still apply to tests.
- Do not add type hints or docstrings to code you are not otherwise changing in
  the same PR, unless the PR is the one bringing existing code up to this
  standard.

## Commands

Run these from the project venv after `python -m pip install -r requirements-dev.txt`:

- Tests: `python -m unittest discover -s tests`
- Lint: `python -m ruff check python tests`
- Type check: `python -m mypy`

Run all three before opening or updating a PR. Lint and type settings are in `pyproject.toml`.

## After a merge

- Switch to `main` and pull: `git switch main && git pull --prune`.
- Delete the local branch. PRs are squash-merged, so `git branch -d` refuses;
  first confirm the PR shows as merged (`gh pr view <n> --json state`), then
  use `git branch -D <branch>`.
- GitHub deletes the remote branch automatically on merge (the repo has
  "Automatically delete head branches" on). If it is still there, delete it
  with `git push origin --delete <branch>`.

## Documented solutions

`docs/solutions/` holds documented solutions to past problems (Maya and Qt
gotchas, shared-drive file writes), organized by category with YAML frontmatter
(`module`, `tags`, `problem_type`). Relevant when implementing or debugging in
documented areas.

## Scratch files and durable notes

`.context/` is git-ignored local scratch (prototypes, probe scripts, logs). Nothing
in it is shared, reviewed or kept, and another clone will not have it. Write down
anything the project needs to keep in `docs/`: a technical reference in
`docs/technical/`, or a solved problem or hard-won Maya or Qt finding in
`docs/solutions/`. Put it in a PR before relying on it.
