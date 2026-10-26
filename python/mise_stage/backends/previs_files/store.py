"""The previs file tree: <root>/sequences/<sequence>/a<action>/v<version>/.

A store is bound to a root folder and a show code and returns plain frozen
records, so a caller (such as a Qt model) never touches the filesystem itself.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from . import metadata, naming
from .errors import AlreadyExistsError, NotFoundError, NumberOutOfRangeError

SEQUENCES_DIR_NAME = "sequences"
SEQUENCE_STEP = 100


@dataclass(frozen=True)
class Sequence:
    number: int
    path: Path


@dataclass(frozen=True)
class Action:
    sequence: int
    number: int
    path: Path


@dataclass(frozen=True)
class Version:
    sequence: int
    action: int
    number: int
    path: Path
    scene_files: Tuple[Path, ...]

    @property
    def has_scene(self):
        return bool(self.scene_files)


def _next_sequence(number):
    return (number // SEQUENCE_STEP + 1) * SEQUENCE_STEP


def _next_by_one(number):
    return number + 1


class PrevisFileStore:
    def __init__(self, root, show):
        self.root = Path(root)
        self.show = naming.check_show(show)

    @property
    def sequences_dir(self):
        return self.root / SEQUENCES_DIR_NAME

    # -- locating folders -------------------------------------------------

    def _require_root(self):
        if not self.root.is_dir():
            raise NotFoundError(f"Previs file root does not exist: {self.root}")

    def _sequence_path(self, sequence):
        return self.sequences_dir / naming.sequence_dir_name(sequence)

    def _action_path(self, sequence, action):
        return self._sequence_path(sequence) / naming.action_dir_name(action)

    def _version_path(self, sequence, action, version):
        return self._action_path(sequence, action) / naming.version_dir_name(version)

    def _require_sequence(self, sequence):
        self._require_root()
        path = self._sequence_path(sequence)
        if not path.is_dir():
            raise NotFoundError(f"Sequence {sequence} does not exist: {path}")
        return path

    def _require_action(self, sequence, action):
        self._require_sequence(sequence)
        path = self._action_path(sequence, action)
        if not path.is_dir():
            raise NotFoundError(
                f"Action {action} does not exist in sequence {sequence}: {path}"
            )
        return path

    def _require_version(self, sequence, action, version):
        self._require_action(sequence, action)
        path = self._version_path(sequence, action, version)
        if not path.is_dir():
            raise NotFoundError(
                f"Version {version} does not exist in sequence {sequence} "
                f"action {action}: {path}"
            )
        return path

    @staticmethod
    def _numbered_dirs(parent, parse):
        """Return (number, path) for each folder in ``parent`` that parse accepts."""
        found = []
        with os.scandir(parent) as entries:
            for entry in entries:
                number = parse(entry.name)
                if number is not None and entry.is_dir():
                    found.append((number, Path(entry.path)))
        return sorted(found)

    # -- listing ----------------------------------------------------------

    def list_sequences(self):
        self._require_root()
        if not self.sequences_dir.is_dir():
            return []
        return [
            Sequence(number, path)
            for number, path in self._numbered_dirs(
                self.sequences_dir, naming.parse_sequence_dir
            )
        ]

    def list_actions(self, sequence):
        sequence_path = self._require_sequence(sequence)
        return [
            Action(sequence, number, path)
            for number, path in self._numbered_dirs(
                sequence_path, naming.parse_action_dir
            )
        ]

    def list_versions(self, sequence, action):
        action_path = self._require_action(sequence, action)
        return [
            self._version(sequence, action, number, path)
            for number, path in self._numbered_dirs(
                action_path, naming.parse_version_dir
            )
        ]

    def latest_version(self, sequence, action):
        """Return the highest-numbered version, or None if there are none."""
        action_path = self._require_action(sequence, action)
        numbered = self._numbered_dirs(action_path, naming.parse_version_dir)
        if not numbered:
            return None
        # Only the latest folder is opened; older versions need no directory scan.
        number, path = numbered[-1]
        return self._version(sequence, action, number, path)

    def _version(self, sequence, action, number, path):
        stem = naming.scene_name(self.show, sequence, action, number)
        with os.scandir(path) as entries:
            scene_files = sorted(
                Path(entry.path)
                for entry in entries
                if Path(entry.name).stem == stem and entry.is_file()
            )
        return Version(sequence, action, number, path, tuple(scene_files))

    # -- creation ---------------------------------------------------------

    @staticmethod
    def _mkdir(path):
        """Create one folder, failing if it exists; this is atomic on local and SMB."""
        try:
            os.mkdir(path)
        except FileExistsError:
            raise AlreadyExistsError(f"Already exists: {path}") from None

    @staticmethod
    def _create_next(highest, first, maximum, step_from, make):
        """Create the next free number with exclusive folder creation.

        If another process takes the candidate first, move on to the next one.
        """
        candidate = first if highest is None else step_from(highest)
        while True:
            if candidate > maximum:
                raise NumberOutOfRangeError(f"No free number left up to {maximum}")
            try:
                make(candidate)
            except AlreadyExistsError:
                candidate = step_from(candidate)
            else:
                return candidate

    def create_sequence(self, number=None):
        """Create a sequence with ``number``, or the next free one when None."""
        self._require_root()
        if number is not None:
            naming.check_sequence(number)
        self.sequences_dir.mkdir(exist_ok=True)

        def make(n):
            self._mkdir(self._sequence_path(n))

        if number is None:
            existing = [s.number for s in self.list_sequences()]
            number = self._create_next(
                max(existing) if existing else None,
                naming.SEQUENCE_MIN,
                naming.SEQUENCE_MAX,
                _next_sequence,
                make,
            )
        else:
            make(number)
        return Sequence(number, self._sequence_path(number))

    def create_action(self, sequence, number=None):
        """Create an action in ``sequence`` with ``number``, or the next free one."""
        self._require_sequence(sequence)
        if number is not None:
            naming.check_action(number)

        def make(n):
            self._mkdir(self._action_path(sequence, n))

        if number is None:
            existing = [a.number for a in self.list_actions(sequence)]
            number = self._create_next(
                max(existing) if existing else None,
                naming.ACTION_MIN,
                naming.ACTION_MAX,
                _next_by_one,
                make,
            )
        else:
            make(number)
        return Action(sequence, number, self._action_path(sequence, number))

    def allocate_version(self, sequence, action, ext):
        """Create the next version folder and return the scene path to save to.

        ``ext`` is the scene file extension, with or without its leading dot.
        The scene file itself is not created.
        """
        extension = naming.check_extension(ext)
        action_path = self._require_action(sequence, action)
        existing = [
            number
            for number, _ in self._numbered_dirs(action_path, naming.parse_version_dir)
        ]

        def make(n):
            self._mkdir(self._version_path(sequence, action, n))

        number = self._create_next(
            max(existing) if existing else None,
            naming.VERSION_MIN,
            naming.VERSION_MAX,
            _next_by_one,
            make,
        )
        name = naming.scene_name(self.show, sequence, action, number)
        return self._version_path(sequence, action, number) / f"{name}.{extension}"

    # -- comments ---------------------------------------------------------

    def get_action_comment(self, sequence, action):
        return metadata.read_comment(self._require_action(sequence, action))

    def set_action_comment(self, sequence, action, comment):
        metadata.write_comment(self._require_action(sequence, action), comment)

    def get_version_comment(self, sequence, action, version):
        return metadata.read_comment(self._require_version(sequence, action, version))

    def set_version_comment(self, sequence, action, version, comment):
        metadata.write_comment(
            self._require_version(sequence, action, version), comment
        )
