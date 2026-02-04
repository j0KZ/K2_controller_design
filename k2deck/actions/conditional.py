"""Conditional Action - Execute different actions based on context.

Allows executing different actions depending on which app is focused,
which apps are running, or the state of toggle buttons.
"""

import logging
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.core.action_factory import MAX_ACTION_DEPTH, create_action
from k2deck.core.context import is_app_focused, is_app_running

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


class ConditionalAction(Action):
    """Execute different actions based on conditions.

    Evaluates conditions in order and executes the first matching action.
    Falls back to default action if no conditions match.

    Config options:
        conditions: List of condition objects, each with:
            - app_focused: Process name that must have focus
            - app_running: Process name that must be running
            - toggle_state: Dict with "note" and "state" (true/false)
            - then: Action config to execute if condition matches

        default: Action config to execute if no conditions match

    Config example:
    {
        "action": "conditional",
        "conditions": [
            {
                "app_focused": "Spotify.exe",
                "then": { "action": "spotify_play_pause" }
            },
            {
                "app_focused": "vlc.exe",
                "then": { "action": "hotkey", "keys": ["space"] }
            }
        ],
        "default": { "action": "hotkey", "keys": ["media_play_pause"] }
    }
    """

    def __init__(self, config: dict):
        """Initialize conditional action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._depth = config.get("_depth", 0)
        self._conditions = config.get("conditions", [])
        self._default_config = config.get("default")

        # Pre-create default action if configured
        self._default_action: Action | None = None
        if self._default_config:
            self._default_action = create_action(self._default_config, self._depth + 1)

    def execute(self, event: "MidiEvent") -> None:
        """Execute the matching conditional action.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Check depth limit
        if self._depth >= MAX_ACTION_DEPTH:
            logger.warning(
                "ConditionalAction at max depth (%d), skipping", MAX_ACTION_DEPTH
            )
            return

        # Evaluate conditions in order
        for condition in self._conditions:
            if self._check_condition(condition):
                then_config = condition.get("then")
                if then_config:
                    action = create_action(then_config, self._depth + 1)
                    if action:
                        logger.debug(
                            "Condition matched: %s -> %s",
                            self._describe_condition(condition),
                            then_config.get("action"),
                        )
                        action.execute(event)
                return

        # No condition matched, execute default
        if self._default_action:
            logger.debug("No condition matched, executing default action")
            self._default_action.execute(event)
        else:
            logger.debug("No condition matched and no default action configured")

    def _check_condition(self, condition: dict) -> bool:
        """Check if a condition is met.

        Args:
            condition: Condition dict to evaluate.

        Returns:
            True if condition is met, False otherwise.
        """
        # Check app_focused condition
        if "app_focused" in condition:
            app_name = condition["app_focused"]
            if not is_app_focused(app_name):
                return False

        # Check app_running condition
        if "app_running" in condition:
            app_name = condition["app_running"]
            if not is_app_running(app_name):
                return False

        # Check toggle_state condition
        if "toggle_state" in condition:
            toggle_check = condition["toggle_state"]
            if not self._check_toggle_state(toggle_check):
                return False

        # All conditions passed (or no conditions specified)
        return True

    def _check_toggle_state(self, toggle_check: dict) -> bool:
        """Check toggle state condition.

        Args:
            toggle_check: Dict with "note" (int) and "state" (bool).

        Returns:
            True if toggle state matches, False otherwise.
        """
        # Import here to avoid circular import
        from k2deck.actions.multi import MultiToggleAction

        note = toggle_check.get("note")
        expected_state = toggle_check.get("state", True)

        if note is None:
            logger.warning("toggle_state condition missing 'note' key")
            return False

        actual_state = MultiToggleAction.get_state(note)
        return actual_state == expected_state

    def _describe_condition(self, condition: dict) -> str:
        """Create human-readable description of a condition.

        Args:
            condition: Condition dict.

        Returns:
            Description string.
        """
        parts = []
        if "app_focused" in condition:
            parts.append(f"app_focused={condition['app_focused']}")
        if "app_running" in condition:
            parts.append(f"app_running={condition['app_running']}")
        if "toggle_state" in condition:
            ts = condition["toggle_state"]
            parts.append(f"toggle[{ts.get('note')}]={ts.get('state')}")

        return " AND ".join(parts) if parts else "always"
