"""Profile Auto-Switcher - Automatically switch profiles based on active app.

This is an OPTIONAL feature that is disabled by default.
Only activates when the user explicitly configures profile_auto_switch rules.
"""

import logging
import threading
from collections.abc import Callable

from k2deck.core.context import get_foreground_app

logger = logging.getLogger(__name__)


class ProfileAutoSwitcher:
    """Watch foreground app and trigger profile switches.

    Disabled by default. Only runs when:
    1. enabled=True in config
    2. At least one rule is configured

    Config example:
    {
        "profile_auto_switch": {
            "enabled": true,
            "check_interval": 0.5,
            "rules": [
                { "app": "obs64.exe", "profile": "streaming" },
                { "app": "Adobe Premiere", "profile": "video_editing" }
            ],
            "default_profile": "default"
        }
    }
    """

    def __init__(
        self,
        on_profile_switch: Callable[[str], None],
        check_interval: float = 0.5,
    ):
        """Initialize profile auto-switcher.

        Args:
            on_profile_switch: Callback when profile should change.
                               Takes profile name as argument.
            check_interval: Seconds between foreground app checks.
        """
        self._on_switch = on_profile_switch
        self._check_interval = check_interval
        self._rules: list[dict] = []
        self._default_profile: str = "default"
        self._current_profile: str | None = None
        self._enabled = False
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def configure(self, config: dict) -> None:
        """Configure auto-switch from config dict.

        Args:
            config: The profile_auto_switch section of the config.
        """
        if not config:
            self._enabled = False
            return

        self._enabled = config.get("enabled", False)
        self._rules = config.get("rules", [])
        self._default_profile = config.get("default_profile", "default")
        self._check_interval = config.get("check_interval", 0.5)

        if self._enabled and not self._rules:
            logger.warning("Profile auto-switch enabled but no rules configured")
            self._enabled = False

        if self._enabled:
            logger.info(
                "Profile auto-switch configured: %d rules, default=%s",
                len(self._rules),
                self._default_profile,
            )

    @property
    def enabled(self) -> bool:
        """Check if auto-switch is enabled."""
        return self._enabled

    @property
    def current_profile(self) -> str | None:
        """Get currently active profile name."""
        return self._current_profile

    def start(self) -> None:
        """Start watching foreground app.

        Does nothing if not enabled or already running.
        """
        if not self._enabled:
            logger.debug("Profile auto-switch not enabled, not starting")
            return

        if self._running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._watch_loop,
            name="ProfileAutoSwitcher",
            daemon=True,
        )
        self._running = True
        self._thread.start()
        logger.info("Profile auto-switch started")

    def stop(self) -> None:
        """Stop watching foreground app."""
        if not self._running:
            return

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._running = False
        self._thread = None
        logger.info("Profile auto-switch stopped")

    def _watch_loop(self) -> None:
        """Background loop checking foreground app."""
        while not self._stop_event.is_set():
            try:
                self._check_and_switch()
            except Exception as e:
                logger.error("Profile auto-switch error: %s", e)

            self._stop_event.wait(self._check_interval)

    def _check_and_switch(self) -> None:
        """Check foreground app and switch profile if needed."""
        app = get_foreground_app()
        if not app:
            return

        app_name = app.name.lower()
        target_profile = self._default_profile

        # Check rules in order, first match wins
        for rule in self._rules:
            rule_app = rule.get("app", "").lower()
            if rule_app and rule_app in app_name:
                target_profile = rule.get("profile", self._default_profile)
                break

        # Only switch if different
        if target_profile != self._current_profile:
            logger.info(
                "Auto-switching profile: %s -> %s (app: %s)",
                self._current_profile or "(none)",
                target_profile,
                app.name,
            )
            self._current_profile = target_profile
            try:
                self._on_switch(target_profile)
            except Exception as e:
                logger.error("Profile switch callback failed: %s", e)

    def force_check(self) -> None:
        """Force an immediate check (useful after config reload)."""
        if self._enabled:
            self._check_and_switch()

    def set_profile(self, profile: str) -> None:
        """Manually set current profile (for sync with manual switches)."""
        self._current_profile = profile
