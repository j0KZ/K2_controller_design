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

## Stream Deck vs K2 Deck - Estado Actualizado

### ✅ Implementado (Paridad o Mejor)

| Feature | Stream Deck | K2 Deck | Estado |
|---------|-------------|---------|--------|
| Hotkeys | ✅ | ✅ | `hotkey` (tap, hold, toggle) |
| Multi-action con delays | ✅ | ✅ | `multi`, `multi_toggle` |
| System commands | ✅ | ✅ | `system` (lock, sleep, shutdown, etc.) |
| Open URL | ✅ | ✅ | `open_url` |
| Clipboard paste | ✅ | ✅ | `clipboard_paste` |
| Sound playback | ✅ | ✅ | `sound_play`, `sound_stop` |
| Audio device switch | ✅ | ✅ | `audio_switch`, `audio_list` |
| OBS control | ✅ | ✅ | `obs_scene`, `obs_stream`, etc. |
| Profile auto-switch | ✅ | ✅ | `profile_switcher.py` |
| Conditional actions | ✅ | ✅ | `conditional` |
| Toggle states | ✅ | ✅ | LED toggle mode |
| Layers/Pages | ✅ | ✅ | Software layers (3) |
| Window focus/launch | ✅ | ✅ | `focus`, `launch` |
| Per-app volume | Plugin | ✅ | `volume` action |
| Spotify | Plugin ($5) | ✅ | **Gratis** - Full API |
| Counter | ✅ | ✅ | `counter` action |
| Text-to-Speech | ✅ | ✅ | `tts` action (Windows SAPI) |

### 🚀 K2 Deck Exclusivo (Mejor que Stream Deck)

| Feature | Descripción |
|---------|-------------|
| **Encoders** | Control rotativo para volumen/seek (SD no tiene) |
| **Faders** | Control analógico continuo (SD no tiene) |
| **Multi-K2** | Dos controladores como uno |
| **MIDI output** | Controlar otros dispositivos MIDI |

### ❌ Pendiente de Implementar

| Feature | Stream Deck | Prioridad | Plan |
|---------|-------------|-----------|------|
| Folders/Sub-pages | ✅ | Alta | Ver §6 |
| Twitch integration | ✅ | Media | Ver §8 |
| Web UI | ✅ | Alta | Ver §4 (existente) |
| Plugin System | ✅ | Baja | Ver §5 (existente) |

### ❌ No Aplicable a K2

| Feature | Razón |
|---------|-------|
| Animated icons | K2 solo tiene LEDs tricolor |
| Title/text on buttons | K2 no tiene display |
| Icon customization | K2 no tiene display |
| Screensaver | K2 no tiene display |
| Timer display | K2 no tiene display |

---

## 6. Folders / Sub-Pages

### Objetivo
Permitir que un botón "abra" un sub-conjunto de acciones, multiplicando la cantidad de controles disponibles sin cambiar de layer físico.

### Concepto
- Un botón configurado como `folder` cambia temporalmente los mappings de otros botones
- LEDs indican que estamos en un folder (todos amber por ejemplo)
- Presionar el mismo botón (o uno de "back") regresa al mapping principal

### Implementación

```python
# k2deck/core/folders.py
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class FolderManager:
    """Manages folder navigation for button sub-pages."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._current_folder: str | None = None
        self._folder_stack: list[str] = []
        self._callbacks: list[Callable] = []
        self._initialized = True

    @property
    def current_folder(self) -> str | None:
        """Get current active folder name."""
        return self._current_folder

    @property
    def in_folder(self) -> bool:
        """Check if we're inside a folder."""
        return self._current_folder is not None

    def enter_folder(self, folder_name: str) -> None:
        """Enter a folder."""
        if self._current_folder:
            self._folder_stack.append(self._current_folder)
        self._current_folder = folder_name
        logger.info("Entered folder: %s", folder_name)
        self._notify_callbacks()

    def exit_folder(self) -> None:
        """Exit current folder (go back)."""
        if self._folder_stack:
            self._current_folder = self._folder_stack.pop()
        else:
            self._current_folder = None
        logger.info("Exited to: %s", self._current_folder or "root")
        self._notify_callbacks()

    def exit_to_root(self) -> None:
        """Exit all folders, return to root."""
        self._current_folder = None
        self._folder_stack.clear()
        logger.info("Exited to root")
        self._notify_callbacks()

    def register_callback(self, callback: Callable) -> None:
        """Register callback for folder changes."""
        self._callbacks.append(callback)

    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(self._current_folder)
            except Exception as e:
                logger.error("Folder callback error: %s", e)


# k2deck/actions/folder.py
class FolderAction(Action):
    """Enter a folder (sub-page of actions)."""

    def __init__(self, config: dict):
        super().__init__(config)
        self._folder = config.get("folder", "")

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        from k2deck.core.folders import FolderManager
        FolderManager().enter_folder(self._folder)


class FolderBackAction(Action):
    """Exit current folder (go back one level)."""

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        from k2deck.core.folders import FolderManager
        FolderManager().exit_folder()


class FolderRootAction(Action):
    """Exit all folders, return to root."""

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        from k2deck.core.folders import FolderManager
        FolderManager().exit_to_root()
```

### Config Format

```json
{
  "mappings": {
    "note_on": {
      "36": {
        "name": "Open OBS Folder",
        "action": "folder",
        "folder": "obs_controls"
      }
    }
  },
  "folders": {
    "obs_controls": {
      "note_on": {
        "36": { "action": "folder_back", "name": "Back" },
        "37": { "action": "obs_scene", "scene": "Gaming" },
        "38": { "action": "obs_scene", "scene": "Desktop" },
        "39": { "action": "obs_stream", "mode": "toggle" },
        "40": { "action": "obs_record", "mode": "toggle" }
      }
    }
  }
}
```

### Integración con MappingEngine

```python
# En mapping_engine.py, modificar resolve():
def resolve(self, event: "MidiEvent") -> tuple[Action | None, dict | None]:
    # Check if in folder
    from k2deck.core.folders import FolderManager
    folder_mgr = FolderManager()

    if folder_mgr.in_folder:
        # Look in folder mappings first
        folder_mappings = self._config.get("folders", {}).get(folder_mgr.current_folder, {})
        # ... resolve from folder_mappings

    # Fall back to regular mappings
    # ... existing logic
```

### Complejidad: Media ⚠️
- Lógica simple de stack para navegación
- **Consideraciones:**
  - Integración con layers (folder per layer?)
  - LED feedback para indicar folder activo
  - Timeout para auto-exit de folder?
  - Máximo depth de folders anidados (3)

### Archivos a crear
- `k2deck/core/folders.py` (~100 LOC)
- `k2deck/actions/folder.py` (~60 LOC)
- Modificar `k2deck/core/mapping_engine.py` (~30 LOC)

### Tests
- ~10 tests: enter/exit/stack/root/callbacks

---

## 7. Counter Action

### Objetivo
Mantener un contador persistente que se puede incrementar/decrementar con botones, útil para tracking (kills, reps, pomodoros, etc.)

### Implementación

```python
# k2deck/core/counters.py
import json
import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

class CounterManager:
    """Manages persistent counters."""

    _instance = None
    COUNTERS_FILE = Path.home() / ".k2deck" / "counters.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._counters: dict[str, int] = {}
        self._callbacks: dict[str, list[Callable]] = {}
        self._load()
        self._initialized = True

    def _load(self) -> None:
        """Load counters from disk."""
        try:
            if self.COUNTERS_FILE.exists():
                self._counters = json.loads(self.COUNTERS_FILE.read_text())
                logger.info("Loaded %d counters", len(self._counters))
        except Exception as e:
            logger.warning("Failed to load counters: %s", e)
            self._counters = {}

    def _save(self) -> None:
        """Save counters to disk."""
        try:
            self.COUNTERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.COUNTERS_FILE.write_text(json.dumps(self._counters, indent=2))
        except Exception as e:
            logger.error("Failed to save counters: %s", e)

    def get(self, name: str) -> int:
        """Get counter value."""
        return self._counters.get(name, 0)

    def set(self, name: str, value: int) -> None:
        """Set counter value."""
        self._counters[name] = value
        self._save()
        self._notify(name, value)
        logger.info("Counter '%s' = %d", name, value)

    def increment(self, name: str, amount: int = 1) -> int:
        """Increment counter, return new value."""
        value = self.get(name) + amount
        self.set(name, value)
        return value

    def decrement(self, name: str, amount: int = 1) -> int:
        """Decrement counter, return new value."""
        value = self.get(name) - amount
        self.set(name, value)
        return value

    def reset(self, name: str) -> None:
        """Reset counter to 0."""
        self.set(name, 0)

    def register_callback(self, name: str, callback: Callable[[int], None]) -> None:
        """Register callback for counter changes."""
        if name not in self._callbacks:
            self._callbacks[name] = []
        self._callbacks[name].append(callback)

    def _notify(self, name: str, value: int) -> None:
        """Notify callbacks for counter."""
        for callback in self._callbacks.get(name, []):
            try:
                callback(value)
            except Exception as e:
                logger.error("Counter callback error: %s", e)


# k2deck/actions/counter.py
class CounterAction(Action):
    """Increment/decrement/reset a persistent counter."""

    def __init__(self, config: dict):
        super().__init__(config)
        self._name = config.get("name", "default")
        self._operation = config.get("operation", "increment")  # increment, decrement, reset, set
        self._amount = config.get("amount", 1)
        self._value = config.get("value", 0)  # For "set" operation

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        from k2deck.core.counters import CounterManager
        mgr = CounterManager()

        if self._operation == "increment":
            value = mgr.increment(self._name, self._amount)
        elif self._operation == "decrement":
            value = mgr.decrement(self._name, self._amount)
        elif self._operation == "reset":
            mgr.reset(self._name)
            value = 0
        elif self._operation == "set":
            mgr.set(self._name, self._value)
            value = self._value
        else:
            return

        logger.info("Counter '%s': %d", self._name, value)
```

### Config Format

```json
{
  "36": {
    "name": "Increment Kills",
    "action": "counter",
    "counter": "kills",
    "operation": "increment"
  },
  "37": {
    "name": "Decrement Kills",
    "action": "counter",
    "counter": "kills",
    "operation": "decrement"
  },
  "38": {
    "name": "Reset Kills",
    "action": "counter",
    "counter": "kills",
    "operation": "reset"
  }
}
```

### Complejidad: Baja ✅
- JSON persistence simple
- Sin display, solo log output
- Callbacks para futura integración con Web UI

### Archivos a crear
- `k2deck/core/counters.py` (~80 LOC)
- `k2deck/actions/counter.py` (~50 LOC)

### Tests
- ~8 tests: get/set/increment/decrement/reset/persistence/callbacks

---

## 8. Twitch Integration

### Objetivo
Integración con Twitch para streamers: chat commands, markers, clips, predictions.

### Implementación

```python
# k2deck/core/twitch_client.py
import logging
import webbrowser
from typing import Any

logger = logging.getLogger(__name__)

# Optional dependency
try:
    from twitchAPI.twitch import Twitch
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.type import AuthScope
    HAS_TWITCH = True
except ImportError:
    HAS_TWITCH = False


class TwitchClientManager:
    """Singleton manager for Twitch API connection."""

    _instance = None
    SCOPES = [
        AuthScope.CHANNEL_MANAGE_BROADCAST,  # Markers, title, game
        AuthScope.CLIPS_EDIT,                 # Create clips
        AuthScope.CHANNEL_MANAGE_PREDICTIONS, # Predictions
        AuthScope.CHAT_EDIT,                  # Send chat messages
        AuthScope.CHAT_READ,                  # Read chat
    ]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._twitch: Any = None
        self._user_id: str | None = None
        self._client_id: str = ""
        self._client_secret: str = ""
        self._connected = False
        self._initialized = True

    def configure(self, client_id: str, client_secret: str) -> None:
        """Configure Twitch API credentials."""
        self._client_id = client_id
        self._client_secret = client_secret

    @property
    def is_available(self) -> bool:
        return HAS_TWITCH

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Authenticate with Twitch."""
        if not HAS_TWITCH:
            logger.warning("twitchAPI not installed. Run: pip install twitchAPI")
            return False

        try:
            self._twitch = await Twitch(self._client_id, self._client_secret)
            auth = UserAuthenticator(self._twitch, self.SCOPES)
            token, refresh = await auth.authenticate()
            await self._twitch.set_user_authentication(token, self.SCOPES, refresh)

            # Get user ID
            users = await self._twitch.get_users()
            self._user_id = users.data[0].id
            self._connected = True
            logger.info("Connected to Twitch as user %s", self._user_id)
            return True
        except Exception as e:
            logger.error("Twitch connection failed: %s", e)
            return False

    async def create_marker(self, description: str = "") -> bool:
        """Create a stream marker."""
        if not self._connected:
            return False
        try:
            await self._twitch.create_stream_marker(self._user_id, description)
            logger.info("Twitch marker created: %s", description)
            return True
        except Exception as e:
            logger.warning("Failed to create marker: %s", e)
            return False

    async def create_clip(self) -> str | None:
        """Create a clip, return clip URL."""
        if not self._connected:
            return None
        try:
            result = await self._twitch.create_clip(self._user_id)
            clip_id = result.data[0].id
            logger.info("Twitch clip created: %s", clip_id)
            return f"https://clips.twitch.tv/{clip_id}"
        except Exception as e:
            logger.warning("Failed to create clip: %s", e)
            return None

    async def send_chat(self, message: str) -> bool:
        """Send chat message."""
        if not self._connected:
            return False
        try:
            await self._twitch.send_chat_message(self._user_id, self._user_id, message)
            logger.info("Chat sent: %s", message[:50])
            return True
        except Exception as e:
            logger.warning("Failed to send chat: %s", e)
            return False

    async def update_title(self, title: str) -> bool:
        """Update stream title."""
        if not self._connected:
            return False
        try:
            await self._twitch.modify_channel_information(self._user_id, title=title)
            logger.info("Stream title updated: %s", title)
            return True
        except Exception as e:
            logger.warning("Failed to update title: %s", e)
            return False


# k2deck/actions/twitch.py
import asyncio

class TwitchMarkerAction(Action):
    """Create a Twitch stream marker."""

    def __init__(self, config: dict):
        super().__init__(config)
        self._description = config.get("description", "")

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        from k2deck.core.twitch_client import TwitchClientManager
        client = TwitchClientManager()
        if not client.is_available:
            return

        asyncio.create_task(client.create_marker(self._description))


class TwitchClipAction(Action):
    """Create a Twitch clip."""

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        from k2deck.core.twitch_client import TwitchClientManager
        client = TwitchClientManager()
        if not client.is_available:
            return

        asyncio.create_task(client.create_clip())


class TwitchChatAction(Action):
    """Send a chat message."""

    def __init__(self, config: dict):
        super().__init__(config)
        self._message = config.get("message", "")

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        from k2deck.core.twitch_client import TwitchClientManager
        client = TwitchClientManager()
        if not client.is_available:
            return

        asyncio.create_task(client.send_chat(self._message))
```

### Config Format

```json
{
  "integrations": {
    "twitch": {
      "enabled": true,
      "client_id": "your-client-id",
      "client_secret": "your-client-secret"
    }
  }
}
```

```json
{
  "36": { "action": "twitch_marker", "description": "Highlight" },
  "37": { "action": "twitch_clip" },
  "38": { "action": "twitch_chat", "message": "Thanks for the follow!" }
}
```

### Dependencias
- `twitchAPI` (pip install twitchAPI)
- Twitch Developer Application (client_id, client_secret)

### Complejidad: Media ⚠️
- OAuth flow similar a Spotify
- Async API requires careful integration
- Rate limits to consider

### Archivos a crear
- `k2deck/core/twitch_client.py` (~200 LOC)
- `k2deck/actions/twitch.py` (~100 LOC)

### Tests
- ~10 tests: mock twitchAPI, test actions

---

## 9. Text-to-Speech

### Objetivo
Reproducir texto como voz, útil para alertas o accesibilidad.

### Implementación

```python
# k2deck/actions/tts.py
import logging
from typing import TYPE_CHECKING

from k2deck.actions.base import Action

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)

# Optional: use Windows SAPI or pyttsx3
try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False


class TTSAction(Action):
    """Speak text using text-to-speech."""

    _engine = None

    def __init__(self, config: dict):
        super().__init__(config)
        self._text = config.get("text", "")
        self._rate = config.get("rate", 150)  # Words per minute
        self._volume = config.get("volume", 1.0)  # 0.0 to 1.0

    @classmethod
    def _get_engine(cls):
        """Get or create TTS engine."""
        if cls._engine is None and HAS_TTS:
            cls._engine = pyttsx3.init()
        return cls._engine

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        if not HAS_TTS:
            logger.warning("pyttsx3 not installed. Run: pip install pyttsx3")
            return

        if not self._text:
            logger.warning("TTSAction: no text configured")
            return

        engine = self._get_engine()
        if engine:
            engine.setProperty('rate', self._rate)
            engine.setProperty('volume', self._volume)
            engine.say(self._text)
            engine.runAndWait()
            logger.info("TTS: %s", self._text[:50])
```

### Config Format

```json
{
  "36": {
    "action": "tts",
    "text": "Stream starting in 5 minutes",
    "rate": 150,
    "volume": 0.8
  }
}
```

### Dependencias
- `pyttsx3` (pip install pyttsx3) - opcional
- Windows SAPI (built-in, no deps)

### Complejidad: Baja ✅

### Archivos a crear
- `k2deck/actions/tts.py` (~50 LOC)

### Tests
- ~5 tests: mock pyttsx3

---

## Orden de Implementación Actualizado

| # | Feature | Estado | LOC | Prioridad |
|---|---------|--------|-----|-----------|
| 1 | Audio Device Switch | ✅ DONE | ~350 | - |
| 2 | OBS WebSocket | ✅ DONE | ~470 | - |
| 3 | Conditional Actions | ✅ DONE | ~300 | - |
| 4 | Sound Playback | ✅ DONE | ~170 | - |
| 5 | Profile Auto-Switch | ✅ DONE | ~150 | - |
| 6 | **Counter** | ✅ DONE | ~130 | - |
| 7 | **Text-to-Speech** | ✅ DONE | ~90 | - |
| 8 | **Folders/Pages** | ❌ TODO | ~190 | Alta |
| 9 | **Twitch Integration** | ❌ TODO | ~300 | Media |
| 10 | Web UI Backend | ❌ TODO | ~600 | Alta |
| 11 | Web UI Frontend | ❌ TODO | ~3000 | Alta |
| 12 | Plugin System | ❌ TODO | ~500 | Baja |

---

## Testing Strategy

### Estado Actual (262 tests ✅, 6 skipped)

| Módulo | Tests | Cobertura |
|--------|-------|-----------|
| `core/keyboard.py` | 25 | Scan codes, INPUT structures, hotkeys |
| `core/layers.py` | 13 | Layer state, callbacks, LED colors |
| `core/mapping_engine.py` | 11 | Config loading, resolution, multi-zone |
| `core/throttle.py` | 13 | Rate limiting, debounce |
| `core/obs_client.py` | 19 | Connection, reconnect, operations |
| `feedback/led_colors.py` | 10 | Color offsets, note calculation |
| `actions/hotkey.py` | 7 | Tap, hold modes, relative |
| `actions/multi.py` | 14 | Sequence execution, toggle state |
| `actions/volume.py` | 15 | Session cache, MIDI→volume mapping |
| `actions/obs.py` | 19 | Scene, source, stream, record, mute |
| `actions/sound.py` | 14 | WAV, MP3, stop, volume |
| `actions/audio_switch.py` | 15 | Device listing, cycling, switch |
| `actions/system.py` | 18 | System commands, URLs, clipboard |
| `actions/conditional.py` | 15 | Conditions, recursion limits, cache |
| `actions/profile_switcher.py` | 8 | Rule matching, auto-switch |
| `actions/counter.py` | 22 | CRUD, persistence, callbacks |
| `actions/tts.py` | 7 | Mock pyttsx3, engine config |

### Tests Requeridos por Feature Pendiente

| Feature | Tests Nuevos | Estrategia |
|---------|--------------|------------|
| **Folders/Pages** | ~10 | Stack navigation, callbacks, integration |
| **Twitch Integration** | ~10 | Mock twitchAPI, OAuth flow |
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
