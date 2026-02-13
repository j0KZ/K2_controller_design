"""Timer Actions - Start/stop/toggle countdown timers.

Useful for pomodoro sessions, stream breaks, or any timed workflow.
Completion callbacks can trigger any K2 Deck action (sound, TTS, etc.).
"""

import logging
import time
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.core.timer_manager import get_timer_manager

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


def _build_completion_callback(on_complete_config: dict | None) -> "(() -> None) | None":
    """Build a callback that creates and executes an action on timer completion.

    Args:
        on_complete_config: Action config dict (e.g., {"action": "sound_play", "file": "bell.wav"}).

    Returns:
        Callback function, or None if no config provided.
    """
    if not on_complete_config or not isinstance(on_complete_config, dict):
        return None

    def callback() -> None:
        from k2deck.core.action_factory import create_action
        from k2deck.core.midi_listener import MidiEvent

        action = create_action(on_complete_config)
        if action:
            synthetic_event = MidiEvent(
                type="note_on",
                channel=0,
                note=0,
                cc=None,
                value=127,
                timestamp=time.time(),
            )
            try:
                action.execute(synthetic_event)
            except Exception as e:
                logger.error("Timer on_complete action error: %s", e)

    return callback


class TimerStartAction(Action):
    """Start a countdown timer.

    If a timer with the same name is already running, it is restarted.

    Config options:
        name: Timer name (required)
        seconds: Duration in seconds (default: 60, minimum: 1)
        on_complete: Action config dict to execute when timer finishes (optional)

    Config example:
    {
        "action": "timer_start",
        "name": "pomodoro",
        "seconds": 1500,
        "on_complete": {
            "action": "sound_play",
            "file": "bell.wav"
        }
    }
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._timer_name = config.get("name", "default")
        self._seconds = max(1, float(config.get("seconds", 60)))
        self._on_complete_cb = _build_completion_callback(config.get("on_complete"))

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        try:
            manager = get_timer_manager()
            manager.start_timer(
                self._timer_name,
                self._seconds,
                on_complete=self._on_complete_cb,
            )
        except Exception as e:
            logger.error("TimerStartAction error: %s", e)


class TimerStopAction(Action):
    """Stop a running timer.

    Config options:
        name: Timer name to stop (required)

    Config example:
    {
        "action": "timer_stop",
        "name": "pomodoro"
    }
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._timer_name = config.get("name", "default")

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        try:
            manager = get_timer_manager()
            manager.stop_timer(self._timer_name)
        except Exception as e:
            logger.error("TimerStopAction error: %s", e)


class TimerToggleAction(Action):
    """Toggle a timer: stop if running, start if stopped.

    Config options:
        name: Timer name (required)
        seconds: Duration in seconds (default: 60, minimum: 1)
        on_complete: Action config dict for completion (optional)

    Config example:
    {
        "action": "timer_toggle",
        "name": "break",
        "seconds": 300,
        "on_complete": {
            "action": "tts",
            "text": "Break is over"
        }
    }
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._timer_name = config.get("name", "default")
        self._seconds = max(1, float(config.get("seconds", 60)))
        self._on_complete_cb = _build_completion_callback(config.get("on_complete"))

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        try:
            manager = get_timer_manager()
            manager.toggle_timer(
                self._timer_name,
                self._seconds,
                on_complete=self._on_complete_cb,
            )
        except Exception as e:
            logger.error("TimerToggleAction error: %s", e)
