"""Folder Manager - Navigate button sub-pages.

Folders allow a button to temporarily change the mappings of other buttons,
multiplying available controls without changing the physical layer.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)

# Maximum folder nesting depth
MAX_DEPTH = 3


class FolderManager:
    """Manages folder navigation for button sub-pages.

    Singleton pattern ensures all actions share the same state.
    Folders are global (not per-layer) and only affect note_on mappings.
    """

    _instance: "FolderManager | None" = None

    def __new__(cls) -> "FolderManager":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the folder manager (only runs once)."""
        if self._initialized:
            return

        self._current_folder: str | None = None
        self._folder_stack: list[str] = []
        self._callbacks: list[Callable[[str | None], None]] = []
        self._initialized = True

    @property
    def current_folder(self) -> str | None:
        """Get current active folder name."""
        return self._current_folder

    @property
    def in_folder(self) -> bool:
        """Check if we're inside a folder."""
        return self._current_folder is not None

    @property
    def depth(self) -> int:
        """Get current folder depth (0 = root)."""
        if self._current_folder is None:
            return 0
        return len(self._folder_stack) + 1

    def enter_folder(self, folder_name: str) -> bool:
        """Enter a folder.

        Args:
            folder_name: Name of the folder to enter.

        Returns:
            True if folder was entered, False if max depth reached.
        """
        if not folder_name:
            logger.warning("FolderManager: empty folder name")
            return False

        # Check max depth
        if self.depth >= MAX_DEPTH:
            logger.warning(
                "FolderManager: max depth %d reached, cannot enter '%s'",
                MAX_DEPTH,
                folder_name,
            )
            return False

        # Push current folder to stack if we're already in one
        if self._current_folder:
            self._folder_stack.append(self._current_folder)

        self._current_folder = folder_name
        logger.info("Entered folder: %s (depth %d)", folder_name, self.depth)
        self._notify_callbacks()
        return True

    def exit_folder(self) -> None:
        """Exit current folder (go back one level)."""
        if self._folder_stack:
            self._current_folder = self._folder_stack.pop()
            logger.info("Exited to folder: %s", self._current_folder)
        else:
            self._current_folder = None
            logger.info("Exited to root")
        self._notify_callbacks()

    def exit_to_root(self) -> None:
        """Exit all folders, return to root."""
        self._current_folder = None
        self._folder_stack.clear()
        logger.info("Exited to root")
        self._notify_callbacks()

    def register_callback(self, callback: Callable[[str | None], None]) -> None:
        """Register callback for folder changes.

        Args:
            callback: Function to call with new folder name (None = root).
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str | None], None]) -> None:
        """Unregister a callback.

        Args:
            callback: Function to remove.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks of folder change."""
        for callback in self._callbacks:
            try:
                callback(self._current_folder)
            except Exception as e:
                logger.error("Folder callback error: %s", e)


def get_folder_manager() -> FolderManager:
    """Get the folder manager singleton.

    Returns:
        The FolderManager instance.
    """
    return FolderManager()
