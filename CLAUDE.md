# K2 Deck — Xone:K2 System Controller

## Project Overview

Python app that turns an Allen & Heath Xone:K2 MIDI controller into a system-wide macro controller for daily workflow: Spotify, Discord, VS Code, and Brave.

**Detailed docs:**
- [docs/Prd.md](docs/Prd.md) — Product vision, features, user scenarios
- [docs/Architecture.md](docs/Architecture.md) — System architecture, data flows, threading, APIs
- [docs/Rules.md](docs/Rules.md) — Code conventions, testing rules, safety protocols
- [docs/Plan.md](docs/Plan.md) — Roadmap, version history, technical debt
- [docs/Scaffold.md](docs/Scaffold.md) — Project structure, module responsibilities, extension guides

## Tech Stack

- **Python 3.12+** (Windows target)
- **MIDI:** `mido` + `python-rtmidi`
- **Keyboard simulation:** `ctypes` SendInput with hardware scan codes (`core/keyboard.py`), `pynput` (mouse_scroll only)
- **Per-app volume:** `pycaw` + `comtypes`
- **Spotify API:** `spotipy`
- **Twitch API:** `twitchAPI`
- **OBS WebSocket:** `obsws-python`
- **Window management:** `pywin32`
- **System tray:** `pystray` + `Pillow`
- **Config hot-reload:** `watchdog`
- **Web UI:** `fastapi` + `uvicorn` + Vue 3 + Pinia + Vite + TailwindCSS
- **MCP:** `mcp` (Claude Desktop integration via stdio)
- **HTTP client:** `httpx` (MCP → REST API bridge)
- **OSC:** Custom encoder in `core/osc.py` (zero deps)
- **Logging:** stdlib `logging`

**Full project structure:** See [docs/Scaffold.md](docs/Scaffold.md)

**Code conventions:** See [docs/Rules.md](docs/Rules.md)

**Roadmap & phase status:** See [docs/Plan.md](docs/Plan.md)

## Dangerous Function Tests — MANDATORY RULES

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
# Run the app
python -m k2deck

# Run MCP server (Claude Desktop integration)
python -m k2deck.mcp

# Run MIDI learn / monitor tools
python -m k2deck.tools.midi_learn
python -m k2deck.tools.midi_monitor

# Run tests
pytest                                    # Backend (34 test files)
cd k2deck/web/frontend && npx vitest run  # Frontend (30 test files)

# Run with debug logging
python -m k2deck --debug
```

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
- Only ONE app can hold the MIDI port at a time.
- Faders send 60+ messages/sec — throttle CC processing to ~30Hz max.

## Critical Constraints

1. **Single MIDI port access.** If another app has the K2 port open, K2 Deck cannot use it. Detect and warn.
2. **Windows only** for now. pycaw and pywin32 are Windows-specific.
3. **No GUI window.** System tray only. The app must be invisible when working.
4. **Never block the MIDI listener.** All actions execute in ThreadPoolExecutor(max_workers=4).
5. **Config is king.** Zero hardcoded MIDI mappings. Everything comes from JSON.
6. **Graceful degradation.** If Spotify API fails → fall back to media keys. If pycaw fails → log and skip. If K2 disconnects → retry loop.
7. **Throttle CC messages.** Rate-limit to ~20-30Hz via `core/throttle.py`. Cache audio sessions (refresh every 5s).
8. **LED colors are NOTE OFFSETS.** Never use velocity for color. See `feedback/led_colors.py`.
9. **Discord hotkeys must be GLOBAL.** User configures in Discord Settings > Keybinds.
10. **Don't auto-focus apps on hotkey.** Stealing focus breaks user workflow.

## Common Gotchas

1. **0-indexed vs 1-indexed.** MIDI channels — K2 uses channel 16 in UI but 15 in code (0-indexed).
2. **API latency vs local solutions.** Prefer system-level approaches (media keys, pycaw) over network APIs when timing matters.
3. **`create_action(config: dict)`** takes a single dict with `"action"` key — NOT two args.
4. **Lazy imports in routes** use try/except blocks — import errors are swallowed silently.
5. **Singleton resets in tests** — See [docs/Rules.md § 4.3](docs/Rules.md) for the full reset table.
