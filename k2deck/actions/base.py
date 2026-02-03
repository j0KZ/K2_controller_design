"""Base action class for K2 Deck actions."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent


class Action(ABC):
    """Abstract base class for all actions."""

    def __init__(self, config: dict):
        """Initialize action with config.

        Args:
            config: Action configuration dict from mapping.
        """
        self.config = config
        self.name = config.get("name", "unnamed")

    @abstractmethod
    def execute(self, event: "MidiEvent") -> None:
        """Execute the action.

        Must not block for more than 100ms.
        Must not raise exceptions (catch and log internally).

        Args:
            event: The MIDI event that triggered this action.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"
