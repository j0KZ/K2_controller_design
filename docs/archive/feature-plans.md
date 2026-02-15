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

### 4.1 Backend (FastAPI) — Plan Completo

#### Referencia Hardware: Xone:K2
```
Controles: 52 por layer × 3 layers = 156 comandos MIDI
├── 6 Encoders (infinite + push) → CC two's complement + Note On/Off
├── 12 Potentiometers → CC absolute 0-127
├── 4 Faders → CC absolute 0-127
├── 16 Buttons (4×4 matrix) → Note On/Off + LED tri-color
├── Layer button → Cambia entre 3 layers
└── Exit button → Note On/Off

LEDs (16 buttons): Control por NOTE OFFSET (no velocity)
├── Red   = base_note + 0
├── Amber = base_note + 36
├── Green = base_note + 72
└── Off   = Note Off en cualquiera

Latching OFF = Control libre de LEDs (nuestro modo)
X:LINK = Dos K2 conectados, un solo USB
```

#### API REST Endpoints

```python
# ═══════════════════════════════════════════════════════════════
# CONFIG & PROFILES
# ═══════════════════════════════════════════════════════════════

GET  /api/config                     # Config del perfil activo
PUT  /api/config                     # Actualizar config (hot-reload)
POST /api/config/validate            # Validar sin guardar
GET  /api/config/export              # Descargar JSON completo (backup)
POST /api/config/import              # Restaurar desde JSON

GET  /api/profiles                   # Lista de perfiles disponibles
POST /api/profiles                   # Crear nuevo perfil
GET  /api/profiles/{name}            # Obtener perfil específico
PUT  /api/profiles/{name}            # Actualizar perfil
DELETE /api/profiles/{name}          # Eliminar perfil
PUT  /api/profiles/{name}/activate   # Activar perfil

# ═══════════════════════════════════════════════════════════════
# ACTIONS (para UI de configuración)
# ═══════════════════════════════════════════════════════════════

GET  /api/actions                    # Lista tipos de acción disponibles
GET  /api/actions/{type}/schema      # JSON Schema para forms dinámicos
POST /api/actions/test               # Ejecutar acción (testing desde UI)

# ═══════════════════════════════════════════════════════════════
# K2 HARDWARE STATE
# ═══════════════════════════════════════════════════════════════

GET  /api/k2/layout                  # Layout del K2 (grid, tipos de control)
GET  /api/k2/state                   # Estado completo (LEDs, layer, folder, conexión)
GET  /api/k2/state/leds              # Estados de todos los LEDs
PUT  /api/k2/state/leds/{note}       # Cambiar LED manualmente (testing)
GET  /api/k2/state/layer             # Layer actual (0, 1, 2)
PUT  /api/k2/state/layer             # Cambiar layer por software
GET  /api/k2/state/folder            # Folder actual (o null)

# ═══════════════════════════════════════════════════════════════
# MIDI DEVICES
# ═══════════════════════════════════════════════════════════════

GET  /api/midi/devices               # Lista dispositivos MIDI disponibles
GET  /api/midi/status                # Estado conexión K2 (connected, port)
POST /api/midi/reconnect             # Forzar reconexión

# ═══════════════════════════════════════════════════════════════
# INTEGRATIONS (OBS, Spotify, Twitch)
# ═══════════════════════════════════════════════════════════════

GET  /api/integrations               # Estado de todas las integraciones
GET  /api/integrations/{name}/status # Estado específico (obs, spotify, twitch)
POST /api/integrations/{name}/connect    # Iniciar conexión/OAuth
POST /api/integrations/{name}/disconnect # Desconectar
```

**Total: 21 endpoints REST**

#### WebSocket Events

```python
WS /ws/events  # Bidireccional

# ─────────────────────────────────────────────────────────────
# Server → Client (push events)
# ─────────────────────────────────────────────────────────────

{ "type": "midi_event",
  "data": { "type": "note_on", "channel": 16, "note": 36, "value": 127 } }

{ "type": "led_change",
  "data": { "note": 36, "color": "green", "on": true } }

{ "type": "layer_change",
  "data": { "layer": 1, "previous": 0 } }

{ "type": "folder_change",
  "data": { "folder": "obs_controls", "previous": null } }

{ "type": "connection_change",
  "data": { "connected": true, "port": "XONE:K2" } }

{ "type": "integration_change",
  "data": { "name": "obs", "status": "connected" } }

{ "type": "profile_change",
  "data": { "profile": "streaming", "previous": "default" } }

# ─────────────────────────────────────────────────────────────
# Client → Server (commands)
# ─────────────────────────────────────────────────────────────

{ "type": "set_led",
  "data": { "note": 36, "color": "amber" } }

{ "type": "trigger_action",
  "data": { "action": "hotkey", "keys": ["ctrl", "s"] } }
```

**Total: 7 eventos server→client, 2 comandos client→server**

#### Sincronización de Controles Analógicos (Faders/Pots)

> **CRÍTICO:** Los faders y potenciómetros son controles ABSOLUTOS (0-127).
> Deben sincronizarse en tiempo real con la UI y persistir sus posiciones.

##### WebSocket Events para Analog Controls

```python
# Server → Client: Posición en tiempo real
{ "type": "analog_change",
  "data": {
    "cc": 16,           # CC number del control
    "value": 87,        # Valor actual (0-127)
    "control_id": "F1", # ID del control
    "type": "fader"     # fader | pot | encoder
  }}

# Server → Client: Estado inicial al conectar
{ "type": "analog_state",
  "data": {
    "controls": [
      { "cc": 16, "value": 87, "control_id": "F1" },
      { "cc": 17, "value": 45, "control_id": "F2" },
      { "cc": 4, "value": 127, "control_id": "P1" },
      // ... todos los controles analógicos
    ]
  }}
```

##### Persistencia de Posiciones

```python
# k2deck/core/analog_state.py
class AnalogStateManager:
    """Persiste y sincroniza posiciones de controles analógicos."""

    STATE_FILE = Path.home() / ".k2deck" / "analog_state.json"

    def __init__(self):
        self._positions: dict[int, int] = {}  # cc -> value
        self._load()

    def update(self, cc: int, value: int) -> None:
        """Actualizar posición (llamado en cada CC message)."""
        self._positions[cc] = value
        # Debounced save (no guardar cada mensaje, throttle a 1/sec)

    def get_all(self) -> dict[int, int]:
        """Obtener todas las posiciones actuales."""
        return self._positions.copy()

    def get(self, cc: int) -> int:
        """Obtener posición de un control."""
        return self._positions.get(cc, 0)
```

##### Modo de Sincronización: JUMP (Preciso)

Cuando el K2 se reconecta, la posición física puede no coincidir con el valor guardado.

**Comportamiento (modo jump - único):**
1. Al conectar: UI muestra las posiciones guardadas ("última foto")
2. Al mover un control: salta inmediatamente al valor físico real
3. Sin confusión: **lo que muevo = lo que pasa**

```python
# Comportamiento simple y predecible
# Si moviste algo mientras apagado → al tocarlo, se ajusta al real
# Puede haber salto, pero ES PRECISO
```

```javascript
// stores/analogState.js
export const useAnalogState = defineStore('analogState', {
  state: () => ({
    positions: {},        // { cc: value } - posiciones actuales
    savedPositions: {},   // { cc: value } - última foto guardada
  }),

  actions: {
    // Al recibir CC del K2 (control se movió)
    handleAnalogChange(cc, physicalValue) {
      // Jump directo al valor físico - sin pickup, sin espera
      this.positions[cc] = physicalValue
      // Emit to action system
    },

    // Al reconectar K2: cargar última foto
    initFromSavedState(saved) {
      this.savedPositions = { ...saved }
      this.positions = { ...saved }  // UI muestra valores guardados
      // Cuando usuario mueva un control, se actualiza al real
    },

    // Guardar estado actual (debounced, 1/sec)
    saveState() {
      this.savedPositions = { ...this.positions }
      // Persistir a ~/.k2deck/analog_state.json
    }
  }
})
```

##### Visualización en UI

```vue
<!-- K2Fader.vue -->
<template>
  <div class="fader-control flex flex-col items-center gap-1">
    <!-- Track vertical -->
    <div class="fader-track h-32 w-4 bg-k2-bg rounded relative">
      <!-- Valor actual (verde) - sube desde abajo -->
      <div
        class="fader-value absolute bottom-0 w-full bg-k2-success rounded-b transition-all"
        :style="{ height: (value / 127 * 100) + '%' }"
      />
      <!-- Knob indicator -->
      <div
        class="fader-knob absolute w-6 h-2 -left-1 bg-k2-text rounded"
        :style="{ bottom: (value / 127 * 100) + '%' }"
      />
    </div>
    <!-- Value label -->
    <span class="text-xs text-k2-text-secondary font-mono">{{ value }}</span>
    <!-- Control ID -->
    <span class="text-[10px] text-k2-text-secondary">{{ controlId }}</span>
  </div>
</template>

<!-- K2Pot.vue -->
<template>
  <div class="pot-control flex flex-col items-center gap-1">
    <!-- Arco SVG mostrando valor -->
    <svg class="w-12 h-12" viewBox="0 0 100 100">
      <!-- Background arc -->
      <path
        d="M 20 80 A 40 40 0 1 1 80 80"
        fill="none"
        stroke="#303030"
        stroke-width="8"
        stroke-linecap="round"
      />
      <!-- Value arc (verde) -->
      <path
        :d="valueArc"
        fill="none"
        stroke="#33d17a"
        stroke-width="8"
        stroke-linecap="round"
      />
      <!-- Center dot -->
      <circle cx="50" cy="50" r="4" fill="#ffffff" />
    </svg>
    <span class="text-xs text-k2-text-secondary font-mono">{{ value }}</span>
    <span class="text-[10px] text-k2-text-secondary">{{ controlId }}</span>
  </div>
</template>
```

##### API Endpoints

```python
GET  /api/k2/state/analog           # Todas las posiciones actuales
GET  /api/k2/state/analog/{cc}      # Posición de un control específico
```

#### K2 Layout Response Example

```json
{
  "name": "Xone:K2",
  "midi_channel": 16,
  "layers": 3,
  "columns": 4,
  "rows": 8,
  "controls": [
    { "id": "enc1", "type": "encoder", "row": 0, "col": 0, "push": true, "led": false, "cc": 0, "note": 0 },
    { "id": "enc2", "type": "encoder", "row": 0, "col": 1, "push": true, "led": false, "cc": 1, "note": 1 },
    { "id": "pot1", "type": "pot", "row": 1, "col": 0, "led": false, "cc": 4 },
    { "id": "pot2", "type": "pot", "row": 1, "col": 1, "led": false, "cc": 5 },
    { "id": "btn_a1", "type": "button", "row": 4, "col": 0, "led": true, "note": 36,
      "led_notes": { "red": 36, "amber": 72, "green": 108 } },
    { "id": "fader1", "type": "fader", "row": 6, "col": 0, "led": false, "cc": 16 }
  ]
}
```

### 4.2 Frontend (Vue.js)

```
k2deck/web/frontend/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── K2Grid.vue           # Grid visual del K2 (layout real)
│   │   │   ├── K2Control.vue        # Control individual (dispatcher)
│   │   │   ├── K2Button.vue         # Botón con LED tricolor
│   │   │   ├── K2Encoder.vue        # Encoder con indicador rotativo
│   │   │   ├── K2Fader.vue          # Fader vertical con valor en tiempo real
│   │   │   ├── K2Pot.vue            # Potenciómetro con arco de valor
│   │   │   ├── K2Led.vue            # LED indicator con animación de color
│   │   │   └── LayerTabs.vue        # Tabs para Layer 0/1/2
│   │   ├── config/
│   │   │   ├── ControlConfig.vue    # Panel de configuración (derecha)
│   │   │   ├── ActionPicker.vue     # Dropdown de tipos de acción
│   │   │   ├── ActionForm.vue       # Form dinámico desde JSON Schema
│   │   │   ├── LedConfig.vue        # Selector de color LED (on/off state)
│   │   │   └── LayerConfig.vue      # Config por layer (tabs)
│   │   ├── actions/
│   │   │   ├── ActionLibrary.vue    # Panel lateral con acciones arrastrables
│   │   │   ├── ActionCard.vue       # Card de acción (draggable)
│   │   │   └── ActionCategories.vue # Filtros: System, Media, OBS, etc.
│   │   ├── profiles/
│   │   │   ├── ProfileManager.vue   # CRUD de perfiles
│   │   │   ├── ProfileDropdown.vue  # Selector de perfil activo
│   │   │   └── ImportExport.vue     # Botones import/export JSON
│   │   ├── status/
│   │   │   ├── IntegrationStatus.vue    # Pills: OBS/Spotify/Twitch
│   │   │   ├── ConnectionStatus.vue     # K2 conectado/desconectado
│   │   │   └── FolderBreadcrumb.vue     # Navegación: / > obs_controls
│   │   ├── monitor/
│   │   │   └── MidiMonitor.vue      # Live MIDI events (bottom bar)
│   │   └── common/
│   │       ├── ValidationError.vue  # Feedback de errores
│   │       └── ConfirmDialog.vue    # Confirmaciones (delete, etc.)
│   ├── stores/
│   │   ├── config.js          # Pinia: config activa + validation
│   │   ├── k2state.js         # Pinia: LEDs, layer, folder, connection
│   │   ├── analogState.js     # Pinia: faders/pots positions + pickup mode
│   │   ├── profiles.js        # Pinia: CRUD perfiles
│   │   ├── actions.js         # Pinia: action types + schemas
│   │   └── integrations.js    # Pinia: OBS/Spotify/Twitch status
│   ├── composables/
│   │   ├── useWebSocket.js    # WebSocket con reconnect + event handlers
│   │   ├── useApi.js          # Fetch helpers con error handling
│   │   ├── useDragDrop.js     # Drag & drop de acciones al grid
│   │   ├── useAnalogSync.js   # Soft takeover + pickup mode logic
│   │   └── useValidation.js   # Validación de config antes de save
│   ├── utils/
│   │   ├── k2Layout.js        # Constantes del layout K2
│   │   └── ledColors.js       # Colores y offsets de LEDs
│   └── App.vue
├── package.json
└── vite.config.js
```

### 4.2.1 Funcionalidad Drag & Drop (Stream Deck-like)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────┐                                                        │
│  │ ACTIONS     │    ┌─────────────────────────────────────────────────┐ │
│  │             │    │              K2 GRID                            │ │
│  │ ┌─────────┐ │    │  ┌────┬────┬────┬────┐                         │ │
│  │ │ Hotkey  │ │    │  │ E1 │ E2 │ E3 │ E4 │  ← Drop zone            │ │
│  │ └─────────┘ │    │  ├────┼────┼────┼────┤                         │ │
│  │ ┌─────────┐ │    │  │🟢A1│ A2 │ A3 │ A4 │  ← LED muestra color    │ │
│  │ │ OBS     │◄├────┼──│    │    │    │    │                         │ │
│  │ └─────────┘ │drag│  └────┴────┴────┴────┘                         │ │
│  │ ┌─────────┐ │    │                                                 │ │
│  │ │ Spotify │ │    │  Layer: [0] [1] [2]                            │ │
│  │ └─────────┘ │    └─────────────────────────────────────────────────┘ │
│  │ ┌─────────┐ │                                                        │
│  │ │ Twitch  │ │    Al soltar acción sobre control:                    │
│  │ └─────────┘ │    1. Abre ControlConfig.vue con ActionForm           │
│  │ ...         │    2. Usuario configura parámetros                    │
│  └─────────────┘    3. Click [Save] → PUT /api/config                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2.2 WebSocket Event Handlers

```javascript
// stores/k2state.js
export const useK2State = defineStore('k2state', {
  state: () => ({
    leds: {},           // { 36: 'green', 72: 'amber', ... }
    layer: 0,           // 0, 1, 2
    folder: null,       // 'obs_controls' | null
    connected: false,   // K2 conectado
  }),

  actions: {
    // Llamado por useWebSocket cuando llega evento
    handleWsEvent(event) {
      switch (event.type) {
        case 'led_change':
          this.leds[event.data.note] = event.data.on ? event.data.color : null
          break
        case 'layer_change':
          this.layer = event.data.layer
          break
        case 'folder_change':
          this.folder = event.data.folder
          break
        case 'connection_change':
          this.connected = event.data.connected
          break
      }
    }
  }
})
```

### 4.3 Decisiones de Diseño (CONFIRMADAS)

| Pregunta | Decisión | Razón |
|----------|----------|-------|
| ¿Puerto? | **8420** (configurable) | Memorable: K-2 layout |
| ¿CORS? | **localhost:\* permitido** | Solo desarrollo local |
| ¿Autenticación? | **Sin auth (localhost only)** | Como Stream Deck, solo escucha 127.0.0.1 |
| ¿Cuándo inicia? | **Siempre activo** | 5MB RAM trivial, simplicidad |
| ¿Mobile responsive? | **No, desktop only** | Optimizado para desktop |
| ¿Framework CSS? | **TailwindCSS** | Estilo similar a Stream Deck |
| ¿Distribución frontend? | **Build → dist/ → FastAPI static** | Single bundle |
| ¿WebSocket reconnect? | **reconnecting-websocket npm** | Exponential backoff |

### Wireframe UI (Stream Deck-like)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  K2 Deck                    [obs ●] [spotify ●] [twitch ○]  [Default ▼] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────┐    ┌───────────────────────────────────┐│
│  │      K2 Visual Layout     │    │       Control Configuration       ││
│  │  ┌────┬────┬────┬────┐   │    │                                   ││
│  │  │ E1 │ E2 │ E3 │ E4 │   │    │  Name: [Spotify Play/Pause     ]  ││
│  │  ├────┼────┼────┼────┤   │    │                                   ││
│  │  │ K1 │ K2 │ K3 │ K4 │   │    │  Action: [spotify_play_pause ▼]   ││
│  │  ├────┼────┼────┼────┤   │    │                                   ││
│  │  │ K5 │ K6 │ K7 │ K8 │   │    │  ┌─ LED Settings ──────────────┐  ││
│  │  ├────┼────┼────┼────┤   │    │  │ On:  [● Green ▼]            │  ││
│  │  │ K9 │K10 │K11 │K12 │   │    │  │ Off: [● Amber ▼]            │  ││
│  │  ├────┼────┼────┼────┤   │    │  └────────────────────────────┘  ││
│  │  │🟢A1│ A2 │ A3 │ A4 │   │    │                                   ││
│  │  ├────┼────┼────┼────┤   │    │  ┌─ Layer Settings ────────────┐  ││
│  │  │ B1 │ B2 │ B3 │ B4 │   │    │  │ Layer 0: [this action    ]  │  ││
│  │  ├────┼────┼────┼────┤   │    │  │ Layer 1: [different      ]  │  ││
│  │  │ C1 │ C2 │ C3 │ C4 │   │    │  │ Layer 2: [another        ]  │  ││
│  │  ├────┼────┼────┼────┤   │    │  └────────────────────────────┘  ││
│  │  │ F1 │ F2 │ F3 │ F4 │   │    │                                   ││
│  │  ├────┼────┼────┼────┤   │    │         [Save] [Cancel] [Test]   ││
│  │  │ D1 │ D2 │ D3 │ D4 │   │    │                                   ││
│  │  └────┴────┴────┴────┘   │    └───────────────────────────────────┘│
│  │  Layer: [0] [1] [2]      │                                         │
│  │  Folder: / > obs_controls│                                         │
│  └───────────────────────────┘                                         │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ MIDI: note_on ch=16 note=36 vel=127 │ K2: Connected │ [Clear]       ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

### Estimación LOC

| Componente | LOC | Descripción |
|------------|-----|-------------|
| Backend (FastAPI) | ~1000 | 24 endpoints + WebSocket + analog sync |
| Frontend (Vue) | ~3200 | Componentes, stores, composables, analog UI |
| **Total Web UI** | **~4200** | |

### Archivos a crear

```
k2deck/
├── core/
│   └── analog_state.py     # Persistencia de posiciones faders/pots (~100 LOC)
│
└── web/
    ├── __init__.py
    ├── server.py               # FastAPI app + lifespan + CORS
    ├── routes/
    │   ├── __init__.py
    │   ├── config.py           # /api/config/* (5 endpoints)
    │   ├── profiles.py         # /api/profiles/* (6 endpoints)
    │   ├── actions.py          # /api/actions/* (3 endpoints)
    │   ├── k2.py               # /api/k2/* (9 endpoints, incluye analog)
    │   ├── midi.py             # /api/midi/* (3 endpoints)
│   └── integrations.py     # /api/integrations/* (4 endpoints)
├── websocket/
│   ├── __init__.py
│   ├── manager.py          # ConnectionManager (broadcast)
│   └── events.py           # Event handlers
├── schemas/
│   ├── __init__.py
│   ├── config.py           # Pydantic models for config
│   ├── actions.py          # Action schemas for validation
│   └── k2.py               # K2 state models
└── frontend/               # Vue.js app
    ├── src/
    ├── dist/               # Built files (served by FastAPI)
    └── package.json
```

### Dependencias Backend

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
websockets>=12.0
pydantic>=2.5.0
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

### Decisiones de Diseño (CONFIRMADAS)
| Pregunta | Decisión | Razón |
|----------|----------|-------|
| ¿Gestión de deps? | **Check automático, no install** | Verificar imports, warning claro si faltan |
| ¿Hot-reload? | **No, solo startup** | Evita estado inconsistente, reinicio no es problema |
| ¿Conflictos de nombres? | **Plugin override con warning** | Configurable en futuro |
| ¿Errores en plugins? | **try/except, log, continuar** | Plugin buggy no crashea K2 |
| ¿Versionado? | **min_k2deck_version en manifest** | Validar en load |

### Mitigaciones de Seguridad
- Plugins solo desde directorio específico (~/.k2deck/plugins)
- Warning en logs cuando plugin se carga
- Opción para deshabilitar plugins en config
- NO ejecutar pip automáticamente (documentar deps requeridas)

### Plugin Manifest Schema (Nuevo)
```json
{
  "name": "string (required)",
  "version": "string (required)",
  "author": "string (optional)",
  "description": "string (optional)",
  "min_k2deck_version": "string (optional, e.g. '0.3.0')",
  "actions": { "action_name": "ClassName" },
  "dependencies": ["pip_package_name"]
}
```

### Archivos a crear
```
k2deck/plugins/
├── __init__.py
├── base.py         # Plugin base class
├── loader.py       # Plugin discovery and loading
├── registry.py     # Action registration + conflict resolution
└── validator.py    # Validate plugin manifest
```

### Adaptación de Plugins Externos (StreamController, etc.)

Para poder adaptar plugins de otros sistemas (como StreamController), nuestro Plugin System incluye:

#### Capa de Compatibilidad

```python
# k2deck/plugins/adapters/streamcontroller.py
class StreamControllerAdapter:
    """Adapter to convert StreamController plugins to K2 Deck format."""

    def __init__(self, sc_plugin_path: Path):
        self.sc_plugin = self._load_sc_plugin(sc_plugin_path)

    def to_k2_action(self, sc_action_class) -> type[Action]:
        """Convert StreamController ActionBase to K2 Deck Action."""

        class AdaptedAction(Action):
            def __init__(self, config: dict):
                super().__init__(config)
                self._sc_action = sc_action_class()
                # Map SC settings to K2 config

            def execute(self, event: MidiEvent) -> None:
                if event.type == "note_on" and event.value > 0:
                    # SC uses on_key_down
                    self._sc_action.on_key_down()
                elif event.type == "note_on" and event.value == 0:
                    # SC uses on_key_up
                    self._sc_action.on_key_up()

        return AdaptedAction
```

#### Mapeo de Conceptos SC → K2

| StreamController | K2 Deck | Notas |
|------------------|---------|-------|
| `ActionBase` | `Action` | Clase base de acciones |
| `on_key_down()` | `execute(event)` donde `event.value > 0` | Press |
| `on_key_up()` | `execute(event)` donde `event.value == 0` | Release |
| `on_tick()` | No soportado (sin LCD) | Timer interno |
| `get_settings()` | `config: dict` en constructor | JSON config |
| `set_media(image)` | `led_manager.set_color()` | Sin LCD, solo LEDs |
| `PluginBase` | `K2Plugin` | Clase base de plugins |
| `BackendBase` | No necesario | Integrado en Action |

#### Plugins de StreamController Adaptables

| Plugin SC | Adaptable | Razón |
|-----------|-----------|-------|
| OBSPlugin | ⚠️ Ya tenemos | Usamos misma lib (obsws-python) |
| MediaPlugin | ⚠️ Ya tenemos | Nuestro es mejor (Spotify API) |
| VolumeMixer | ⚠️ Ya tenemos | pycaw |
| AudioSwitcher | ⚠️ Ya tenemos | PolicyConfig |
| Counter | ⚠️ Ya tenemos | Más features |
| Clocks | ✅ **Adaptar** | Timer/Countdown |
| Speedtest | ✅ Adaptar | Nuevo |
| Weather | ✅ Adaptar | Nuevo (sin LCD = TTS/LED) |
| IFTTT/Webhooks | ✅ Adaptar | Nuevo |

---

## 6. Timer/Countdown Actions

### Objetivo
Timers y countdowns para streaming (pomodoro, breaks, raid timers).

### Implementación

```python
# k2deck/actions/timer.py
import threading
import time
from typing import Callable

class TimerManager:
    """Singleton for managing active timers."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._timers = {}
        return cls._instance

    def start_timer(self, name: str, seconds: int,
                    on_tick: Callable[[int], None] = None,
                    on_complete: Callable[[], None] = None) -> bool:
        """Start a countdown timer."""
        if name in self._timers:
            return False  # Already running

        def _run():
            remaining = seconds
            while remaining > 0 and name in self._timers:
                if on_tick:
                    on_tick(remaining)
                time.sleep(1)
                remaining -= 1

            if name in self._timers:
                del self._timers[name]
                if on_complete:
                    on_complete()

        thread = threading.Thread(target=_run, daemon=True)
        self._timers[name] = {"thread": thread, "remaining": seconds}
        thread.start()
        return True

    def stop_timer(self, name: str) -> bool:
        """Stop a running timer."""
        if name in self._timers:
            del self._timers[name]
            return True
        return False

    def get_remaining(self, name: str) -> int | None:
        """Get remaining seconds for a timer."""
        if name in self._timers:
            return self._timers[name].get("remaining")
        return None


class TimerStartAction(Action):
    """Start a countdown timer.

    Config:
        name: Timer identifier
        seconds: Duration in seconds
        on_complete: Optional action to execute when done
        tts_announce: Announce remaining time via TTS (optional)
        led_note: LED to flash when complete (optional)
    """

    def execute(self, event: MidiEvent) -> None:
        if event.type != "note_on" or event.value == 0:
            return

        name = self._config.get("name", "default")
        seconds = self._config.get("seconds", 60)

        def on_complete():
            # Flash LED if configured
            if led_note := self._config.get("led_note"):
                # Flash green 3 times
                pass
            # TTS if configured
            if self._config.get("tts_announce"):
                # Announce completion
                pass
            # Execute completion action if configured
            if complete_action := self._config.get("on_complete"):
                # Execute action
                pass

        TimerManager().start_timer(name, seconds, on_complete=on_complete)


class TimerStopAction(Action):
    """Stop a running timer."""

    def execute(self, event: MidiEvent) -> None:
        if event.type != "note_on" or event.value == 0:
            return

        name = self._config.get("name", "default")
        TimerManager().stop_timer(name)


class TimerToggleAction(Action):
    """Toggle timer start/stop."""

    def execute(self, event: MidiEvent) -> None:
        if event.type != "note_on" or event.value == 0:
            return

        name = self._config.get("name", "default")
        manager = TimerManager()

        if manager.get_remaining(name) is not None:
            manager.stop_timer(name)
        else:
            seconds = self._config.get("seconds", 60)
            manager.start_timer(name, seconds)
```

### Config Examples

```json
{
  "action": "timer_start",
  "name": "pomodoro",
  "seconds": 1500,
  "tts_announce": true,
  "led_note": 36,
  "on_complete": { "action": "sound_play", "file": "bell.wav" }
}
```

```json
{
  "action": "timer_toggle",
  "name": "break_timer",
  "seconds": 300
}
```

### Estimación
- ~120 LOC
- 0 dependencias nuevas
- ~8 tests

---

## 7. UX/UI Reference: StreamController

> **Fuente:** Análisis de screenshots reales + código fuente de StreamController
> - Repositorio: StreamController-main/src/
> - Screenshots: 5 capturas de UI real de StreamController

### Layout Real de StreamController (Observado)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [≡ Menu]      StreamController           [Deck 1 ▼]   [Deck 2]   [+]  │ ← Header con selector de decks
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────┐  ┌───────────────────────────┐ │
│  │         DEVICE GRID (3×5)           │  │     CONFIG SIDEBAR        │ │
│  │  ┌─────┬─────┬─────┐                │  │  ┌───────────────────────┐│ │
│  │  │     │     │     │  [Page: 1]     │  │  │ State: [1] [2] [3]   ││ │ ← StateSwitcher
│  │  │ btn │ btn │ btn │  [Page: 2]     │  │  └───────────────────────┘│ │
│  │  │     │     │     │  ...           │  │  ┌───────────────────────┐│ │
│  │  ├─────┼─────┼─────┤                │  │  │ [Icon] Select Image  ││ │ ← IconSelector
│  │  │     │     │     │                │  │  └───────────────────────┘│ │
│  │  │ btn │ btn │ btn │                │  │  ┌───────────────────────┐│ │
│  │  │     │     │     │                │  │  │ Label: [___________] ││ │ ← LabelEditor
│  │  ├─────┼─────┼─────┤                │  │  │ Position: [Top ▼]    ││ │
│  │  │     │     │     │                │  │  └───────────────────────┘│ │
│  │  │ btn │ btn │ btn │                │  │  ┌───────────────────────┐│ │
│  │  │     │     │     │                │  │  │ Action: [Select ▼]   ││ │ ← ActionManager
│  │  ├─────┼─────┼─────┤                │  │  │ ┌───────────────────┐││ │
│  │  │     │     │     │                │  │  │ │ + Add Action      │││ │
│  │  │ btn │ btn │ btn │                │  │  │ └───────────────────┘││ │
│  │  │     │     │     │                │  │  └───────────────────────┘│ │
│  │  ├─────┼─────┼─────┤                │  │                           │ │
│  │  │     │     │     │                │  │  [Show All Settings ▼]    │ │
│  │  │ btn │ btn │ btn │                │  │                           │ │
│  │  │     │     │     │                │  └───────────────────────────┘ │
│  │  └─────┴─────┴─────┘                │                                │
│  └─────────────────────────────────────┘                                │
│                                                                         │
│  [◀ Prev Page]                              [Next Page ▶]              │ ← Page navigation
└─────────────────────────────────────────────────────────────────────────┘
```

### Componentes Reales de StreamController (del código)

**Ubicación:** `StreamController-main/src/windows/mainWindow/elements/Sidebar/`

| Componente SC | Archivo | Función | Mapeo K2 Deck |
|---------------|---------|---------|---------------|
| `KeyEditor` | `elements/KeyEditor/` | Editor principal de tecla | `ControlConfig.vue` |
| `StateSwitcher` | `StateSwitcher.py` | Cambiar entre estados (multi-action) | `LayerTabs.vue` |
| `IconSelector` | `IconSelector.py` | Seleccionar icono para tecla | No aplica (sin LCD) |
| `ImageEditor` | `ImageEditor.py` | Editar imagen de tecla | No aplica (sin LCD) |
| `LabelEditor` | `LabelEditor.py` | Editar label de tecla | `ActionForm.vue` (campo name) |
| `ActionManager` | `ActionManager.py` | Gestionar acciones de tecla | `ActionPicker.vue` + `ActionForm.vue` |

### Eventos de ActionBase (del código fuente)

**Ubicación:** `StreamController-main/src/backend/PluginManager/ActionBase.py`

```python
# Eventos de Key (botones)
class KeyEvent(Enum):
    DOWN = "down"           # Tecla presionada
    UP = "up"               # Tecla liberada
    SHORT_UP = "short_up"   # Press corto (< hold threshold)
    HOLD_START = "hold_start"  # Inicio de hold
    HOLD_STOP = "hold_stop"    # Fin de hold

# Eventos de Dial (encoders - Stream Deck+)
class DialEvent(Enum):
    TURN_CW = "turn_cw"     # Giro clockwise
    TURN_CCW = "turn_ccw"   # Giro counter-clockwise
    # También: push down, push up

# Eventos de Touchscreen (Stream Deck+)
class TouchscreenEvent(Enum):
    SHORT = "short"         # Tap corto
    LONG = "long"           # Tap largo
    DRAG = "drag"           # Drag gesture
```

**Mapeo a K2 Deck:**

| SC Event | K2 Deck Equivalente |
|----------|---------------------|
| `KeyEvent.DOWN` | `note_on` con `value > 0` |
| `KeyEvent.UP` | `note_on` con `value == 0` |
| `KeyEvent.SHORT_UP` | Detectar por tiempo (< 500ms) |
| `KeyEvent.HOLD_START` | Detectar por tiempo (> 500ms) |
| `DialEvent.TURN_CW` | CC con `value == 1` (two's complement) |
| `DialEvent.TURN_CCW` | CC con `value == 127` (two's complement) |

### Plugin Store Modal (Observado en Screenshot)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [←]  Store                                              [Search: ___] │
├─────────────────────────────────────────────────────────────────────────┤
│  Categories:     All | Official | Community | Installed                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────┐  ┌─────────────────────────┐              │
│  │ [icon]                  │  │ [icon]                  │              │
│  │ OBS Controller          │  │ Spotify Integration     │              │
│  │ ★★★★☆  v1.2.0          │  │ ★★★★★  v2.0.1          │              │
│  │ Control OBS Studio...   │  │ Full Spotify control... │              │
│  │ [Install]               │  │ [Installed ✓]           │              │
│  └─────────────────────────┘  └─────────────────────────┘              │
│                                                                         │
│  ┌─────────────────────────┐  ┌─────────────────────────┐              │
│  │ [icon]                  │  │ [icon]                  │              │
│  │ Volume Mixer            │  │ Counter                 │              │
│  │ ★★★★☆  v1.0.0          │  │ ★★★☆☆  v0.9.0          │              │
│  │ Per-app volume...       │  │ Persistent counters...  │              │
│  │ [Install]               │  │ [Install]               │              │
│  └─────────────────────────┘  └─────────────────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Paleta de Colores Real (Observada)

StreamController usa GTK4 + libadwaita con tema oscuro:

```javascript
// tailwind.config.js - Basado en screenshots reales
module.exports = {
  theme: {
    extend: {
      colors: {
        // Colores observados en StreamController
        'k2-bg': '#242424',           // Fondo principal (gris muy oscuro)
        'k2-surface': '#303030',       // Cards y sidebars
        'k2-surface-hover': '#3d3d3d', // Hover state
        'k2-border': '#484848',        // Bordes sutiles
        'k2-text': '#ffffff',          // Texto principal
        'k2-text-secondary': '#9a9a9a',// Texto secundario
        'k2-accent': '#3584e4',        // Accent azul (libadwaita)
        'k2-accent-hover': '#4a9cf8',  // Accent hover
        'k2-success': '#33d17a',       // Verde éxito
        'k2-warning': '#f6d32d',       // Amarillo warning
        'k2-error': '#e01b24',         // Rojo error
        // LED colors (K2 específico)
        'led-red': '#ff3333',
        'led-amber': '#ffaa00',
        'led-green': '#00ff66',
      }
    }
  }
}
```

### Patrones UI a Copiar

| Patrón SC (Real) | Implementación K2 Deck | Prioridad |
|------------------|------------------------|-----------|
| **Two-panel layout** | Grid izq + Config der | Alta |
| **Dark theme (libadwaita)** | Tailwind con palette arriba | Alta |
| **Click-to-select key** | Click control → highlight + panel | Alta |
| **State switcher tabs** | LayerTabs.vue (Layer 0/1/2) | Alta |
| **Action dropdown** | ActionPicker.vue con categorías | Alta |
| **Page navigation** | Folder navigation (bottom bar) | Alta |
| **Deck selector (header)** | Profile dropdown | Media |
| **Settings expandable** | "Show All Settings" collapse | Media |
| **Store modal** | Plugin browser (futuro) | Baja |

### Componente K2Control.vue (Adaptado de SC)

```vue
<!-- K2Control.vue - Basado en KeyEditor de SC -->
<template>
  <div
    class="k2-control relative rounded-lg cursor-pointer transition-all
           bg-k2-surface hover:bg-k2-surface-hover border border-k2-border"
    :class="[
      isButton ? 'aspect-square' : 'aspect-[1/2]',
      isSelected ? 'ring-2 ring-k2-accent' : ''
    ]"
    @click="$emit('select', control.id)"
  >
    <!-- LED indicator (K2 específico - no existe en SC) -->
    <div
      v-if="control.led && ledState"
      class="absolute top-1 right-1 w-3 h-3 rounded-full shadow-lg"
      :class="{
        'bg-led-red': ledState === 'red',
        'bg-led-amber': ledState === 'amber',
        'bg-led-green': ledState === 'green'
      }"
    />

    <!-- Control type indicator -->
    <div class="absolute top-1 left-1">
      <span class="text-[10px] text-k2-text-secondary uppercase">
        {{ control.type }}
      </span>
    </div>

    <!-- Action name (center) -->
    <div class="flex items-center justify-center h-full p-2">
      <span v-if="actionName" class="text-xs text-k2-text text-center truncate">
        {{ actionName }}
      </span>
      <span v-else class="text-xs text-k2-text-secondary">
        Empty
      </span>
    </div>

    <!-- Control ID (bottom) -->
    <div class="absolute bottom-1 left-1/2 -translate-x-1/2">
      <span class="text-[10px] text-k2-text-secondary">{{ control.id }}</span>
    </div>
  </div>
</template>
```

### Diferencias Clave: SC vs K2 Deck

| Aspecto | StreamController | K2 Deck |
|---------|------------------|---------|
| **Hardware** | Stream Deck (LCD buttons) | Xone:K2 (MIDI, LEDs tricolor) |
| **Display** | Icons + text en cada tecla | Solo LEDs (R/A/G) |
| **Encoders** | Solo Stream Deck+ | 6 encoders nativos |
| **Faders** | No tiene | 4 faders nativos |
| **States** | Multi-state por tecla | Layers (3) por todo el device |
| **Framework** | GTK4 + Python | Vue.js + FastAPI |
| **Plugins** | Python packages | Python packages (compatible) |

### Layout Oficial Xone:K2 (de overlays oficiales Allen & Heath)

> **Fuente:** `docs/K2_Overlays/K2_Master.pdf` y `K2_Blank.pdf`

```
┌──────────────────────────────────────────────────────────────┐
│  ❋XONE:K2                                   ALLEN&HEATH      │
├──────────────────────────────────────────────────────────────┤
│     Col 0        Col 1        Col 2        Col 3             │
│                                                              │
│   [◐ LED]      [◐ LED]      [◐ LED]      [◐ LED]   Row 0    │
│    ◎ E1         ◎ E2         ◎ E3         ◎ E4     Encoders │
│   [□ btn]      [□ btn]      [□ btn]      [□ btn]   +Push+LED│
│                                                              │
│    ◎ P1         ◎ P2         ◎ P3         ◎ P4     Row 1    │
│   [□ btn]      [□ btn]      [□ btn]      [□ btn]   Pots     │
│                                                    +Btn+LED │
│    ◎ P5         ◎ P6         ◎ P7         ◎ P8     Row 2    │
│    ◎ P9         ◎ P10        ◎ P11        ◎ P12    Pots×2   │
│   [□ btn]      [□ btn]      [□ btn]      [□ btn]   +Btn+LED │
│                                                              │
│    ║ F1         ║ F2         ║ F3         ║ F4     Row 3    │
│    ║            ║            ║            ║        Faders   │
│    ║            ║            ║            ║        (largo)  │
│    ●            ●            ●            ●                 │
│                                                              │
│  (MIDI CH)   (LATCH LAYERS)                                 │
│   [□ A]       [□ B]        [□ C]        [□ D]     Row 4     │
│   [□ E]       [□ F]        [□ G]        [□ H]     Buttons   │
│   [□ I]       [□ J]        [□ K]        [□ L]     4×4 Grid  │
│   [□ M]       [□ N]        [□ O]        [□ P]     +LED cada │
│                                                              │
│   LAYER      ◎ SCROLL    ◎ SEL        SHIFT      Row 5     │
│   [□]        (encoder)   (encoder)    [□]        Control   │
│              POWER ON SCR            EXIT SETUP             │
└──────────────────────────────────────────────────────────────┘
```

#### Conteo de Controles (por Layer)

| Tipo | Cantidad | Con LED | MIDI Type | Notas |
|------|----------|---------|-----------|-------|
| **Encoders** | 4 (+2 system) | Sí (4) | CC (two's complement) | Push = Note |
| **Potentiometers** | 12 | No | CC (0-127) | Absoluto |
| **Faders** | 4 | No | CC (0-127) | Absoluto, ~60 msg/sec |
| **Buttons** | 16 (A-P) + 12 | Sí (28) | Note On/Off | Tri-color LED |
| **Layer/Shift** | 2 | Sí | Note On/Off | Botones especiales |
| **Total** | **52** | **34 LEDs** | | ×3 Layers = 156 MIDI msgs |

#### Mapeo de IDs para Web UI

```javascript
// utils/k2Layout.js
export const K2_LAYOUT = {
  rows: [
    // Row 0: Encoders with LED + push button
    { type: 'encoder-row', controls: [
      { id: 'E1', type: 'encoder', hasLed: true, hasPush: true },
      { id: 'E2', type: 'encoder', hasLed: true, hasPush: true },
      { id: 'E3', type: 'encoder', hasLed: true, hasPush: true },
      { id: 'E4', type: 'encoder', hasLed: true, hasPush: true },
    ]},
    // Row 1: Pots + buttons with LED
    { type: 'pot-btn-row', controls: [
      { id: 'P1', type: 'pot' }, { id: 'P2', type: 'pot' },
      { id: 'P3', type: 'pot' }, { id: 'P4', type: 'pot' },
    ], buttons: [
      { id: 'B1', type: 'button', hasLed: true },
      { id: 'B2', type: 'button', hasLed: true },
      { id: 'B3', type: 'button', hasLed: true },
      { id: 'B4', type: 'button', hasLed: true },
    ]},
    // Row 2: Pots ×2 + buttons with LED
    { type: 'pot-pot-btn-row', controls: [
      { id: 'P5', type: 'pot' }, { id: 'P6', type: 'pot' },
      { id: 'P7', type: 'pot' }, { id: 'P8', type: 'pot' },
      { id: 'P9', type: 'pot' }, { id: 'P10', type: 'pot' },
      { id: 'P11', type: 'pot' }, { id: 'P12', type: 'pot' },
    ], buttons: [
      { id: 'B5', type: 'button', hasLed: true },
      { id: 'B6', type: 'button', hasLed: true },
      { id: 'B7', type: 'button', hasLed: true },
      { id: 'B8', type: 'button', hasLed: true },
    ]},
    // Row 3: Faders (tall)
    { type: 'fader-row', controls: [
      { id: 'F1', type: 'fader' }, { id: 'F2', type: 'fader' },
      { id: 'F3', type: 'fader' }, { id: 'F4', type: 'fader' },
    ]},
    // Row 4-7: 4×4 Button grid (A-P)
    { type: 'button-row', controls: [
      { id: 'A', type: 'button', hasLed: true, label: 'MIDI CH' },
      { id: 'B', type: 'button', hasLed: true, label: 'LATCH' },
      { id: 'C', type: 'button', hasLed: true },
      { id: 'D', type: 'button', hasLed: true },
    ]},
    { type: 'button-row', controls: [
      { id: 'E', type: 'button', hasLed: true },
      { id: 'F', type: 'button', hasLed: true },
      { id: 'G', type: 'button', hasLed: true },
      { id: 'H', type: 'button', hasLed: true },
    ]},
    { type: 'button-row', controls: [
      { id: 'I', type: 'button', hasLed: true },
      { id: 'J', type: 'button', hasLed: true },
      { id: 'K', type: 'button', hasLed: true },
      { id: 'L', type: 'button', hasLed: true },
    ]},
    { type: 'button-row', controls: [
      { id: 'M', type: 'button', hasLed: true },
      { id: 'N', type: 'button', hasLed: true },
      { id: 'O', type: 'button', hasLed: true },
      { id: 'P', type: 'button', hasLed: true },
    ]},
    // Row 8: Control row (Layer, Scroll/Sel encoders, Shift)
    { type: 'control-row', controls: [
      { id: 'LAYER', type: 'button', hasLed: true, special: true },
      { id: 'SCROLL', type: 'encoder', hasPush: true, special: true },
      { id: 'SEL', type: 'encoder', hasPush: true, special: true },
      { id: 'SHIFT', type: 'button', hasLed: true, special: true },
    ]},
  ],
  totalControls: 52,
  totalLeds: 34,
  layers: 3,
}
```

### Mejoras UX Propuestas sobre StreamController

Basado en el layout real del K2, estas mejoras aprovechan las ventajas del hardware:

| Mejora | SC no tiene | K2 Deck implementa | Prioridad |
|--------|-------------|-------------------|-----------|
| **Grid visual real** | Buttons uniformes | Layout mixto (enc/pot/fader/btn) | Alta |
| **Valores en tiempo real** | Solo on/off | Faders/encoders muestran valor | Alta |
| **MIDI Learn visual** | Config manual | Click control + mueve K2 = asigna | Alta |
| **Undo/Redo** | No visible | Ctrl+Z/Y con historial | Media |
| **Templates** | Solo plugins | Presets: Spotify, OBS, Gaming | Media |
| **Keyboard shortcuts** | Mouse-only | Tab, 1-3, /, Ctrl+S | Media |
| **Status enriquecido** | Pills básicos | K2 + OBS + Spotify + Twitch detalle | Media |

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

### Decisiones de Diseño (CONFIRMADAS)
| Pregunta | Decisión | Razón |
|----------|----------|-------|
| ¿Folder per layer? | **No, folders son globales** | Simplifica implementación, estado único |
| ¿Afecta encoders/faders? | **No, solo note_on (botones)** | Folders son "sub-menús de botones" |
| ¿Timeout de folder? | **No** | Layer button cambia color (3 colores = 3 layers), LED feedback suficiente |
| ¿LED behavior? | **Según config del folder** | Cada botón define su LED, más flexible |
| ¿Max depth? | **3 niveles** | Enforceado en enter_folder() |

### Notas de Implementación
- Agregar `unregister_callback(callback)` al FolderManager
- `enter_folder()` debe validar que folder existe en config
- Log warning si folder no existe

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

### Decisiones de Diseño (CONFIRMADAS)
| Pregunta | Decisión | Razón |
|----------|----------|-------|
| ¿Async integration? | **ThreadPoolExecutor + asyncio.run()** | K2 Deck es sync, thread separado para async |
| ¿OAuth flow? | **Flow completo (como Spotify)** | UX limpia, browser popup, callback server |
| ¿Token storage? | **~/.k2deck/twitch_tokens.json** | Consistente con Spotify |
| ¿Rate limiting? | **1 acción/segundo mínimo** | Twitch rate limits estrictos |
| ¿Reconnect? | **Retry cada 30s (como OBS)** | Patrón probado |

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
| 6 | Counter | ✅ DONE | ~130 | - |
| 7 | Text-to-Speech | ✅ DONE | ~90 | - |
| 8 | Folders/Pages | ✅ DONE | ~545 | - |
| 9 | Twitch Integration | ✅ DONE | ~570 | - |
| 10 | Web UI Backend | ✅ DONE | ~850 | - |
| 11 | **Web UI Frontend** | ❌ TODO | ~3000 | Alta |
| 12 | **Timer/Countdown** | ❌ TODO | ~120 | Media |
| 13 | **Plugin System** | ❌ TODO | ~600 | Baja |

---

## Testing Strategy

### Estado Actual (360 tests ✅, 7 skipped)

| Módulo | Tests | Cobertura |
|--------|-------|-----------|
| `core/keyboard.py` | 25 | Scan codes, INPUT structures, hotkeys |
| `core/layers.py` | 13 | Layer state, callbacks, LED colors |
| `core/mapping_engine.py` | 11 | Config loading, resolution, multi-zone |
| `core/throttle.py` | 13 | Rate limiting, debounce |
| `core/obs_client.py` | 19 | Connection, reconnect, operations |
| `core/analog_state.py` | 19 | Singleton, persistence, callbacks, debounce |
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
| `core/folders.py` | 23 | Stack navigation, callbacks, max depth |
| `actions/twitch.py` | 24 | Mock twitchAPI, actions, rate limiting |
| `web/*` | 32 | Config API, Profiles, K2 state, WebSocket |

### Tests Requeridos por Feature Pendiente

| Feature | Tests Nuevos | Estrategia |
|---------|--------------|------------|
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
