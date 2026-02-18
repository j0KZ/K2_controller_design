"""Tests for k2deck.actions.osc_send — OSC Send action classes."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from k2deck.actions.osc_send import (
    OscSendAction,
    OscSendRelativeAction,
    OscSendTriggerAction,
    _apply_curve,
    _scale_to_range,
)


@dataclass
class FakeMidiEvent:
    """Minimal MidiEvent stub for testing."""

    type: str
    channel: int = 16
    note: int | None = None
    cc: int | None = None
    value: int = 0
    timestamp: float = 0.0


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
class TestApplyCurve:
    def test_linear_passthrough(self):
        assert _apply_curve(0.5, "linear") == 0.5

    def test_exponential_zero(self):
        assert _apply_curve(0.0, "exponential") == 0.0

    def test_exponential_one(self):
        assert _apply_curve(1.0, "exponential") == 1.0

    def test_exponential_midpoint(self):
        result = _apply_curve(0.5, "exponential")
        assert result == pytest.approx(0.125, abs=0.001)

    def test_unknown_curve_defaults_to_linear(self):
        assert _apply_curve(0.7, "unknown") == 0.7


class TestScaleToRange:
    def test_zero_to_min(self):
        assert _scale_to_range(0.0, 200.0, 12000.0) == 200.0

    def test_one_to_max(self):
        assert _scale_to_range(1.0, 200.0, 12000.0) == 12000.0

    def test_midpoint(self):
        assert _scale_to_range(0.5, 0.0, 100.0) == 50.0

    def test_negative_range(self):
        assert _scale_to_range(0.5, -10.0, 10.0) == 0.0


# ---------------------------------------------------------------------------
# OscSendAction (cc_absolute — faders/pots)
# ---------------------------------------------------------------------------
@patch("k2deck.actions.osc_send.OscSender")
class TestOscSendAction:
    def test_ignores_non_cc_events(self, mock_sender_cls):
        """Note events should be ignored."""
        action = OscSendAction({"action": "osc_send", "osc_port": 9000})
        event = FakeMidiEvent(type="note_on", note=36, value=127)
        action.execute(event)
        mock_sender_cls.return_value.send.assert_not_called()

    def test_midi_0_maps_to_min(self, mock_sender_cls):
        """MIDI value 0 → min output value."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendAction(
            {
                "action": "osc_send",
                "osc_port": 9000,
                "osc_param": "cutoff",
                "min": 200,
                "max": 12000,
            }
        )
        event = FakeMidiEvent(type="cc", cc=16, value=0)
        action.execute(event)

        mock_sender.send.assert_called_once()
        args = mock_sender.send.call_args[0]
        assert args[0] == "/pd/param"
        assert args[1] == "cutoff"
        assert args[2] == pytest.approx(200.0, abs=0.1)

    def test_midi_127_maps_to_max(self, mock_sender_cls):
        """MIDI value 127 → max output value."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendAction(
            {
                "action": "osc_send",
                "osc_port": 9000,
                "osc_param": "cutoff",
                "min": 200,
                "max": 12000,
            }
        )
        event = FakeMidiEvent(type="cc", cc=16, value=127)
        action.execute(event)

        args = mock_sender.send.call_args[0]
        assert args[2] == pytest.approx(12000.0, abs=0.1)

    def test_midi_64_linear_midpoint(self, mock_sender_cls):
        """MIDI 64 with linear curve → midpoint of range."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendAction(
            {
                "action": "osc_send",
                "osc_port": 9000,
                "osc_param": "vol",
                "min": 0,
                "max": 100,
                "curve": "linear",
            }
        )
        event = FakeMidiEvent(type="cc", cc=16, value=64)
        action.execute(event)

        args = mock_sender.send.call_args[0]
        assert args[2] == pytest.approx(50.39, abs=0.5)

    def test_exponential_curve(self, mock_sender_cls):
        """MIDI 64 with exponential curve → ~12.5% of range."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendAction(
            {
                "action": "osc_send",
                "osc_port": 9000,
                "osc_param": "cutoff",
                "min": 0,
                "max": 100,
                "curve": "exponential",
            }
        )
        event = FakeMidiEvent(type="cc", cc=16, value=64)
        action.execute(event)

        args = mock_sender.send.call_args[0]
        # (64/127)^3 ≈ 0.128 → 12.8
        assert args[2] == pytest.approx(12.8, abs=1.0)

    def test_sends_without_param_when_empty(self, mock_sender_cls):
        """When osc_param is empty, send only the value."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendAction(
            {
                "action": "osc_send",
                "osc_port": 9000,
            }
        )
        event = FakeMidiEvent(type="cc", cc=16, value=64)
        action.execute(event)

        args = mock_sender.send.call_args[0]
        assert args[0] == "/pd/param"
        assert len(args) == 2  # address + value only

    def test_default_config_values(self, mock_sender_cls):
        """Verify defaults: host=127.0.0.1, port=9000, min=0, max=1."""
        action = OscSendAction({"action": "osc_send"})
        assert action._host == "127.0.0.1"
        assert action._port == 9000
        assert action._address == "/pd/param"
        assert action._min == 0.0
        assert action._max == 1.0
        assert action._curve == "linear"

    def test_custom_host_port_address(self, mock_sender_cls):
        """Custom host, port, address are used."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendAction(
            {
                "action": "osc_send",
                "osc_host": "192.168.1.10",
                "osc_port": 8000,
                "osc_address": "/custom/path",
                "osc_param": "test",
            }
        )
        event = FakeMidiEvent(type="cc", cc=16, value=64)
        action.execute(event)

        mock_sender_cls.assert_called_with("192.168.1.10", 8000)
        args = mock_sender.send.call_args[0]
        assert args[0] == "/custom/path"

    def test_error_handling(self, mock_sender_cls):
        """OscSender.send raising doesn't crash the action."""
        mock_sender = MagicMock()
        mock_sender.send.side_effect = OSError("fail")
        mock_sender_cls.return_value = mock_sender

        action = OscSendAction(
            {
                "action": "osc_send",
                "osc_port": 9000,
                "osc_param": "test",
            }
        )
        event = FakeMidiEvent(type="cc", cc=16, value=64)

        # Should not raise
        action.execute(event)


# ---------------------------------------------------------------------------
# OscSendRelativeAction (cc_relative — encoders)
# ---------------------------------------------------------------------------
@patch("k2deck.actions.osc_send.OscSender")
class TestOscSendRelativeAction:
    def setup_method(self):
        OscSendRelativeAction.reset_accumulators()

    def test_ignores_non_cc_events(self, mock_sender_cls):
        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "detune",
            }
        )
        event = FakeMidiEvent(type="note_on", note=36, value=127)
        action.execute(event)
        mock_sender_cls.return_value.send.assert_not_called()

    def test_cw_increments(self, mock_sender_cls):
        """CW rotation (value=1) increments by step."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "detune",
                "min": 0,
                "max": 100,
                "step": 1,
                "initial": 50,
            }
        )
        event = FakeMidiEvent(type="cc", cc=0, value=1)
        action.execute(event)

        args = mock_sender.send.call_args[0]
        assert args[2] == pytest.approx(51.0)

    def test_ccw_decrements(self, mock_sender_cls):
        """CCW rotation (value=127 → -1) decrements by step."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "detune",
                "min": 0,
                "max": 100,
                "step": 1,
                "initial": 50,
            }
        )
        event = FakeMidiEvent(type="cc", cc=0, value=127)
        action.execute(event)

        args = mock_sender.send.call_args[0]
        assert args[2] == pytest.approx(49.0)

    def test_fast_cw_multiple_steps(self, mock_sender_cls):
        """Fast CW (value=3) increments by 3 * step."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "rate",
                "min": 0,
                "max": 100,
                "step": 2,
                "initial": 50,
            }
        )
        event = FakeMidiEvent(type="cc", cc=0, value=3)
        action.execute(event)

        args = mock_sender.send.call_args[0]
        # 50 + 3*2 = 56
        assert args[2] == pytest.approx(56.0)

    def test_clips_to_max(self, mock_sender_cls):
        """Accumulator doesn't exceed max."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "clip_max",
                "min": 0,
                "max": 10,
                "step": 1,
                "initial": 9,
            }
        )
        event = FakeMidiEvent(type="cc", cc=0, value=5)
        action.execute(event)

        args = mock_sender.send.call_args[0]
        assert args[2] == pytest.approx(10.0)

    def test_clips_to_min(self, mock_sender_cls):
        """Accumulator doesn't go below min."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "clip_min",
                "min": 0,
                "max": 100,
                "step": 1,
                "initial": 2,
            }
        )
        event = FakeMidiEvent(type="cc", cc=0, value=126)  # -2
        action.execute(event)

        args = mock_sender.send.call_args[0]
        assert args[2] == pytest.approx(0.0)

    def test_default_initial_is_midpoint(self, mock_sender_cls):
        """Default initial value is (min + max) / 2."""
        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "mid",
                "min": 10,
                "max": 90,
            }
        )
        assert action._initial == pytest.approx(50.0)

    def test_custom_initial_value(self, mock_sender_cls):
        """Custom initial value is used."""
        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "custom",
                "min": 0,
                "max": 100,
                "initial": 25,
            }
        )
        assert action._initial == pytest.approx(25.0)

    def test_value_0_ignored(self, mock_sender_cls):
        """CC value 0 does nothing."""
        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "ign0",
            }
        )
        event = FakeMidiEvent(type="cc", cc=0, value=0)
        action.execute(event)
        mock_sender_cls.return_value.send.assert_not_called()

    def test_value_64_ignored(self, mock_sender_cls):
        """CC value 64 does nothing."""
        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "ign64",
            }
        )
        event = FakeMidiEvent(type="cc", cc=0, value=64)
        action.execute(event)
        mock_sender_cls.return_value.send.assert_not_called()

    def test_state_persists_across_instances(self, mock_sender_cls):
        """Class-level accumulator works across new Action instances."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        config = {
            "action": "osc_send_relative",
            "osc_param": "persist",
            "min": 0,
            "max": 100,
            "step": 1,
            "initial": 50,
        }

        # First instance: CW +1
        action1 = OscSendRelativeAction(config)
        action1.execute(FakeMidiEvent(type="cc", cc=0, value=1))

        # Second instance (same param): CW +1 again
        action2 = OscSendRelativeAction(config)
        action2.execute(FakeMidiEvent(type="cc", cc=0, value=1))

        # Should be 52 (50 + 1 + 1), not 51
        args = mock_sender.send.call_args[0]
        assert args[2] == pytest.approx(52.0)

    def test_different_params_independent(self, mock_sender_cls):
        """Different osc_param keys have independent accumulators."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action_a = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "param_a",
                "min": 0,
                "max": 100,
                "step": 10,
                "initial": 50,
            }
        )
        action_b = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "param_b",
                "min": 0,
                "max": 100,
                "step": 1,
                "initial": 0,
            }
        )

        action_a.execute(FakeMidiEvent(type="cc", cc=0, value=1))
        action_b.execute(FakeMidiEvent(type="cc", cc=1, value=1))

        calls = mock_sender.send.call_args_list
        # param_a: 50 + 10 = 60
        assert calls[0][0][2] == pytest.approx(60.0)
        # param_b: 0 + 1 = 1
        assert calls[1][0][2] == pytest.approx(1.0)

    def test_reset_accumulators(self, mock_sender_cls):
        """reset_accumulators clears all state."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        config = {
            "action": "osc_send_relative",
            "osc_param": "reset_test",
            "min": 0,
            "max": 100,
            "step": 1,
            "initial": 50,
        }

        action = OscSendRelativeAction(config)
        action.execute(FakeMidiEvent(type="cc", cc=0, value=1))  # 51

        OscSendRelativeAction.reset_accumulators()

        action2 = OscSendRelativeAction(config)
        action2.execute(FakeMidiEvent(type="cc", cc=0, value=1))  # Back to 51, not 52

        args = mock_sender.send.call_args[0]
        assert args[2] == pytest.approx(51.0)

    def test_sends_without_param(self, mock_sender_cls):
        """When osc_param is empty, send value only."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "min": 0,
                "max": 100,
                "step": 1,
                "initial": 50,
            }
        )
        event = FakeMidiEvent(type="cc", cc=0, value=1)
        action.execute(event)

        args = mock_sender.send.call_args[0]
        assert len(args) == 2  # address + value only

    def test_error_handling(self, mock_sender_cls):
        """OscSender errors don't crash the action."""
        mock_sender = MagicMock()
        mock_sender.send.side_effect = OSError("fail")
        mock_sender_cls.return_value = mock_sender

        action = OscSendRelativeAction(
            {
                "action": "osc_send_relative",
                "osc_param": "err",
                "min": 0,
                "max": 100,
                "initial": 50,
            }
        )
        # Should not raise
        action.execute(FakeMidiEvent(type="cc", cc=0, value=1))


# ---------------------------------------------------------------------------
# OscSendTriggerAction (note_on — buttons)
# ---------------------------------------------------------------------------
@patch("k2deck.actions.osc_send.OscSender")
class TestOscSendTriggerAction:
    def setup_method(self):
        OscSendTriggerAction.reset_toggle_states()

    def test_ignores_cc_events(self, mock_sender_cls):
        action = OscSendTriggerAction(
            {
                "action": "osc_send_trigger",
                "osc_param": "mute",
            }
        )
        event = FakeMidiEvent(type="cc", cc=16, value=64)
        action.execute(event)
        mock_sender_cls.return_value.send.assert_not_called()

    def test_ignores_zero_velocity(self, mock_sender_cls):
        """Note on with velocity 0 (release) is ignored."""
        action = OscSendTriggerAction(
            {
                "action": "osc_send_trigger",
                "osc_param": "mute",
            }
        )
        event = FakeMidiEvent(type="note_on", note=48, value=0)
        action.execute(event)
        mock_sender_cls.return_value.send.assert_not_called()

    def test_bang_mode_sends_one(self, mock_sender_cls):
        """Bang mode always sends 1.0."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendTriggerAction(
            {
                "action": "osc_send_trigger",
                "osc_param": "bang_test",
                "mode": "bang",
            }
        )

        # Press twice
        for _ in range(2):
            action.execute(FakeMidiEvent(type="note_on", note=48, value=127))

        # Both sends should be 1.0
        for call in mock_sender.send.call_args_list:
            assert call[0][2] == pytest.approx(1.0)

    def test_toggle_mode_alternates(self, mock_sender_cls):
        """Toggle mode alternates between 1.0 and 0.0."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendTriggerAction(
            {
                "action": "osc_send_trigger",
                "osc_param": "toggle_test",
                "mode": "toggle",
            }
        )

        press = FakeMidiEvent(type="note_on", note=48, value=127)
        action.execute(press)  # 1st: on
        action.execute(press)  # 2nd: off
        action.execute(press)  # 3rd: on

        calls = mock_sender.send.call_args_list
        assert calls[0][0][2] == pytest.approx(1.0)
        assert calls[1][0][2] == pytest.approx(0.0)
        assert calls[2][0][2] == pytest.approx(1.0)

    def test_default_mode_is_bang(self, mock_sender_cls):
        """Default mode is bang."""
        action = OscSendTriggerAction(
            {
                "action": "osc_send_trigger",
                "osc_param": "default",
            }
        )
        assert action._mode == "bang"

    def test_sends_with_param_name(self, mock_sender_cls):
        """Sends address + param + value."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendTriggerAction(
            {
                "action": "osc_send_trigger",
                "osc_address": "/pd/param",
                "osc_param": "mixer__p__mute",
            }
        )
        action.execute(FakeMidiEvent(type="note_on", note=48, value=127))

        args = mock_sender.send.call_args[0]
        assert args[0] == "/pd/param"
        assert args[1] == "mixer__p__mute"
        assert args[2] == pytest.approx(1.0)

    def test_sends_without_param(self, mock_sender_cls):
        """When osc_param is empty, send value only."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action = OscSendTriggerAction(
            {
                "action": "osc_send_trigger",
            }
        )
        action.execute(FakeMidiEvent(type="note_on", note=48, value=127))

        args = mock_sender.send.call_args[0]
        assert len(args) == 2  # address + value

    def test_reset_toggle_states(self, mock_sender_cls):
        """reset_toggle_states clears all state."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        config = {
            "action": "osc_send_trigger",
            "osc_param": "reset_t",
            "mode": "toggle",
        }

        action = OscSendTriggerAction(config)
        action.execute(FakeMidiEvent(type="note_on", note=48, value=127))  # → 1.0

        OscSendTriggerAction.reset_toggle_states()

        action2 = OscSendTriggerAction(config)
        action2.execute(
            FakeMidiEvent(type="note_on", note=48, value=127)
        )  # → 1.0 again (reset)

        calls = mock_sender.send.call_args_list
        assert calls[0][0][2] == pytest.approx(1.0)
        assert calls[1][0][2] == pytest.approx(1.0)

    def test_different_params_independent_toggles(self, mock_sender_cls):
        """Different params have independent toggle states."""
        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        action_a = OscSendTriggerAction(
            {
                "action": "osc_send_trigger",
                "osc_param": "mute_a",
                "mode": "toggle",
            }
        )
        action_b = OscSendTriggerAction(
            {
                "action": "osc_send_trigger",
                "osc_param": "mute_b",
                "mode": "toggle",
            }
        )

        press = FakeMidiEvent(type="note_on", note=48, value=127)
        action_a.execute(press)  # a → 1.0
        action_a.execute(press)  # a → 0.0
        action_b.execute(press)  # b → 1.0 (independent)

        calls = mock_sender.send.call_args_list
        assert calls[0][0][2] == pytest.approx(1.0)  # a on
        assert calls[1][0][2] == pytest.approx(0.0)  # a off
        assert calls[2][0][2] == pytest.approx(1.0)  # b on (not off)

    def test_error_handling(self, mock_sender_cls):
        """OscSender errors don't crash the action."""
        mock_sender = MagicMock()
        mock_sender.send.side_effect = OSError("fail")
        mock_sender_cls.return_value = mock_sender

        action = OscSendTriggerAction(
            {
                "action": "osc_send_trigger",
                "osc_param": "err",
            }
        )
        # Should not raise
        action.execute(FakeMidiEvent(type="note_on", note=48, value=127))
