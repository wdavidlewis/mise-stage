"""Errors raised by the previs file API."""


class PrevisFilesError(Exception):
    """Base class: anything wrong with the previs file tree or a request on it."""


class NotFoundError(PrevisFilesError):
    """A root, sequence, action or version that was asked for does not exist."""


class AlreadyExistsError(PrevisFilesError):
    """A sequence, action or version to be created already exists."""


class InvalidNameError(PrevisFilesError):
    """A scene name, show code or folder name does not follow the convention."""


class NumberOutOfRangeError(PrevisFilesError):
    """A sequence, action or version number is outside its allowed range."""


class MetadataError(PrevisFilesError):
    """A metadata file exists but cannot be read."""
