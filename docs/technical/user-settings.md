# User settings

User settings are values that belong to one artist on one machine and profile, such as whether to confirm before deleting a camera. They survive a restart, and they are separate from [show config settings](config.md): a setting is one or the other, never both, so neither overrides the other. The `user_settings` package needs no Maya or Qt, only the standard library and PyYAML, and takes its folder as an argument instead of reading config itself.

Every user setting has a default and belongs to one group, such as Cameras or Camera Monitor. The group is only used to reset settings together. A setting is addressed by its key alone, and keys are unique across all groups.

## Settings that ship

| Key | Group | Kind | Default | Meaning |
|---|---|---|---|---|
| `CONFIRM_CAMERA_DELETE` | Cameras | on/off | on | Ask before deleting a camera |
| `AUTO_OPEN_CAMERA_MONITOR` | Camera Monitor | on/off | off | Open the camera monitor when a camera is activated and the monitor is closed |

Nothing reads them yet; the camera manager will.

## Using them from Python

```python
from mise_stage.backends.user_settings import CONFIRM_CAMERA_DELETE, UserSettings

settings = UserSettings()                    # the artist's own settings file

settings.get(CONFIRM_CAMERA_DELETE)          # True until the artist changes it
settings.set(CONFIRM_CAMERA_DELETE, False)   # saved to the file straight away
settings.reset_group("Cameras")              # back to the defaults for one group
settings.reset_all()                         # or for every user setting
```

A read always goes to the file, so it sees a change another Maya session just saved. Import the key constants (`CONFIRM_CAMERA_DELETE`) instead of retyping the strings.

A value can be on/off, a whole number, a number, text, or one choice from a list. The default decides which: a whole-number setting rejects `True`, and a number setting accepts a whole number. To add a setting, declare it in `python/mise_stage/backends/user_settings/definitions.py`:

```python
from mise_stage.backends.user_settings import SettingDefinition

SettingDefinition("RENDER_QUALITY", "Rendering", "medium", ("low", "medium", "high"))
```

## The settings file

The file is `user_settings.yaml` in a `mise-stage` folder inside the operating system's per-user app-data folder, not Maya's preferences folder, so a Maya upgrade does not lose it.

| System | Folder |
|---|---|
| Windows | `%APPDATA%\mise-stage` |
| macOS | `~/Library/Application Support/mise-stage` |
| Other | `$XDG_CONFIG_HOME/mise-stage`, or `~/.config/mise-stage` |

It is flat `KEY: value` pairs, in the same format as the show config files:

```yaml
CONFIRM_CAMERA_DELETE: false
```

The file does not exist until an artist first changes a setting away from its default, and once it exists it is never removed. A reset takes the reset keys out of the file, so those settings follow any later change to their defaults.

You can edit the file by hand. Know that:

- A setting you leave out uses its default.
- A value the setting cannot hold (text for an on/off setting, or a choice not in the list) is ignored and the default is used. The log gets one warning per key per Maya session.
- A key that is not a user setting is ignored, warned about once, and kept in the file.
- Comments and formatting are not kept. The next time a setting is saved, the file is rewritten without them.
- If the file is not valid YAML, settings read as their defaults. The next time a setting is saved, the broken file is renamed to `user_settings.yaml.invalid` (replacing an older one) and a new file is written, so your edits are not lost.

## Several Maya sessions

Every save and reset takes a lock file, `user_settings.yaml.lock`, beside the settings file. It re-reads the file under the lock and changes only its own keys, so two sessions that set different settings at once both keep their change. A session that cannot get the lock within about five seconds raises `SettingsWriteError`. A lock file older than about 30 seconds is taken to be left by a crashed session and is cleared.

Every save writes a whole new file and swaps it in, so a read never sees half a file.

## Errors

All errors derive from `UserSettingsError`.

| Error | When |
|---|---|
| `UnknownSettingError` | A setting that is not declared is read or set |
| `UnknownGroupError` | A group that is not declared is reset |
| `InvalidValueError` | A value the setting cannot hold is set. Nothing is written |
| `SettingsWriteError` | The folder cannot be created, the file cannot be written, or the lock cannot be taken. It names the file |

When a save fails, the new value is held for the rest of that Maya session and is what reads return, until that setting is next set or reset successfully.
