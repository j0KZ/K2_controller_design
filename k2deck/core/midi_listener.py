"""MIDI Listener with auto-reconnect support.

Listens for MIDI input from the K2 in a background thread and dispatches
events to a callback. Automatically attempts to reconnect if the device
is disconnected.
"""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import mido

logger = logging.getLogger(__name__)


@dataclass
class MidiEvent:
    """Parsed MIDI event."""

    type: str  # "note_on", "note_off", "cc"
    channel: int  # 1-16 (user-facing)
    note: int | None  # For note events
    cc: int | None  # For CC events
    value: int  # velocity or CC value
    timestamp: float  # time.time()

    @classmethod
    def from_mido(cls, msg: mido.Message) -> "MidiEvent | None":
        """Create MidiEvent from mido Message."""
        ts = time.time()
        channel = msg.channel + 1 if hasattr(msg, "channel") else 0

        if msg.type == "note_on":
            return cls(
                type="note_on" if msg.velocity > 0 else "note_off",
                channel=channel,
                note=msg.note,
                cc=None,
                value=msg.velocity,
                timestamp=ts,
            )
        elif msg.type == "note_off":
            return cls(
                type="note_off",
                channel=channel,
                note=msg.note,
                cc=None,
                value=msg.velocity,
                timestamp=ts,
            )
        elif msg.type == "control_change":
            return cls(
                type="cc",
                channel=channel,
                note=None,
                cc=msg.control,
                value=msg.value,
                timestamp=ts,
            )
        return None


class MidiListener:
    """MIDI input listener with auto-reconnect."""

    def __init__(
        self,
        device_name: str,
        callback: Callable[[MidiEvent], None],
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: int = 60,
    ):
        """Initialize MIDI listener.

        Args:
            device_name: Name of the MIDI device to connect to.
            callback: Function to call with each MidiEvent.
            reconnect_interval: Seconds between reconnect attempts.
            max_reconnect_attempts: Maximum number of reconnect attempts.
        """
        self._device_name = device_name
        self._callback = callback
        self._reconnect_interval = reconnect_interval
        self._max_reconnect_attempts = max_reconnect_attempts

        self._port: mido.ports.BaseInput | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._connected = False
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to MIDI device."""
        with self._lock:
            return self._connected

    @property
    def is_running(self) -> bool:
        """Check if listener thread is running."""
        return self._running

    def _find_device(self) -> str | None:
        """Find the MIDI device by name (partial match)."""
        inputs = mido.get_input_names()
        for name in inputs:
            if self._device_name.lower() in name.lower():
                return name
        return None

    def _connect(self) -> bool:
        """Attempt to connect to the MIDI device."""
        device = self._find_device()
        if not device:
            logger.debug("Device '%s' not found", self._device_name)
            return False

        try:
            self._port = mido.open_input(device)
            with self._lock:
                self._connected = True
            logger.info("Connected to MIDI device: %s", device)
            return True
        except Exception as e:
            logger.warning("Failed to open MIDI port: %s", e)
            return False

    def _disconnect(self) -> None:
        """Close the MIDI port."""
        if self._port:
            try:
                self._port.close()
            except Exception:
                pass
            self._port = None
        with self._lock:
            self._connected = False

    def _listen_loop(self) -> None:
        """Main listening loop (runs in thread)."""
        reconnect_count = 0

        while self._running:
            # Try to connect if not connected
            if not self._connected:
                if self._connect():
                    reconnect_count = 0
                else:
                    reconnect_count += 1
                    if reconnect_count >= self._max_reconnect_attempts:
                        logger.error(
                            "Max reconnect attempts reached. Stopping listener."
                        )
                        self._running = False
                        break
                    time.sleep(self._reconnect_interval)
                    continue

            # Read messages
            try:
                for msg in self._port.iter_pending():
                    event = MidiEvent.from_mido(msg)
                    if event:
                        try:
                            self._callback(event)
                        except Exception as e:
                            logger.error("Callback error: %s", e)

                time.sleep(0.001)  # Small sleep to prevent CPU spin

            except Exception as e:
                logger.warning("MIDI read error: %s. Attempting reconnect...", e)
                self._disconnect()

    def start(self) -> None:
        """Start listening in background thread."""
        if self._running:
            logger.warning("Listener already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("MIDI listener started")

    def stop(self) -> None:
        """Stop listening and clean up."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._disconnect()
        logger.info("MIDI listener stopped")

    def reconnect(self) -> bool:
        """Force a reconnection attempt."""
        self._disconnect()
        return self._connect()
