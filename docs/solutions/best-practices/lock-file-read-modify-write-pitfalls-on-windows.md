---
title: "Atomic replace is not a lock: lock-file read-modify-write pitfalls on Windows"
date: 2026-10-27
category: best-practices
module: backends/user_settings
problem_type: best_practice
component: tooling
severity: medium
applies_when:
  - "Several processes (for example two Maya sessions) can update one small file by reading it, changing a key and writing it back"
  - "Building an exclusive-create lock file with os.open and O_EXCL, on Windows or on Windows and POSIX"
  - "Writing or reviewing a stale-lock recovery path"
tags: [lock-file, o-excl, os-replace, lost-update, windows, permissionerror, stale-lock, concurrency]
---

# Atomic replace is not a lock: lock-file read-modify-write pitfalls on Windows

## Context

`python/mise_stage/backends/user_settings/` keeps each artist's settings in one YAML file that several Maya sessions on the same machine can change at once. Each save re-reads the file, changes its own keys and writes the whole file back. The first version wrote the new file through a temp file and `os.replace`, the pattern in [atomic-file-writes-preserve-shared-permissions.md](atomic-file-writes-preserve-shared-permissions.md), on the belief that this made concurrent saves safe. It did not. Review of PR #33 then found three more problems in the first lock-file loop: two were fixed before merge, and the third, a stale-lock race, was left unbuilt on purpose and is tracked in #34.

## Guidance

**1. Atomic replace stops half-written files, not lost updates.** Two sessions that both read the old file, each change a different key and each swap in a complete new file leave only the last writer's key. A read-modify-write that several processes share needs a lock around the whole read, change and write (`python/mise_stage/backends/user_settings/store.py:299` takes it in `_update`), plus the busy retry on the swap (`store.py:327`).

Before the lock, an 8-thread test where each thread set its own key 25 times failed in each of three runs. The final file held values like `[1, 0, 0, 0, 0, 1, 25, 22]` where `[25] * 8` was expected. In one run the same test instead raised `[WinError 5] Access is denied` from `os.replace`, even with the busy retry in place, so eight writers can keep the target busy longer than the retry waits. Write the concurrency test first and watch it fail on the unlocked code: `tests/test_user_settings_lock.py:35` is that test.

**2. An exclusive-create lock loop has three traps.** The lock is `os.open(path, O_CREAT | O_EXCL | O_WRONLY)` in a retry loop (`lock.py:45`).

- **Do not treat every `PermissionError` as "someone else has the lock".** Windows refuses for a moment while the previous holder's lock file is being deleted, and that case should be retried. A folder that denies file creation also raises `PermissionError`, and treating it the same way made every save wait the full 5 seconds, then blame another session. Retry a bounded number of times, and re-raise when no lock file exists (`lock.py:49-55`). Test it with the folder denying creation (`tests/test_user_settings_lock.py:132`).
- **Only `continue` after a stale lock was actually removed.** The first loop did `if stale: remove(); continue`. When the removal failed (a read-only attribute, a directory in the way, a long-lived hold by antivirus or an indexer), `continue` jumped over the deadline check and the sleep, and the loop spun forever, freezing Maya. `_remove()` now returns whether the file is gone, and the loop continues only then (`lock.py:56`, `lock.py:85-98`). Test it with `unlink` patched to fail (`tests/test_user_settings_lock.py:143`).
- **Breaking a stale lock by path is not atomic.** Two sessions that both judged the same old lock stale can interleave: A removes it and creates its own lock, then B removes A's new lock by the same path and creates its own, so both are in the critical section. `__exit__` has the matching flaw, since it removes whatever lock file is at the path (`lock.py:68-76`). A lock held for more than `STALE_AFTER` seconds by a stalled but live holder is broken the same way. This is deliberately not fixed; see #34.

**3. A race test that never reaches the race passes for the wrong reason.** The test for "a key another session adds just before a reset takes the lock" first passed against the old code, because the old code returned before taking the lock, so the injected add never ran. It became a real test only after adding `self.assertEqual(injected, [1], ...)` (`tests/test_user_settings_store.py:397`). When a test injects an event into a window, assert that the injection happened.

## Why This Matters

Each of these fails quietly and rarely, which is why they survive: a lost update looks like a setting that did not stick, the spinning loop needs an undeletable stale file, and the 5-second stall needs a locked-down profile folder. All of them were found only by a test that forces the case or by a reviewer reading the loop, not by using the feature.

## When to Apply

- Any file or small store that more than one process updates by read-modify-write on a local disk, including a second Maya session on the same machine.
- Any new exclusive-create lock file, and any change to stale-lock handling, including whatever #34 settles on.
- Reviewing a loop of the form "try to create, else wait" for a `continue` that skips the deadline.

## Examples

The loop shape that survived review, as pseudocode (the real code is `lock.py:40-60`):

```text
deadline = now + LOCK_WAIT
loop:
    try: create lock file exclusively; return
    except already-exists: pass
    except permission-denied:
        count += 1
        if count > limit and lock file does not exist: re-raise
    if lock is old and removing it worked: continue   # only after a successful removal
    if now >= deadline: raise "cannot get the lock"
    sleep briefly
```

## Related

- [atomic-file-writes-preserve-shared-permissions.md](atomic-file-writes-preserve-shared-permissions.md): the temp-file swap and permission carry-over this builds on.
- `docs/technical/user-settings.md`: how the user settings lock behaves.
- #34: making stale-lock recovery safe when two sessions clear it at once.
- #33: the pull request that added the user settings system. Line numbers above are as merged in #33; look up the function names (`_update`, `_write`, `FileLock.__enter__`, `FileLock._remove`) if the files have moved on.
