# mise-stage
Camera, shot and render management in Maya

## Layout

```text
python/utils/config/         settings module
python/utils/previs_files/   previs file tree API (sequences, actions, versions)
config/                defaults.yaml plus one <SHOW>.yaml per show
tests/                 unittest suite
```

## Configuration

Settings are read as attributes of the config module:

```python
from utils import config

config.DEFAULT_RENDER_WIDTH   # 1920
config.DEFAULT_RENDER_HEIGHT  # 1080
```

`config/defaults.yaml` defines every setting. The `SHOW` environment variable (a short alphanumeric code, e.g. `SHOW=abc`) selects a show, and `config/<SHOW>.yaml` overrides defaults key by key. Settings load once, on first import.

To add a show, create `config/<SHOW>.yaml` containing only the keys to override:

```yaml
DEFAULT_RENDER_WIDTH: 2048
```

Errors are raised at import rather than falling back to defaults:

- `SHOW` contains anything other than letters and digits.
- `SHOW` is set but `config/<SHOW>.yaml` does not exist.
- A show file sets a key that is not in `defaults.yaml`.

With `SHOW` unset, only the defaults load and a warning is logged.

`PREVIS_FILE_ROOT` is the folder holding a show's previs files. It is empty by default, so a show sets its own in `config/<SHOW>.yaml`.

## Previs files

The `previs_files` package manages the folder tree of scenes. It needs no Maya or Qt, only the standard library, and takes the root and show code as arguments instead of reading config itself.

```text
<root>/sequences/0100/a007/v003/abc_0100_a007_v003.ma
                   │    │    └─ version folder, 3 digits, from 1
                   │    └────── action folder, 3 digits, from 0
                   └─────────── sequence folder, 4 digits, from 0
```

Sequences are normally numbered in hundreds, and gaps in sequence and action numbers are normal. Numbers never widen: going past 9999 sequences, or 999 actions or versions, is an error. A scene file is named `<showcode>_<sequence>_a<action>_v<version>.<ext>`.

```python
from utils import config
from utils.previs_files import PrevisFileStore

store = PrevisFileStore(config.PREVIS_FILE_ROOT, "abc")  # root must exist

store.create_sequence()                  # next multiple of 100; or create_sequence(300)
store.create_action(100)                 # next free action; or create_action(100, 7)
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

## Requirements

Python with [PyYAML](https://pypi.org/project/PyYAML/). Maya's Python must be able to `import yaml`; check this in the script editor before relying on the config module there. Run the tests with `pip install pyyaml` then `python -m unittest discover -s tests`.
