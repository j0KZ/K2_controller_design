"""MIDI Output for sending LED commands to the K2.

Handles sending Note On/Off messages to control the K2's LEDs.
Includes auto-reconnect support similar to MidiListener.
"""

import logging
import threading
import time

import mido

logger = logging.getLogger(__name__)


class MidiOutput:
    """MIDI output for sending LED control messages."""

    def __init__(
        self,
        device_name: str,
        channel: int = 16,
        reconnect_interval: float = 5.0,
    ):
        """Initialize MIDI output.

        Args:
            device_name: Name of the MIDI device to connect to.
            channel: MIDI channel (1-16, user-facing).
            reconnect_interval: Seconds between reconnect attempts.
        """
        self._device_name = device_name
        self._channel = channel - 1  # Convert to 0-indexed
        self._reconnect_interval = reconnect_interval

        self._port: mido.ports.BaseOutput | None = None
        self._connected = False
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to MIDI device."""
        with self._lock:
            return self._connected

    def _find_device(self) -> str | None:
        """Find the MIDI device by name (partial match)."""
        outputs = mido.get_output_names()
        for name in outputs:
            if self._device_name.lower() in name.lower():
                return name
        return None

    def open(self) -> bool:
        """Open the MIDI output port."""
        with self._lock:
            if self._connected:
                return True

            device = self._find_device()
            if not device:
                logger.warning("Output device '%s' not found", self._device_name)
                return False

            try:
                self._port = mido.open_output(device)
                self._connected = True
                logger.info("Opened MIDI output: %s", device)
                return True
            except Exception as e:
                logger.error("Failed to open MIDI output: %s", e)
                return False

    def close(self) -> None:
        """Close the MIDI output port."""
        with self._lock:
            if self._port:
                try:
                    self._port.close()
                except Exception:
                    pass
                self._port = None
            self._connected = False
            logger.info("MIDI output closed")

    def send_note_on(self, note: int, velocity: int = 127) -> bool:
        """Send a Note On message.

        Args:
            note: MIDI note number (0-127).
            velocity: Note velocity (0-127).

        Returns:
            True if sent successfully, False otherwise.
        """
        with self._lock:
            if not self._connected or not self._port:
                logger.debug("Cannot send: not connected")
                return False

            try:
                msg = mido.Message(
                    "note_on",
                    channel=self._channel,
                    note=note,
                    velocity=velocity,
                )
                self._port.send(msg)
                logger.debug("Sent Note On: note=%d vel=%d", note, velocity)
                return True
            except Exception as e:
                logger.error("Failed to send Note On: %s", e)
                self._connected = False
                return False

    def send_note_off(self, note: int) -> bool:
        """Send a Note Off message.

        Args:
            note: MIDI note number (0-127).

        Returns:
            True if sent successfully, False otherwise.
        """
        with self._lock:
            if not self._connected or not self._port:
                logger.debug("Cannot send: not connected")
                return False

            try:
                msg = mido.Message(
                    "note_off",
                    channel=self._channel,
                    note=note,
                    velocity=0,
                )
                self._port.send(msg)
                logger.debug("Sent Note Off: note=%d", note)
                return True
            except Exception as e:
                logger.error("Failed to send Note Off: %s", e)
                self._connected = False
                return False

    def send_cc(self, control: int, value: int) -> bool:
        """Send a Control Change message.

        Args:
            control: CC number (0-127).
            value: CC value (0-127).

        Returns:
            True if sent successfully, False otherwise.
        """
        with self._lock:
            if not self._connected or not self._port:
                return False

            try:
                msg = mido.Message(
                    "control_change",
                    channel=self._channel,
                    control=control,
                    value=value,
                )
                self._port.send(msg)
                return True
            except Exception as e:
                logger.error("Failed to send CC: %s", e)
                self._connected = False
                return False

    def reconnect(self) -> bool:
        """Close and reopen the port."""
        self.close()
        time.sleep(0.1)
        return self.open()
