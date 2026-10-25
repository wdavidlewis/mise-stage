---
title: Previs File Manager Backend API - Plan
type: feat
date: 2026-10-25
topic: previs-file-manager-api
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-brainstorm
execution: code
---

# Previs File Manager Backend API - Plan

## Goal Capsule

- **Objective:** A file/scene manager can find, create, and annotate previs scenes, organized by sequence, action, and version, through one backend API that follows the project's naming and folder conventions.
- **Product authority:** The Product Contract below. This plan covers the backend API only; the PyQt MVC UI that will call it is not active scope.
- **Open blockers:** None.

---

## Product Contract

### Summary

A pure-Python backend, with no Maya or Qt dependency, manages the previs folder tree. It lists sequences, actions, and versions, creates sequences and actions, allocates the next version and returns the scene path to save to, finds the latest version, parses and builds scene names, and reads and writes a comment on an action or version. It is given the previs file root and the show code explicitly, and a new `PREVIS_FILE_ROOT` setting is added to the config defaults. Terms follow `GLOSSARY.md`: Sequence, Action, Version, Scene file.

### Problem Frame

The PyQt/Maya file manager has nothing to read from or write to yet. Scenes live in a folder tree (sequence, then action, then version) whose naming rules exist only as a convention, so every caller would otherwise reimplement them. The UI's model layer needs one place that owns the conventions and that can be tested outside Maya.

### Key Decisions

- **Backend is independent of Maya, Qt, and the config module.** The root and show code are passed in; callers read `PREVIS_FILE_ROOT` and the show code from config. Governs R1, R12. (session-settled: user-directed — chosen over reading config inside the API: user wants the root passed in so the backend is reusable and testable.)
- **Sequence numbers step by 100; action and version numbers step by 1; callers may always pass an explicit number.** Sequence numbers carry production meaning and leave room to insert sequences between existing ones; gaps are normal for sequences and actions and rare for versions. Governs R7, R8. (session-settled: user-directed — chosen over max+1 for sequences: user wants sequences in hundreds.)
- **Numbers have fixed widths and never widen.** Overflow is an error because parsing depends on the fixed width. Governs R1, R3, R7, R8. (session-settled: user-directed — chosen over widening the field: user chose overflow as an error.)
- **A version's scene files are found by matching the name stem, with any extension.** The extension can change over a project's life, and a folder with a `.mb` file must not be flagged missing because a caller asked for `.ma`. Governs R5, R9.
- **Versions are listed even when they have no scene file, and version numbers are never reused.** A failed or abandoned save leaves a visible, flagged version instead of a silent gap or a reused number. Governs R5, R6, R8.
- **A missing parent is an error, but a fresh show with no folders is normal.** A wrong sequence or action number fails loudly instead of creating a stray folder. Governs R4, R7, R13.
- **Metadata is a comment only for now,** stored so more fields can be added later without moving files. Governs R10, R11.

### Requirements

**Layout and naming**

- R1. The tree under the root is `sequences/<sequence>/<action>/<version>/`, where sequence is 4 digits, action is 3 digits, and version is 3 digits, all zero padded. Sequences and actions run from 0; versions run from 1. A Scene file is named `<showcode>_<sequence>_a<action>_v<version>.<ext>` and lives in its version folder.
- R2. Action numbers are scoped to their sequence; the same action number under different sequences is unrelated.
- R3. The API builds a scene name from its parts and parses a name back into show code, sequence, action, and version, rejecting names that don't match R1, including numbers outside the ranges above.
- R4. Folders and files that don't match the naming convention, or whose name carries a different show code, are ignored by every listing.

**Listing and lookup**

- R5. The API lists sequences, the actions under a sequence, and the versions under an action, each in ascending numeric order. A version entry lists its scene files (every file in the folder whose stem is the version's name, with any extension, in sorted order); an empty list means the scene file is missing.
- R6. The API finds the latest version of an action, whether or not it has a scene file. It does not offer a "latest with a scene file" lookup; callers filter the list from R5.

**Creation**

- R7. The API creates a sequence or an action using a caller-supplied number or, on request, the next free number. For sequences the next free number is the next multiple of 100 above the highest existing sequence (0 when there are none); for actions it is one above the highest existing action (0 when there are none). Creating one that already exists, or a number out of range, is an error. Creating an action under a sequence that doesn't exist is an error.
- R8. The API allocates the next version of an action by creating its folder and returning the scene path the caller should save to. The number is one above the highest existing version (1 when there are none), and two simultaneous allocations never receive the same number. Exceeding version 999 is an error.
- R9. The scene file extension (such as `.ma` or `.mb`) is supplied by the caller and used only to build the path returned by R8; the API does not fix one.

**Metadata**

- R10. An action and a version each have a comment that the API can read and write. A missing comment reads as empty, not as an error. A comment is never seen half written, and when two people save at once the last write wins.
- R11. A comment is stored and returned exactly as written, including Unicode text, multiple lines, and emoji.

**Settings and missing folders**

- R12. `PREVIS_FILE_ROOT` is added to `config/defaults.yaml` as a default setting, empty, that shows can override. The API appends `sequences` to the root it is given; checking that the root is set is the caller's job.
- R13. Listing the actions of a sequence, or the versions of an action, that doesn't exist is a not-found error. Listing sequences when the `sequences` folder doesn't exist returns an empty list, and creating the first sequence creates that folder.

### Acceptance Examples

- AE1. **Covers R5, R8.** Given an action with versions 1 and 2 where version 2 has no scene file, when the versions are listed, both appear and version 2 has an empty scene-file list; allocating the next version creates 3, not a second 2.
- AE2. **Covers R7.** Given sequence 100 exists, when a caller creates sequence 100 with an explicit number, the call fails and nothing changes. When a caller asks for the next free sequence number, 200 is created; if the highest sequence is 150, the result is also 200.
- AE3. **Covers R4.** Given a `notes` folder and a file `readme.txt` next to the action folders, when actions are listed, neither appears and no error is raised.
- AE4. **Covers R10, R11.** Given a version comment of "Caméra déplacée — 新しい", with a second line and an emoji, when it is written and read back, the text is identical.
- AE5. **Covers R10.** Given an action with no comment, when its comment is read, the result is an empty comment.
- AE6. **Covers R3.** Given the name `abc_0100_a007_v012`, when parsed, the result is show `abc`, sequence 100, action 7, version 12; a name with a two-digit version, or version 0, is rejected.
- AE7. **Covers R5, R4.** Given a version folder containing `abc_0100_a007_v003.ma`, `abc_0100_a007_v003.mb`, `abc_0100_a007_v003.ma.bak`, and `xyz_0100_a007_v003.ma`, when it is listed for show `abc`, the scene files are the `.ma` and `.mb` files only.
- AE8. **Covers R7, R13.** Given no sequence 300, when an action is created under sequence 300, the call fails and no folder is made. Given no `sequences` folder, listing sequences returns an empty list, and creating sequence 0 makes the folder.
- AE9. **Covers R7.** Given no sequences, the first next-free sequence is 0 and the second is 100; given no actions in a sequence, the first next-free action is 0, then 1. A request that would exceed 9999 (sequence) or 999 (action) fails.
- AE10. **Covers R8.** Given several callers allocating the next version of the same action at the same moment, each receives a different version number and none fail with a collision.

### Scope Boundaries

Deferred for later:

- Delete, rename, and move of sequences, actions, and versions.
- Metadata fields beyond the comment.
- Locking or conflict handling when two people edit the same comment.
- A "latest version with a scene file" lookup.
- Any UI, and any Maya open/save integration.

---

## Dependencies / Assumptions

- Show code and the `PREVIS_FILE_ROOT` value are read from config by the caller (the future model layer), not by this API.
- The root is on local disk or an SMB share, where creating a folder exclusively is atomic. On synced storage (Dropbox, a Perforce workspace) R8's guarantee would not hold.
- The comment is plain text with no markup.
- Tests run outside Maya in the existing `mise-py311` virtualenv.

## Outstanding Questions

### Deferred to Planning

- How metadata is stored on disk (a sidecar JSON file is the leading option) and where the API module lives under `python/`.
- How Windows path length, case-insensitive names, and a file locked mid-write are handled and tested.
