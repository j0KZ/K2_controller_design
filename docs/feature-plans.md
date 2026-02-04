# K2 Deck - Feature Plans

## 1. Audio Device Switch

### Objetivo
Cambiar dispositivo de salida/entrada de audio con un botón.

### Implementación

```python
# k2deck/actions/audio_switch.py
from pycaw.pycaw import AudioUtilities, IMMDeviceEnumerator
from comtypes import CLSCTX_ALL

class AudioSwitchAction(Action):
    """Switch default audio output/input device."""

    def execute(self, event):
        # Cycle through configured devices
        # or switch to specific device
```

### Config Format
```json
{
  "name": "Switch Headphones/Speakers",
  "action": "audio_switch",
  "devices": ["Speakers", "Headphones"],
  "type": "output"  // "output" or "input"
}
```

### Dependencias
- `pycaw` (ya instalado)
- `comtypes` (ya instalado)
- Windows PolicyConfig API (para set default device)

### Complejidad: Media-Alta ⚠️
- pycaw puede listar dispositivos ✅
- **CRÍTICO:** pycaw NO puede cambiar el dispositivo default
- Cambiar default requiere PolicyConfig COM interface (~200 LOC adicionales)
- Necesita definir IPolicyConfig interface manualmente con ctypes/comtypes
- Referencia: [AudioDeviceCmdlets](https://github.com/frgnca/AudioDeviceCmdlets)
- Alternativa: usar `pycaw` para listar + `nircmd` para cambiar (dependency externa)

### Archivos a crear
- `k2deck/actions/audio_switch.py`
- `k2deck/core/policy_config.py` (COM interface para cambiar default)

---

## 2. OBS WebSocket

### Objetivo
Controlar OBS Studio: cambiar escenas, toggle sources, start/stop streaming.

### Implementación

```python
# k2deck/actions/obs.py
import obsws_python as obs

class OBSAction(Action):
    """Base class for OBS actions."""
    _client = None

    @classmethod
    def connect(cls, host="localhost", port=4455, password=""):
        cls._client = obs.ReqClient(host=host, port=port, password=password)

class OBSSceneAction(OBSAction):
    """Switch to a specific scene."""

    def execute(self, event):
        scene = self.config.get("scene")
        self._client.set_current_program_scene(scene)

class OBSSourceToggleAction(OBSAction):
    """Toggle source visibility."""

class OBSStreamAction(OBSAction):
    """Start/stop streaming."""

class OBSRecordAction(OBSAction):
    """Start/stop recording."""
```

### Config Format
```json
{
  "name": "Scene: Gaming",
  "action": "obs_scene",
  "scene": "Gaming"
}
```

```json
{
  "name": "Toggle Webcam",
  "action": "obs_source_toggle",
  "scene": "Main",
  "source": "Webcam"
}
```

```json
{
  "name": "Start Stream",
  "action": "obs_stream",
  "mode": "toggle"  // "start", "stop", "toggle"
}
```

### Config Global (OBS connection)
```json
{
  "integrations": {
    "obs": {
      "enabled": true,
      "host": "localhost",
      "port": 4455,
      "password": "your-password"
    }
  }
}
```

### Dependencias
- `obsws-python` (pip install obsws-python)
- OBS Studio con WebSocket plugin (incluido en OBS 28+)

### Complejidad: Media ⚠️
- La librería obsws-python maneja conexión básica ✅
- **Falta considerar:**
  - Reconexión automática si OBS se cierra/reinicia
  - Manejo de errores (OBS no corriendo, password incorrecto)
  - Inicialización lazy (no conectar hasta primera acción OBS)
  - Rate limiting para acciones rápidas
  - Estado de conexión visible en logs/tray

### Archivos a crear
- `k2deck/actions/obs.py`
- `k2deck/core/obs_client.py` (singleton con reconnect logic)

---

## 3. Conditional Actions

### Objetivo
Ejecutar diferentes acciones según contexto (app activa, estado, etc.)

### Implementación

```python
# k2deck/actions/conditional.py
import win32gui
import win32process
import psutil

class ConditionalAction(Action):
    """Execute different actions based on conditions."""

    def execute(self, event):
        conditions = self.config.get("conditions", [])

        for condition in conditions:
            if self._check_condition(condition):
                self._execute_action(condition.get("then"))
                return

        # Execute default if no condition matched
        default = self.config.get("default")
        if default:
            self._execute_action(default)

    def _check_condition(self, condition):
        if "app_focused" in condition:
            return self._is_app_focused(condition["app_focused"])
        if "app_running" in condition:
            return self._is_app_running(condition["app_running"])
        if "state" in condition:
            return self._check_state(condition["state"])
        return False

    def _is_app_focused(self, app_name):
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        return app_name.lower() in process.name().lower()
```

### Config Format
```json
{
  "name": "Context Play/Pause",
  "action": "conditional",
  "conditions": [
    {
      "app_focused": "Spotify.exe",
      "then": { "action": "spotify_play_pause" }
    },
    {
      "app_focused": "vlc.exe",
      "then": { "action": "hotkey", "keys": ["space"] }
    },
    {
      "app_focused": "brave.exe",
      "then": { "action": "hotkey", "keys": ["k"] }
    }
  ],
  "default": { "action": "hotkey", "keys": ["media_play_pause"] }
}
```

### Tipos de condiciones
| Condición | Descripción |
|-----------|-------------|
| `app_focused` | App tiene foco |
| `app_running` | App está corriendo |
| `time_range` | Hora del día |
| `layer` | Layer actual del K2 |
| `toggle_state` | Estado de un toggle |

### Complejidad: Media ⚠️
- Detección de app activa con win32gui ✅
- **Problemas a resolver:**
  - Rendimiento: win32gui + psutil cada vez = ~5-10ms
  - Necesita caché de foreground app (refresh cada 100-200ms)
  - Riesgo de recursión si `then` contiene otro `conditional`
  - Necesita límite de profundidad (max 3 niveles)
  - Action factory para instanciar acciones anidadas dinámicamente
  - Validación de config para prevenir ciclos

### Archivos a crear
- `k2deck/actions/conditional.py`
- `k2deck/core/context.py` (utilidades de contexto + caché)
- `k2deck/core/action_factory.py` (crear acciones desde config dict)

---

## 4. Web UI

### Arquitectura

```
┌─────────────────────────────────────────────────┐
│                   Web Browser                    │
│  ┌─────────────────────────────────────────────┐│
│  │              Vue.js Frontend                 ││
│  │  - Visual mapping editor                    ││
│  │  - Drag & drop actions                      ││
│  │  - Live MIDI monitor                        ││
│  │  - Profile manager                          ││
│  └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
                        │
                   WebSocket
                        │
┌─────────────────────────────────────────────────┐
│              FastAPI Backend                     │
│  ┌─────────────────────────────────────────────┐│
│  │  /api/config     - CRUD configs             ││
│  │  /api/actions    - Available actions        ││
│  │  /api/midi       - MIDI state               ││
│  │  /ws/events      - Live MIDI events         ││
│  └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────┐
│              K2 Deck Core                        │
│  - MappingEngine                                │
│  - MidiListener                                 │
│  - Actions                                      │
└─────────────────────────────────────────────────┘
```

### 4.1 Backend (FastAPI)

```python
# k2deck/web/server.py
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# REST endpoints
@app.get("/api/config")
async def get_config():
    """Get current config."""

@app.put("/api/config")
async def update_config(config: dict):
    """Update and hot-reload config."""

@app.get("/api/actions")
async def get_available_actions():
    """List all available action types with schemas."""

@app.get("/api/midi/devices")
async def get_midi_devices():
    """List MIDI devices."""

# WebSocket for live events
@app.websocket("/ws/events")
async def midi_events(websocket: WebSocket):
    """Stream MIDI events in real-time."""
```

### 4.2 Frontend (Vue.js)

```
k2deck/web/frontend/
├── src/
│   ├── components/
│   │   ├── K2Layout.vue       # Visual K2 representation
│   │   ├── ButtonConfig.vue   # Button config editor
│   │   ├── FaderConfig.vue    # Fader config editor
│   │   ├── EncoderConfig.vue  # Encoder config editor
│   │   ├── ActionPicker.vue   # Action type selector
│   │   ├── MidiMonitor.vue    # Live MIDI display
│   │   └── ProfileList.vue    # Profile manager
│   ├── stores/
│   │   ├── config.js          # Pinia store for config
│   │   └── midi.js            # Pinia store for MIDI state
│   └── App.vue
├── package.json
└── vite.config.js
```

### 4.3 Config Schema (para validación y UI)

```python
# k2deck/core/schema.py
ACTION_SCHEMAS = {
    "hotkey": {
        "properties": {
            "keys": {"type": "array", "items": {"type": "string"}},
            "mode": {"type": "string", "enum": ["tap", "hold", "toggle"]}
        },
        "required": ["keys"]
    },
    "volume": {
        "properties": {
            "target_process": {"type": "string"}
        },
        "required": ["target_process"]
    },
    # ... etc
}
```

### Dependencias
- `fastapi`
- `uvicorn`
- `websockets`
- Vue.js 3 + Vite (frontend)
- Pinia (state management)
- TailwindCSS (styling)

### Complejidad: Alta ⚠️
- Backend: Media (FastAPI es simple) ✅
- **Problemas no considerados:**
  - CORS configuration para desarrollo local
  - Autenticación (al menos token básico para localhost)
  - Hot-reload de config sin reiniciar app
  - Comunicación bidireccional: backend ↔ frontend ↔ K2 core
  - Build/bundle del frontend para distribución
  - Servir frontend estático desde FastAPI en producción
  - WebSocket reconnect en frontend

### Estimación LOC Corregida
- Backend: ~400 LOC ✅
- Frontend: ~3000 LOC (no 1500) - componentes, stores, utilidades, estilos

### Archivos a crear
```
k2deck/web/
├── __init__.py
├── server.py           # FastAPI app + CORS + static files
├── routes/
│   ├── config.py
│   ├── actions.py
│   └── midi.py
├── middleware/
│   └── auth.py         # Token auth para localhost
└── frontend/           # Vue.js app (separado)
    ├── src/
    │   ├── components/
    │   ├── stores/
    │   ├── composables/  # WebSocket, API hooks
    │   └── utils/
    └── dist/           # Built files served by FastAPI
```

---

## 5. Plugin System

### Objetivo
Permitir extensiones sin modificar el código core.

### Arquitectura

```
k2deck/
├── plugins/
│   ├── __init__.py
│   └── loader.py
│
~/.k2deck/plugins/      # User plugins
├── my_plugin/
│   ├── __init__.py
│   ├── plugin.json     # Metadata
│   └── actions.py      # Custom actions
```

### Plugin Interface

```python
# k2deck/plugins/base.py
class K2Plugin:
    """Base class for plugins."""

    name: str
    version: str
    actions: dict[str, type[Action]]  # Action types to register

    def on_load(self, app):
        """Called when plugin loads."""
        pass

    def on_unload(self):
        """Called when plugin unloads."""
        pass
```

### Plugin Manifest
```json
// plugin.json
{
  "name": "OBS Advanced",
  "version": "1.0.0",
  "author": "j0kz",
  "description": "Advanced OBS controls",
  "actions": {
    "obs_replay": "ObsReplayAction",
    "obs_screenshot": "ObsScreenshotAction"
  },
  "dependencies": ["obsws-python"]
}
```

### Plugin Loader

```python
# k2deck/plugins/loader.py
class PluginLoader:
    def __init__(self, plugin_dirs: list[Path]):
        self.plugins = {}

    def discover(self):
        """Find all plugins in plugin directories."""

    def load(self, plugin_name: str):
        """Load and initialize a plugin."""

    def unload(self, plugin_name: str):
        """Unload a plugin."""

    def get_actions(self) -> dict[str, type[Action]]:
        """Get all actions from loaded plugins."""
```

### Complejidad: Alta ⚠️
- Cargar módulos Python dinámicamente ✅
- **Problemas no considerados:**
  - Seguridad: plugins pueden ejecutar código arbitrario
  - Gestión de dependencias: ¿pip install automático? ¿venv separado?
  - Versionado: compatibilidad plugin ↔ K2 Deck version
  - Hot-reload de plugins sin reiniciar app
  - Conflictos de nombres entre plugins
  - Prioridad de acciones (plugin vs built-in)
  - UI para gestionar plugins (enable/disable/configure)
  - Documentación/template para crear plugins

### Mitigaciones de Seguridad
- Plugins solo desde directorio específico (~/.k2deck/plugins)
- Warning en logs cuando plugin se carga
- Opción para deshabilitar plugins en config
- NO ejecutar pip automáticamente (documentar deps requeridas)

### Archivos a crear
```
k2deck/plugins/
├── __init__.py
├── base.py         # Plugin base class
├── loader.py       # Plugin discovery and loading
├── registry.py     # Action registration + conflict resolution
└── validator.py    # Validate plugin manifest
```

---

## Orden de Implementación Recomendado

| # | Feature | Razón |
|---|---------|-------|
| 1 | **Audio Device Switch** | Pequeño, útil, no requiere deps nuevas |
| 2 | **Conditional Actions** | Pequeño, muy útil para workflows |
| 3 | **OBS WebSocket** | Media, popular, bien documentado |
| 4 | **Web UI Backend** | Necesario antes del frontend |
| 5 | **Web UI Frontend** | Depende del backend |
| 6 | **Plugin System** | Último, requiere arquitectura estable |

---

## Estimación de Trabajo (Corregida)

| Feature | Archivos | LOC aprox | Deps nuevas | Notas |
|---------|----------|-----------|-------------|-------|
| Audio Switch | 2 | ~350 | - | PolicyConfig COM interface |
| Conditional | 3 | ~300 | - | + action factory + context cache |
| OBS | 2 | ~400 | obsws-python | + reconnect logic |
| Web Backend | 6 | ~600 | fastapi, uvicorn | + auth + middleware |
| Web Frontend | 15+ | ~3000 | vue, vite, tailwind | Estimación realista |
| Plugins | 5 | ~500 | - | + validator + conflict resolution |

**Total: ~5150 LOC** (vs ~2850 original)

[ADJUSTED: optimistic → realistic]

---

## Stream Deck Features No Considerados

Features de Stream Deck que K2 Deck aún no tiene planificados:

### Ya Implementados ✅
| Feature | Estado |
|---------|--------|
| Multi-action con delays | ✅ `multi_toggle` action |
| Hotkeys | ✅ `hotkey` action |
| Per-app volume | ✅ `volume` action |
| Toggle states | ✅ LED toggle mode |
| Layers | ✅ Software layers |

### Falta Implementar (Prioridad Alta)
| Feature | Descripción | Complejidad |
|---------|-------------|-------------|
| **Profile auto-switch** | Cambiar perfil según app activa | Media |
| **Website open** | Abrir URL en browser default | Baja |
| **System commands** | Shutdown, sleep, lock, restart | Baja |
| **Sound playback** | Reproducir archivo de audio | Media |

### Falta Implementar (Prioridad Media)
| Feature | Descripción | Complejidad |
|---------|-------------|-------------|
| **Folders/Pages** | Botón que abre "sub-página" de acciones | Alta |
| **Timer/Stopwatch** | Mostrar tiempo en pantalla (no aplicable a K2 sin display) | N/A |
| **Counter** | Incrementar/decrementar valor persistente | Baja |
| **Text-to-Speech** | Leer texto en voz alta | Media |
| **Clipboard actions** | Pegar texto predefinido | Baja |

### No Aplicable a K2 ❌
| Feature | Razón |
|---------|-------|
| Animated icons | K2 solo tiene LEDs tricolor |
| Title/text on buttons | K2 no tiene display |
| Icon customization | K2 no tiene display |
| Screensaver | K2 no tiene display |

### Nuevas Acciones Sugeridas

```python
# k2deck/actions/system.py (ampliar)
class OpenURLAction(Action):
    """Open URL in default browser."""
    # config: { "url": "https://..." }

class SystemCommandAction(Action):
    """Execute system command: shutdown, sleep, lock, restart."""
    # config: { "command": "lock" }  # lock, sleep, shutdown, restart, hibernate

class SoundPlayAction(Action):
    """Play audio file."""
    # config: { "file": "path/to/sound.mp3", "volume": 80 }

class ClipboardPasteAction(Action):
    """Paste predefined text."""
    # config: { "text": "Hello world" }

class CounterAction(Action):
    """Increment/decrement persistent counter."""
    # config: { "name": "my_counter", "operation": "increment" }
```

### Profile Auto-Switch (Detalle)

```python
# k2deck/core/profile_switcher.py
class ProfileAutoSwitcher:
    """Watch foreground app and switch profiles automatically."""

    def __init__(self, rules: list[dict]):
        # rules: [{"app": "obs64.exe", "profile": "streaming"}, ...]
        self._rules = rules
        self._current_profile = None

    def check_and_switch(self):
        """Called from context cache update."""
        foreground = get_foreground_app()
        for rule in self._rules:
            if rule["app"].lower() in foreground.lower():
                if self._current_profile != rule["profile"]:
                    self._switch_profile(rule["profile"])
                return
```

### Config para Auto-Switch

```json
{
  "profile_auto_switch": {
    "enabled": true,
    "rules": [
      { "app": "obs64.exe", "profile": "streaming" },
      { "app": "Adobe Premiere", "profile": "video_editing" },
      { "app": "Ableton", "profile": "music" }
    ],
    "default_profile": "default"
  }
}
```

---

## Orden de Implementación Actualizado

| # | Feature | Razón | LOC |
|---|---------|-------|-----|
| 1 | **System Commands** | Trivial, muy útil | ~50 |
| 2 | **Open URL** | Trivial, muy útil | ~30 |
| 3 | **Clipboard Paste** | Trivial, muy útil | ~40 |
| 4 | **Conditional Actions** | Base para auto-switch | ~300 |
| 5 | **Profile Auto-Switch** | Usa conditional, muy útil | ~150 |
| 6 | **Audio Device Switch** | Media, popular request | ~350 |
| 7 | **OBS WebSocket** | Media, streaming users | ~400 |
| 8 | **Sound Playback** | Media, nice-to-have | ~100 |
| 9 | **Web UI Backend** | Necesario antes frontend | ~600 |
| 10 | **Web UI Frontend** | Depende del backend | ~3000 |
| 11 | **Plugin System** | Último, requiere estabilidad | ~500 |

---

## Testing Strategy

### Estado Actual (107 tests ✅)

| Módulo | Tests | Cobertura |
|--------|-------|-----------|
| `core/keyboard.py` | 25 | Scan codes, INPUT structures, hotkeys |
| `core/layers.py` | 13 | Layer state, callbacks, LED colors |
| `core/mapping_engine.py` | 11 | Config loading, resolution, multi-zone |
| `core/throttle.py` | 9 | Rate limiting, debounce |
| `feedback/led_colors.py` | 10 | Color offsets, note calculation |
| `actions/hotkey.py` | 7 | Tap, hold modes, relative |
| `actions/multi.py` | 14 | Sequence execution, toggle state |
| `actions/volume.py` | 15 | Session cache, MIDI→volume mapping |

### Tests Requeridos por Feature

| Feature | Tests Nuevos | Estrategia |
|---------|--------------|------------|
| **System Commands** | ~5 | Mock `os.system`, `subprocess` |
| **Open URL** | ~3 | Mock `webbrowser.open` |
| **Clipboard Paste** | ~4 | Mock `pyperclip` |
| **Conditional Actions** | ~15 | Mock `win32gui`, test cache, recursion limits |
| **Profile Auto-Switch** | ~8 | Mock context, test rule matching |
| **Audio Device Switch** | ~10 | Mock PolicyConfig COM, test cycling |
| **OBS WebSocket** | ~12 | Mock `obsws-python`, test reconnect |
| **Sound Playback** | ~5 | Mock audio playback library |
| **Web UI Backend** | ~20 | FastAPI TestClient, WebSocket mocks |
| **Web UI Frontend** | ~30 | Vue Test Utils, Vitest |
| **Plugin System** | ~15 | Test loader, conflicts, validation |

### Reglas de Testing

1. **Cada feature nuevo debe incluir tests**
   - Mínimo 80% cobertura del código nuevo
   - Tests de edge cases (null, empty, invalid input)
   - Tests de integración donde aplique

2. **Mocking strategy**
   - MIDI hardware → siempre mock
   - Windows APIs (pycaw, win32gui) → mock para unit tests
   - External APIs (Spotify, OBS) → mock con fixtures realistas

3. **Comando de verificación**
   ```bash
   # Run all tests before commit
   python -m pytest -v

   # Run with coverage
   python -m pytest --cov=k2deck --cov-report=term-missing
   ```

4. **CI/CD**
   - Tests deben pasar antes de merge
   - Coverage no debe bajar del 70%

### Módulos Sin Tests (Aceptable)

| Módulo | Razón |
|--------|-------|
| `core/midi_listener.py` | Hardware dependency |
| `core/midi_output.py` | Hardware dependency |
| `core/spotify_client.py` | OAuth flow, API calls |
| `tools/*.py` | CLI tools, manual testing |
| `k2deck.py` | Main app, integration testing |
