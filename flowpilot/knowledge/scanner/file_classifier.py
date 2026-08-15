"""File classification utilities for the FlowPilot Repository Scanner.
 
This module provides a single, stateless :class:`FileClassifier` that
determines the :class:`~flowpilot.core.models.FileType` of a file and
answers higher-level questions about a file's role within a GNU Radio
repository (source code, documentation, block definition, test, or
example), based on its name, suffix, and location.
"""
 
from __future__ import annotations
 
from pathlib import Path
from typing import Dict, FrozenSet, Tuple
 
from flowpilot.core.models import FileType
 
__all__ = ["FileClassifier"]
 
 
class FileClassifier:
    """Classifies repository files by :class:`FileType` and semantic role.
 
    This class is intentionally stateless: every method is a pure
    function of its arguments, making instances safe to share and reuse
    across threads and scanning sessions.
    """
 
    _CMAKE_FILENAMES: FrozenSet[str] = frozenset({"cmakelists.txt"})
 
    _SOURCE_TYPES: FrozenSet[FileType] = frozenset(
        {FileType.PYTHON, FileType.CPP_SOURCE, FileType.CPP_HEADER}
    )
    _DOCUMENTATION_TYPES: FrozenSet[FileType] = frozenset(
        {FileType.MARKDOWN, FileType.RESTRUCTURED_TEXT}
    )
    _BLOCK_DEFINITION_TYPES: FrozenSet[FileType] = frozenset(
        {FileType.BLOCK_YML, FileType.TREE_YML}
    )
 
    _TEST_DIRECTORY_NAMES: FrozenSet[str] = frozenset({"test", "tests", "qa"})
    _EXAMPLE_DIRECTORY_NAMES: FrozenSet[str] = frozenset(
        {"example", "examples", "demo", "demos"}
    )
    _TEST_FILENAME_PREFIXES: Tuple[str, ...] = ("test_", "qa_")
    _TEST_FILENAME_SUFFIXES: Tuple[str, ...] = ("_test.py", "_tests.py")
 
    _TYPE_DESCRIPTIONS: Dict[FileType, str] = {
        FileType.BLOCK_YML: "GNU Radio Companion block definition",
        FileType.TREE_YML: "GNU Radio Companion category tree definition",
        FileType.GRC: "GNU Radio Companion flowgraph",
        FileType.PYTHON: "Python source file",
        FileType.CPP_SOURCE: "C++ source file",
        FileType.CPP_HEADER: "C++ header file",
        FileType.MARKDOWN: "Markdown documentation",
        FileType.RESTRUCTURED_TEXT: "reStructuredText documentation",
        FileType.JSON: "JSON document",
        FileType.TEXT: "Plain text document",
        FileType.CMAKE: "CMake build file",
        FileType.IMAGE: "Image asset",
        FileType.UNKNOWN: "Unclassified file",
    }
 
    def classify(self, path: Path) -> FileType:
        """Classifies a file into a :class:`FileType`.
 
        Args:
            path: The file to classify. The file need not exist on disk;
                classification is performed on the filename alone.
 
        Returns:
            The classified :class:`FileType`.
        """
        filename = path.name.lower()
        if filename in self._CMAKE_FILENAMES:
            return FileType.CMAKE
        if filename.endswith(".block.yml") or filename.endswith(".block.yaml"):
            return FileType.BLOCK_YML
        if filename.endswith(".tree.yml") or filename.endswith(".tree.yaml"):
            return FileType.TREE_YML
        suffix = path.suffix.lstrip(".").lower()
        return FileType.from_suffix(suffix)
 
    def describe(self, path: Path) -> str:
        """Returns a human-readable description of a file's classification.
 
        Args:
            path: The file to describe.
 
        Returns:
            A short, human-readable description of the file's type.
        """
        return self._TYPE_DESCRIPTIONS[self.classify(path)]
 
    def is_source(self, path: Path) -> bool:
        """Determines whether a file is a source code file.
 
        Args:
            path: The file to inspect.
 
        Returns:
            ``True`` if the file is Python, C++ source, or C++ header.
        """
        return self.classify(path) in self._SOURCE_TYPES
 
    def is_documentation(self, path: Path) -> bool:
        """Determines whether a file is a documentation file.
 
        Args:
            path: The file to inspect.
 
        Returns:
            ``True`` if the file is Markdown or reStructuredText.
        """
        return self.classify(path) in self._DOCUMENTATION_TYPES
 
    def is_block_definition(self, path: Path) -> bool:
        """Determines whether a file is a GNU Radio Companion block definition.
 
        Args:
            path: The file to inspect.
 
        Returns:
            ``True`` if the file is a ``*.block.yml`` or ``*.tree.yml``
            file.
        """
        return self.classify(path) in self._BLOCK_DEFINITION_TYPES
 
    def is_image(self, path: Path) -> bool:
        """Determines whether a file is an image asset.
 
        Args:
            path: The file to inspect.
 
        Returns:
            ``True`` if the file is classified as :attr:`FileType.IMAGE`.
        """
        return self.classify(path) is FileType.IMAGE
 
    def is_test(self, path: Path) -> bool:
        """Determines whether a file appears to be a test artifact.
 
        A file is considered a test if it resides within a directory
        conventionally used for tests (e.g. ``tests/``) or if its
        filename follows a common test naming convention (e.g.
        ``test_foo.py``).
 
        Args:
            path: The file to inspect.
 
        Returns:
            ``True`` if the file appears to be a test artifact.
        """
        if any(part.lower() in self._TEST_DIRECTORY_NAMES for part in path.parts[:-1]):
            return True
        filename = path.name.lower()
        if filename.startswith(self._TEST_FILENAME_PREFIXES):
            return True
        return filename.endswith(self._TEST_FILENAME_SUFFIXES)
 
    def is_example(self, path: Path) -> bool:
        """Determines whether a file appears to be an example artifact.
 
        A file is considered an example if it resides within a directory
        conventionally used for examples or demos (e.g. ``examples/``).
 
        Args:
            path: The file to inspect.
 
        Returns:
            ``True`` if the file appears to be an example artifact.
        """
        return any(part.lower() in self._EXAMPLE_DIRECTORY_NAMES for part in path.parts[:-1])