# Copilot review instructions

mise-stage manages cameras, shots and renders for previs in Maya. Read `GLOSSARY.md` first: Sequence, Action, Version and Scene file are domain terms with fixed meanings.

## Layers

- Code lives under `python/mise_stage/`. `backends/` is pure Python with no Maya or Qt imports; flag any `maya`, `PySide` or `PyQt` import there. UI code (a model, view and controller per element) goes in `ui/`.
- Backends use only the standard library and must run in Maya's Python 3.11. Flag syntax or APIs newer than 3.11.
- Settings come from `mise_stage.config`. Backends take paths and show codes as arguments instead of reading config themselves.

## Platform

- Developers use Windows. Shared project files sit on local disk or SMB shares, so flag needless directory scans (each one is a network round trip) and code that assumes POSIX-only behavior. Windows briefly refuses to open or replace a file another process is writing.
- Creating a folder is the lock when allocating numbers. Do not suggest check-then-create patterns for that.

## Conventions

- Scene files are named `<showcode>_<sequence>_a<action>_v<version>.<ext>`, with 4-, 3- and 3-digit zero-padded numbers that never widen.
- Tree problems raise the package's own errors (subclasses of `PrevisFilesError`).
- Tests use `unittest` (`python -m unittest discover -s tests`) and must run outside Maya.
- README examples must run as written, so check any code sample against the API.

## Review focus

- Prefer correctness, concurrency and shared-drive problems over style.
- Skip purely stylistic suggestions; no linter is configured yet.
