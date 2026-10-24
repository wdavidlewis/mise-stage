# mise-stage
Camera, shot and render management in Maya

## Layout

```text
python/utils/config/   settings module (the only code so far)
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

## Requirements

Python with [PyYAML](https://pypi.org/project/PyYAML/). Maya's Python must be able to `import yaml`; check this in the script editor before relying on the config module there. Run the tests with `pip install pyyaml` then `python -m unittest discover -s tests`.
