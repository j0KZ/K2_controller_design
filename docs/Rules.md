# K2 Deck — Development Rules

## 1. Code Style

- **Python 3.12+** features: type hints, match/case, f-strings, `X | Y` union types
- **Type hints** on all function signatures
- **Docstrings:** Google style, brief
- **Max file length:** 300 LOC — if exceeding, extract to submodules
- **Import order:** stdlib → third-party → local, separated by blank lines
- **Naming:**
  - Files: `snake_case.py`
  - Classes: `PascalCase`
  - Functions/methods: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
  - Config keys: `snake_case`

## 2. Error Handling

- **MIDI operations:** Always wrap in try/except — ports disconnect any time
- **External API calls** (Spotify, OBS, Twitch, pycaw): try/except with logging
- **Actions:** Never crash on a single failed action — log and continue listening
- **Action ABC contract:** `execute()` must not block >100ms, must not raise
- **MIDI port loss:** Auto-reconnect every 5 seconds, notify via system tray
- **Integration failure:** Graceful degradation — fall back to alternative (e.g., Spotify API fails → media keys) or skip with warning

## 3. Logging

- Use `logging` module, **never `print()`**
- **Levels:**
  - DEBUG: MIDI messages (high volume, toggleable)
  - INFO: Action execution
  - WARNING: Recoverable errors
  - ERROR: Failures
- **Format:** `[%(asctime)s] %(levelname)s %(name)s: %(message)s`
- MIDI message logging must be toggleable (60+ msgs/sec from faders)

## 4. Testing Rules

### 4.1 General

| Stack | Framework | Config |
|-------|-----------|--------|
| Backend | pytest + pytest-asyncio | `pytest.ini`: `asyncio_mode = auto` |
| Frontend | vitest + @vue/test-utils + happy-dom | `vitest.config.js` |

- Mock MIDI devices — no hardware dependency in unit tests
- Test config loading with valid/invalid JSON
- Test action execution with mocked system calls

### 4.2 Dangerous Function Testing — MANDATORY

When testing functions that perform dangerous system operations (sleep, shutdown, restart, hibernate, delete):

1. **ALWAYS** run `pytest --collect-only` FIRST on new test files
2. **Use `patch.dict()`** for class-level dicts — `@patch` decorators won't intercept functions captured at import time:
   ```python
   with patch.dict(SystemAction.COMMANDS, {"sleep": MagicMock()}):
       action.execute(event)
   ```
3. **Mark direct tests** with `@pytest.mark.skip(reason="Dangerous: could execute if mock fails")`
4. **Why:** A failed mock = real execution. A test once put the developer's PC to sleep.

### 4.3 Singleton Reset Pattern

Reset singletons in test fixtures to prevent state leaking between tests:

| Singleton | Reset |
|-----------|-------|
| `AnalogStateManager` | `AnalogStateManager._instance = None` |
| `TimerManager` | `TimerManager._instance = None` |
| `K2DeckClient` (MCP) | `client_module._client = None` |
| `LedManager` | Fresh instance per test (not global singleton in tests) |
| `OscSender` | `OscSender._instances = {}` |
| `ConnectionManager` | `websocket.manager._connection_manager = None` |

### 4.4 Backend Mocking Patterns

- **Lazy imports in routes:** Routes use `from k2deck.feedback.led_manager import get_led_manager` inside functions. Patch at that module path:
  ```python
  @patch("k2deck.feedback.led_manager.get_led_manager")
  ```
- **uvicorn:** Imported locally in server functions — `patch.object(uvicorn, "run")`
- **Spotify:** `get_spotify_client` doesn't exist — use `patch.dict(sys.modules, ...)` with fake module
- **create_action:** Takes single dict with `"action"` key — NOT two args
- **Test app:** Patch `CONFIG_DIR` in both `config` and `profiles` routes
- **MCP tests:** Import `call_tool`/`list_tools` directly, patch `get_client()` with `AsyncMock`

### 4.5 Frontend Mocking Patterns

- **Always** `setActivePinia(createPinia())` in `beforeEach`
- Mock `useApi` with `vi.mock('@/composables/useApi', ...)` — return different responses based on path argument
- Components that trigger API calls on mount (IntegrationPills, ProfileDropdown): mock must return valid shaped data
- ControlConfig: clicking close clears selection, causing re-render crash — parent App.vue controls unmounting via `v-if`

## 5. Safety Protocols

### 5.1 Before Modifying Code
- **Read** the file before editing — never assume file contents
- **Glob/Grep** to verify a file/function/class exists before referencing it
- **Never** invent API endpoints — verify in router files first
- **Never** reference imports or paths without confirming they exist
- Mark unverified assumptions with `[UNVERIFIED]` — resolve before implementation

### 5.2 After Editing Code
- **Python:** Verify syntax with `python -c "import ast; ast.parse(open('file').read())"`
- **JS:** Verify with `node --check file.js` (not for JSX — use `npm run build`)
- Verify all new imports exist (Glob for the module path)
- If editing a function signature: Grep all callers and update them

### 5.3 Deletion Safety
When asked to delete or remove:
1. List ALL affected files
2. Show git status
3. Suggest alternatives (archive, gitignore, move)
4. Require explicit confirmation

## 6. Configuration Rules

- **JSON format only** — no YAML/TOML
- All config in `k2deck/config/` directory
- Profile files: `{profile_name}.json`
- **Validate on load** — fail fast with clear error messages
- Use `json.loads()` with schema validation, not blind key access
- Unknown action types → log warning, skip (don't crash)

## 7. MIDI-Specific Rules

- **Never block the MIDI listener** — all actions execute in ThreadPoolExecutor(max_workers=4)
- **Zero hardcoded MIDI mappings** — everything comes from JSON config
- **Throttle CC messages** — faders send 60+ msgs/sec. Rate-limit via `core/throttle.py` (~30Hz for general, ~20Hz for volume)
- **LED colors are NOTE OFFSETS, not velocity** — red=+0, amber=+36, green=+72. Sending velocity values WILL NOT WORK.
- **K2 encoder CC values:** Two's complement (1-63=CW, 65-127=CCW). Not absolute.
- **0-indexed vs 1-indexed:** MIDI channels — mido uses 0-indexed, K2 UI shows 1-indexed. Always verify which convention the API expects.
- **Latching layers must be OFF** for free LED control. If ON, layer dictates color.

## 8. Architecture Rules

- **No GUI window** — system tray only. The app must be invisible when working.
- **Single MIDI port access** — detect and warn if another app has the K2 port.
- **Don't auto-focus apps on hotkey** — Discord/Spotify hotkeys work globally. Stealing focus breaks user workflow. Window focus is opt-in only.
- **Discord global hotkeys** must be configured by the user in Discord Settings > Keybinds.
- **Graceful degradation** — if Spotify API fails → fall back to media keys. If pycaw fails → log and skip. If K2 disconnects → retry loop.
- **Config is king** — zero hardcoded mappings, all behavior from JSON.
