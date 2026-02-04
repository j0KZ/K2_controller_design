# K2 Deck - Changelog

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
- 166 tests passing (6 skipped for safety)
- New test files for: keyboard, layers, conditional actions, profile switcher, multi actions, system actions, volume actions

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
