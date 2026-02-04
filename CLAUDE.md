# K2 Deck — Xone:K2 System Controller

## Project Overview

Python app that turns an Allen & Heath Xone:K2 MIDI controller into a system-wide macro controller for daily workflow: Spotify, Discord, VS Code, and Brave.

**Architecture doc:** See `docs/k2-controller-design.md` for full design, hardware reference, column layout, and architecture diagrams.

## Tech Stack

- **Python 3.12+** (Windows target)
- **MIDI:** `mido` + `python-rtmidi`
- **Keyboard simulation:** `pynput`
- **Per-app volume:** `pycaw` + `comtypes`
- **Spotify API:** `spotipy`
- **Window management:** `pywin32`
- **System tray:** `pystray` + `Pillow`
- **Config hot-reload:** `watchdog`
- **Logging:** stdlib `logging`

## Project Structure

```
k2deck/
├── __main__.py            # `python -m k2deck` entry
├── k2deck.py              # App init + system tray
├── config/
│   └── default.json        # Default mapping profile
├── core/
│   ├── __init__.py
│   ├── midi_listener.py    # MIDI input + auto-reconnect
│   ├── midi_output.py      # MIDI output to K2 (LEDs)
│   ├── mapping_engine.py   # Resolves MIDI event → action
│   ├── profile_manager.py  # Load/switch profiles, hot-reload
│   └── throttle.py         # Rate limiter for CC messages
├── actions/
│   ├── __init__.py
│   ├── base.py             # Action ABC
│   ├── hotkey.py           # pynput keystroke simulation
│   ├── mouse_scroll.py     # pynput mouse scroll simulation
│   ├── volume.py           # pycaw per-app volume
│   ├── spotify.py          # spotipy API actions [Phase 2]
│   ├── window.py           # pywin32 focus/launch [Phase 2]
│   └── system.py           # Lock, screenshot, etc.
├── feedback/
│   ├── __init__.py
│   ├── led_manager.py      # LED state machine
│   └── led_colors.py       # Color offset constants (NOT velocity!)
├── tools/
│   ├── __init__.py
│   ├── midi_learn.py       # CLI: discover controls + LED test
│   └── midi_monitor.py     # CLI: raw MIDI traffic monitor
├── tests/
│   ├── __init__.py
│   ├── test_mapping_engine.py
│   ├── test_hotkey_action.py
│   ├── test_volume_action.py
│   ├── test_led_manager.py
│   └── test_throttle.py
├── requirements.txt
└── README.md
```

## Conventions

### Code Style
- Python 3.12+ features OK (type hints, match/case, f-strings)
- Type hints on all function signatures
- Docstrings: Google style, brief
- Max file length: 300 LOC. If exceeding, extract to submodules.
- Imports: stdlib → third-party → local, separated by blank line

### Error Handling
- All MIDI operations wrapped in try/except — MIDI ports can disconnect at any time
- All external API calls (Spotify, pycaw) must have try/except with logging
- Never crash on a single failed action — log and continue listening
- On MIDI port loss: attempt reconnect every 5 seconds, notify via tray

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Config keys: `snake_case`

### Config
- JSON format, no YAML/TOML
- All config in `config/` directory
- Profile files: `{profile_name}.json`
- Validate config on load — fail fast with clear error messages
- Use `json.loads()` with schema validation, not blind key access

### Logging
- Use `logging` module, never `print()`
- Levels: DEBUG for MIDI messages, INFO for actions, WARNING for recoverable errors, ERROR for failures
- Format: `[%(asctime)s] %(levelname)s %(name)s: %(message)s`
- MIDI message logging must be toggleable (high volume)

### Testing
- Use `pytest`
- Mock MIDI devices for unit tests (no hardware dependency)
- Test config loading with valid/invalid JSON
- Test mapping resolution independently
- Test action execution with mocked system calls

#### ⚠️ DANGEROUS FUNCTION TESTS — MANDATORY RULES

When testing functions that perform dangerous system operations (sleep, shutdown, restart, hibernate, delete, format, etc.):

1. **ALWAYS run `pytest --collect-only` FIRST** on new test files to verify collection without execution
2. **Use `patch.dict()` for class-level dicts** — If a class stores functions in a dict at import time (like `COMMANDS = {"sleep": sleep_computer}`), `@patch` decorators WON'T prevent execution. The dict captures the real function reference at import. Use:
   ```python
   with patch.dict(SystemAction.COMMANDS, {"sleep": MagicMock()}):
       action.execute(event)
   ```
3. **Mark direct function tests with `@pytest.mark.skip`** — Tests that call dangerous functions directly (even with mocks) should be skipped by default:
   ```python
   @pytest.mark.skip(reason="Dangerous: could actually sleep the PC if mock fails")
   @patch('k2deck.actions.system.ctypes')
   def test_sleep_computer(self, mock_ctypes):
       ...
   ```
4. **Ask for confirmation** before running tests involving: `ctypes.windll`, `subprocess.run` with shutdown/restart, file deletion, or any system power management

**WHY:** A failed mock = real execution. A test once put the user's PC to sleep because `@patch('module.ctypes')` didn't intercept the already-captured function in `COMMANDS` dict.

## Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python -m k2deck

# Run MIDI learn tool
python -m k2deck.tools.midi_learn

# Run MIDI monitor
python -m k2deck.tools.midi_monitor

# Run tests
pytest

# Run with debug logging
python -m k2deck --debug
```

## Implementation Phases

Build in this order. Each phase must be fully functional before moving to next.

### Phase 1: MVP (build this first)
1. `tools/midi_learn.py` — detect K2, print all MIDI messages
2. `core/midi_listener.py` — async MIDI listener with reconnect
3. `core/mapping_engine.py` — JSON config → action resolution
4. `actions/hotkey.py` — pynput keystroke execution
5. `actions/volume.py` — pycaw per-app volume control
6. `feedback/led_manager.py` — basic LED on/off/color
7. `core/midi_output.py` — send LED commands to K2
8. `config/default.json` — working default profile
9. `k2deck.py` — entry point with system tray

### Phase 2: Rich integrations
10. `actions/spotify.py` — spotipy OAuth + API actions
11. `actions/window.py` — pywin32 focus/launch
12. `core/profile_manager.py` — multi-profile + hot-reload
13. Encoder acceleration (fast turn = bigger step)

### Phase 3: Polish
14. Context-aware mode (detect active window)
15. Web UI for visual mapping editor
16. Windows auto-start installer
17. README with setup guide

## Hardware Notes

- K2 default MIDI channel: 15 (0-indexed: 14). User's K2 is on channel 16 (0-indexed: 15).
- **CRITICAL — LED colors use NOTE OFFSET, not velocity:**
  - Red = base_note + 0
  - Amber = base_note + 36
  - Green = base_note + 72
  - Example: button at note 36 → Red=36, Amber=72, Green=108
  - New color overwrites active one. No need to turn off first.
  - Verified in Mixxx source: `XoneK2.color = { red: 0, amber: 36, green: 72 }`
- **Latching layers MUST be OFF** for free LED control. If ON, layer dictates color.
- K2 encoders send CC in two's complement: value 1 = CW, value 127 = CCW
- K2 faders/knobs send CC values 0-127 (absolute)
- K2 buttons send Note On (press, vel 127) / Note Off (release, vel 0)
- Exact note/CC numbers vary by config — `midi_learn.py` discovers them
- Only ONE app can hold the MIDI port at a time. Check for exclusive access.
- If K2 not connected at startup: enter standby mode, retry every 5s.
- Faders can send 60+ messages/sec — throttle CC processing to ~30Hz max.

## Critical Constraints

1. **Single MIDI port access.** If another app has the K2 port open, K2 Deck cannot use it. Detect and warn.
2. **Windows only** for now. pycaw and pywin32 are Windows-specific.
3. **No GUI window.** System tray only. The app must be invisible when working.
4. **Never block the MIDI listener.** All actions execute in ThreadPoolExecutor(max_workers=4).
5. **Config is king.** Zero hardcoded MIDI mappings. Everything comes from JSON.
6. **Graceful degradation.** If Spotify API fails → fall back to media keys. If pycaw fails on an app → log and skip. If K2 disconnects → retry loop.
7. **Throttle CC messages.** Faders send 60+ msgs/sec. Rate-limit pycaw calls to ~20-30Hz via `core/throttle.py`. Cache audio sessions (refresh every 5s).
8. **LED colors are NOTE OFFSETS.** Never use velocity for color. See `feedback/led_colors.py` and Hardware Notes.
9. **Discord hotkeys must be GLOBAL.** User must configure them in Discord Settings > Keybinds. Document in README.
10. **Don't auto-focus apps on hotkey.** Discord/Spotify hotkeys work globally. Stealing focus breaks user workflow. Window focus is Phase 2 opt-in only.
