"""Minimal OSC 1.0 encoder and UDP sender for Pure Data bridge.

Implements the subset of OSC needed to send float, int, and string
messages over UDP. No external dependencies — uses stdlib only.

OSC spec: http://opensoundcontrol.org/spec-1_0
"""

import logging
import socket
import struct
import threading

logger = logging.getLogger(__name__)


def osc_string(s: str) -> bytes:
    """Encode string as OSC string (null-terminated, 4-byte padded).

    Args:
        s: String to encode.

    Returns:
        Padded bytes.
    """
    encoded = s.encode("utf-8") + b"\x00"
    padded_len = (len(encoded) + 3) & ~3
    return encoded.ljust(padded_len, b"\x00")


def osc_int(value: int) -> bytes:
    """Encode int32 big-endian.

    Args:
        value: Integer to encode.

    Returns:
        4 bytes big-endian.
    """
    return struct.pack(">i", value)


def osc_float(value: float) -> bytes:
    """Encode float32 big-endian (IEEE 754).

    Args:
        value: Float to encode.

    Returns:
        4 bytes big-endian.
    """
    return struct.pack(">f", value)


def build_osc_message(address: str, *args: int | float | str) -> bytes:
    """Build a complete OSC message with type tag string.

    Args:
        address: OSC address pattern (e.g., "/pd/param").
        *args: Values to encode (int, float, or str).

    Returns:
        Complete OSC binary message.

    Raises:
        ValueError: If an argument has an unsupported type.
    """
    data = osc_string(address)

    type_tag = ","
    arg_data = b""

    for arg in args:
        if isinstance(arg, float):
            type_tag += "f"
            arg_data += osc_float(arg)
        elif isinstance(arg, int):
            type_tag += "i"
            arg_data += osc_int(arg)
        elif isinstance(arg, str):
            type_tag += "s"
            arg_data += osc_string(arg)
        else:
            raise ValueError(f"Unsupported OSC argument type: {type(arg)}")

    data += osc_string(type_tag)
    data += arg_data
    return data


class OscSender:
    """Thread-safe UDP sender with socket reuse per (host, port).

    Keyed singleton: one persistent socket per destination.
    This differs from the project's single-instance singleton (OBSClientManager)
    because multiple OSC destinations may be active simultaneously
    (e.g., different Pd instances on different ports).

    Usage:
        sender = OscSender("127.0.0.1", 9000)
        sender.send("/pd/param", "cutoff", 0.75)
    """

    _instances: dict[tuple[str, int], "OscSender"] = {}
    _lock = threading.Lock()

    def __new__(cls, host: str = "127.0.0.1", port: int = 9000) -> "OscSender":
        """Get or create singleton instance for (host, port)."""
        key = (host, port)
        if key not in cls._instances:
            with cls._lock:
                if key not in cls._instances:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instances[key] = instance
        return cls._instances[key]

    def __init__(self, host: str = "127.0.0.1", port: int = 9000) -> None:
        """Initialize sender (only runs once per host:port).

        Args:
            host: Target hostname or IP.
            port: Target UDP port.
        """
        if self._initialized:
            return
        self._host = host
        self._port = port
        self._socket: socket.socket | None = None
        self._send_lock = threading.Lock()
        self._initialized = True

    def _ensure_socket(self) -> socket.socket:
        """Lazily create UDP socket.

        Returns:
            The UDP socket.
        """
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return self._socket

    def send(self, address: str, *args: int | float | str) -> bool:
        """Build and send an OSC message.

        Thread-safe. Never raises — logs errors and returns False.

        Args:
            address: OSC address pattern (e.g., "/pd/param").
            *args: Message arguments (int, float, or str).

        Returns:
            True if sent successfully, False on error.
        """
        try:
            msg = build_osc_message(address, *args)
            with self._send_lock:
                sock = self._ensure_socket()
                sock.sendto(msg, (self._host, self._port))
            return True
        except Exception as e:
            logger.error("OSC send to %s:%d failed: %s", self._host, self._port, e)
            return False

    def close(self) -> None:
        """Close the UDP socket."""
        with self._send_lock:
            if self._socket:
                self._socket.close()
                self._socket = None

    @classmethod
    def close_all(cls) -> None:
        """Close all cached sockets (call on app shutdown)."""
        with cls._lock:
            for sender in cls._instances.values():
                sender.close()
            cls._instances.clear()

    @classmethod
    def _reset(cls) -> None:
        """Reset all instances (for testing only)."""
        cls.close_all()

    def __repr__(self) -> str:
        return f"OscSender({self._host}:{self._port})"
