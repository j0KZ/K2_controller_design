"""Tests for k2deck.core.instance_lock — single-instance guard."""

from unittest.mock import MagicMock, patch

import winerror

from k2deck.core.instance_lock import (
    _FAIL_OPEN,
    acquire_instance_lock,
    release_instance_lock,
)


class TestAcquireInstanceLock:
    """Tests for acquire_instance_lock()."""

    @patch("k2deck.core.instance_lock.win32api")
    @patch("k2deck.core.instance_lock.win32event")
    def test_acquires_mutex_successfully(self, mock_event, mock_api):
        mock_event.CreateMutex.return_value = MagicMock(name="mutex_handle")
        mock_api.GetLastError.return_value = 0

        result = acquire_instance_lock()

        assert result is not None
        assert result is not _FAIL_OPEN
        mock_event.CreateMutex.assert_called_once()

    @patch("k2deck.core.instance_lock.win32api")
    @patch("k2deck.core.instance_lock.win32event")
    def test_returns_none_when_already_running(self, mock_event, mock_api):
        mock_event.CreateMutex.return_value = MagicMock(name="mutex_handle")
        mock_api.GetLastError.return_value = winerror.ERROR_ALREADY_EXISTS

        result = acquire_instance_lock()

        assert result is None
        mock_api.CloseHandle.assert_called_once()

    @patch("k2deck.core.instance_lock.win32api")
    @patch("k2deck.core.instance_lock.win32event")
    def test_fail_open_on_exception(self, mock_event, mock_api):
        mock_event.CreateMutex.side_effect = OSError("mutex failed")

        result = acquire_instance_lock()

        assert result is _FAIL_OPEN

    @patch("k2deck.core.instance_lock.win32api")
    @patch("k2deck.core.instance_lock.win32event")
    def test_mutex_name_contains_username(self, mock_event, mock_api):
        mock_api.GetLastError.return_value = 0
        acquire_instance_lock()

        call_args = mock_event.CreateMutex.call_args
        mutex_name = call_args[0][2]
        assert mutex_name.startswith("Global\\K2Deck-")


class TestReleaseInstanceLock:
    """Tests for release_instance_lock()."""

    @patch("k2deck.core.instance_lock.win32api")
    def test_releases_valid_handle(self, mock_api):
        handle = MagicMock(name="mutex_handle")
        release_instance_lock(handle)

        mock_api.CloseHandle.assert_called_once_with(handle)

    @patch("k2deck.core.instance_lock.win32api")
    def test_noop_on_none(self, mock_api):
        release_instance_lock(None)

        mock_api.CloseHandle.assert_not_called()

    @patch("k2deck.core.instance_lock.win32api")
    def test_noop_on_fail_open(self, mock_api):
        release_instance_lock(_FAIL_OPEN)

        mock_api.CloseHandle.assert_not_called()

    @patch("k2deck.core.instance_lock.win32api")
    def test_handles_close_exception(self, mock_api):
        mock_api.CloseHandle.side_effect = OSError("close failed")
        handle = MagicMock(name="mutex_handle")

        # Should not raise
        release_instance_lock(handle)


class TestMainIntegration:
    """Test that main() respects the instance lock."""

    @patch("k2deck.k2deck.K2DeckApp")
    @patch("k2deck.core.instance_lock.acquire_instance_lock", return_value=None)
    @patch("sys.argv", ["k2deck"])
    def test_main_exits_when_already_running(self, mock_lock, mock_app):
        from k2deck.k2deck import main

        result = main()

        assert result is None
        mock_app.assert_not_called()
