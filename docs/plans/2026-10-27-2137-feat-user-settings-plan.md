---
title: User Settings - Plan
type: feat
date: 2026-10-27
topic: user-settings
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-brainstorm
execution: code
---

# User Settings - Plan

## Goal Capsule

- **Objective:** Artists have a place for preferences that belong to them on one machine and profile, rather than to a show or a scene, so features such as the camera manager can remember what each artist chose.
- **Product authority:** The Product Contract wins on behavior. This plan covers user settings only. Scene settings (#21), the camera manager, a settings dialog and moving the camera monitor's display state are not active scope.
- **Open blockers:** None.

---

## Product Contract

### Summary

A user settings system for mise-stage. Each artist's values live in a file in their own profile folder, and each setting has a default. Settings belong to groups, and values can be on/off, a number, free text or one choice from a list. Artists can reset one group or all settings to defaults. The system ships with the camera manager's first two settings declared and no consumer.

### Problem Frame

mise-stage has one kind of setting today: per-show values read from `config/defaults.yaml` and `config/<SHOW>.yaml` (`docs/technical/config.md`). They are shared by a production and read-only at run time. Nothing stores a value that is one artist's own and must survive a restart.

The only local store is a Maya preference that the camera monitor uses privately for its display state. The camera manager is about to need preferences of its own, such as whether to confirm a camera delete. Each feature would otherwise invent its own storage.

Settings now fall into three kinds, each with its own home and no overlap: show config settings, user settings (this plan) and scene settings (#21). A setting lives in exactly one kind, so no precedence rules are needed.

### Key Decisions

- **User settings are stored in a file in the artist's profile folder.** Governs R1. (session-settled: user-directed — chosen over Maya preferences and over a per-user file on the shared drive: a plain file can be inspected and edited, does not depend on Maya, and avoids shared-drive write concerns.)
- **User settings are a separate namespace from show config settings and scene settings.** Governs R3. (session-settled: user-directed — chosen over letting a user setting override a show setting, and over letting a show lock a user setting: a setting in one place needs no precedence rules.)
- **Features change settings through Python only.** Governs R7. (session-settled: user-directed — chosen over a settings dialog on the shell and over hand-editing only.)
- **The camera monitor's display state stays in its Maya preference.** Governs R6. (session-settled: user-directed — it will most likely become a scene setting, so #21 decides its permanent home.)
- **The system ships with the camera manager's two settings and no consumer.** Governs R6. (session-settled: user-directed — chosen over shipping the system with no settings and over wiring a demo consumer.)
- **A bad file, bad value or unknown key falls back to defaults with a warning.** Governs R13. (session-settled: user-approved — chosen over raising an error as show settings do and over backing up and resetting the file: a typo in a personal file must not stop Maya tooling from starting.)
- **The code is pure Python in `backends/user_settings/`, with tests in `tests/test_user_settings*.py`.** Governs R14. (session-settled: user-approved — chosen over extending the read-only `config` module and over adding a `dcc/` adapter.)
- **A file, once created, is never removed, and nothing checks whether settings are at their defaults.** Governs R9, R10. (session-settled: user-directed.)
- **A lock file around each read-modify-write keeps two sessions from losing each other's changes.** Governs R24. (session-settled: user-directed — chosen over optimistic re-read and retry, which leaves a small window for lost updates, and over last-writer-wins, which would drop AE6.)
- **Settings use uppercase keys like show config, and each group holds the settings for what they act on.** Governs R6. (session-settled: user-directed — chosen over lowercase dotted keys. Confirm-on-delete is in Cameras and auto-open is in Camera Monitor, not together.)
- **A failed write raises instead of failing quietly, and a read goes to the file except for a value whose save failed.** Governs R15, R16. (session-settled: user-approved — chosen over a warning on write and over a session-long cache: a silent failure would let the artist think a preference was saved, and a cache would hide another session's changes.)
- **Confirm-on-delete defaults to on and auto-open defaults to off.** Governs R6. (session-settled: user-approved — a delete is hard to undo, and a panel should not open unasked.)
- **A reset removes the reset keys from the file instead of writing default values into it.** Governs R11, R12. Settings then follow later changes to the defaults. (session-settled: user-approved.)

### Requirements

**Storage and defaults**

- R1. Each artist's user settings are stored in a plain-text file in their own profile folder, local to that machine and profile. The folder is the operating system's per-user app-data folder, not Maya's preferences folder, so a Maya upgrade does not lose the settings.
- R21. The file is in the same plain-text format as the show config files, and artists may edit it by hand. The docs say how.
- R2. Every user setting has a default, used when the file or the key is missing.
- R3. A setting is a user setting, a show config setting or a scene setting, never more than one, and a user setting is not affected by show config or scene settings.
- R4. Each user setting belongs to exactly one group, such as Camera Monitor, Cameras or Rendering.
- R5. A user setting's value can be on/off, a number, free text, or one choice from a fixed list, and the setting's default decides which. A choice setting rejects any value outside its list.
- R6. The camera manager's two settings are declared, and nothing reads them yet. Each is addressed by its key alone, and a key is unique across all user settings.

  | Key | Group | Kind | Default | Meaning |
  |---|---|---|---|---|
  | `CONFIRM_CAMERA_DELETE` | Cameras | on/off | on | Ask before deleting a camera |
  | `AUTO_OPEN_CAMERA_MONITOR` | Camera Monitor | on/off | off | Open the camera monitor when a camera is activated and the monitor is closed |

**Reading and writing**

- R7. Features read and write user settings through Python. There is no settings dialog.
- R8. Setting a value writes to the file immediately and changes only that key.
- R24. Every set and every reset takes a short-lived lock beside the settings file, re-reads the file under the lock, changes only its own keys, writes, and releases the lock, so no session's change is lost. A session that cannot get the lock within a short wait raises an error per R15. The lock works on Windows and on POSIX.
- R9. The file is created the first time a setting is changed away from its default. While no file exists, setting a value equal to its default does not create one.
- R10. Once the file exists it is never removed, even when every setting is back at its default. A value set equal to its default is written like any other.

- R19. Setting a value the setting cannot hold (the wrong kind, or a choice outside its list) raises an error and writes nothing.
- R20. Reading or setting a setting that is not declared raises an error.
- R15. A set that cannot be written (the folder cannot be created, or the file is read-only or locked) raises an error naming the file. The new value is held for the rest of the session and is the value reads return (R16).
- R16. A read returns the value in the file as it is now, including a change another Maya session just made. The one exception is a value whose save failed (R15): it is returned instead of the file's value until that setting is next set or reset successfully.

**Reset**

- R11. An artist can reset one group to its defaults, which affects no other group.
- R12. An artist can reset all user settings to their defaults.
- R17. A reset when no file exists, or when the file holds none of the reset keys, does nothing and creates no file.

**Bad data**

- R13. An unreadable file, a wrong-typed value, an out-of-list choice or an unknown key logs a warning and falls back to the default. The file is not rewritten until the artist next sets a setting. A warning appears once per key per Maya session.
- R23. Setting a value leaves unknown keys in the file untouched. Comments and formatting are not preserved, and the docs say so (R21).

**Placement**

- R14. The code lives in `python/mise_stage/backends/user_settings/` with no Maya or Qt import, and its tests in `tests/test_user_settings*.py`. There is no `dcc/` or `ui/` part.
- R18. `GLOSSARY.md` is updated in the same PR: "Setting" becomes "Show config setting", and "User setting" and "Group" are added.
- R22. The PR adds `docs/technical/user-settings.md`, lists it in `docs/technical/README.md` and links it from `docs/technical/config.md`.

### Acceptance Examples

- AE1. **Covers R9.** Given no settings file, when a feature sets a value equal to its default, no file is created. When it then sets a value different from the default, the file is created holding that value.
- AE2. **Covers R8, R10.** Given a file with one changed setting, when the feature sets that setting back to its default, the file remains and holds the default value, and other keys are unchanged.
- AE3. **Covers R11.** Given changed settings in the Cameras and Rendering groups, when the Cameras group is reset, the Cameras settings read their defaults and the Rendering settings keep their values.
- AE4. **Covers R12.** Given changed settings in several groups, when all are reset, every setting reads its default and the file still exists.
- AE5. **Covers R13.** Given a file that holds a text value for an on/off setting, when the setting is read, it returns the default and a warning is logged. The file is unchanged until a setting is next set.
- AE6. **Covers R8, R24.** Given two Maya sessions open, when each sets a different setting at the same moment, both values are in the file. The same holds when one session resets a group while the other sets a setting outside it.
- AE10. **Covers R24.** Given another session holds the lock past the wait, when a feature sets a setting, an error names the file and no change is written.
- AE7. **Covers R16.** Given two Maya sessions open, when one sets a setting, the other reads the new value without restarting.
- AE8. **Covers R15, R16.** Given a read-only settings folder, when a feature sets a setting, an error names the file, and a read in the same session returns the new value. When the folder later becomes writable and the setting is set again, the value is written and reads follow the file again.
- AE9. **Covers R17.** Given no settings file, when a group is reset, no file exists afterwards.

### Scope Boundaries

**Deferred for later**

- A settings dialog and any button or menu item for the reset operations.
- A way for a feature to be told when a setting changes. Features read when they need the value.
- Moving the camera monitor's display state off its Maya preference. #21 decides its home.
- Reading the camera manager settings in a feature. The camera manager itself is separate work.
- Settings that follow an artist between workstations.

**Outside this work**

- Scene settings, which are #21.
- Letting a show override or lock a user setting.
- The glossary term "Scene setting". It waits for #21.

### Dependencies / Assumptions

- Unit tests in CI are the whole verification. No Maya hand-check is needed because the code imports no Maya or Qt (R14).
- #21 is planned separately and shares the three-kind split described in the Problem Frame.
- The camera manager is not built yet, so the two settings have no reader until it is.

### Outstanding Questions

**Deferred to Planning**

- The exact folder and file names under each platform's per-user app-data folder.
- How a setting, its group, its default and its list of choices are declared.
- The lock's wait time, and how a lock left behind by a crashed session is recognised and cleared.
- Whether the atomic-write practice in `docs/solutions/best-practices/atomic-file-writes-preserve-shared-permissions.md` applies to a profile folder.
- The Python names of the read, set and reset functions. The settings are addressed by the keys in R6.
- How group names are validated.

### Sources / Research

- `docs/technical/config.md` and `python/mise_stage/config/__init__.py`: the show config settings this plan sits beside.
- `docs/plans/2026-10-26-1344-feat-camera-monitor-plan.md`: the monitor's interim Maya preference and its pointer to #20 and #21.
- `docs/solutions/best-practices/atomic-file-writes-preserve-shared-permissions.md`: the existing atomic-write guidance.
- GitHub issues #20 and #21.
