# mise-stage
Camera, shot and render management in Maya

## Layout

```text
python/mise_stage/                       the one top-level package; put python/ on sys.path
python/mise_stage/config/                settings module
python/mise_stage/backends/              data and logic with no Maya or Qt imports
python/mise_stage/backends/previs_files/ previs file tree API (sequences, actions, versions)
config/                                  defaults.yaml plus one <SHOW>.yaml per show
tests/                                   unittest suite
```

The code is split into layers, and imports only point downward:

- `backends/` is pure Python and never imports Maya or Qt, so it tests outside Maya.
- `dcc/` (not created yet) will hold thin adapters that touch Maya, such as camera queries and scene open and save. It may import `maya` and `backends`, never Qt, and it translates between Maya nodes and backend records.
- `ui/` (not created yet) will hold the Qt code, with a model, view and controller per element. It may use both `backends` and `dcc`.

## Technical docs

API and technical reference lives in [docs/technical/](docs/technical/README.md), including [configuration](docs/technical/config.md) and the [previs files API](docs/technical/previs-files.md).

## Requirements

Python with [PyYAML](https://pypi.org/project/PyYAML/). Maya's Python must be able to `import yaml`; check this in the script editor before relying on the config module there. Run the tests with `pip install pyyaml` then `python -m unittest discover -s tests`.
