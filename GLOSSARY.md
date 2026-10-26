# mise-stage Glossary

mise-stage manages cameras, shots and renders for previs in Maya, across several shows. This glossary defines the project's domain language.

## Shows and settings

**Show**:
A production with its own settings, identified by a show code.
_Avoid_: Project, production (in code and docs)

**Show code**:
The short alphanumeric identifier of a show, given in the `SHOW` environment variable. It names the show's override file.
_Avoid_: Show name, show ID

**Setting**:
A named value the tools read to decide how they behave, such as the render width. Each setting is an uppercase key in the config files.
_Avoid_: Option, config value, parameter

**Default setting**:
A setting's value in `config/defaults.yaml`, used by every show unless that show overrides it.
_Avoid_: Global setting, base setting

**Show override**:
A setting a show sets in its own file (`config/<SHOW>.yaml`) to replace the default. Keys a show omits keep their default values.
_Avoid_: Show config, show settings file

## Previs

**Previs**:
Previsualization: a rough, animated version of a scene made before final production, used to plan shots and cameras.
_Avoid_: Previz, animatic (unless referring to a specific deliverable)

**Shot**:
A continuous piece of footage within a **Sequence**, shot from a single camera.

**Sequence**:
A series of connected shots that work together as a distinct narrative unit with its own beginning, middle and end, usually building toward a major plot turn or climax. A feature film typically has 15 to 40. Sequences are numbered from 0, normally in steps of 100, and gaps in the numbering are normal.
_Avoid_: Scene (a different film-making term), reel

**Action**:
A contiguous group of shots within a **Sequence** that share the same action or location; sometimes used for variations. Actions are numbered from 0 within their sequence, and the same number under different sequences is unrelated. Gaps in the numbering are normal.
_Avoid_: Beat, setup

**Version**:
One saved iteration of an **Action**, with its own **Scene file** and comment. Versions are numbered from 1; gaps are possible but rare.
_Avoid_: Revision, iteration, take

**Scene file**:
The Maya file holding a **Version**'s work, named from the show code, sequence, action and version numbers.
_Avoid_: Maya file, shot file

**Camera**:
The Maya camera that frames a shot and is used to render it.

**Camera monitor**:
A Maya panel that shows the view through a camera without letting the artist move it, with display settings of its own. For now it shows persp.

**Render**:
An image or image sequence produced from a camera at a set resolution.

## Flagged ambiguities

- "config" and "settings" were used interchangeably for the values and the module that reads them. Resolved: a single value is a **Setting**. The module is the config module; the words for the values are not interchangeable with it.
- "show" was used for the production and for its file. Resolved: the production is a **Show**; its code is the **Show code**; its file is a **Show override** file.
