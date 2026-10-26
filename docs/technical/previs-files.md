# Previs files

The `previs_files` package manages the folder tree of scenes. It needs no Maya or Qt, only the standard library, and takes the root and show code as arguments instead of reading config itself.

```text
<root>/sequences/0100/a007/v003/abc_0100_a007_v003.ma
                   │    │    └─ version folder, 3 digits, from 1
                   │    └────── action folder, 3 digits, from 0
                   └─────────── sequence folder, 4 digits, from 0
```

Sequences are normally numbered in hundreds, and gaps in sequence and action numbers are normal. Numbers never widen: going past 9999 sequences, or 999 actions or versions, is an error. A scene file is named `<showcode>_<sequence>_a<action>_v<version>.<ext>`.

```python
from mise_stage import config
from mise_stage.backends.previs_files import PrevisFileStore

store = PrevisFileStore(config.PREVIS_FILE_ROOT, "abc")  # root must exist

store.create_sequence(100)               # explicit number; create_sequence() picks and returns the next free one
store.create_action(100, 7)              # explicit number; create_action(100) picks and returns the next free one
path = store.allocate_version(100, 7, "ma")  # makes v001, returns the path to save to

store.list_sequences()
store.list_actions(100)
store.list_versions(100, 7)              # each version lists its scene files
store.latest_version(100, 7)

store.set_version_comment(100, 7, 1, "Camera moved")
store.get_version_comment(100, 7, 1)     # set/get_action_comment for actions
```

Comments are Unicode, stored in a `meta.json` file in the action or version folder. A version with no scene file yet is still listed, with an empty `scene_files`. All errors derive from `PrevisFilesError`.

Allocating the next version relies on creating a folder being atomic, which holds on local disks and SMB shares but not on synced storage such as Dropbox.
