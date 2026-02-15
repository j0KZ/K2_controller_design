# K2 Deck — Product Requirements Document

## 1. Product Vision

**One-sentence:** Turn an Allen & Heath Xone:K2 MIDI controller into a system-wide macro controller for daily workflow.

**Problem:** The Xone:K2 is designed for DJ software — there's no good tool to use it as a general-purpose system controller. Existing solutions (Companion, MIDI-OX) are either too complex, require intermediaries, or don't support per-app volume and LED feedback natively on Windows.

**Solution:** A Python background app that intercepts K2 MIDI events and executes 48 different action types — keyboard shortcuts, per-app volume, Spotify/OBS/Twitch API calls, OSC messages, timers, and more — with tri-color LED feedback and a Web UI for configuration.

## 2. Target User

- Power user / developer / streamer who owns a Xone:K2
- Daily tools: Spotify, Discord, VS Code, Brave, OBS
- Wants physical tactile control without leaving the current workflow
- Prefers precision over smoothness (Jump mode for faders)
- Comfortable with JSON config files, willing to run CLI tools

## 3. Hardware Target

**Allen & Heath Xone:K2**

```
┌─────────────────────────────────────────────┐
│  [ENC1]    [ENC2]    [ENC3]    [ENC4]       │  4 encoders (infinite + push)
│  ○ push    ○ push    ○ push    ○ push       │
│                                              │
│  (K1)      (K2)      (K3)      (K4)         │  Row 1: 4 pots
│  (K5)      (K6)      (K7)      (K8)         │  Row 2: 4 pots
│  (K9)      (K10)     (K11)     (K12)        │  Row 3: 4 pots
│                                              │
│  [A1]      [A2]      [A3]      [A4]         │  Row A: 4 buttons (tri-color LED)
│  [B1]      [B2]      [B3]      [B4]         │  Row B: 4 buttons
│  [C1]      [C2]      [C3]      [C4]         │  Row C: 4 buttons
│                                              │
│  ║F1║      ║F2║      ║F3║      ║F4║         │  4 faders
│                                              │
│  [D1]      [D2]      [D3]      [D4]         │  Row D: 4 buttons
│  [LAYER]   [ENC5]    [ENC6]    [EXIT]       │  Bottom row
└─────────────────────────────────────────────┘
```

**Control inventory:** 6 encoders (infinite + push), 12 pots, 4 faders, 16 buttons with tri-color LEDs, layer + exit buttons. Total: 52 controls per layer, up to 156 with 3 software layers.

**Key hardware constraints:**
- Single MIDI port access — only one app can hold the K2 port
- K2 doesn't report physical positions on connect — requires Jump mode
- LED colors use **note number offset** (+0=red, +36=amber, +72=green), NOT velocity
- Encoders use two's complement CC (1=CW, 127=CCW)
- Faders send up to 60+ CC messages/second — requires throttling

## 4. Core Features

| Feature | Version | Description |
|---------|---------|-------------|
| MIDI I/O + auto-reconnect | v0.1.0 | Detect K2, listen for events, reconnect on unplug |
| Keyboard hotkeys (SendInput) | v0.1.0 | Simulate keystroke combos with hardware scan codes |
| Per-app volume (pycaw) | v0.1.0 | Faders control individual app volumes |
| Mouse scroll via encoders | v0.1.0 | Encoder rotation → scroll wheel simulation |
| LED feedback (toggle/flash/static) | v0.1.0 | Tri-color LED state tracking with visual modes |
| System tray background app | v0.1.0 | Invisible operation, tray menu for config/status |
| Config hot-reload | v0.1.0 | Edit JSON, app reloads automatically (watchdog) |
| System commands | v0.2.0 | Lock, sleep, shutdown, screenshot, URL open, clipboard |
| Multi-toggle actions | v0.2.0 | Toggle between on/off hotkey sequences |
| Window focus/launch | v0.2.0 | pywin32 window management |
| Conditional actions | v0.3.0 | Different action per focused app |
| Software layers (1-3) | v0.3.0 | 3x controls on same hardware |
| OBS WebSocket integration | v0.3.0 | Scene switch, source toggle, stream/record control |
| Spotify API integration | v0.3.0 | Like, shuffle, seek, volume via spotipy OAuth |
| Twitch API integration | v0.3.0 | Markers, clips, chat, title/game changes |
| Audio device switching | v0.3.0 | Cycle speakers/headphones with a button |
| Sound playback + TTS | v0.3.0 | Play audio files, text-to-speech on button press |
| Counters (persistent) | v0.3.0 | Increment/decrement/reset counters, persisted to disk |
| Folders (button sub-pages) | v0.3.0 | Navigate into sub-page mappings |
| Multi-K2 support | v0.3.0 | Two K2 controllers as one (zone-based config) |
| OSC bridge to Pure Data | v0.4.0 | Forward MIDI events as OSC messages over UDP |
| MCP server (Claude Desktop) | v0.5.0 | 10 tools for AI control of K2 hardware |
| Timer/countdown actions | v0.5.0 | Named countdowns with completion callbacks |
| Web UI (Vue 3 + FastAPI) | v0.3.0+ | 28 REST endpoints, WebSocket, visual config editor |

## 5. Feature Categories

### Input Simulation
Keyboard hotkeys (tap, hold, toggle modes), mouse scroll, media keys. Uses Windows SendInput API with hardware scan codes for reliability.

### App Control
Spotify (9 actions), OBS (5 actions), Twitch (5 actions). Full API integration with OAuth, lazy connect, and auto-reconnect.

### System Control
Per-app and master volume, audio device switching, system commands (lock, sleep, screenshot), window focus/launch, URL open, clipboard paste.

### Advanced Logic
Conditional actions (different action per focused app), multi-toggle sequences, folders (button sub-pages), counters, software layers (3x controls), timer/countdown with completion callbacks.

### Audio/Visual Bridge
OSC send to Pure Data (normalize, curve, scale), sound playback (WAV/MP3), text-to-speech.

### Monitoring & Configuration
Web UI with visual K2 grid, MIDI monitor, profile management. MCP server for Claude Desktop integration. MIDI learn tool for discovering hardware mappings.

## 6. User Scenarios

### Streaming
OBS scene switch with a button, Twitch stream marker/clip, Discord mute/deafen toggle with LED feedback, timer for break reminders, sound effects on button press.

### Coding
VS Code run/debug, terminal toggle, sidebar toggle with LED. Discord mute. Spotify play/pause + next/prev via media keys. Per-app volume for Discord/Spotify/VS Code on separate faders.

### Music Production
OSC bridge sends fader/pot/encoder values to Pure Data. Each control maps to a synthesis parameter. LED indicates active patches. Timer for session tracking.

### AI-Assisted Workflow
Claude reads K2 state via MCP, suggests mappings, triggers actions by name. "Set all LEDs to green" or "activate the streaming profile" from natural language.

## 7. Success Criteria

| Metric | Target |
|--------|--------|
| Button press to action latency | < 50ms |
| Auto-reconnect on K2 replug | < 5s |
| Crash on single action failure | Never — log and continue |
| Fader CC throttle | ~30Hz (from 60+ raw) |
| Backend test coverage | 636 passing, 7 skipped (dangerous ops) |
| Frontend test coverage | 91%+ statements, 270+ tests |
| Action types supported | 48 |

## 8. Platform Constraints

- **Windows 10/11 only** — pycaw, pywin32, ctypes SendInput are Windows-specific
- **Python 3.12+** — uses type hints, match/case, f-strings
- **Single MIDI port** — only one app can hold the K2 port at a time
- **No GUI window** — system tray only, invisible when working
- **JSON config only** — no YAML/TOML, no database
- **Discord hotkeys must be global** — user configures in Discord Settings > Keybinds
