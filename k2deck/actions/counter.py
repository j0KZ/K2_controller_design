"""Counter Action - Increment/decrement/reset persistent counters.

Useful for tracking kills, reps, pomodoros, or any countable metric.
"""

import logging
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.core.counters import get_counter_manager

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


class CounterAction(Action):
    """Increment/decrement/reset a persistent counter.

    Config options:
        name: Counter name (required)
        operation: "increment", "decrement", "reset", or "set" (default: "increment")
        amount: Amount for increment/decrement (default: 1)
        value: Value for "set" operation (default: 0)

    Config example (increment):
    {
        "action": "counter",
        "name": "kills",
        "operation": "increment"
    }

    Config example (decrement by 5):
    {
        "action": "counter",
        "name": "lives",
        "operation": "decrement",
        "amount": 5
    }

    Config example (reset):
    {
        "action": "counter",
        "name": "kills",
        "operation": "reset"
    }

    Config example (set to specific value):
    {
        "action": "counter",
        "name": "score",
        "operation": "set",
        "value": 100
    }
    """

    def __init__(self, config: dict) -> None:
        """Initialize counter action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._name = config.get("name", "default")
        self._operation = config.get("operation", "increment")
        self._amount = config.get("amount", 1)
        self._value = config.get("value", 0)

    def execute(self, event: "MidiEvent") -> None:
        """Execute counter operation.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        mgr = get_counter_manager()

        if self._operation == "increment":
            value = mgr.increment(self._name, self._amount)
        elif self._operation == "decrement":
            value = mgr.decrement(self._name, self._amount)
        elif self._operation == "reset":
            mgr.reset(self._name)
            value = 0
        elif self._operation == "set":
            mgr.set(self._name, self._value)
            value = self._value
        else:
            logger.warning("CounterAction: unknown operation '%s'", self._operation)
            return

        logger.info("Counter '%s': %d", self._name, value)
