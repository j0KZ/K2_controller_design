# K2 Deck — Architecture

## 1. System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                          K2 Deck                                  │
│                                                                   │
│  ┌──────────┐   ┌───────────┐   ┌─────────────────────────────┐  │
│  │  MIDI    │──▶│  Throttle  │──▶│  Mapping Engine             │  │
│  │ Listener │   │  + Fader   │   │  (48 action types)          │  │
│  │ (mido)   │   │  Debouncer │   │  layers + folders + zones   │  │
│  └──────────┘   └───────────┘   └──────────┬──────────────────┘  │
│       │                                     │                     │
│       │                              ThreadPoolExecutor(4)        │
│       │                                     │                     │
│  ┌──────────┐   ┌──────────┐    ┌───────────▼─────────────────┐  │
│  │  MIDI    │◀──│   LED    │    │  Actions                    │  │
│  │  Output  │   │ Manager  │    │  hotkey, volume, spotify,   │  │
│  │ (mido)   │   │(feedback)│    │  obs, twitch, osc, timer... │  │
│  └──────────┘   └──────────┘    └─────────────────────────────┘  │
│                                                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐                  │
│  │ System   │   │ Analog   │   │ Web Server   │                  │
│  │  Tray    │   │  State   │   │ (FastAPI)    │                  │
│  │(pystray) │   │ Manager  │   │ + Vue.js SPA │                  │
│  └──────────┘   └──────────┘   └──────┬───────┘                  │
│                                        │                          │
└────────────────────────────────────────┼──────────────────────────┘
                                         │
                              ┌──────────▼───────────┐
                              │  MCP Server (stdio)   │
                              │  Claude Desktop       │
                              │  ←httpx→ REST API     │
                              └──────────────────────┘

External:
  K2 → OSC UDP → Pure Data (port 9000)
  K2 → httpx   → Spotify API / Twitch API
  K2 → obsws   → OBS WebSocket (port 4455)
```

## 2. Threading Model

| Thread | Purpose | Module | Notes |
|--------|---------|--------|-------|
| Main | pystray event loop | `k2deck.py` | Blocks. Start everything before entering. |
| MIDI listener | mido message loop | `core/midi_listener.py` | Daemon thread. Calls `_on_midi_event()`. |
| Action workers (4) | Execute actions | `k2deck.py` ThreadPoolExecutor | Prevents blocking MIDI thread. |
| Fader debouncer | Ensure final value | `core/throttle.py` FaderDebouncer | Timer threads per active fader. |
| Reconnect | Retry MIDI port | `core/midi_listener.py` | 5s retry loop on disconnect. |
| Web server | uvicorn (FastAPI) | `web/server.py` | Daemon thread, port 8420. |
| WebSocket | Async broadcast | `web/websocket/manager.py` | Shares web server's event loop. |
| Timer threads | 1 per active timer | `core/timer_manager.py` | Daemon threads, 1s tick resolution. |
| Connection monitor | Poll K2 status | `k2deck.py` | 2s polling loop. |

## 3. Data Flow: MIDI Event Pipeline

```
K2 Hardware (USB MIDI)
  │
  ▼
MidiListener (daemon thread)
  │  Parses mido Message → MidiEvent dataclass
  │
  ▼
_on_midi_event() [k2deck.py]
  │
  ├─ CC absolute (fader)?
  │    ├─ FaderDebouncer: queue final value (50ms delay)
  │    ├─ Extreme value (0 or 127)? → bypass throttle
  │    └─ ThrottleManager: skip if <33ms since last
  │
  ├─ CC relative (encoder)?
  │    └─ ThrottleManager: standard rate limit
  │
  └─ Note On (button)?
       └─ Pass through (no throttle)
  │
  ▼
MappingEngine.resolve(event)
  │  1. Check MIDI channel matches (zone support)
  │  2. Check layer button → cycle layer
  │  3. Check folder state → folder mappings
  │  4. Look up: note_on[note] or cc_absolute[cc] or cc_relative[cc]
  │  5. Check layer-specific overrides (layer_1/2/3)
  │  6. ACTION_TYPES[action_type] → instantiate Action class
  │
  ▼
ThreadPoolExecutor.submit(_execute_action)
  │  1. action.execute(event)
  │  2. Handle LED feedback (toggle/flash/static)
  │
  ▼
WebSocket broadcast (thread-safe via asyncio.run_coroutine_threadsafe)
  │  → midi_event, led_change, analog_change, etc.
  │
  ▼
AnalogStateManager (for CC absolute)
  │  → Persist to ~/.k2deck/analog_state.json (debounced 1/sec)
```

## 4. Action System

**Base class:** `Action` ABC in `actions/base.py`
- `__init__(self, config: dict)` — receives full mapping config dict
- `execute(self, event: MidiEvent) -> None` — must not block >100ms, must not raise
- All 48 types registered in `ACTION_TYPES` dict in `core/mapping_engine.py`

**Creation:** `create_action({"action": "hotkey", "keys": ["ctrl", "s"]})` reads `config["action"]`, looks up class in `ACTION_TYPES`, returns instance. Single dict argument — NOT two args.

**Categories:**

| Category | Types | Count |
|----------|-------|-------|
| Input simulation | hotkey, hotkey_relative, media_key, mouse_scroll | 4 |
| Volume/audio | volume, audio_switch, audio_list | 3 |
| System | system, noop, open_url, clipboard_paste | 4 |
| Sequencing | multi, multi_toggle, conditional | 3 |
| Window | focus, launch | 2 |
| Spotify API | spotify_* (play_pause, next, prev, like, shuffle, repeat, volume, seek, prev_next) | 9 |
| OBS WebSocket | obs_scene, obs_source_toggle, obs_stream, obs_record, obs_mute | 5 |
| Twitch API | twitch_marker, twitch_clip, twitch_chat, twitch_title, twitch_game | 5 |
| Sound/speech | sound_play, sound_stop, tts | 3 |
| Counter | counter | 1 |
| Navigation | folder, folder_back, folder_root | 3 |
| OSC | osc_send, osc_send_relative, osc_send_trigger | 3 |
| Timer | timer_start, timer_stop, timer_toggle | 3 |
| **Total** | | **48** |

## 5. Configuration System

**Format:** JSON only. Profiles stored in `k2deck/config/*.json`.

**Structure:** `profile_name`, `midi_channel`, `midi_device`, `led_color_offsets`, `throttle`, `mappings` (note_on, cc_absolute, cc_relative), `led_defaults`, optional `folders`, `zones`, `integrations`.

**Layers:** A mapping entry can have `layer_1`, `layer_2`, `layer_3` keys. If present, mapping engine uses the current layer's sub-config.

**Folders:** Button sub-pages. Top-level `"folders"` key maps folder names to note_on overrides.

**Zones (multi-K2):** Top-level `"zones"` key maps MIDI channels to separate mapping sets.

**Hot-reload:** `profile_switcher.py` uses watchdog `FileSystemEventHandler` to watch config directory. On change: validate JSON → reload mapping engine.

**Validation:** `MappingEngine._validate_config()` checks required keys, known action types, channel range. Unknown action types log warning, skip.

## 6. LED System

**Hardware:** LEDs controlled by MIDI Note On/Off. Color determined by **note number offset**, NOT velocity.

```
base_note + 0   → Red
base_note + 36  → Amber
base_note + 72  → Green
Note Off        → Off
```

New color overwrites active — no need to send Note Off first.

**Software:** `LedManager` singleton tracks `{base_note: color}` state. Thread-safe with Lock.
- `set_led(note, color)` — send Note On at `note + offset`
- `toggle_led(note, on_color, off_color)` — flip between two colors
- `flash_led(note, color, times)` — blink N times, return to previous state
- `all_off()` — turn off all tracked LEDs
- `get_all_states()` — return current state dict

## 7. Web Architecture

### 7.1 Backend (FastAPI)

28 REST endpoints across 4 routers, all prefixed with `/api`:

| Router | Prefix | Endpoints | Key operations |
|--------|--------|-----------|----------------|
| config | `/api/config` | 5 | GET/PUT config, validate, export/import |
| profiles | `/api/profiles` | 6 | CRUD + activate profile |
| k2 | `/api/k2` | 13 | State, LEDs, layer, folder, analog, MIDI, trigger, timers |
| integrations | `/api/integrations` | 4 | Status, connect/disconnect per integration |

Server listens on `localhost:8420` only (security). CORS allows `localhost:*` via regex.

### 7.2 WebSocket Protocol

Endpoint: `ws://localhost:8420/ws/events`

**Server → Client (9 event types):**

| Event | Data | Trigger |
|-------|------|---------|
| `midi_event` | type, channel, note, cc, value | Every MIDI message |
| `led_change` | note, color, on | LED state change |
| `layer_change` | layer, previous | Layer button press |
| `folder_change` | folder, previous | Folder navigation |
| `connection_change` | connected, port | K2 plug/unplug |
| `integration_change` | name, status | OBS/Spotify/Twitch status |
| `profile_change` | profile, previous | Profile switch |
| `analog_change` | cc, value, control_id | Fader/pot movement |
| `analog_state` | controls[] | Initial state on connect |

**Client → Server (2 commands):**

| Command | Data | Effect |
|---------|------|--------|
| `set_led` | note, color | Change LED via LedManager |
| `trigger_action` | action, ...config | Execute action via create_action |

**Thread safety:** `set_server_loop()` captures the async event loop at startup. `broadcast_sync()` uses `asyncio.run_coroutine_threadsafe()` to bridge MIDI thread to async WebSocket.

### 7.3 Frontend (Vue 3)

**Component tree:**
```
App.vue
├── AppHeader (ConnectionStatus, ProfileDropdown, IntegrationPills)
├── K2Grid (K2Row → K2Control → K2Button/K2Encoder/K2Pot/K2Fader + K2Led)
│   ├── LayerTabs
│   └── FolderBreadcrumb
├── ControlConfig (ActionPicker, ActionForm, LedConfig)
├── MidiMonitor (MidiEventItem)
└── ToastContainer
```

**Stores (Pinia):** config, k2State, analogState, profiles, integrations, midi, ui
**Composables:** useApi (HTTP), useWebSocket (reconnecting WS), useKeyboard (shortcuts)

## 8. MCP Integration

```
Claude Desktop ←(stdio)→ MCP Server ←(HTTP/httpx)→ REST API (:8420)
                                                         ↓
                                                  MIDI + LEDs + Actions
```

**10 tools:** `get_k2_state`, `get_k2_layout`, `set_led`, `set_layer`, `list_profiles`, `get_profile`, `activate_profile`, `get_integrations`, `trigger_action`, `get_timers`

**Pattern:** `mcp.server.Server` with `@app.list_tools()` / `@app.call_tool()` decorators. Each tool calls REST API via `K2DeckClient` (lazy-init singleton, `httpx.AsyncClient`).

**Auto-start:** `ensure_web_server()` checks if port 8420 is open. If not, spawns `python -m k2deck` as orphaned subprocess with `CREATE_NO_WINDOW` flag.

## 9. OSC Bridge

```
K2 Hardware → K2 Deck (MIDI) → OSC UDP → Pure Data (port 9000)
```

K2 Deck owns the MIDI port. Pure Data receives parameter values via OSC.

| Action | Input | Behavior |
|--------|-------|----------|
| `osc_send` | CC absolute | Normalize 0-127 → apply curve → scale → send float |
| `osc_send_relative` | CC relative | Accumulate two's complement deltas → send float |
| `osc_send_trigger` | Note On | Send bang (1.0) or toggle (1.0/0.0) |

**`OscSender`:** Keyed singleton — one persistent UDP socket per (host, port). Thread-safe. Zero external dependencies (custom OSC 1.0 encoder in `core/osc.py`).

## 10. External Integrations

| Integration | Client | Library | Connection | Auth |
|-------------|--------|---------|------------|------|
| Spotify | `core/spotify_client.py` | spotipy | OAuth web flow | Token in `config/spotify_token.json` + keyring |
| OBS | `core/obs_client.py` | obsws-python | WebSocket v5 | Password in config |
| Twitch | `core/twitch_client.py` | twitchAPI | OAuth | Token in keyring |

All clients: singleton pattern, lazy connection (first use), auto-reconnect on failure, graceful degradation (log warning, skip action).

## 11. Persistence

| Data | Location | Format | Updated |
|------|----------|--------|---------|
| Config profiles | `k2deck/config/*.json` | JSON | Manual / hot-reload |
| Analog positions | `~/.k2deck/analog_state.json` | JSON | Debounced 1/sec |
| Counters | `~/.k2deck/counters.json` | JSON | On change |
| Spotify token | `config/spotify_token.json` | JSON | On OAuth refresh |
| API credentials | Windows keyring | OS native | On auth |

Timers are transient — not persisted to disk. Restart = timers gone.

## 12. Technology Decisions

| Decision | Alternative | Rationale |
|----------|-------------|-----------|
| Python (not Node) | Electron | pycaw/pywin32 native Windows, no GUI needed, lighter |
| SendInput/ctypes (not pynput) | pynput keyboard | Hardware scan codes, no stuck keys, works with games |
| pycaw (not nircmd) | subprocess + nircmd | Native API, per-process volume, no shell calls |
| JSON config (not YAML) | YAML/TOML | Native in Python, no deps, sufficient for this use |
| ThreadPoolExecutor (not asyncio) | Full async | pycaw/pywin32/pynput are sync. Thread pool simpler. |
| FastAPI (not Flask) | Flask | Async-native, auto docs, WebSocket built-in |
| Vue 3 + Pinia (not React) | React | Simpler for this scale, Composition API maps well |
| stdio MCP (not HTTP) | HTTP transport | Claude Desktop requires stdio. HTTP client bridges to REST. |
| Custom OSC encoder (not python-osc) | python-osc | Zero deps, <100 LOC, only need send (not receive) |
| System tray (not GUI) | tkinter/Qt | Invisible when working. Tray icon sufficient. |
