"""Folder Actions - Navigate button sub-pages.

Actions for entering, exiting, and navigating folders (button sub-pages).
"""

import logging
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.core.folders import get_folder_manager

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


class FolderAction(Action):
    """Enter a folder (sub-page of actions).

    Config options:
        folder: Name of the folder to enter (required)

    Config example:
    {
        "action": "folder",
        "folder": "obs_controls"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize folder action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._folder = config.get("folder", "")

    def execute(self, event: "MidiEvent") -> None:
        """Execute folder enter.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        if not self._folder:
            logger.warning("FolderAction: no folder configured")
            return

        get_folder_manager().enter_folder(self._folder)


class FolderBackAction(Action):
    """Exit current folder (go back one level).

    Config example:
    {
        "action": "folder_back"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize folder back action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)

    def execute(self, event: "MidiEvent") -> None:
        """Execute folder exit.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        get_folder_manager().exit_folder()


class FolderRootAction(Action):
    """Exit all folders, return to root.

    Config example:
    {
        "action": "folder_root"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize folder root action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)

    def execute(self, event: "MidiEvent") -> None:
        """Execute exit to root.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        get_folder_manager().exit_to_root()
