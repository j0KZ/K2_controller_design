# K2 Deck — Implementation Instructions

Reference `k2-controller-design.md` for architecture and `CLAUDE.md` for conventions.

---

## Phase 1: MVP — Step by Step

### Step 1: Project scaffold

Create the full directory structure from CLAUDE.md. Initialize all `__init__.py` files. Create `requirements.txt` with pinned versions:

```
mido>=1.3.0
python-rtmidi>=1.5.0
pynput>=1.7.6
pycaw>=20230407
comtypes>=1.2.0
spotipy>=2.23.0
pywin32>=306
pystray>=0.19.5
Pillow>=10.0.0
watchdog>=3.0.0
pytest>=8.0.0
```

Create `k2deck/__main__.py` so `python -m k2deck` works.

---

### Step 2: MIDI Learn Tool (`tools/midi_learn.py`)

**This is the first thing to build and test.**

Functionality:
1. List all available MIDI input devices
2. Auto-detect device containing "XONE" or "K2" in name
3. If not found, let user pick from list
4. Open MIDI input port
5. Print every incoming MIDI message in human-readable format:
   - Note On: `[HH:MM:SS] NOTE ON  | ch:XX | note:XX | vel:XXX`
   - Note Off: `[HH:MM:SS] NOTE OFF | ch:XX | note:XX | vel:XXX`
   - CC: `[HH:MM:SS] CC      | ch:XX | cc:XXX | val:XXX`
6. On Ctrl+C, ask if user wants to save discovered mappings to JSON
7. Save format: `{ "controls_discovered": [ { "type": "note_on", "channel": 16, "note": 36, "label": "unknown" }, ... ] }`

**Error handling:**
- If no MIDI devices found → print clear message, suggest checking USB connection
- If port busy → print which process might have it (best effort)
- KeyboardInterrupt → clean shutdown, close port

Make it runnable as both `python -m k2deck.tools.midi_learn` and `python tools/midi_learn.py`.

---

### Step 3: MIDI Listener (`core/midi_listener.py`)

Class: `MidiListener`

```python
class MidiListener:
    def __init__(self, device_name: str, callback: Callable[[MidiEvent], None])
    def start(self) -> None          # Start listening in background thread
    def stop(self) -> None           # Clean shutdown
    def reconnect(self) -> bool      # Attempt reconnect if port lost
    @property
    def is_connected(self) -> bool
```

**MidiEvent dataclass:**
```python
@dataclass
class MidiEvent:
    type: str           # "note_on", "note_off", "cc"
    channel: int        # 1-16
    note: int | None    # For note events
    cc: int | None      # For CC events
    value: int          # velocity or CC value
    timestamp: float    # time.time()
```

**Behavior:**
- Runs in a daemon thread
- On message received, parse into MidiEvent and call callback
- On port disconnect: log warning, enter reconnect loop (every 5s, max 60 attempts)
- On reconnect success: log info, resume
- Thread-safe: callback might be called from different thread

---

### Step 4: Mapping Engine (`core/mapping_engine.py`)

Class: `MappingEngine`

```python
class MappingEngine:
    def __init__(self, config_path: str)
    def load_config(self, config_path: str) -> None
    def resolve(self, event: MidiEvent) -> Action | None
    def reload(self) -> None
```

**Logic:**
1. Load JSON config
2. Validate structure (required keys: `midi_channel`, `mappings`)
3. On `resolve(event)`:
   - Check event channel matches config channel
   - Look up by event type:
     - `note_on` → `mappings.note_on[str(event.note)]`
     - `cc` with value 0-127 absolute → `mappings.cc_absolute[str(event.cc)]`
     - `cc` with relative values (1=CW, 127=CCW) → `mappings.cc_relative[str(event.cc)]`
   - If found, instantiate and return appropriate Action
   - If not found, return None (unmapped control — this is normal, don't log as error)

**Config validation rules:**
- `midi_channel`: int 1-16
- `mappings`: must have at least one of `note_on`, `cc`, `cc_relative`
- Each mapping entry must have `name` (str) and `action` (str matching known action type)
- Unknown action types → log warning, skip

---

### Step 5: Action Base (`actions/base.py`)

```python
from abc import ABC, abstractmethod

class Action(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.name = config.get("name", "unnamed")

    @abstractmethod
    def execute(self, event: MidiEvent) -> None:
        """Execute the action. Must not block. Must not raise."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"
```

All actions inherit from this. `execute()` must:
- Never raise exceptions (catch and log internally)
- Never block for more than 100ms (use threads for slow ops)
- Receive the full MidiEvent for context (velocity, value, etc.)

---

### Step 6: Hotkey Action (`actions/hotkey.py`)

```python
class HotkeyAction(Action):
    def execute(self, event: MidiEvent) -> None:
        # Only trigger on Note On with velocity > 0, or on CC change
        # Use pynput.keyboard.Controller to press/release keys
        # Support: single keys, combos (ctrl+shift+m), sequences
```

**Config format:**
```json
{
  "action": "hotkey",
  "keys": ["ctrl", "shift", "m"],
  "target_app": "Discord"  // optional: focus this app first
}
```

**Key mapping:** Convert string key names to pynput Key/KeyCode. Support:
- Modifiers: `ctrl`, `alt`, `shift`, `win`, `cmd`
- Special: `space`, `enter`, `tab`, `escape`, `backspace`, `delete`
- F-keys: `f1`-`f24`
- Media: `media_play_pause`, `media_next`, `media_previous`, `volume_up`, `volume_down`, `volume_mute`
- Letters/numbers: `a`-`z`, `0`-`9`
- Symbols: mapped by character

**For `hotkey_relative` (encoder CW/CCW):**
```json
{
  "action": "hotkey_relative",
  "cw": ["ctrl", "tab"],
  "ccw": ["ctrl", "shift", "tab"]
}
```
Determine direction from CC value: 1-63 = CW, 65-127 = CCW.

---

### Step 6b: Mouse Scroll Action (`actions/mouse_scroll.py`)

```python
class MouseScrollAction(Action):
    def execute(self, event: MidiEvent) -> None:
        # For CC relative events (encoders)
        # Determine direction: value 1-63 = CW (scroll up), 65-127 = CCW (scroll down)
        # Use pynput.mouse.Controller to scroll
```

**Config format:**
```json
{
  "action": "mouse_scroll",
  "step": 5
}
```

Uses `pynput.mouse.Controller().scroll(0, step)` for up and `scroll(0, -step)` for down. Scroll happens wherever the mouse cursor currently is — no window targeting.

---

### Step 6c: Throttle Manager (`core/throttle.py`)

```python
class ThrottleManager:
    def __init__(self, max_hz: int = 30):
        self._last_call: dict[str, float] = {}  # key → timestamp
        self._interval = 1.0 / max_hz

    def should_process(self, key: str) -> bool:
        """Returns True if enough time has passed since last call for this key."""
        now = time.monotonic()
        last = self._last_call.get(key, 0)
        if now - last < self._interval:
            return False
        self._last_call[key] = now
        return True
```

**Why:** Faders send 60+ CC messages/sec. Without throttling, pycaw `SetMasterVolume()` gets called 60+ times/sec which hammers the Windows Audio API. Throttle to 20-30Hz.

**Usage in the pipeline:**
```python
def on_midi_event(event: MidiEvent):
    if event.type == "cc":
        if not throttle.should_process(f"cc_{event.cc}"):
            return  # Skip this message
    # ... proceed with mapping resolution
```

---

### Step 7: Volume Action (`actions/volume.py`)

```python
class VolumeAction(Action):
    def execute(self, event: MidiEvent) -> None:
        # event.value is 0-127 from fader
        # Convert to 0.0-1.0
        # Use pycaw to set volume for target process
```

**Config format:**
```json
{
  "action": "volume",
  "target_process": "Spotify.exe"  // process name, or "__master__" for system volume
}
```

**pycaw usage pattern:**
```python
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

sessions = AudioUtilities.GetAllSessions()
for session in sessions:
    if session.Process and session.Process.name() == target:
        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
        volume.SetMasterVolume(value / 127.0, None)
```

**For `__master__`:**
```python
from pycaw.pycaw import AudioUtilities
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import IAudioEndpointVolume

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
volume.SetMasterVolumeLevelScalar(value / 127.0, None)
```

**Edge cases:**
- Process not found → log debug (app might not be running), don't error
- Multiple instances of same process → set volume on all
- Cache session lookup — don't query AudioUtilities on every fader move. Refresh cache every 5 seconds.

---

### Step 8: LED Manager (`feedback/led_manager.py`)

```python
class LedManager:
    def __init__(self, midi_output: MidiOutput, color_offsets: dict)
    def set_led(self, base_note: int, color: str) -> None      # "red", "amber", "green", "off"
    def toggle_led(self, base_note: int, on_color: str, off_color: str = "off") -> None
    def flash_led(self, base_note: int, color: str, times: int = 3) -> None
    def all_off(self) -> None
    def restore_defaults(self, config: dict) -> None
```

**CRITICAL: LED colors use NOTE OFFSET, not velocity.**

Each button has 3 MIDI notes (one per color). Color = base_note + offset:
```python
# led_colors.py
COLOR_OFFSETS = {"red": 0, "amber": 36, "green": 72}

def led_note(base_note: int, color: str) -> int:
    """Convert button base note + color to the actual MIDI note to send."""
    return base_note + COLOR_OFFSETS[color]

# Example: button at note 36
# Red:   send Note On 36  (36 + 0)
# Amber: send Note On 72  (36 + 36)
# Green: send Note On 108 (36 + 72)
# Off:   send Note Off on any of the 3 notes
```

Verified in Mixxx source: `XoneK2.color = { red: 0, amber: 36, green: 72 }`
Verified in VirtualDJ: `<led note="0x24"/>` (red), `<led note="0x48"/>` (amber), `<led note="0x6C"/>` (green)

New color overwrites active — no need to send Note Off before changing color.

**Toggle state:** LedManager maintains `{base_note: str}` mapping current color per button. Thread-safe with Lock.

---

### Step 9: MIDI Output (`core/midi_output.py`)

```python
class MidiOutput:
    def __init__(self, device_name: str, channel: int)
    def send_note_on(self, note: int, velocity: int) -> None
    def send_note_off(self, note: int) -> None
    def open(self) -> None
    def close(self) -> None
```

Wrapper around `mido.open_output()`. Same reconnect logic as listener.

---

### Step 10: Entry Point (`k2deck.py`)

```python
def main():
    # 1. Parse args (--debug, --config path, --learn)
    # 2. Setup logging
    # 3. Load config
    # 4. Initialize MidiListener
    # 5. Initialize MidiOutput
    # 6. Initialize MappingEngine
    # 7. Initialize LedManager
    # 8. Initialize action instances
    # 9. Wire callback: listener → mapping_engine → action.execute()
    # 10. Start listener
    # 11. Start system tray (blocks main thread)
    # 12. On tray quit: stop listener, close output, exit
```

**System tray menu:**
- Status: "Connected to XONE:K2" / "Disconnected"
- Profile: submenu with available profiles
- MIDI Monitor: toggle debug logging to console
- Reload Config
- Quit

**The callback pipeline:**
```python
def on_midi_event(event: MidiEvent):
    action = mapping_engine.resolve(event)
    if action is None:
        return  # Unmapped control
    
    logger.info(f"Executing: {action}")
    
    # Execute in thread pool to never block MIDI listener
    executor.submit(action.execute, event)
    
    # Handle LED feedback if configured
    led_config = action.config.get("led")
    if led_config:
        if led_config.get("toggle"):
            led_manager.toggle_led(led_config["note"], led_config["color"])
        else:
            led_manager.set_led(led_config["note"], led_config["color"])
```

---

### Step 11: Default Config (`config/default.json`)

Create a working default config based on the column layout in `k2-controller-design.md`. Use placeholder note/CC numbers that can be updated after running `midi_learn.py`. Add comments explaining each mapping (JSON doesn't support comments — use `"_comment"` keys or a separate `README` in config/).

---

## Phase 2: Implementation Notes

### Spotify Action (`actions/spotify.py`)

- Use `spotipy` with `SpotifyOAuth` flow
- Scopes needed: `user-read-playback-state`, `user-modify-playback-state`, `user-library-modify`, `user-library-read`
- Store refresh token in `config/spotify_token.json` (gitignored)
- Actions: `play_pause`, `next`, `previous`, `like`, `seek` (relative), `get_current_track`
- On first run: open browser for OAuth, save token
- On token expired: auto-refresh
- Fallback: if API fails, use media key hotkeys

### Window Action (`actions/window.py`)

- `pywin32` to find window by process name or title
- `SetForegroundWindow` to focus
- `ShellExecute` to launch if not running
- Optional: `target_app` in any action config → focus that app before executing hotkey

### Profile Manager (`core/profile_manager.py`)

- Watch `config/` directory with `watchdog`
- On file change: validate JSON → hot-reload mapping engine
- K2 Layer button (bottom-left) → switch between profiles
- Show current profile name in tray tooltip

---

## Testing Strategy

### Unit Tests (no hardware needed)

```
tests/
├── test_mapping_engine.py    # Config loading, event resolution
├── test_hotkey_action.py     # Key name parsing, combo building
├── test_volume_action.py     # Value conversion, edge cases
├── test_led_manager.py       # Toggle state, color mapping
└── test_config_validation.py # Valid/invalid JSON handling
```

**Mock pattern:**
```python
# Mock mido for MIDI tests
@patch("k2deck.core.midi_listener.mido.open_input")
def test_listener_starts(mock_open):
    mock_port = MagicMock()
    mock_open.return_value = mock_port
    listener = MidiListener("XONE:K2", callback=lambda e: None)
    listener.start()
    mock_open.assert_called_once()
```

### Integration Tests (with hardware)

Mark with `@pytest.mark.hardware` — skipped by default:
```bash
pytest                      # Unit tests only
pytest -m hardware          # Include hardware tests
```

---

## Common Pitfalls to Avoid

1. **Don't use `mido.open_input()` without specifying the exact device name.** It defaults to the first device, which might not be the K2.

2. **pycaw session enumeration is expensive.** Cache it. Don't call `GetAllSessions()` on every fader move (60+ times/second).

3. **pynput `press()` and `release()` must be paired.** For combos, press all modifiers first, then the key, then release in reverse order. Use the `hotkey` context manager pattern.

4. **MIDI channel numbering confusion.** mido uses 0-indexed channels (0-15). The K2 and most MIDI docs use 1-indexed (1-16). Always convert at the boundary.

5. **K2 encoder CC values are two's complement.** Value 1 = CW one step. Value 127 (-1) = CCW one step. Value 2 = CW two steps. Don't treat as absolute.

6. **Thread safety.** The MIDI callback runs in the listener thread. Action execution happens in thread pool. LED state dict needs a lock.

7. **System tray blocks main thread.** `pystray` runs its own event loop. Start MIDI listener before entering tray loop.

8. **On Windows, `python-rtmidi` needs the Visual C++ Build Tools** if installing from source. Recommend: `pip install python-rtmidi` should get a wheel. If not, install VS Build Tools first.

9. **CRITICAL: LED colors are NOTE OFFSET, not velocity.** Red = base+0, Amber = base+36, Green = base+72. Sending velocity values to control color WILL NOT WORK. See `feedback/led_colors.py`.

10. **Don't auto-focus apps when sending hotkeys.** Discord Mute (Ctrl+Shift+M) and Spotify media keys work globally. `SetForegroundWindow()` steals focus. Only use in Phase 2 `window.py` as opt-in.

11. **Throttle fader CC messages.** Without throttling, faders generate 60+ events/sec hammering pycaw. Use `core/throttle.py` to cap at 20-30Hz.

12. **Discord global hotkeys must be configured by the user.** Not enabled by default. User must configure in Discord Settings > Keybinds. Document in README.
