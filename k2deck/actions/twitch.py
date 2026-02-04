"""Twitch Actions - Control Twitch stream via API.

Actions for creating markers, clips, sending chat messages, and updating stream info.
"""

import logging
from typing import TYPE_CHECKING

from k2deck.actions.base import Action

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


class TwitchMarkerAction(Action):
    """Create a Twitch stream marker.

    Config options:
        description: Optional marker description (max 140 chars)

    Config example:
    {
        "action": "twitch_marker",
        "description": "Highlight moment"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize marker action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._description = config.get("description", "")

    def execute(self, event: "MidiEvent") -> None:
        """Execute marker creation.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        from k2deck.core.twitch_client import get_twitch_client

        client = get_twitch_client()
        if not client.is_available:
            logger.debug("Twitch not available (twitchAPI not installed)")
            return

        if not client.is_connected:
            logger.debug("Twitch not connected")
            return

        client.create_marker(self._description)


class TwitchClipAction(Action):
    """Create a Twitch clip.

    Config example:
    {
        "action": "twitch_clip"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize clip action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)

    def execute(self, event: "MidiEvent") -> None:
        """Execute clip creation.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        from k2deck.core.twitch_client import get_twitch_client

        client = get_twitch_client()
        if not client.is_available:
            logger.debug("Twitch not available (twitchAPI not installed)")
            return

        if not client.is_connected:
            logger.debug("Twitch not connected")
            return

        clip_url = client.create_clip()
        if clip_url:
            logger.info("Clip created: %s", clip_url)


class TwitchChatAction(Action):
    """Send a chat message to your Twitch channel.

    Config options:
        message: Message to send (max 500 chars, required)

    Config example:
    {
        "action": "twitch_chat",
        "message": "Thanks for watching!"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize chat action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._message = config.get("message", "")

    def execute(self, event: "MidiEvent") -> None:
        """Execute chat message.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        if not self._message:
            logger.warning("TwitchChatAction: no message configured")
            return

        from k2deck.core.twitch_client import get_twitch_client

        client = get_twitch_client()
        if not client.is_available:
            logger.debug("Twitch not available (twitchAPI not installed)")
            return

        if not client.is_connected:
            logger.debug("Twitch not connected")
            return

        client.send_chat(self._message)


class TwitchTitleAction(Action):
    """Update Twitch stream title.

    Config options:
        title: New stream title (required)

    Config example:
    {
        "action": "twitch_title",
        "title": "Just Chatting with viewers!"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize title action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._title = config.get("title", "")

    def execute(self, event: "MidiEvent") -> None:
        """Execute title update.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        if not self._title:
            logger.warning("TwitchTitleAction: no title configured")
            return

        from k2deck.core.twitch_client import get_twitch_client

        client = get_twitch_client()
        if not client.is_available:
            logger.debug("Twitch not available (twitchAPI not installed)")
            return

        if not client.is_connected:
            logger.debug("Twitch not connected")
            return

        client.update_title(self._title)


class TwitchGameAction(Action):
    """Update Twitch stream game/category.

    Config options:
        game: Game/category name (required)

    Config example:
    {
        "action": "twitch_game",
        "game": "Just Chatting"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize game action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._game = config.get("game", "")

    def execute(self, event: "MidiEvent") -> None:
        """Execute game update.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        if not self._game:
            logger.warning("TwitchGameAction: no game configured")
            return

        from k2deck.core.twitch_client import get_twitch_client

        client = get_twitch_client()
        if not client.is_available:
            logger.debug("Twitch not available (twitchAPI not installed)")
            return

        if not client.is_connected:
            logger.debug("Twitch not connected")
            return

        client.update_game(self._game)
