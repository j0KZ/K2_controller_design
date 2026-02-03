# K2 Deck — Xone:K2 System Controller

## Concepto

App Python que convierte el Xone:K2 en un macro controller para el workflow diario: Spotify, Discord, VS Code y Brave. Sin intermediarios, sin Ableton, sin Companion.

---

## Hardware Reference: Xone:K2

```
┌─────────────────────────────────────────────┐
│  [ENC1]    [ENC2]    [ENC3]    [ENC4]       │  4 encoders (infinite + push)
│  ○ push    ○ push    ○ push    ○ push       │  → CC two's complement + Note On/Off
│                                              │
│  (K1)      (K2)      (K3)      (K4)         │  Row 1: 4 pots (0-127, CC absolute)
│  (K5)      (K6)      (K7)      (K8)         │  Row 2: 4 pots
│  (K9)      (K10)     (K11)     (K12)        │  Row 3: 4 pots
│                                              │
│  [A1]      [A2]      [A3]      [A4]         │  Row A: 4 buttons (tri-color LED)
│  [B1]      [B2]      [B3]      [B4]         │  Row B: 4 buttons (tri-color LED)
│  [C1]      [C2]      [C3]      [C4]         │  Row C: 4 buttons (tri-color LED)
│                                              │
│  ║F1║      ║F2║      ║F3║      ║F4║         │  4 faders (0-127, CC absolute)
│                                              │
│  [D1]      [D2]      [D3]      [D4]         │  Row D: 4 buttons (tri-color LED)
│  [LAYER]   [ENC5]    [ENC6]    [EXIT]       │  Bottom: layer + 2 push-encoders + exit
└─────────────────────────────────────────────┘

Controles: 52 (single layer) / 171 (3 layers)
MIDI Channel: 15 (default, 0-indexed: 14) — tu K2 está en channel 16 (0-indexed: 15)
Encoders: CC two's complement (1=CW, 127=CCW). Push = Note On/Off.
Pots: CC absolute 0-127.
Faders: CC absolute 0-127.
Buttons: Note On (press, vel 127) / Note Off (release, vel 0).
Layers: 3 layers. Con latching off, layers deshabilitadas y LED controlable libremente.
```

### LED Control — NOTE OFFSET, NO VELOCITY

**CRÍTICO: Los LEDs del K2 se controlan por NOTE NUMBER, no por velocity.**

Cada botón tiene 3 notas MIDI asignadas (una por color). El color se determina sumando un offset al note number base del botón:

```
Color     Offset    Ejemplo (botón base = note 36)
───────   ───────   ─────────────────────────────────
Red       +0        Send Note On 36  → LED rojo
Amber     +36       Send Note On 72  → LED ámbar
Green     +72       Send Note On 108 → LED verde
Off       Note Off en cualquiera de las 3 notas
```

**Verificado en Mixxx source:**
```javascript
XoneK2.color = { red: 0, amber: 36, green: 72 };
```

**Verificado en VirtualDJ mapping:**
```xml
<led note="0x24" name="BUTTON_A_RED_LED" />    <!-- 0x24 = 36 -->
<led note="0x48" name="BUTTON_A_AMBER_LED" />  <!-- 0x48 = 72 = 36+36 -->
<led note="0x6C" name="BUTTON_A_GREEN_LED" />  <!-- 0x6C = 108 = 36+72 -->
```

Para cambiar color: enviar Note On en la nota del nuevo color. No hace falta apagar el anterior — el nuevo color sobreescribe al activo.

**IMPORTANTE:** Latching layers debe estar OFF para control libre de LEDs. Si latching está ON, el color del LED lo determina el layer activo (Red/Amber/Green), no el MIDI output.

---

## Diseño por Columnas: 1 App = 1 Columna

```
         COL 1          COL 2          COL 3          COL 4
         SPOTIFY        DISCORD        VS CODE        BRAVE/SYSTEM
         ───────        ───────        ───────        ────────────

ENC      Seek ←→ [1]    Scroll ←→ [2] Scroll ←→ [2]  Switch tabs [3]
ENC push Like track [1]  Mute mic      Cmd Palette     New tab

K row1   EQ Bass         Input vol [4]  Font size       Zoom level
K row2   EQ Mid          Output vol     Scroll speed    —
K row3   EQ Treble       — (reserva)    — (reserva)     — (reserva)

BTN A    ▶ Play/Pause    🎤 Mute mic    ▶ Run/Debug     🔄 Refresh
BTN B    ⏭ Next          🔇 Deafen      ⌨ Terminal      ✕ Close tab
BTN C    ⏮ Prev          📺 Screenshare 📁 Sidebar       🔧 DevTools

FADER    🔊 App vol      🔊 App vol     🔊 App vol      🔊 Master vol

BTN D    🔀 Shuffle      🔕 DnD toggle  📝 Format doc   ⭐ Bookmark
```

### Notas de diseño

```
[1] Seek y Like requieren Spotify API (spotipy) → Fase 2.
    Fallback Fase 1: Seek = media keys (impreciso). Like = no disponible.

[2] Scroll en Discord/VS Code requiere MOUSE SCROLL simulation,
    no keyboard hotkeys. Usar pynput mouse.scroll().
    Action type necesario: "mouse_scroll"

[3] Switch tabs: Ctrl+Tab (CW) / Ctrl+Shift+Tab (CCW).
    Action type: "hotkey_relative"

[4] Discord input/output vol son controles del sistema operativo,
    no de Discord. Usan pycaw sobre Discord.exe.
    Per-user volume NO es posible sin Discord API/bot.
```

### LED Feedback Plan

| Botón | Estado ON               | Estado OFF     |
|-------|-------------------------|----------------|
| A1    | Green (playing)         | Amber (paused) |
| A2    | Red (mic muted)         | Green (live)   |
| B2    | Red (deafened)          | Off            |
| B3    | Green (terminal open)   | Off            |
| C4    | Amber (DevTools open)   | Off            |
| D2    | Red (Do Not Disturb)    | Off            |

**Limitación:** El estado real de Spotify/Discord no se puede leer sin API. En Fase 1, los LEDs son toggle local (el app trackea su propio estado, puede desincronizarse del estado real). En Fase 2 con APIs, se sincronizan.

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│                         K2 Deck                          │
│                                                          │
│  ┌──────────┐    ┌───────────┐    ┌──────────────────┐   │
│  │  MIDI    │───▶│  Mapping  │───▶│  Action Engine   │   │
│  │ Listener │    │  Engine   │    │                  │   │
│  │ (mido)   │    │  (JSON)   │    │ ┌──────────────┐ │   │
│  └──────────┘    └───────────┘    │ │ Hotkey       │ │   │
│       │                           │ │ (pynput kb)  │ │   │
│       │          ┌───────────┐    │ ├──────────────┤ │   │
│       │          │  Profile  │    │ │ MouseScroll  │ │   │
│       │          │  Manager  │    │ │ (pynput ms)  │ │   │
│       │          │           │    │ ├──────────────┤ │   │
│       │          └───────────┘    │ │ Volume       │ │   │
│       │                           │ │ (pycaw)      │ │   │
│  ┌──────────┐    ┌───────────┐    │ ├──────────────┤ │   │
│  │  MIDI    │◀───│   LED     │    │ │ Spotify      │ │   │
│  │ Output   │    │  Manager  │    │ │ (spotipy)    │ │   │
│  │ (mido)   │    │           │    │ ├──────────────┤ │   │
│  └──────────┘    └───────────┘    │ │ Window       │ │   │
│                                   │ │ (pywin32)    │ │   │
│  ┌──────────┐    ┌───────────┐    │ ├──────────────┤ │   │
│  │ System   │    │ Throttle  │    │ │ System       │ │   │
│  │  Tray    │    │ Manager   │    │ │ (lock, etc)  │ │   │
│  │(pystray) │    │ (CC rate) │    │ └──────────────┘ │   │
│  └──────────┘    └───────────┘    └──────────────────┘   │
│                                                          │
│  ┌──────────┐                                            │
│  │ Web UI   │  ← Fase 3                                 │
│  │ (Flask)  │                                            │
│  └──────────┘                                            │
└──────────────────────────────────────────────────────────┘

Threading model:
  Main thread      → pystray event loop
  MIDI thread      → mido listener (daemon)
  Action thread    → ThreadPoolExecutor (max_workers=4)
  Throttle         → Rate-limit CC actions (faders/knobs: max 30 calls/sec)
  Reconnect thread → Si K2 se desconecta, retry cada 5s
```

---

## Stack Técnico

| Componente | Librería | Propósito |
|---|---|---|
| MIDI I/O | `mido` + `python-rtmidi` | Escuchar K2 + enviar LEDs |
| Hotkeys | `pynput` (keyboard) | Simular atajos de teclado |
| Mouse scroll | `pynput` (mouse) | Simular scroll para encoders |
| Volume por app | `pycaw` + `comtypes` | Control volumen individual (Windows Audio API) |
| Spotify | `spotipy` | API: like, seek, playlists. Fallback: media keys |
| Window manager | `pywin32` | Focus/launch apps |
| Config | JSON + `watchdog` | Hot-reload de config sin reiniciar |
| System tray | `pystray` + `Pillow` | Icono en tray, menú contextual |
| Logging | `logging` stdlib | Debug de MIDI messages |

---

## Estructura del Proyecto

```
k2deck/
├── __main__.py            # `python -m k2deck` entry
├── k2deck.py              # App init + system tray
├── config/
│   ├── default.json        # Mapeo por defecto
│   ├── coding.json         # Profile: VS Code focus
│   └── music.json          # Profile: Spotify focus
├── core/
│   ├── __init__.py
│   ├── midi_listener.py    # MIDI input + reconnect
│   ├── midi_output.py      # MIDI output (LEDs)
│   ├── mapping_engine.py   # MIDI event → action
│   ├── profile_manager.py  # Profile load/switch/hot-reload
│   └── throttle.py         # Rate limiter para CC (faders/knobs)
├── actions/
│   ├── __init__.py
│   ├── base.py             # Action ABC
│   ├── hotkey.py           # Keyboard simulation (pynput)
│   ├── mouse_scroll.py     # Mouse scroll simulation (pynput)
│   ├── volume.py           # Per-app volume (pycaw)
│   ├── spotify.py          # Spotify Web API (spotipy) [Fase 2]
│   ├── window.py           # Focus/launch apps (pywin32) [Fase 2]
│   └── system.py           # Lock, screenshot, etc.
├── feedback/
│   ├── __init__.py
│   ├── led_manager.py      # LED state machine
│   └── led_colors.py       # Color offset constants + note→LED mapping
├── tools/
│   ├── __init__.py
│   ├── midi_learn.py       # CLI: interactive discover + LED test + save
│   └── midi_monitor.py     # CLI: raw passthrough (debug only)
├── tests/
│   ├── __init__.py
│   ├── test_mapping_engine.py
│   ├── test_hotkey_action.py
│   ├── test_volume_action.py
│   ├── test_led_manager.py
│   └── test_throttle.py
├── requirements.txt
└── README.md
```

---

## Action Types Registry

Todas las action types que el mapping engine debe soportar:

| Action type | Clase | Input | Descripción |
|---|---|---|---|
| `hotkey` | HotkeyAction | Note On | Simula combo de teclado |
| `hotkey_relative` | HotkeyAction | CC relative | CW→hotkey A, CCW→hotkey B |
| `mouse_scroll` | MouseScrollAction | CC relative | CW→scroll up, CCW→scroll down |
| `volume` | VolumeAction | CC absolute | Fader/knob → volumen de app |
| `media_key` | HotkeyAction | Note On | Media keys (play, next, prev, mute) |
| `spotify_*` | SpotifyAction | Note On / CC | API actions [Fase 2] |
| `launch` | WindowAction | Note On | Abrir/focus app [Fase 2] |
| `system` | SystemAction | Note On | Lock, screenshot, etc. |
| `multi` | MultiAction | any | Ejecuta lista de actions en secuencia |
| `noop` | — | any | Mapeo explícitamente vacío (suppress log) |

---

## Config JSON: Formato

```json
{
  "profile_name": "default",
  "midi_channel": 16,
  "midi_device": "XONE:K2",
  
  "_note": "Los note/CC numbers son PLACEHOLDER. Correr midi_learn.py para obtener los reales.",

  "led_color_offsets": {
    "red": 0,
    "amber": 36,
    "green": 72
  },

  "throttle": {
    "cc_max_hz": 30,
    "cc_volume_max_hz": 20
  },

  "mappings": {
    "note_on": {
      "36": {
        "name": "Spotify Play/Pause",
        "action": "media_key",
        "keys": ["media_play_pause"],
        "led": { "color": "green", "mode": "toggle", "off_color": "amber" }
      },
      "37": {
        "name": "Spotify Next",
        "action": "media_key",
        "keys": ["media_next"]
      },
      "38": {
        "name": "Spotify Prev",
        "action": "media_key",
        "keys": ["media_previous"]
      },
      "40": {
        "name": "Discord Mute",
        "action": "hotkey",
        "keys": ["ctrl", "shift", "m"],
        "_note": "Requiere que Discord tenga este hotkey configurado como GLOBAL",
        "led": { "color": "red", "mode": "toggle", "off_color": "green" }
      },
      "41": {
        "name": "Discord Deafen",
        "action": "hotkey",
        "keys": ["ctrl", "shift", "d"],
        "led": { "color": "red", "mode": "toggle" }
      },
      "44": {
        "name": "VS Code Run/Debug",
        "action": "hotkey",
        "keys": ["f5"],
        "led": { "color": "green", "mode": "flash", "flash_count": 3 }
      },
      "45": {
        "name": "VS Code Terminal",
        "action": "hotkey",
        "keys": ["ctrl", "`"],
        "led": { "color": "green", "mode": "toggle" }
      },
      "48": {
        "name": "Brave Refresh",
        "action": "hotkey",
        "keys": ["f5"]
      },
      "52": {
        "name": "Shuffle Toggle",
        "action": "noop",
        "_note": "Fase 2: requiere Spotify API"
      }
    },

    "cc_absolute": {
      "1": {
        "name": "Spotify Volume",
        "action": "volume",
        "target_process": "Spotify.exe",
        "_note": "CC number es placeholder. Verificar con midi_learn."
      },
      "2": {
        "name": "Discord Volume", 
        "action": "volume",
        "target_process": "Discord.exe"
      },
      "3": {
        "name": "VS Code Volume",
        "action": "volume",
        "target_process": "Code.exe"
      },
      "4": {
        "name": "Master Volume",
        "action": "volume",
        "target_process": "__master__"
      }
    },

    "cc_relative": {
      "16": {
        "name": "Spotify Seek",
        "action": "noop",
        "_note": "Fase 2: requiere Spotify API. Sin API no hay seek preciso."
      },
      "17": {
        "name": "Discord Scroll",
        "action": "mouse_scroll",
        "step": 3,
        "_note": "Scroll up/down. Requiere que Discord tenga foco."
      },
      "18": {
        "name": "VS Code Scroll",
        "action": "mouse_scroll",
        "step": 5
      },
      "19": {
        "name": "Switch Brave Tab",
        "action": "hotkey_relative",
        "cw": ["ctrl", "tab"],
        "ccw": ["ctrl", "shift", "tab"]
      }
    }
  },

  "led_defaults": {
    "on_start": [
      { "note": 36, "color": "amber" }
    ],
    "on_connect": "all_off",
    "startup_animation": true
  }
}
```

---

## Flujos Principales

### 1. Fader → Volumen de App (con throttle)

```
K2 Fader move (60+ msgs/sec posibles)
  → CC message (ch 16, cc# X, value 0-127)
  → Throttle: ¿pasaron >33ms desde último call? Si no, skip.
  → mapping_engine.resolve("cc_absolute", X)
  → VolumeAction.execute(target="Spotify.exe", value=0.75)
  → pycaw: set Spotify volume to 75%
     → Session cache: refresh cada 5s, no en cada call
```

### 2. Botón → Hotkey con LED feedback

```
K2 Button press
  → Note On (ch 16, note 36, vel 127)
  → mapping_engine.resolve("note_on", 36)
  → HotkeyAction.execute(keys=["media_play_pause"])
  → pynput: simula media key
  → LED Manager: toggle estado interno
    → Si ahora ON: send Note On (36 + 72) = note 108 → LED verde
    → Si ahora OFF: send Note On (36 + 36) = note 72 → LED ámbar
```

### 3. Encoder → Mouse Scroll

```
K2 Encoder turn CW
  → CC message (ch 16, cc# 18, value 1)
  → mapping_engine.resolve("cc_relative", 18)
  → direction = CW (value 1-63)
  → MouseScrollAction.execute(direction=UP, step=5)
  → pynput: mouse.scroll(0, 5)

K2 Encoder turn CCW
  → CC message (ch 16, cc# 18, value 127)
  → direction = CCW (value 65-127)
  → MouseScrollAction.execute(direction=DOWN, step=5)
  → pynput: mouse.scroll(0, -5)
```

### 4. Encoder → Acción direccional (hotkey)

```
K2 Encoder turn CW
  → CC message (ch 16, cc# 19, value 1)
  → mapping_engine.resolve("cc_relative", 19)
  → HotkeyAction.execute(keys=["ctrl", "tab"])  [next tab]

K2 Encoder turn CCW  
  → CC message (ch 16, cc# 19, value 127)
  → HotkeyAction.execute(keys=["ctrl", "shift", "tab"])  [prev tab]
```

### 5. Botón → Spotify API (Fase 2)

```
K2 Encoder push (Like)
  → Note On (ch 16, note 32, vel 127)
  → SpotifyAction.like_current_track()
  → spotipy: GET current track → PUT save track
  → LED Manager: flash green 3 times → vuelve a estado anterior
  
  Error path:
  → spotipy raises → log warning → LED flash red 1 time → continue
```

---

## Fases de Implementación

### Fase 1: MVP funcional

| # | Componente | Resultado verificable |
|---|---|---|
| 1 | `tools/midi_learn.py` | Imprime MIDI del K2 en consola + test LEDs |
| 2 | `core/midi_listener.py` | Recibe MIDI en thread, reconecta si pierde K2 |
| 3 | `core/midi_output.py` | Envía Note On al K2, LEDs prenden |
| 4 | `core/throttle.py` | Rate limita CC a N calls/sec |
| 5 | `core/mapping_engine.py` | JSON config → resuelve events a actions |
| 6 | `actions/hotkey.py` | Simula teclas, funciona en background |
| 7 | `actions/mouse_scroll.py` | Simula scroll, funciona en background |
| 8 | `actions/volume.py` | Fader controla volumen de Spotify/Discord/etc |
| 9 | `feedback/led_colors.py` | Constants de offsets + helpers |
| 10 | `feedback/led_manager.py` | Toggle/flash/static con state tracking |
| 11 | `config/default.json` | Profile funcional (con note numbers reales post-learn) |
| 12 | `k2deck.py` + `__main__.py` | Entry point + system tray + pipeline completo |

**Resultado Fase 1:** K2 funciona como macro pad. Faders = volumen por app. Botones = hotkeys con LED feedback. Encoders = scroll + tab switch.

### Fase 2: Integración rica

| # | Componente | Resultado verificable |
|---|---|---|
| 13 | `actions/spotify.py` | Like, seek, playlist info via API |
| 14 | `actions/window.py` | Focus/launch apps antes de hotkey |
| 15 | `core/profile_manager.py` | Layer button cambia profile + hot-reload |
| 16 | Encoder acceleration | Giro rápido = step multiplicado |
| 17 | Spotify state sync | LEDs reflejan estado real (playing/paused) |

### Fase 3: Pulido

| # | Componente |
|---|---|
| 18 | Context-aware (detecta ventana activa, ajusta mappings) |
| 19 | Web UI para editar mapeos visualmente |
| 20 | Auto-start con Windows (scheduled task) |
| 21 | README completo con setup guide |

---

## Decisiones de Diseño & Trade-offs

| Decisión | Alternativa | Razón |
|---|---|---|
| Python (no Node) | Node + electron | pycaw nativo Windows, no necesita UI, más liviano |
| JSON config (no YAML) | YAML/TOML | Nativo en Python, sin deps extra. Suficiente. |
| pynput (no pyautogui) | pyautogui | Más bajo nivel, funciona en background, keyboard + mouse |
| pycaw (no nircmd) | subprocess + nircmd | API nativa, per-process volume, no shell calls |
| Spotify API + media key fallback | Solo media keys | API da like/seek/state. Media keys = Fase 1 fallback |
| System tray (no GUI) | tkinter | Invisible cuando funciona. Tray icon suficiente. |
| ThreadPoolExecutor (no asyncio) | asyncio | pycaw/pynput/pywin32 son sync. Thread pool más simple. |
| NO focus app por defecto | Auto-focus | Discord/Spotify hotkeys son globales. Focus roba ventana activa. |

---

## Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Puerto MIDI ocupado | No arranca | Detectar al inicio, nombrar qué app lo tiene. Retry con backoff. |
| K2 no conectado al iniciar | No arranca | Modo standby: esperar K2, retry cada 5s. Notificar en tray. |
| K2 se desconecta mid-use | Se cae | Reconnect loop automático. LED all-off detecta desconexión. |
| pycaw falla en apps UWP/Electron | Sin volumen | Fallback: buscar por substring en process name. Log warning. |
| Fader spam (60+ msgs/sec) | CPU/API saturado | Throttle manager: max 20-30 calls/sec para volume. |
| pycaw GetAllSessions() lento | Latencia en fader | Cache de sessions, refresh cada 5s en thread separado. |
| Spotify OAuth expira | API falla | Auto-refresh token. Fallback a media keys. |
| LED state desynced | Confuso visualmente | Fase 2: polling API para sync real. Fase 1: disclaimer. |
| LED note mapping incorrecto | LEDs random | midi_learn incluye LED test mode (prende cada LED por color). |
| Discord global hotkey no config | Botón no hace nada | README: instrucciones para configurar Discord keybinds. |
| Python no arranca con Windows | Olvido manual | Fase 3: installer crea scheduled task. |

---

## Dependencias (requirements.txt)

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

**Nota:** `python-rtmidi` puede requerir Visual C++ Build Tools en Windows si no hay wheel pre-compilado. En la mayoría de los casos pip instala el wheel sin problema.

---

## MIDI Learn Tool

**Primer tool que se ejecuta. Descubre el mapeo real del K2.**

```
$ python -m k2deck.tools.midi_learn
K2 Deck MIDI Learn Tool
========================

Scanning MIDI devices...
Found: XONE:K2 MIDI

[LEARN MODE] Press any control on the K2:

[14:32:01] NOTE ON  | ch:16 | note:36  | vel:127  ← press
[14:32:01] NOTE OFF | ch:16 | note:36  | vel:0    ← release
[14:32:03] CC ABS   | ch:16 | cc:1     | val:64   ← fader midpoint
[14:32:05] CC REL   | ch:16 | cc:16    | val:1    ← encoder CW
[14:32:05] CC REL   | ch:16 | cc:16    | val:127  ← encoder CCW

Commands:
  [L] Test LEDs (cycles R/A/G on last pressed button)
  [S] Save discovered controls to k2_map.json
  [Q] Quit

[LED TEST] Sending Note On 36 (red)...  → ¿Se prendió rojo? [y/n]
[LED TEST] Sending Note On 72 (amber)... → ¿Se prendió ámbar? [y/n]
[LED TEST] Sending Note On 108 (green)... → ¿Se prendió verde? [y/n]
✓ LED mapping confirmed for button at note 36.
```

**El LED test integrado en midi_learn es crítico** — confirma que los offsets de color funcionan antes de configurar el profile completo.

---

## Changelog de Auditoría

Problemas encontrados y corregidos en esta versión:

1. **CRÍTICO: LED colors eran velocity-based (incorrecto).** Corregido a note offset (+0/+36/+72). Verificado con Mixxx source y VirtualDJ mappings.
2. **Discord "User 1/2/3 vol" via knobs.** Eliminado — per-user volume no es posible sin Discord bot/API. Reemplazado por input/output volume vía pycaw.
3. **Scroll actions (Discord/VS Code) no tenían action type.** Agregado `mouse_scroll` action type con pynput mouse.
4. **Spotify Seek en Fase 1 config.** Movido a `noop` — requiere API, no hay seek por hotkeys.
5. **12 knobs casi todos sin uso.** Reasignados: EQ Spotify, Discord volumes, VS Code font size, Brave zoom.
6. **CC section ambigua (absolute vs relative mezclados).** Separado en `cc_absolute` y `cc_relative` explícitamente.
7. **`target_app` renombrado a `target_process`.** pycaw busca por nombre de proceso (.exe).
8. **Sin throttle para faders.** Agregado `throttle.py` + config `cc_max_hz`. Sin esto, 60+ pycaw calls/sec.
9. **Sin pycaw session cache.** Documentado: cache sessions, refresh cada 5s.
10. **K2 desconectado al inicio no contemplado.** Agregado modo standby con retry.
11. **Faltaban `__init__.py` en la estructura.** Agregados.
12. **Faltaba `__main__.py`.** Agregado para `python -m k2deck`.
13. **Faltaba `tests/` directory.** Agregado.
14. **LED `note` field redundante en config.** Eliminado — se infiere del note del mapping padre.
15. **Faltaba `mouse_scroll.py` en actions.** Agregado.
16. **Faltaba `throttle.py` en core.** Agregado.
17. **Threading model no documentado.** Agregado en arquitectura.
18. **`target_app` focus-stealing en hotkeys.** Eliminado como default — hotkeys globales no necesitan focus.
19. **Action types no listados.** Agregada tabla registry completa.
20. **`led_maps.py` renombrado a `led_colors.py`.** Más descriptivo.
21. **Latching layers warning.** Documentado: debe estar OFF para LED libre.
