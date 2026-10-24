---
title: Per-Show Config System - Plan
type: feat
date: 2026-10-24
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
---

# Per-Show Config System - Plan

## Goal Capsule

- **Objective:** The settings of the show an artist is working on are available to previs tools through one config reader, with no per-show code and no wrong-show settings applied silently.
- **Means:** Layered YAML settings, defaults plus per-show overrides, read through one config module (KTD1, KTD2).
- **Authority:** The Product Contract wins on behavior; a KTD wins on implementation mechanism; a unit overrides neither.
- **Execution profile:** Code. Work happens on branch `4-show-config` and lands as a PR containing `Closes #4`.
- **Stop conditions:** Build and test the code regardless of the Maya check. If the maintainer reports that PyYAML is not importable in the target Maya, stop before merge and ask (see Open Questions), since the format choice then needs revisiting.
- **Who finishes:** `ce-work` implements, verifies, and opens the PR.

---

## Product Contract

### Summary

A config module exposes every setting as an uppercase attribute, e.g. `config.DEFAULT_RENDER_WIDTH`. Values come from `config/defaults.yaml`, overlaid by `config/<SHOW>.yaml` when the `SHOW` environment variable names a show.

### Problem Frame

mise-stage manages shots, cameras and renders for previs in Maya across several shows. Each show wants different defaults (render resolution is the first example), and the tools should not hard-code them or fork per show. A show whose settings silently fail to load would render previs at the wrong settings, so misconfiguration has to be loud.

### Requirements

**Settings access**

- R1. Code reads a setting as an attribute of the config module (`config.DEFAULT_RENDER_WIDTH`, `config.DEFAULT_RENDER_HEIGHT`), with the value's native type (int stays int).
- R2. The module ships `config/defaults.yaml` defining every setting, initially `DEFAULT_RENDER_WIDTH` and `DEFAULT_RENDER_HEIGHT`.

**Show overrides**

- R3. When `SHOW` names a show, `config/<SHOW>.yaml` overrides defaults key by key; keys it omits keep their default values.
- R4. `SHOW` unset or empty yields defaults only, with a logged note that no show is active.
- R5. `SHOW` set but `config/<SHOW>.yaml` missing is an error naming the show and the expected path.
- R6. A show file key absent from `defaults.yaml` is an error naming the key and file.
- R7. `SHOW` must be alphanumeric; any other value is an error before any file is read.

**Lifecycle and docs**

- R8. Settings load once, on first import; there is no hot reload.
- R9. `README.md` documents the layout, the defaults-plus-overrides model, and how to add a show.

### Key Decisions

- **Fail loudly on a bad show.** A wrong or mistyped `SHOW` raises instead of falling back to defaults, because defaults would render the wrong show's settings without anyone noticing. (session-settled: user-approved — chosen over silently falling back to defaults: a silent fallback hides a typo'd show code until a render comes out wrong.) Governs R5, R6, R7.

### Scope Boundaries

- Not built: a config-directory override env var, nested or namespaced settings, runtime reload, a schema or per-key type validation beyond what YAML parses. None is needed for the stated use, and each can be added later without breaking `config.<NAME>` access.
- Not built: any consumer of the settings. Shot, camera and render tools are separate work.
- Considered and not built: an explicit check that YAML files have a mapping at the top level. A malformed file already fails at import with a Python error the artist sees at once.
- Considered and not built: a sample show file in `config/`. A fake show would ship settings that look real; the README documents the shape instead.

### Open Questions

Deferred, non-blocking for the code:

- Whether PyYAML is importable in the target Maya. If it is not, either vendor PyYAML under `python/` or revisit INI. Check by running `import yaml` in Maya's script editor.

---

## Planning Contract

### Key Technical Decisions

- KTD1. **YAML read with `yaml.safe_load`.** Typed values and readable structure, at the cost of a PyYAML dependency inside Maya. (session-settled: user-directed — chosen over INI: INI is stdlib-only but returns strings and has weak list support; the user accepted the PyYAML-in-Maya risk.) `safe_load` rather than `load` so a config file can never construct arbitrary objects.
- KTD2. **Settings become module attributes at import.** The module loads once and copies each key into its own namespace, so `config.NAME` needs no accessor object and R8 holds by construction.
- KTD3. **Loading is a pure function over explicit arguments.** `_load_settings(show, config_dir)` takes the show code and directory and returns the merged dict; the import-time code calls it with `os.environ.get("SHOW")` and the repo's `config/` directory. This is what makes the override and error rules testable without touching the environment.
- KTD4. **Config directory is found relative to the module file.** `config/` sits at the repo root, three directories above the one containing `python/utils/config/__init__.py` (four `dirname` steps from `__file__`), so it resolves the same regardless of the Maya session's working directory.
- KTD5. **One exception type, `ConfigError`.** All R5, R6, R7 failures and malformed files raise it, with messages naming the show, key, or path involved.

### Assumptions

- The show code is used as the filename exactly as given; on a case-sensitive filesystem `SHOW=Abc` looks for `Abc.yaml`.
- `python/` is on `sys.path` in Maya (the way tools are installed is outside this plan), so the import is `from utils import config`.
- A show file that is empty counts as having no overrides.
- "Alphanumeric" means ASCII letters and digits only; underscores and hyphens are rejected.

### Output Structure

```text
python/
  utils/
    __init__.py            # empty, marks the package
    config/
      __init__.py          # the only code file
config/
  defaults.yaml
tests/
  test_config.py
```

### Risks & Dependencies

- **PyYAML availability in Maya** is the only external dependency and is unverified. The local `python` on the dev machine also lacks it, so tests need `pip install pyyaml` first.

---

## Implementation Units

### U1. Config module, defaults, and tests

- **Goal:** Deliver the loader, default settings, and automated proof of the override and error rules.
- **Requirements:** R1, R2, R3, R4, R5, R6, R7, R8
- **Dependencies:** none
- **Files:**
  - Create `python/utils/__init__.py`
  - Create `python/utils/config/__init__.py`
  - Create `config/defaults.yaml`
  - Create `tests/test_config.py`
- **Approach:**
  1. `defaults.yaml` holds flat uppercase keys; seed it with `DEFAULT_RENDER_WIDTH: 1920` and `DEFAULT_RENDER_HEIGHT: 1080`.
  2. Implement `_load_settings` per KTD3: validate `SHOW` first (R7), read defaults, return them when `SHOW` is unset or empty and log the note at WARNING level so it shows under Python's default logging (R4), otherwise read the show file and merge (R3), raising `ConfigError` for a missing file (R5) or unknown key (R6).
  3. At module level, call `_load_settings` once and `globals().update(...)` the result (KTD2, R8).
- **Patterns to follow:** None in the repo yet; this sets the convention. Use the stdlib `logging` module with `logging.getLogger(__name__)`.
- **Test scenarios:** use `unittest` and a temporary config directory, importing the module with `python/` added to `sys.path`.
  - `SHOW` unset with a defaults file: returns exactly the defaults (R4).
  - `SHOW=""`: same as unset (R4).
  - `SHOW` unset: the no-active-show note is logged at WARNING (R4).
  - Show file overriding only `DEFAULT_RENDER_WIDTH`: width replaced, height keeps its default, both ints (R1, R3).
  - `SHOW=abc` with no `abc.yaml`: `ConfigError` whose message contains `abc` and the expected path (R5).
  - Show file with key `NOT_A_SETTING`: `ConfigError` naming the key and file (R6).
  - `SHOW` values `../x`, `a-b`, `a b`: `ConfigError` raised before any file read, checked with a config dir that does not exist (R7).
  - Empty show file: returns defaults (assumption).
  - Test setup removes `SHOW` from `os.environ` before importing the module, and subprocess tests pass an explicit env, so a developer's own `SHOW` cannot break the import.
  - Integration, subprocess with `PYTHONPATH=python` and `SHOW` unset: `from utils import config; config.DEFAULT_RENDER_WIDTH` equals the value in the real `config/defaults.yaml` (R1, R2).
  - Integration, subprocess with `SHOW=nosuchshow`: import fails with `ConfigError` (R5, R8).
- **Verification:** `python -m unittest discover -s tests` passes with PyYAML installed.

### U2. README documentation

- **Goal:** Tell a new teammate the layout and how to add a show.
- **Requirements:** R9
- **Dependencies:** U1
- **Files:** Modify `README.md`
- **Approach:** Add a short section covering the `python/` and `config/` layout, the defaults-plus-overrides model, setting `SHOW`, adding `config/<SHOW>.yaml` with only the keys to override, the three error cases, and the PyYAML requirement for Maya's Python. Keep the existing two-line description at the top.
- **Test expectation:** none -- documentation only.
- **Verification:** The README's example keys match `config/defaults.yaml`.

---

## Verification Contract

| Check | Command or action | Applies to |
|---|---|---|
| Automated tests | `pip install pyyaml` then `python -m unittest discover -s tests` | U1 |
| PyYAML in Maya | The maintainer runs `import yaml` in Maya's script editor; if it fails, the Open Question is resolved before merging. The executing agent cannot run this | U1 |
| Smoke in Maya | With `SHOW` unset, `from utils import config; config.DEFAULT_RENDER_WIDTH` returns 1920 | U1 |

## Definition of Done

- Every requirement R1–R9 is covered by a unit and, for R1–R8, by a passing test.
- `python -m unittest discover -s tests` passes.
- The README matches the shipped keys and behavior.
- No abandoned experimental code remains in the diff.
- The PR is open from `4-show-config` and its description contains `Closes #4`. It states the Maya PyYAML check as pending the maintainer, and merge waits on that result.

## Sources

- GitHub issue `wdavidlewis/mise-stage#4`
- `AGENTS.md` for branch and PR workflow
