# K2 Deck - Changelog

## [0.4.0] - 2026-02-13

### Added
- **OSC Send Actions** — Forward MIDI events to Pure Data via OSC UDP
  - `osc_send` (cc_absolute): Faders/pots → normalize → curve → scale → send OSC
  - `osc_send_relative` (cc_relative): Encoders → accumulate two's complement deltas → send OSC
  - `osc_send_trigger` (note_on): Buttons → bang or toggle → send OSC
  - New files: `actions/osc_send.py`, `core/osc.py`
  - 77 new tests across `tests/test_osc.py` and `tests/test_osc_send_action.py`

- **OSC 1.0 Encoder** (`core/osc.py`) — Minimal OSC encoder + UDP sender, zero external dependencies
  - `OscSender` keyed singleton: one persistent socket per (host, port) destination
  - Thread-safe with lazy socket creation
  - Functions: `osc_string()`, `osc_int()`, `osc_float()`, `build_osc_message()`

### Changed
- Registered 3 new action types in `core/mapping_engine.py`
- Added OSC socket cleanup on shutdown (`k2deck.py`)
- Added accumulator/toggle state reset on config reload (`k2deck.py`)

### Cross-project
- Updated `mcp_pure_data` (future: `synthlab-mcp`) config generator to emit
  `osc_send` / `osc_send_relative` / `osc_send_trigger` actions instead of `noop`
  - Modified: `src/controllers/k2-deck-config.ts`
  - Updated tests: `tests/controllers/controller.test.ts`
  - All 619 tests passing

### Architecture
```
K2 hardware → K2 Deck (MIDI) → OSC UDP → Pure Data (bridge patch)
                 ↓
          LEDs + System Actions + Web UI (unchanged)
```
K2 Deck owns the MIDI port. Pure Data receives parameter values via OSC on port 9000.
This solves the single-MIDI-port constraint without losing any existing K2 Deck functionality.

---

## [0.3.0] - 2025-02-04

### Added
- **Conditional Actions** (`conditional`) - Execute different actions based on context
  - `app_focused`: Check if specific app has focus
  - `app_running`: Check if specific app is running
  - `toggle_state`: Check state of toggle buttons
  - Supports nested actions with depth limit (max 3 levels)
  - New files: `actions/conditional.py`, `core/action_factory.py`, `core/context.py`

- **Profile Auto-Switch** (optional) - Automatically switch profiles based on active app
  - Disabled by default, only activates when explicitly configured
  - Background thread monitors foreground app
  - Case-insensitive, partial app name matching
  - New file: `core/profile_switcher.py`

- **Sound Playback** (`sound_play`, `sound_stop`) - Play audio files on button press
  - WAV files: Native Windows support (no dependencies)
  - MP3/OGG: Requires pygame (optional)
  - New file: `actions/sound.py`

- **Audio Device Switch** (`audio_switch`, `audio_list`) - Change default audio device
  - Cycle between speakers/headphones with a button
  - Uses Windows IPolicyConfig COM interface
  - Supports output and input devices
  - New files: `core/audio_devices.py`, `actions/audio_switch.py`

- **OBS WebSocket Integration** (`obs_scene`, `obs_source_toggle`, `obs_stream`, `obs_record`, `obs_mute`)
  - Control OBS Studio via WebSocket v5 API
  - Switch scenes with a button press
  - Toggle source visibility (webcam, overlays, etc.)
  - Start/stop/toggle streaming and recording
  - Mute/unmute audio inputs
  - Singleton client with auto-reconnect logic
  - Lazy connection (only connects on first OBS action)
  - Requires `obsws-python` (optional dependency)
  - New files: `core/obs_client.py`, `actions/obs.py`

- **Counter Actions** (`counter`) - Persistent counters for tracking
  - Increment, decrement, reset, or set counter values
  - Counters persist to `~/.k2deck/counters.json`
  - Callback system for state change notifications
  - Singleton CounterManager with JSON persistence
  - New files: `core/counters.py`, `actions/counter.py`

- **Text-to-Speech** (`tts`) - Speak text on button press
  - Uses Windows SAPI via pyttsx3 (system default voice)
  - Configurable speech rate and volume
  - Optional dependency with graceful fallback
  - New file: `actions/tts.py`

- **Software Layers** - 3x the controls on same hardware
  - Layer button cycles through layers 1-2-3
  - Per-layer mappings in config (`layer_1`, `layer_2`, `layer_3`)
  - LED color indicates current layer (red/amber/green)
  - New file: `core/layers.py`

- **New keyboard module** (`core/keyboard.py`)
  - Pure ctypes/SendInput implementation (no pynput dependency)
  - Proper scan codes for all keys
  - Media key support via virtual key codes
  - State tracking for held keys

- **Spotify API integration** (`actions/spotify.py`)
  - Full Spotify control: play/pause, next/prev, like, shuffle, repeat
  - Volume control, seek with encoders
  - OAuth flow with token persistence
  - New files: `actions/spotify.py`, `core/spotify_client.py`

- **Multi-K2 support** - Use two K2 controllers as one
  - Zone-based configuration (different MIDI channels)
  - Example config: `config/dual_k2_example.json`

### Changed
- Migrated from pynput to native SendInput for keyboard simulation
- Improved modifier key handling in multi-action sequences
- Tests now use `patch.dict()` for dangerous system commands

### Tests
- 262 tests passing (6 skipped for safety)
- New test files for: keyboard, layers, conditional actions, profile switcher, multi actions, system actions, volume actions, sound, audio switch, OBS, counter, TTS

---

## [0.2.0] - 2025-02-03

### Added
- **System Commands** (`system`) - Lock, sleep, shutdown, restart, hibernate, screenshot
- **Open URL** (`open_url`) - Open URLs in default browser
- **Clipboard Paste** (`clipboard_paste`) - Paste predefined text
- **Multi-Toggle** (`multi_toggle`) - Toggle between on/off action sequences
- **Window Focus/Launch** (`focus`, `launch`) - Focus or launch applications

### Changed
- Improved documentation in CLAUDE.md for dangerous test functions

---

## [0.1.0] - 2025-02-02

### Added
- Initial MVP release
- MIDI listener with auto-reconnect
- Mapping engine with JSON configuration
- Hotkey actions (tap, hold modes)
- Volume control (master and per-app via pycaw)
- Mouse scroll simulation
- LED feedback with color control
- System tray integration
- Config hot-reload via watchdog
