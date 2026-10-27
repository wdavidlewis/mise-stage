"""The previs file tree: <root>/sequences/<sequence>/a<action>/v<version>/.

A store is bound to a root folder and a show code and returns plain frozen
records, so a caller (such as a Qt model) never touches the filesystem itself.
"""
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from . import metadata, naming
from .errors import AlreadyExistsError, NotFoundError, NumberOutOfRangeError

SEQUENCES_DIR_NAME = "sequences"
SEQUENCE_STEP = 100


@dataclass(frozen=True)
class Sequence:
    """A sequence folder.

    Attributes:
        number: The sequence number.
        path: The sequence folder.
    """

    number: int
    path: Path


@dataclass(frozen=True)
class Action:
    """An action folder.

    Attributes:
        sequence: The number of the sequence holding the action.
        number: The action number.
        path: The action folder.
    """

    sequence: int
    number: int
    path: Path


@dataclass(frozen=True)
class Version:
    """A version folder and the scene files saved in it.

    Attributes:
        sequence: The number of the sequence holding the version.
        action: The number of the action holding the version.
        number: The version number.
        path: The version folder.
        scene_files: The scene files in the folder, sorted by path.
    """

    sequence: int
    action: int
    number: int
    path: Path
    scene_files: Tuple[Path, ...]

    @property
    def has_scene(self) -> bool:
        """Whether the version has at least one scene file."""
        return bool(self.scene_files)


def _next_sequence(number: int) -> int:
    """Return the first sequence number after ``number`` on the step grid."""
    return (number // SEQUENCE_STEP + 1) * SEQUENCE_STEP


def _next_by_one(number: int) -> int:
    """Return the number after ``number``."""
    return number + 1


class PrevisFileStore:
    """The previs file tree under one root folder, for one show.

    Args:
        root: The folder holding the ``sequences`` tree. It must exist for
            operations that read or write the tree.
        show: The show code, letters and digits only. It is used in scene names.

    Raises:
        InvalidNameError: If ``show`` is not a valid show code.
    """

    def __init__(self, root: str | os.PathLike[str], show: str) -> None:
        self.root = Path(root)
        self.show = naming.check_show(show)

    @property
    def sequences_dir(self) -> Path:
        """The folder holding the sequence folders."""
        return self.root / SEQUENCES_DIR_NAME

    # -- locating folders -------------------------------------------------

    def _require_root(self) -> None:
        """Raise NotFoundError if the root folder does not exist."""
        if not self.root.is_dir():
            raise NotFoundError(f"Previs file root does not exist: {self.root}")

    def _sequence_path(self, sequence: int) -> Path:
        """Return the path of a sequence folder, whether or not it exists."""
        return self.sequences_dir / naming.sequence_dir_name(sequence)

    def _action_path(self, sequence: int, action: int) -> Path:
        """Return the path of an action folder, whether or not it exists."""
        return self._sequence_path(sequence) / naming.action_dir_name(action)

    def _version_path(self, sequence: int, action: int, version: int) -> Path:
        """Return the path of a version folder, whether or not it exists."""
        return self._action_path(sequence, action) / naming.version_dir_name(version)

    def _require_sequence(self, sequence: int) -> Path:
        """Return the sequence folder path, raising NotFoundError if it is missing."""
        self._require_root()
        path = self._sequence_path(sequence)
        if not path.is_dir():
            raise NotFoundError(f"Sequence {sequence} does not exist: {path}")
        return path

    def _require_action(self, sequence: int, action: int) -> Path:
        """Return the action folder path, raising NotFoundError if it is missing."""
        self._require_sequence(sequence)
        path = self._action_path(sequence, action)
        if not path.is_dir():
            raise NotFoundError(
                f"Action {action} does not exist in sequence {sequence}: {path}"
            )
        return path

    def _require_version(self, sequence: int, action: int, version: int) -> Path:
        """Return the version folder path, raising NotFoundError if it is missing."""
        self._require_action(sequence, action)
        path = self._version_path(sequence, action, version)
        if not path.is_dir():
            raise NotFoundError(
                f"Version {version} does not exist in sequence {sequence} "
                f"action {action}: {path}"
            )
        return path

    @staticmethod
    def _numbered_dirs(
        parent: Path, parse: Callable[[str], int | None]
    ) -> list[tuple[int, Path]]:
        """Return (number, path) for each folder in ``parent`` that parse accepts."""
        found = []
        with os.scandir(parent) as entries:
            for entry in entries:
                number = parse(entry.name)
                if number is not None and entry.is_dir():
                    found.append((number, Path(entry.path)))
        return sorted(found)

    # -- listing ----------------------------------------------------------

    def list_sequences(self) -> list[Sequence]:
        """List the sequences in the root, sorted by number.

        Returns:
            The sequences, or an empty list if the sequences folder does not exist.

        Raises:
            NotFoundError: If the root folder does not exist.
        """
        self._require_root()
        if not self.sequences_dir.is_dir():
            return []
        return [
            Sequence(number, path)
            for number, path in self._numbered_dirs(
                self.sequences_dir, naming.parse_sequence_dir
            )
        ]

    def list_actions(self, sequence: int) -> list[Action]:
        """List the actions in a sequence, sorted by number.

        Raises:
            NotFoundError: If the sequence does not exist.
        """
        sequence_path = self._require_sequence(sequence)
        return [
            Action(sequence, number, path)
            for number, path in self._numbered_dirs(
                sequence_path, naming.parse_action_dir
            )
        ]

    def list_versions(self, sequence: int, action: int) -> list[Version]:
        """List the versions of an action, sorted by number.

        Raises:
            NotFoundError: If the sequence or action does not exist.
        """
        action_path = self._require_action(sequence, action)
        return [
            self._version(sequence, action, number, path)
            for number, path in self._numbered_dirs(
                action_path, naming.parse_version_dir
            )
        ]

    def latest_version(self, sequence: int, action: int) -> Version | None:
        """Return the highest-numbered version, or None if there are none.

        Raises:
            NotFoundError: If the sequence or action does not exist.
        """
        action_path = self._require_action(sequence, action)
        numbered = self._numbered_dirs(action_path, naming.parse_version_dir)
        if not numbered:
            return None
        # Only the latest folder is opened; older versions need no directory scan.
        number, path = numbered[-1]
        return self._version(sequence, action, number, path)

    def _version(
        self, sequence: int, action: int, number: int, path: Path
    ) -> Version:
        """Build a Version record, collecting the scene files in its folder."""
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
    def _mkdir(path: Path) -> None:
        """Create one folder, failing if it exists; this is atomic on local and SMB.

        Raises:
            AlreadyExistsError: If the folder already exists.
        """
        try:
            os.mkdir(path)
        except FileExistsError:
            raise AlreadyExistsError(f"Already exists: {path}") from None

    @staticmethod
    def _create_next(
        highest: int | None,
        first: int,
        maximum: int,
        step_from: Callable[[int], int],
        make: Callable[[int], None],
    ) -> int:
        """Create the next free number with exclusive folder creation.

        If another process takes the candidate first, move on to the next one.

        Args:
            highest: The highest existing number, or None if there are none.
            first: The number to use when there are none.
            maximum: The largest allowed number.
            step_from: Returns the number after a given one.
            make: Creates the folder for a number, raising AlreadyExistsError if
                it is taken.

        Returns:
            The number that was created.

        Raises:
            NumberOutOfRangeError: If no free number is left up to ``maximum``.
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

    def create_sequence(self, number: int | None = None) -> Sequence:
        """Create a sequence folder.

        Args:
            number: The sequence number. If None, the next free one on the
                sequence step is used.

        Returns:
            The created sequence.

        Raises:
            AlreadyExistsError: If ``number`` is given and the sequence exists.
            NumberOutOfRangeError: If ``number`` is out of range, or no free
                number is left.
            NotFoundError: If the root folder does not exist.
        """
        self._require_root()
        if number is not None:
            naming.check_sequence(number)
        self.sequences_dir.mkdir(exist_ok=True)

        def make(n: int) -> None:
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

    def create_action(self, sequence: int, number: int | None = None) -> Action:
        """Create an action folder in a sequence.

        Args:
            sequence: The sequence number that holds the action.
            number: The action number. If None, the next free one is used.

        Returns:
            The created action.

        Raises:
            NotFoundError: If the sequence does not exist.
            AlreadyExistsError: If ``number`` is given and the action exists.
            NumberOutOfRangeError: If ``number`` is out of range, or no free
                number is left.
        """
        self._require_sequence(sequence)
        if number is not None:
            naming.check_action(number)

        def make(n: int) -> None:
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

    def allocate_version(self, sequence: int, action: int, ext: str) -> Path:
        """Create the next version folder and return the scene path to save to.

        ``ext`` is the scene file extension, with or without its leading dot.
        The scene file itself is not created.

        Args:
            sequence: The sequence number.
            action: The action number.
            ext: The scene file extension, such as ``"ma"`` or ``".mb"``.

        Returns:
            The path of the scene file in the new version folder.

        Raises:
            NotFoundError: If the sequence or action does not exist.
            InvalidNameError: If ``ext`` is not letters and digits.
            NumberOutOfRangeError: If no free version number is left.
        """
        extension = naming.check_extension(ext)
        action_path = self._require_action(sequence, action)
        existing = [
            number
            for number, _ in self._numbered_dirs(action_path, naming.parse_version_dir)
        ]

        def make(n: int) -> None:
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

    def get_action_comment(self, sequence: int, action: int) -> str:
        """Return the comment on an action, or "" when there is none.

        Raises:
            NotFoundError: If the sequence or action does not exist.
            MetadataError: If the metadata file cannot be read.
        """
        return metadata.read_comment(self._require_action(sequence, action))

    def set_action_comment(self, sequence: int, action: int, comment: str) -> None:
        """Store a comment on an action.

        Raises:
            NotFoundError: If the sequence or action does not exist.
            MetadataError: If the existing metadata file cannot be read.
        """
        metadata.write_comment(self._require_action(sequence, action), comment)

    def get_version_comment(self, sequence: int, action: int, version: int) -> str:
        """Return the comment on a version, or "" when there is none.

        Raises:
            NotFoundError: If the sequence, action or version does not exist.
            MetadataError: If the metadata file cannot be read.
        """
        return metadata.read_comment(self._require_version(sequence, action, version))

    def set_version_comment(
        self, sequence: int, action: int, version: int, comment: str
    ) -> None:
        """Store a comment on a version.

        Raises:
            NotFoundError: If the sequence, action or version does not exist.
            MetadataError: If the existing metadata file cannot be read.
        """
        metadata.write_comment(
            self._require_version(sequence, action, version), comment
        )
