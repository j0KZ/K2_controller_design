# K2 Deck — Project Scaffold

## 1. Directory Overview

```
k2deck/
├── __main__.py                # `python -m k2deck` entry point
├── k2deck.py                  # App init, system tray, MIDI pipeline, lifecycle
│
├── config/
│   ├── default.json           # Default mapping profile (active)
│   └── dual_k2_example.json   # Template for dual-controller setup
│
├── core/                      # Core infrastructure (20 modules)
│   ├── __init__.py
│   ├── midi_listener.py       # MIDI input + auto-reconnect (daemon thread)
│   ├── midi_output.py         # MIDI output to K2 (LED commands)
│   ├── mapping_engine.py      # MIDI event → Action resolution + ACTION_TYPES registry
│   ├── keyboard.py            # SendInput/ctypes keystroke simulation (replaced pynput)
│   ├── throttle.py            # CC rate limiter (~30Hz) + FaderDebouncer
│   ├── analog_state.py        # Persist fader/pot positions (Jump mode)
│   ├── layers.py              # Software layer state (1-3)
│   ├── folders.py             # Button sub-page navigation
│   ├── counters.py            # Persistent counters (JSON)
│   ├── timer_manager.py       # Countdown timer singleton (daemon threads)
│   ├── osc.py                 # OSC 1.0 encoder + OscSender UDP singleton
│   ├── action_factory.py      # Create action instances from config dicts
│   ├── context.py             # Active-window detection (pywin32)
│   ├── profile_switcher.py    # Profile loading/switching + hot-reload (watchdog)
│   ├── audio_devices.py       # Audio device enumeration + switching (pycaw)
│   ├── secure_storage.py      # Windows keyring for OAuth tokens
│   ├── spotify_client.py      # Spotify API wrapper (spotipy OAuth)
│   ├── twitch_client.py       # Twitch API client (twitchAPI OAuth)
│   ├── obs_client.py          # OBS WebSocket client (obsws-python, auto-reconnect)
│   ├── autostart.py           # Windows auto-start (VBScript in Startup folder)
│   └── instance_lock.py       # Single-instance guard (Windows named mutex)
│
├── actions/                   # Action types (18 modules, 48 registered types)
│   ├── __init__.py
│   ├── base.py                # Action ABC — execute(event) contract
│   ├── hotkey.py              # HotkeyAction, HotkeyRelativeAction (SendInput)
│   ├── mouse_scroll.py        # MouseScrollAction (pynput mouse)
│   ├── volume.py              # VolumeAction (pycaw per-app + master)
│   ├── system.py              # SystemAction, NoopAction, OpenURLAction, ClipboardPasteAction
│   ├── multi.py               # MultiAction (sequence), MultiToggleAction (on/off)
│   ├── conditional.py         # ConditionalAction (context-aware dispatch)
│   ├── window.py              # FocusAction, LaunchAction (pywin32)
│   ├── spotify.py             # 9 Spotify actions (API: play, next, like, shuffle, etc.)
│   ├── obs.py                 # 5 OBS actions (scene, source, stream, record, mute)
│   ├── twitch.py              # 5 Twitch actions (marker, clip, chat, title, game)
│   ├── sound.py               # SoundPlayAction, SoundStopAction
│   ├── tts.py                 # TTSAction (Windows SAPI via pyttsx3)
│   ├── counter.py             # CounterAction (increment, decrement, reset)
│   ├── folder.py              # FolderAction, FolderBackAction, FolderRootAction
│   ├── audio_switch.py        # AudioSwitchAction, AudioListAction
│   ├── osc_send.py            # OscSendAction, OscSendRelativeAction, OscSendTriggerAction
│   └── timer.py               # TimerStartAction, TimerStopAction, TimerToggleAction
│
├── feedback/                  # LED control
│   ├── __init__.py
│   ├── led_manager.py         # LED state machine (singleton: set, toggle, flash, all_off)
│   └── led_colors.py          # Color offset constants (red=+0, amber=+36, green=+72)
│
├── web/                       # FastAPI backend + Vue frontend
│   ├── __init__.py
│   ├── server.py              # FastAPI app creation, WebSocket handler, uvicorn runner
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── config.py          # /api/config — CRUD, validate, export/import (5 endpoints)
│   │   ├── profiles.py        # /api/profiles — list, create, get, update, delete, activate (6 endpoints)
│   │   ├── k2.py              # /api/k2 — state, LEDs, layer, folder, analog, MIDI, trigger, timers (13 endpoints)
│   │   └── integrations.py    # /api/integrations — status, connect, disconnect (4 endpoints)
│   ├── websocket/
│   │   ├── __init__.py
│   │   └── manager.py         # ConnectionManager, EventType enum, broadcast functions
│   └── frontend/              # Vue 3 SPA
│       ├── index.html
│       ├── vite.config.js
│       ├── vitest.config.js
│       ├── tailwind.config.js
│       ├── package.json
│       └── src/
│           ├── main.js
│           ├── App.vue
│           ├── style.css
│           ├── components/
│           │   ├── layout/         # K2 visual representation
│           │   │   ├── K2Grid.vue, K2Row.vue, K2Control.vue
│           │   │   ├── K2Button.vue, K2Encoder.vue, K2Pot.vue, K2Fader.vue
│           │   │   ├── K2Led.vue, LayerTabs.vue, FolderBreadcrumb.vue
│           │   ├── header/         # Top bar
│           │   │   ├── AppHeader.vue, ConnectionStatus.vue
│           │   │   ├── ProfileDropdown.vue, IntegrationPills.vue
│           │   ├── config/         # Action editor
│           │   │   ├── ControlConfig.vue, ActionPicker.vue
│           │   │   ├── ActionForm.vue, LedConfig.vue
│           │   ├── monitor/        # MIDI event log
│           │   │   ├── MidiMonitor.vue, MidiEventItem.vue
│           │   └── common/
│           │       └── ToastContainer.vue
│           ├── stores/             # Pinia (7 stores)
│           │   ├── config.js, k2State.js, analogState.js
│           │   ├── profiles.js, integrations.js, midi.js, ui.js
│           └── composables/        # Reusable logic (3)
│               ├── useApi.js, useWebSocket.js, useKeyboard.js
│
├── mcp/                       # Claude Desktop integration
│   ├── __init__.py
│   ├── __main__.py            # `python -m k2deck.mcp` entry
│   ├── client.py              # K2DeckClient (httpx AsyncClient, lazy singleton)
│   └── server.py              # MCP server (stdio, 10 tools)
│
├── tools/                     # CLI utilities
│   ├── __init__.py
│   ├── midi_learn.py          # Interactive MIDI discovery + LED test
│   └── midi_monitor.py        # Raw MIDI traffic monitor
│
└── tests/                     # Backend tests (34 files)
    ├── __init__.py
    ├── test_mapping_engine.py, test_hotkey_action.py, test_volume_action.py
    ├── test_led_colors.py, test_throttle.py, test_keyboard.py, test_layers.py
    ├── test_multi_action.py, test_system_action.py, test_conditional_action.py
    ├── test_profile_switcher.py, test_sound_action.py, test_sound_extended.py
    ├── test_audio_switch.py, test_obs.py, test_obs_extended.py, test_tts.py
    ├── test_counter.py, test_folder.py, test_twitch.py, test_analog_state.py
    ├── test_action_factory.py, test_server_extended.py
    ├── test_web_api.py, test_web_api_extended.py, test_websocket_manager.py
    ├── test_integrations_routes.py, test_k2_routes_trigger.py
    ├── test_osc.py, test_osc_send_action.py
    ├── test_timer_manager.py, test_timer_action.py
    └── test_mcp_client.py, test_mcp_server.py
```

Frontend tests (30 files) are co-located as `*.test.js` next to their source files.

---

## 2. Module Responsibilities

### core/ — Infrastructure

| Module | Responsibility |
|--------|---------------|
| `midi_listener.py` | MIDI input in daemon thread, auto-reconnect every 5s on disconnect |
| `midi_output.py` | Send MIDI Note On/Off to K2 for LED control |
| `mapping_engine.py` | Load JSON config → resolve MIDI events to actions via 48-entry `ACTION_TYPES` dict |
| `keyboard.py` | Windows SendInput API with hardware scan codes (replaced pynput for keyboard) |
| `throttle.py` | Rate-limit CC messages from faders/pots (~30Hz). `FaderDebouncer` ensures final value. |
| `analog_state.py` | Persist fader/pot positions to `~/.k2deck/analog_state.json`. Jump mode sync. |
| `layers.py` | Software layers 1-3 — layer button cycles, per-layer mappings |
| `folders.py` | Button sub-pages — navigate into/out of folder mappings |
| `counters.py` | Persistent counters to `~/.k2deck/counters.json` |
| `timer_manager.py` | Singleton `TimerManager` — named countdowns with daemon threads, completion callbacks |
| `osc.py` | OSC 1.0 message encoder + `OscSender` keyed singleton (one UDP socket per host:port) |
| `action_factory.py` | Create action instances from config dicts (for dynamic creation outside mapping engine) |
| `context.py` | Get foreground window app name via pywin32 (for conditional actions) |
| `profile_switcher.py` | Profile loading, switching, hot-reload via watchdog file watcher |
| `audio_devices.py` | Enumerate/switch Windows audio devices (pycaw + IPolicyConfig COM) |
| `secure_storage.py` | Store/retrieve OAuth tokens via Windows keyring |
| `spotify_client.py` | Spotipy wrapper: OAuth flow, token persistence, API calls |
| `twitch_client.py` | Twitch API: channel info, markers, clips, chat, moderation |
| `obs_client.py` | OBS WebSocket v5 client: singleton, lazy connect, auto-reconnect |
| `autostart.py` | Windows auto-start: create/remove VBScript in Startup folder |
| `instance_lock.py` | Single-instance guard: Windows named mutex, fail-open |

### actions/ — 48 Registered Action Types

All actions inherit from `Action` ABC (`base.py`). Contract:
- `__init__(self, config: dict)` — receives mapping config dict
- `execute(self, event: MidiEvent) -> None` — must not block >100ms, must not raise

| Module | Types | Description |
|--------|-------|-------------|
| `hotkey.py` | `hotkey`, `hotkey_relative`, `media_key` | Keyboard simulation (SendInput). `media_key` is `HotkeyAction` alias. |
| `mouse_scroll.py` | `mouse_scroll` | Encoder → scroll (pynput mouse) |
| `volume.py` | `volume` | Fader → per-app or master volume (pycaw) |
| `system.py` | `system`, `noop`, `open_url`, `clipboard_paste` | Lock, screenshot, shutdown, URLs, paste |
| `multi.py` | `multi`, `multi_toggle` | Hotkey sequence; toggle between on/off sequences |
| `conditional.py` | `conditional` | Context-aware — different actions per focused app |
| `window.py` | `focus`, `launch` | Focus or launch Windows apps (pywin32) |
| `spotify.py` | `spotify_play_pause`, `spotify_next`, `spotify_previous`, `spotify_like`, `spotify_shuffle`, `spotify_repeat`, `spotify_volume`, `spotify_seek`, `spotify_prev_next` | Spotify Web API actions (9 types) |
| `obs.py` | `obs_scene`, `obs_source_toggle`, `obs_stream`, `obs_record`, `obs_mute` | OBS WebSocket actions (5 types) |
| `twitch.py` | `twitch_marker`, `twitch_clip`, `twitch_chat`, `twitch_title`, `twitch_game` | Twitch API actions (5 types) |
| `sound.py` | `sound_play`, `sound_stop` | Play/stop audio files (WAV native, MP3 via pygame) |
| `tts.py` | `tts` | Text-to-speech (Windows SAPI) |
| `counter.py` | `counter` | Persistent counter operations |
| `folder.py` | `folder`, `folder_back`, `folder_root` | Navigate button sub-pages |
| `audio_switch.py` | `audio_switch`, `audio_list` | Switch/list audio devices |
| `osc_send.py` | `osc_send`, `osc_send_relative`, `osc_send_trigger` | Send OSC to Pure Data |
| `timer.py` | `timer_start`, `timer_stop`, `timer_toggle` | Named countdown timers |

### feedback/ — LED System

- `led_manager.py`: Singleton `LedManager` — `set_led()`, `turn_off()`, `toggle_led()`, `flash_led()`, `get_all_states()`
- `led_colors.py`: `COLOR_OFFSETS = {"red": 0, "amber": 36, "green": 72}` + `led_note()` helper

### web/ — API & Frontend

- **28 REST endpoints** across 4 routers (config, profiles, k2, integrations)
- **WebSocket** at `/ws/events` — 9 server→client events, 2 client→server commands
- **Vue 3** SPA: 22 components, 7 Pinia stores, 3 composables

### mcp/ — Claude Desktop

- `server.py`: 10 MCP tools via `@app.list_tools()` / `@app.call_tool()` decorators
- `client.py`: `K2DeckClient` lazy singleton wrapping `httpx.AsyncClient`
- Auto-starts web server via orphaned subprocess if not running

---

## 3. Extension Guides

### 3.1 Adding a New Action Type

1. **Create** `k2deck/actions/my_action.py`:

```python
from k2deck.actions.base import Action
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

class MyAction(Action):
    def execute(self, event: "MidiEvent") -> None:
        try:
            value = self.config.get("my_param", "default")
            # ... do work ...
        except Exception:
            logging.getLogger(__name__).error("MyAction failed", exc_info=True)
```

2. **Register** in `k2deck/core/mapping_engine.py`:

```python
from k2deck.actions.my_action import MyAction
# Add to ACTION_TYPES dict:
ACTION_TYPES: dict[str, type[Action]] = {
    ...
    "my_action": MyAction,
}
```

3. **Config** — add to a profile JSON:

```json
{
  "36": {
    "name": "My Action",
    "action": "my_action",
    "my_param": "some_value"
  }
}
```

4. **Test** — create `k2deck/tests/test_my_action.py` following existing patterns.

### 3.2 Adding a New REST API Route

1. **Create** `k2deck/web/routes/my_route.py`:

```python
from fastapi import APIRouter
router = APIRouter()

@router.get("/something")
async def get_something():
    return {"status": "ok"}
```

2. **Register** in `k2deck/web/server.py` → `create_app()`:

```python
from k2deck.web.routes import my_route
app.include_router(my_route.router, prefix="/api/my_route", tags=["my_route"])
```

3. **Test** — add to existing `test_web_api.py` or create a new test file.

### 3.3 Adding a New Frontend Component

1. **Create** `k2deck/web/frontend/src/components/<category>/MyComponent.vue`
2. **Create** co-located test: `MyComponent.test.js` (same directory)
3. **Wire** into parent component (e.g., import in `App.vue` or relevant parent)
4. **Add** to Pinia store if it manages state (e.g., `stores/config.js`)
5. **Test setup**: Always `setActivePinia(createPinia())` in `beforeEach`

### 3.4 Adding a New MCP Tool

1. **Add Tool** in `k2deck/mcp/server.py` → `list_tools()`:

```python
Tool(
    name="my_tool",
    description="What it does",
    inputSchema={"type": "object", "properties": {...}, "required": [...]},
),
```

2. **Add handler** in `call_tool()`:

```python
elif name == "my_tool":
    client = await get_client()
    result = await client.get("/api/my_endpoint")
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

3. **Add REST endpoint** if needed (in `web/routes/k2.py` or new route file).
4. **Test** in `k2deck/tests/test_mcp_server.py` — patch `get_client()` with `AsyncMock`.

### 3.5 Adding a New Integration Client

1. **Create** client in `k2deck/core/my_client.py` (singleton pattern: `_instance`, `get_my_client()`)
2. **Create** action(s) in `k2deck/actions/my_integration.py`
3. **Register** action types in `mapping_engine.py` → `ACTION_TYPES`
4. **Add** config section in profile JSON under `integrations`
5. **Add** status endpoint in `web/routes/integrations.py`
6. **Cleanup** — add shutdown logic in `k2deck.py` cleanup block if using persistent connections

---

## 4. Key Patterns

### 4.1 Singleton Pattern

Used by: `LedManager`, `AnalogStateManager`, `TimerManager`, `OscSender`, `ConnectionManager`, `K2DeckClient`

```python
# Module-level instance
_instance: MyManager | None = None

def get_my_manager() -> MyManager:
    global _instance
    if _instance is None:
        _instance = MyManager()
    return _instance

# Test reset:
MyManager._instance = None  # or module._instance = None
```

### 4.2 Action Config Pattern

All actions receive a single `dict` with an `"action"` key plus type-specific fields:

```json
{
  "name": "Discord Mute",
  "action": "hotkey",
  "keys": ["ctrl", "shift", "m"],
  "led": { "color": "red", "mode": "toggle", "off_color": "green" }
}
```

`create_action(config: dict)` — takes the full dict, reads `config["action"]` to pick the class.

### 4.3 WebSocket Broadcast (thread-safe)

MIDI events arrive on a daemon thread but WebSocket is async. Bridge pattern:

```python
# At startup: capture the event loop
set_server_loop(asyncio.get_running_loop())

# From any thread:
def broadcast_sync(event: WebSocketEvent):
    loop = _server_loop
    if loop:
        asyncio.run_coroutine_threadsafe(manager.broadcast(event), loop)
```

### 4.4 Lazy Import Pattern

Routes use lazy imports inside try/except for optional dependencies:

```python
@router.get("/state/leds")
async def get_led_states():
    try:
        from k2deck.feedback.led_manager import get_led_manager
        led_manager = get_led_manager()
        return {"leds": led_manager.get_all_states()}
    except Exception:
        return {"leds": {}}
```

---

## 5. Configuration File Formats

### 5.1 Profile JSON (`config/*.json`)

```json
{
  "profile_name": "default",
  "midi_channel": 16,
  "midi_device": "XONE:K2",
  "led_color_offsets": { "red": 0, "amber": 36, "green": 72 },
  "throttle": { "cc_max_hz": 30, "cc_volume_max_hz": 20 },
  "mappings": {
    "note_on": { "<note>": { "name": "...", "action": "...", ... } },
    "cc_absolute": { "<cc>": { "name": "...", "action": "volume", "target_process": "..." } },
    "cc_relative": { "<cc>": { "name": "...", "action": "mouse_scroll", "step": 5 } }
  },
  "led_defaults": { "on_start": [...], "on_connect": "all_off" }
}
```

Layer-specific: add `"layer_1"`, `"layer_2"`, `"layer_3"` keys inside a mapping entry.
Zones (multi-K2): add `"zones"` top-level key with per-channel mappings.

### 5.2 Analog State (`~/.k2deck/analog_state.json`) — auto-generated

```json
{ "1": 64, "2": 127, "5": 0 }
```

Maps CC numbers to last-known values (0-127).

### 5.3 Counters (`~/.k2deck/counters.json`) — auto-generated

```json
{ "stream_count": 42, "pomodoro": 3 }
```

---

## 6. CLI Commands

```bash
python -m k2deck                  # Run main app (system tray + MIDI)
python -m k2deck --debug          # Run with DEBUG logging
python -m k2deck --config path    # Use custom config file
python -m k2deck.mcp              # Run MCP server (Claude Desktop)
python -m k2deck.tools.midi_learn # Interactive MIDI discovery + LED test
python -m k2deck.tools.midi_monitor # Raw MIDI traffic passthrough
pytest                            # Run backend tests (34 files)
cd k2deck/web/frontend && npx vitest # Run frontend tests (30 files)
```
