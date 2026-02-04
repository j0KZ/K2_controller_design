"""Action Factory - Create action instances from config dicts.

Used by ConditionalAction and other actions that need to instantiate
nested actions dynamically.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from k2deck.actions.base import Action

logger = logging.getLogger(__name__)

# Maximum recursion depth for nested actions (e.g., conditional inside conditional)
MAX_ACTION_DEPTH = 3


class ActionCreationError(Exception):
    """Raised when action creation fails."""

    pass


def create_action(config: dict, depth: int = 0) -> "Action | None":
    """Create an action instance from a config dict.

    Args:
        config: Action configuration dict. Must contain "action" key.
        depth: Current recursion depth (for limiting nested conditionals).

    Returns:
        Action instance or None if creation fails.

    Raises:
        ActionCreationError: If depth limit exceeded or invalid config.
    """
    if depth > MAX_ACTION_DEPTH:
        raise ActionCreationError(
            f"Maximum action depth ({MAX_ACTION_DEPTH}) exceeded. "
            "Check for circular conditional references."
        )

    if not isinstance(config, dict):
        logger.warning("Action config must be a dict, got: %s", type(config).__name__)
        return None

    action_type = config.get("action")
    if not action_type:
        logger.warning("Action config missing 'action' key")
        return None

    # Lazy import to avoid circular dependency
    from k2deck.core.mapping_engine import ACTION_TYPES

    if action_type not in ACTION_TYPES:
        logger.warning("Unknown action type: %s", action_type)
        return None

    action_class = ACTION_TYPES[action_type]

    # Inject depth for actions that support it (like ConditionalAction)
    config_with_depth = config.copy()
    config_with_depth["_depth"] = depth

    try:
        return action_class(config_with_depth)
    except Exception as e:
        logger.error("Failed to create action '%s': %s", action_type, e)
        return None


def create_actions(configs: list[dict], depth: int = 0) -> list["Action"]:
    """Create multiple action instances from a list of configs.

    Args:
        configs: List of action configuration dicts.
        depth: Current recursion depth.

    Returns:
        List of successfully created Action instances.
    """
    actions = []
    for config in configs:
        action = create_action(config, depth)
        if action:
            actions.append(action)
    return actions
