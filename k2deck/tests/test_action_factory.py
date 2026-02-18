"""Tests for action_factory.py - Action creation from config dicts."""

from unittest.mock import MagicMock, patch

import pytest

from k2deck.core.action_factory import (
    MAX_ACTION_DEPTH,
    ActionCreationError,
    create_action,
    create_actions,
)


class TestCreateAction:
    """Test create_action function."""

    def test_returns_none_for_non_dict_config(self):
        """Should return None for non-dict input."""
        assert create_action("not_a_dict") is None
        assert create_action(42) is None
        assert create_action(None) is None
        assert create_action([]) is None

    def test_returns_none_for_missing_action_key(self):
        """Should return None if 'action' key is missing."""
        assert create_action({}) is None
        assert create_action({"name": "test"}) is None

    def test_returns_none_for_empty_action(self):
        """Should return None if action value is empty/falsy."""
        assert create_action({"action": ""}) is None
        assert create_action({"action": None}) is None

    def test_returns_none_for_unknown_action_type(self):
        """Should return None for unregistered action type."""
        # ACTION_TYPES is imported lazily inside the function from mapping_engine
        with patch("k2deck.core.mapping_engine.ACTION_TYPES", {}):
            assert create_action({"action": "nonexistent"}) is None

    def test_raises_on_depth_exceeded(self):
        """Should raise ActionCreationError when depth limit exceeded."""
        with pytest.raises(ActionCreationError, match="Maximum action depth"):
            create_action({"action": "hotkey"}, depth=MAX_ACTION_DEPTH + 1)

    def test_creates_valid_action(self):
        """Should create action instance for valid config."""
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        with patch(
            "k2deck.core.mapping_engine.ACTION_TYPES",
            {"hotkey": mock_class},
        ):
            result = create_action({"action": "hotkey", "keys": ["f1"]})

        assert result is mock_instance
        call_args = mock_class.call_args[0][0]
        assert call_args["_depth"] == 0
        assert call_args["action"] == "hotkey"

    def test_injects_depth_into_config(self):
        """Should pass depth parameter to action class."""
        mock_class = MagicMock()

        with patch(
            "k2deck.core.mapping_engine.ACTION_TYPES",
            {"hotkey": mock_class},
        ):
            create_action({"action": "hotkey"}, depth=2)

        call_args = mock_class.call_args[0][0]
        assert call_args["_depth"] == 2

    def test_returns_none_on_action_init_exception(self):
        """Should return None if action constructor raises."""
        mock_class = MagicMock(side_effect=ValueError("bad config"))

        with patch(
            "k2deck.core.mapping_engine.ACTION_TYPES",
            {"hotkey": mock_class},
        ):
            result = create_action({"action": "hotkey"})

        assert result is None


class TestCreateActions:
    """Test create_actions function."""

    def test_creates_multiple_actions(self):
        """Should create list of actions from configs."""
        mock_class = MagicMock()

        with patch(
            "k2deck.core.mapping_engine.ACTION_TYPES",
            {"hotkey": mock_class},
        ):
            configs = [
                {"action": "hotkey", "keys": ["f1"]},
                {"action": "hotkey", "keys": ["f2"]},
            ]
            result = create_actions(configs)

        assert len(result) == 2

    def test_skips_invalid_configs(self):
        """Should skip configs that fail to create."""
        mock_class = MagicMock()

        with patch(
            "k2deck.core.mapping_engine.ACTION_TYPES",
            {"hotkey": mock_class},
        ):
            configs = [
                {"action": "hotkey"},
                {"action": "nonexistent"},  # unknown
                "not_a_dict",  # invalid
                {"action": "hotkey"},
            ]
            result = create_actions(configs)

        assert len(result) == 2

    def test_empty_list_returns_empty(self):
        """Should return empty list for empty input."""
        result = create_actions([])
        assert result == []

    def test_passes_depth_through(self):
        """Should pass depth to each create_action call."""
        mock_class = MagicMock()

        with patch(
            "k2deck.core.mapping_engine.ACTION_TYPES",
            {"hotkey": mock_class},
        ):
            create_actions([{"action": "hotkey"}], depth=2)

        call_args = mock_class.call_args[0][0]
        assert call_args["_depth"] == 2
