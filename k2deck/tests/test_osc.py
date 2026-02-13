"""Tests for k2deck.core.osc — OSC 1.0 encoder and UDP sender."""

import struct
import threading
from unittest.mock import MagicMock, patch

import pytest

from k2deck.core.osc import (
    OscSender,
    build_osc_message,
    osc_float,
    osc_int,
    osc_string,
)


# ---------------------------------------------------------------------------
# osc_string
# ---------------------------------------------------------------------------
class TestOscString:
    def test_empty_string(self):
        """Empty string → null byte + 3 padding = 4 bytes."""
        result = osc_string("")
        assert result == b"\x00\x00\x00\x00"
        assert len(result) % 4 == 0

    def test_short_string(self):
        """'hi' → 'hi\\0' (3 bytes) + 1 pad = 4 bytes."""
        result = osc_string("hi")
        assert result == b"hi\x00\x00"
        assert len(result) == 4

    def test_exact_boundary(self):
        """'abc' → 'abc\\0' = exactly 4 bytes, no extra padding."""
        result = osc_string("abc")
        assert result == b"abc\x00"
        assert len(result) == 4

    def test_longer_string(self):
        """'hello' → 'hello\\0' (6 bytes) padded to 8."""
        result = osc_string("hello")
        assert result == b"hello\x00\x00\x00"
        assert len(result) == 8

    def test_7_char_string(self):
        """7 chars + null = 8 bytes, exact boundary."""
        result = osc_string("abcdefg")
        assert result == b"abcdefg\x00"
        assert len(result) == 8

    def test_always_4_byte_aligned(self):
        """Various lengths always produce 4-byte aligned output."""
        for length in range(0, 20):
            s = "x" * length
            result = osc_string(s)
            assert len(result) % 4 == 0, f"len={length} produced {len(result)} bytes"
            assert result[length] == 0  # Null terminator present


# ---------------------------------------------------------------------------
# osc_int
# ---------------------------------------------------------------------------
class TestOscInt:
    def test_zero(self):
        assert osc_int(0) == b"\x00\x00\x00\x00"

    def test_positive(self):
        assert osc_int(42) == struct.pack(">i", 42)

    def test_negative(self):
        assert osc_int(-1) == struct.pack(">i", -1)

    def test_max_int32(self):
        assert osc_int(2147483647) == struct.pack(">i", 2147483647)

    def test_min_int32(self):
        assert osc_int(-2147483648) == struct.pack(">i", -2147483648)


# ---------------------------------------------------------------------------
# osc_float
# ---------------------------------------------------------------------------
class TestOscFloat:
    def test_zero(self):
        assert osc_float(0.0) == struct.pack(">f", 0.0)

    def test_one(self):
        assert osc_float(1.0) == struct.pack(">f", 1.0)

    def test_fractional(self):
        assert osc_float(0.5) == struct.pack(">f", 0.5)

    def test_negative(self):
        assert osc_float(-1.0) == struct.pack(">f", -1.0)


# ---------------------------------------------------------------------------
# build_osc_message
# ---------------------------------------------------------------------------
class TestBuildOscMessage:
    def test_no_args(self):
        """Address + comma-only type tag."""
        msg = build_osc_message("/test")
        # Address: "/test\0" padded to 8 + type tag: ",\0" padded to 4
        assert msg[:5] == b"/test"
        assert b"," in msg

    def test_single_float(self):
        msg = build_osc_message("/test", 0.5)
        assert struct.pack(">f", 0.5) in msg

    def test_single_int(self):
        msg = build_osc_message("/test", 42)
        assert struct.pack(">i", 42) in msg

    def test_single_string(self):
        msg = build_osc_message("/test", "hello")
        assert b"hello" in msg

    def test_mixed_string_and_float(self):
        """Typical use case: /pd/param 'cutoff' 0.75."""
        msg = build_osc_message("/pd/param", "cutoff", 0.75)
        # Type tag should contain ",sf"
        assert b",sf" in msg
        assert b"cutoff" in msg
        assert struct.pack(">f", 0.75) in msg

    def test_type_tag_order(self):
        """Type tags match argument order."""
        msg = build_osc_message("/test", 1, 2.0, "three")
        assert b",ifs" in msg

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported OSC"):
            build_osc_message("/test", [1, 2, 3])

    def test_address_is_4_byte_aligned(self):
        """Address portion is always 4-byte aligned."""
        msg = build_osc_message("/a")
        # "/a\0" = 3 bytes, padded to 4
        assert msg[:4] == b"/a\x00\x00"


# ---------------------------------------------------------------------------
# OscSender
# ---------------------------------------------------------------------------
class TestOscSender:
    def setup_method(self):
        """Reset singleton state before each test."""
        OscSender._reset()

    def test_singleton_same_host_port(self):
        """Same (host, port) returns same instance."""
        a = OscSender("127.0.0.1", 9000)
        b = OscSender("127.0.0.1", 9000)
        assert a is b

    def test_different_port_creates_new(self):
        """Different port creates new instance."""
        a = OscSender("127.0.0.1", 9000)
        b = OscSender("127.0.0.1", 9001)
        assert a is not b

    def test_different_host_creates_new(self):
        """Different host creates new instance."""
        a = OscSender("127.0.0.1", 9000)
        b = OscSender("192.168.1.1", 9000)
        assert a is not b

    @patch("k2deck.core.osc.socket.socket")
    def test_send_creates_socket_lazily(self, mock_socket_cls):
        """Socket created on first send, not on __init__."""
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        sender = OscSender("127.0.0.1", 9000)
        assert sender._socket is None

        sender.send("/test", 1.0)
        mock_socket_cls.assert_called_once()

    @patch("k2deck.core.osc.socket.socket")
    def test_send_calls_sendto(self, mock_socket_cls):
        """Verify sendto is called with correct host:port."""
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        sender = OscSender("127.0.0.1", 9000)
        result = sender.send("/pd/param", "cutoff", 0.5)

        assert result is True
        mock_sock.sendto.assert_called_once()
        args = mock_sock.sendto.call_args
        assert args[0][1] == ("127.0.0.1", 9000)

    @patch("k2deck.core.osc.socket.socket")
    def test_send_error_returns_false(self, mock_socket_cls):
        """Socket error returns False, doesn't raise."""
        mock_sock = MagicMock()
        mock_sock.sendto.side_effect = OSError("Connection refused")
        mock_socket_cls.return_value = mock_sock

        sender = OscSender("127.0.0.1", 9000)
        result = sender.send("/test", 1.0)

        assert result is False

    @patch("k2deck.core.osc.socket.socket")
    def test_close_clears_socket(self, mock_socket_cls):
        """close() closes and clears the socket."""
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        sender = OscSender("127.0.0.1", 9000)
        sender.send("/test")  # Create socket
        sender.close()

        mock_sock.close.assert_called_once()
        assert sender._socket is None

    def test_close_all_clears_instances(self):
        """close_all() removes all cached senders."""
        OscSender("127.0.0.1", 9000)
        OscSender("127.0.0.1", 9001)
        assert len(OscSender._instances) == 2

        OscSender.close_all()
        assert len(OscSender._instances) == 0

    @patch("k2deck.core.osc.socket.socket")
    def test_socket_reused_across_sends(self, mock_socket_cls):
        """Multiple sends reuse the same socket."""
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        sender = OscSender("127.0.0.1", 9000)
        sender.send("/test", 1.0)
        sender.send("/test", 2.0)
        sender.send("/test", 3.0)

        # Socket created once, sendto called 3 times
        mock_socket_cls.assert_called_once()
        assert mock_sock.sendto.call_count == 3

    @patch("k2deck.core.osc.socket.socket")
    def test_thread_safety(self, mock_socket_cls):
        """Multiple threads sending concurrently don't crash."""
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        sender = OscSender("127.0.0.1", 9000)
        errors = []

        def send_many():
            try:
                for i in range(50):
                    sender.send("/test", float(i))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=send_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert mock_sock.sendto.call_count == 200

    def test_repr(self):
        sender = OscSender("127.0.0.1", 9000)
        assert repr(sender) == "OscSender(127.0.0.1:9000)"
