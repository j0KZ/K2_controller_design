"""Tests for k2deck.actions.timer — Timer Actions."""

import time
from unittest.mock import MagicMock, patch

from k2deck.actions.timer import TimerStartAction, TimerStopAction, TimerToggleAction
from k2deck.core.midi_listener import MidiEvent
from k2deck.core.timer_manager import TimerManager, get_timer_manager


def _note_on(velocity=127):
    """Create a note_on MidiEvent."""
    return MidiEvent(type="note_on", channel=1, note=48, cc=None, value=velocity, timestamp=time.time())


def _cc_event():
    """Create a CC MidiEvent."""
    return MidiEvent(type="cc", channel=1, note=None, cc=16, value=64, timestamp=time.time())


class TestTimerStartAction:
    def setup_method(self):
        TimerManager._instance = None

    def teardown_method(self):
        if TimerManager._instance is not None:
            TimerManager._instance.stop_all()
            TimerManager._instance = None

    def test_starts_timer_on_note_on(self):
        """Starts timer on button press."""
        action = TimerStartAction({"name": "test", "seconds": 60})
        action.execute(_note_on())

        mgr = get_timer_manager()
        assert mgr.is_running("test")

    def test_ignores_note_off(self):
        """Does not trigger on velocity 0 (note off)."""
        action = TimerStartAction({"name": "test", "seconds": 60})
        action.execute(_note_on(velocity=0))

        mgr = get_timer_manager()
        assert not mgr.is_running("test")

    def test_ignores_cc_event(self):
        """Does not trigger on CC events."""
        action = TimerStartAction({"name": "test", "seconds": 60})
        action.execute(_cc_event())

        mgr = get_timer_manager()
        assert not mgr.is_running("test")

    def test_default_seconds(self):
        """Uses 60s default when seconds not specified."""
        action = TimerStartAction({"name": "test"})
        action.execute(_note_on())

        mgr = get_timer_manager()
        remaining = mgr.get_remaining("test")
        assert remaining is not None
        assert remaining >= 59

    def test_seconds_clamped_to_minimum(self):
        """Seconds below 1 are clamped."""
        action = TimerStartAction({"name": "test", "seconds": -5})
        assert action._seconds == 1

    def test_on_complete_executes_action(self):
        """on_complete config creates and executes an action."""
        mock_action = MagicMock()

        with patch("k2deck.core.action_factory.create_action", return_value=mock_action):
            action = TimerStartAction({
                "name": "test",
                "seconds": 1,
                "on_complete": {"action": "noop"},
            })
            action.execute(_note_on())

            # Wait for timer to complete
            import threading
            deadline = time.time() + 5
            while time.time() < deadline:
                if mock_action.execute.called:
                    break
                time.sleep(0.1)

            mock_action.execute.assert_called_once()

    def test_on_complete_none_when_missing(self):
        """No callback when on_complete not specified."""
        action = TimerStartAction({"name": "test", "seconds": 60})
        assert action._on_complete_cb is None

    def test_on_complete_invalid_config_returns_none(self):
        """Invalid on_complete config results in no callback."""
        action = TimerStartAction({"name": "test", "on_complete": "not_a_dict"})
        assert action._on_complete_cb is None


class TestTimerStopAction:
    def setup_method(self):
        TimerManager._instance = None

    def teardown_method(self):
        if TimerManager._instance is not None:
            TimerManager._instance.stop_all()
            TimerManager._instance = None

    def test_stops_running_timer(self):
        """Stops a running timer on button press."""
        mgr = get_timer_manager()
        mgr.start_timer("test", 60)
        assert mgr.is_running("test")

        action = TimerStopAction({"name": "test"})
        action.execute(_note_on())
        time.sleep(0.1)
        assert not mgr.is_running("test")

    def test_ignores_note_off(self):
        """Does not trigger on velocity 0."""
        mgr = get_timer_manager()
        mgr.start_timer("test", 60)

        action = TimerStopAction({"name": "test"})
        action.execute(_note_on(velocity=0))
        assert mgr.is_running("test")

    def test_stop_nonexistent_no_error(self):
        """Stopping a nonexistent timer does not raise."""
        action = TimerStopAction({"name": "nonexistent"})
        action.execute(_note_on())  # Should not raise


class TestTimerToggleAction:
    def setup_method(self):
        TimerManager._instance = None

    def teardown_method(self):
        if TimerManager._instance is not None:
            TimerManager._instance.stop_all()
            TimerManager._instance = None

    def test_first_press_starts(self):
        """First press starts the timer."""
        action = TimerToggleAction({"name": "test", "seconds": 60})
        action.execute(_note_on())

        mgr = get_timer_manager()
        assert mgr.is_running("test")

    def test_second_press_stops(self):
        """Second press stops the timer."""
        action = TimerToggleAction({"name": "test", "seconds": 60})
        action.execute(_note_on())
        time.sleep(0.1)
        action.execute(_note_on())
        time.sleep(0.1)

        mgr = get_timer_manager()
        assert not mgr.is_running("test")

    def test_third_press_restarts(self):
        """Third press restarts the timer."""
        action = TimerToggleAction({"name": "test", "seconds": 60})
        action.execute(_note_on())
        time.sleep(0.1)
        action.execute(_note_on())
        time.sleep(0.1)
        action.execute(_note_on())
        time.sleep(0.1)

        mgr = get_timer_manager()
        assert mgr.is_running("test")

    def test_ignores_cc(self):
        """Does not trigger on CC events."""
        action = TimerToggleAction({"name": "test", "seconds": 60})
        action.execute(_cc_event())

        mgr = get_timer_manager()
        assert not mgr.is_running("test")
