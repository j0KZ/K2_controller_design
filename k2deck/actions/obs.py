"""OBS Actions - Control OBS Studio via WebSocket.

Actions for scene switching, source visibility, streaming, and recording.
Requires obsws-python (pip install obsws-python) and OBS Studio 28+.
"""

import logging
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.core.obs_client import get_obs_client

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


class OBSSceneAction(Action):
    """Switch to a specific OBS scene.

    Config options:
        scene: Name of the scene to switch to (required)

    Config example:
    {
        "action": "obs_scene",
        "scene": "Gaming"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize OBS scene action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._scene = config.get("scene", "")

    def execute(self, event: "MidiEvent") -> None:
        """Switch to the configured scene.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        if not self._scene:
            logger.warning("OBSSceneAction: no scene configured")
            return

        client = get_obs_client()
        if not client.is_available:
            logger.warning("OBS: obsws-python not installed")
            return

        client.set_scene(self._scene)


class OBSSourceToggleAction(Action):
    """Toggle visibility of an OBS source.

    Config options:
        scene: Name of the scene containing the source (required)
        source: Name of the source to toggle (required)
        visible: Optional - True to show, False to hide, omit to toggle

    Config example (toggle):
    {
        "action": "obs_source_toggle",
        "scene": "Main",
        "source": "Webcam"
    }

    Config example (set visibility):
    {
        "action": "obs_source_toggle",
        "scene": "Main",
        "source": "Webcam",
        "visible": true
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize OBS source toggle action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._scene = config.get("scene", "")
        self._source = config.get("source", "")
        self._visible = config.get("visible")  # None = toggle

    def execute(self, event: "MidiEvent") -> None:
        """Toggle or set source visibility.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        if not self._scene:
            logger.warning("OBSSourceToggleAction: no scene configured")
            return
        if not self._source:
            logger.warning("OBSSourceToggleAction: no source configured")
            return

        client = get_obs_client()
        if not client.is_available:
            logger.warning("OBS: obsws-python not installed")
            return

        client.toggle_source_visibility(self._scene, self._source, self._visible)


class OBSStreamAction(Action):
    """Control OBS streaming.

    Config options:
        mode: "start", "stop", or "toggle" (default: "toggle")

    Config example:
    {
        "action": "obs_stream",
        "mode": "toggle"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize OBS stream action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._mode = config.get("mode", "toggle")

    def execute(self, event: "MidiEvent") -> None:
        """Control streaming.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        client = get_obs_client()
        if not client.is_available:
            logger.warning("OBS: obsws-python not installed")
            return

        client.toggle_stream(self._mode)


class OBSRecordAction(Action):
    """Control OBS recording.

    Config options:
        mode: "start", "stop", "toggle", or "pause" (default: "toggle")

    Config example:
    {
        "action": "obs_record",
        "mode": "toggle"
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize OBS record action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._mode = config.get("mode", "toggle")

    def execute(self, event: "MidiEvent") -> None:
        """Control recording.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        client = get_obs_client()
        if not client.is_available:
            logger.warning("OBS: obsws-python not installed")
            return

        client.toggle_record(self._mode)


class OBSMuteAction(Action):
    """Control OBS audio input mute state.

    Config options:
        input: Name of the audio input (required)
        muted: Optional - True to mute, False to unmute, omit to toggle

    Config example (toggle):
    {
        "action": "obs_mute",
        "input": "Mic/Aux"
    }

    Config example (set state):
    {
        "action": "obs_mute",
        "input": "Mic/Aux",
        "muted": true
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize OBS mute action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._input = config.get("input", "")
        self._muted = config.get("muted")  # None = toggle

    def execute(self, event: "MidiEvent") -> None:
        """Toggle or set mute state.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        if not self._input:
            logger.warning("OBSMuteAction: no input configured")
            return

        client = get_obs_client()
        if not client.is_available:
            logger.warning("OBS: obsws-python not installed")
            return

        client.toggle_mute(self._input, self._muted)
