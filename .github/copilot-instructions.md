# Copilot review instructions

mise-stage manages cameras, shots and renders for previs in Maya. Read `GLOSSARY.md` first: Sequence, Action, Version and Scene file are domain terms with fixed meanings.

## Layers

- Code lives under `python/mise_stage/` in three layers, and imports only point downward:
  - `backends/` is pure Python with no Maya or Qt imports. Flag any `maya`, `PySide` or `PyQt` import there.
  - `dcc/` holds thin adapters that touch Maya (`maya.cmds`, scene open and save). It may import `maya` and `backends`, but never Qt. Flag any `PySide` or `PyQt` import there, and any logic that belongs in a backend (naming, validation, ordering) rather than in the adapter.
  - `ui/` holds Qt code, a model, view and controller per element. It may use `backends` and `dcc`. Flag Qt code anywhere else, and Maya calls made directly from views.
  - `backends/` must not import `dcc` or `ui`, and `dcc/` must not import `ui`.
- All layers use only the standard library plus Maya and Qt where allowed, and must run in Maya's Python 3.11. Flag syntax or APIs newer than 3.11.
- Settings come from `mise_stage.config`. Backends take paths and show codes as arguments instead of reading config themselves.

## Platform

- Developers use Windows. Shared project files sit on local disk or SMB shares, so flag needless directory scans (each one is a network round trip) and code that assumes POSIX-only behavior. Windows briefly refuses to open or replace a file another process is writing.
- Creating a folder is the lock when allocating numbers. Do not suggest check-then-create patterns for that.

## Conventions

- Scene files are named `<showcode>_<sequence>_a<action>_v<version>.<ext>`, with 4-, 3- and 3-digit zero-padded numbers that never widen.
- Tree problems raise the package's own errors (subclasses of `PrevisFilesError`).
- Tests use `unittest` (`python -m unittest discover -s tests`) and must run outside Maya.
- Documentation examples (the README and `docs/technical/`) must run as written, so check any code sample against the API.
- Python uses Google-style docstrings and type hints on every function signature, per the "Code style" section of `AGENTS.md`. Test methods are exempt from docstrings.

## Review focus

- Prefer correctness, concurrency and shared-drive problems over style.
- Missing type hints or docstrings on new or changed code is not a stylistic nit: flag it, citing the "Code style" section of `AGENTS.md`.
- Skip other purely stylistic suggestions. Ruff (lint) and mypy run in CI, so leave what they report to CI.
