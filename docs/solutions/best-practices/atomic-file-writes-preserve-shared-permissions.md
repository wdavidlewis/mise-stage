---
title: Atomic file writes must carry over the target's permissions
date: 2026-10-25
category: best-practices
module: backends/previs_files
problem_type: best_practice
component: tooling
severity: medium
applies_when:
  - Writing a file into the shared previs tree by temp file then os.replace
  - Adding another writer for render or other pipeline data on a shared drive
tags: [atomic-write, permissions, mkstemp, os-replace, shared-drive, windows]
---

# Atomic file writes must carry over the target's permissions

## Context

`write_comment` in `python/mise_stage/backends/previs_files/metadata.py` saves `meta.json` by writing a temp file and swapping it in with `os.replace`, so a reader never sees a half-written file. Copilot's review of PR #8 found that this swap silently changed who could use the file. Tests on Windows could not show it, so it is easy to repeat in the next atomic writer.

## Guidance

`tempfile.mkstemp` creates the file readable and writable by its owner only (`0o600`). `os.replace` keeps the temp file's inode and mode, so the target takes on those bits. On a shared POSIX tree, the first artist to save a comment locks everyone else out of that file.

Before the swap, `chmod` the temp file to the mode the finished file should have:

- If the target exists, copy its mode.
- If it is new, take the folder's mode with the execute bits masked off (`& 0o666`).
- Treat a failing `chmod` as non-fatal. Some filesystems have no permission bits, and the save should still work.

`_shared_mode(path, folder)` and the `chmod` call in `write_comment` do this. Reuse or extract that helper rather than writing a second atomic writer without it.

Two other details of the same save path:

- Use a unique temp name (`mkstemp` in the target folder, so the swap stays on one filesystem) so simultaneous writers do not collide.
- Wrap `os.replace` in `_retry_if_busy`. Windows raises `PermissionError` while another writer is mid-swap, and it clears within milliseconds.

## Why This Matters

The failure only appears on POSIX with more than one user, and a Windows-only test run passes. The code gives no hint that the temp file's default mode matters, so a new writer for render data would plausibly omit the `chmod`.

## When to Apply

- Any new code that writes a file into the shared previs or render tree through a temp file and rename.
- Reviewing such a change: check for the mode carry-over.

## Related

- PR #8 (Copilot review finding, fixed before merge)
