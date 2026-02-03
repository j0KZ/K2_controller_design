"""K2 Deck - Main application with system tray.

Entry point for the K2 macro controller application.
"""

import argparse
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None
    Image = None
    ImageDraw = None

from k2deck.core.mapping_engine import MappingEngine
from k2deck.core.midi_listener import MidiEvent, MidiListener
from k2deck.core.midi_output import MidiOutput
from k2deck.core.throttle import FaderDebouncer, ThrottleManager
from k2deck.feedback.led_manager import LedManager

logger = logging.getLogger("k2deck")

# Default paths
DEFAULT_CONFIG = Path(__file__).parent / "config" / "default.json"


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    format_str = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt="%H:%M:%S",
    )
    # Reduce noise from libraries
    logging.getLogger("pynput").setLevel(logging.WARNING)
    logging.getLogger("comtypes").setLevel(logging.WARNING)


def create_tray_icon() -> "Image.Image | None":
    """Create a simple tray icon."""
    if Image is None:
        return None

    # Create a simple colored square icon
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Draw a K2-inspired icon (rounded square with "K2" text concept)
    draw.rounded_rectangle(
        [4, 4, size - 4, size - 4],
        radius=8,
        fill=(100, 100, 200),
        outline=(60, 60, 160),
        width=2,
    )
    # Draw inner detail
    draw.rectangle([16, 16, 24, 48], fill=(200, 200, 255))
    draw.rectangle([32, 16, 48, 48], fill=(200, 200, 255))

    return image


class K2DeckApp:
    """Main K2 Deck application."""

    def __init__(
        self,
        config_path: Path,
        device_name: str = "XONE:K2",
        debug: bool = False,
    ):
        """Initialize the application.

        Args:
            config_path: Path to config JSON file.
            device_name: MIDI device name to connect to.
            debug: Enable debug logging.
        """
        self._config_path = config_path
        self._device_name = device_name
        self._debug = debug
        self._running = False

        # Components
        self._mapping_engine: MappingEngine | None = None
        self._midi_listener: MidiListener | None = None
        self._midi_output: MidiOutput | None = None
        self._led_manager: LedManager | None = None
        self._throttle = ThrottleManager(max_hz=30)
        self._fader_debouncer = FaderDebouncer(delay_ms=50)
        self._executor = ThreadPoolExecutor(max_workers=4)

        # State
        self._status = "Disconnected"
        self._tray: "pystray.Icon | None" = None

    def _load_config(self) -> bool:
        """Load configuration."""
        try:
            self._mapping_engine = MappingEngine(self._config_path)
            logger.info("Config loaded: %s", self._config_path)
            return True
        except Exception as e:
            logger.error("Failed to load config: %s", e)
            return False

    def _setup_midi(self) -> bool:
        """Initialize MIDI input and output."""
        if not self._mapping_engine:
            return False

        channel = self._mapping_engine.midi_channel

        # MIDI Output (for LEDs)
        self._midi_output = MidiOutput(self._device_name, channel)
        if not self._midi_output.open():
            logger.warning("Could not open MIDI output - LEDs will not work")

        # LED Manager
        self._led_manager = LedManager(
            self._midi_output,
            self._mapping_engine.led_color_offsets,
        )

        # MIDI Listener
        self._midi_listener = MidiListener(
            self._device_name,
            self._on_midi_event,
        )

        return True

    def _on_midi_event(self, event: MidiEvent) -> None:
        """Handle incoming MIDI event."""
        # For CC events, check if this is a fader (cc_absolute)
        if event.type == "cc":
            mappings = self._mapping_engine._mappings
            cc_absolute = mappings.get("cc_absolute", {})
            is_fader = str(event.cc) in cc_absolute

            if is_fader:
                # Always debounce faders to ensure final value is applied
                self._fader_debouncer.debounce(
                    f"cc_{event.cc}",
                    event.value,
                    lambda val, cc=event.cc, ch=event.channel: self._apply_fader_value(cc, ch, val),
                )

                # ALWAYS let extreme values (0 and 127) through immediately
                # This ensures min/max volume is applied even when moving fast
                is_extreme = event.value in (0, 127)
                if is_extreme:
                    pass  # Skip throttle check, always process
                elif not self._throttle.should_process(f"cc_{event.cc}"):
                    return
            else:
                # Non-fader CC (encoders, etc.) - apply normal throttle
                if not self._throttle.should_process(f"cc_{event.cc}"):
                    return

        # Resolve to action
        action, mapping_config = self._mapping_engine.resolve(event)

        if action is None:
            if self._debug:
                logger.debug(
                    "Unmapped: %s ch:%d %s=%s val=%d",
                    event.type,
                    event.channel,
                    "note" if event.note else "cc",
                    event.note if event.note else event.cc,
                    event.value,
                )
            return

        logger.info("Executing: %s", action)

        # Execute action in thread pool
        self._executor.submit(self._execute_action, action, event, mapping_config)

    def _apply_fader_value(self, cc: int, channel: int, value: int) -> None:
        """Apply debounced fader value.

        Called by FaderDebouncer after movement stops to ensure final value.
        """
        # Create a synthetic event for the final value
        final_event = MidiEvent(
            type="cc",
            channel=channel,
            note=None,
            cc=cc,
            value=value,
        )

        # Resolve and execute
        action, mapping_config = self._mapping_engine.resolve(final_event)
        if action:
            logger.info("Applying final fader value: cc_%d = %d", cc, value)
            self._executor.submit(self._execute_action, action, final_event, mapping_config)

    def _execute_action(
        self,
        action,
        event: MidiEvent,
        mapping_config: dict | None,
    ) -> None:
        """Execute action and handle LED feedback."""
        try:
            action.execute(event)
        except Exception as e:
            logger.error("Action execution error: %s", e)

        # Handle LED feedback
        if mapping_config and self._led_manager and event.type == "note_on":
            led_config = mapping_config.get("led")
            if led_config and event.note is not None:
                self._handle_led_feedback(event.note, led_config)

    def _handle_led_feedback(self, note: int, led_config: dict) -> None:
        """Handle LED feedback for a button press."""
        mode = led_config.get("mode", "static")
        color = led_config.get("color", "green")
        off_color = led_config.get("off_color", "off")

        if mode == "toggle":
            self._led_manager.toggle_led(note, color, off_color)
        elif mode == "flash":
            times = led_config.get("flash_count", 3)
            self._led_manager.flash_led(note, color, times)
        else:
            self._led_manager.set_led(note, color)

    def _setup_defaults(self) -> None:
        """Set up default LED states."""
        if not self._mapping_engine or not self._led_manager:
            return

        led_defaults = self._mapping_engine.config.get("led_defaults", {})

        # Turn all off first
        if led_defaults.get("on_connect") == "all_off":
            self._led_manager.all_off()

        # Startup animation
        if led_defaults.get("startup_animation"):
            notes = self._mapping_engine.get_all_button_notes()
            if notes:
                self._led_manager.startup_animation(notes[:12])

        # Set default states
        on_start = led_defaults.get("on_start", [])
        self._led_manager.restore_defaults(on_start)

    def _create_tray_menu(self) -> "pystray.Menu":
        """Create system tray menu."""
        return pystray.Menu(
            pystray.MenuItem(
                lambda text: f"Status: {self._status}",
                lambda: None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Reload Config", self._on_reload_config),
            pystray.MenuItem(
                "Debug Mode",
                self._on_toggle_debug,
                checked=lambda item: self._debug,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit),
        )

    def _on_reload_config(self) -> None:
        """Handle config reload request."""
        logger.info("Reloading config...")
        try:
            self._mapping_engine.load_config(self._config_path)
            self._setup_defaults()
            logger.info("Config reloaded successfully")
        except Exception as e:
            logger.error("Failed to reload config: %s", e)

    def _on_toggle_debug(self) -> None:
        """Toggle debug mode."""
        self._debug = not self._debug
        level = logging.DEBUG if self._debug else logging.INFO
        logging.getLogger("k2deck").setLevel(level)
        logger.info("Debug mode: %s", "ON" if self._debug else "OFF")

    def _on_quit(self) -> None:
        """Handle quit request."""
        logger.info("Quitting...")
        self._running = False
        if self._tray:
            self._tray.stop()

    def _update_status(self, status: str) -> None:
        """Update connection status."""
        self._status = status
        if self._tray:
            self._tray.update_menu()

    def _connection_monitor(self) -> None:
        """Monitor connection status in background."""
        while self._running:
            if self._midi_listener:
                if self._midi_listener.is_connected:
                    self._update_status("Connected")
                else:
                    self._update_status("Disconnected - Reconnecting...")
            threading.Event().wait(2.0)

    def run(self) -> int:
        """Run the application.

        Returns:
            Exit code (0 for success).
        """
        # Load config
        if not self._load_config():
            return 1

        # Setup MIDI
        if not self._setup_midi():
            return 1

        self._running = True

        # Start MIDI listener
        self._midi_listener.start()

        # Setup default LED states
        self._setup_defaults()

        # Start connection monitor
        monitor_thread = threading.Thread(
            target=self._connection_monitor,
            daemon=True,
        )
        monitor_thread.start()

        # Run with or without tray
        if pystray is not None:
            icon = create_tray_icon()
            self._tray = pystray.Icon(
                "K2 Deck",
                icon,
                "K2 Deck",
                menu=self._create_tray_menu(),
            )
            logger.info("Starting system tray...")
            self._tray.run()
        else:
            logger.warning("pystray not available - running without tray")
            print("K2 Deck running. Press Ctrl+C to quit.")
            try:
                while self._running:
                    threading.Event().wait(1.0)
            except KeyboardInterrupt:
                pass

        # Cleanup
        self._running = False
        self._fader_debouncer.cancel()  # Cancel pending debounced callbacks
        if self._midi_listener:
            self._midi_listener.stop()
        if self._led_manager:
            self._led_manager.all_off()
        if self._midi_output:
            self._midi_output.close()
        self._executor.shutdown(wait=False)

        logger.info("K2 Deck stopped")
        return 0


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="K2 Deck - Xone:K2 System Controller"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to config JSON file",
    )
    parser.add_argument(
        "--device",
        "-d",
        default="XONE:K2",
        help="MIDI device name (partial match)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--learn",
        action="store_true",
        help="Run MIDI learn tool instead of main app",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.debug)

    # MIDI learn mode
    if args.learn:
        from k2deck.tools.midi_learn import main as learn_main
        learn_main()
        return

    # Run main app
    app = K2DeckApp(
        config_path=args.config,
        device_name=args.device,
        debug=args.debug,
    )
    sys.exit(app.run())


if __name__ == "__main__":
    main()
