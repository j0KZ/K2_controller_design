# Changelog

All notable changes to K2 Deck will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

#### Documentation
- **UX/UI Reference (§7 in feature-plans.md):**
  - StreamController real UI analysis from screenshots and source code
  - GTK4 + libadwaita theme documentation with actual color values
  - Component mapping: StreamController → K2 Deck equivalents
  - Official K2 hardware layout from Allen & Heath overlay PDFs
  - ASCII diagram of all 52 controls (4 encoders, 12 pots, 16 buttons, 4 faders)
  - `K2_LAYOUT` JavaScript constant for Web UI grid generation

- **Analog Control Sync (Jump Mode):**
  - `AnalogStateManager` design for persisting fader/pot positions
  - WebSocket events: `analog_change` (real-time), `analog_state` (initial)
  - Jump mode behavior: immediate sync to physical position on move
  - Pinia store pattern for frontend analog state management

- **Architecture Updates (k2-controller-design.md):**
  - Updated fader flow diagram with `AnalogStateManager` and WebSocket broadcast
  - New "Sincronización de Controles Analógicos" section
  - Corrected tech stack: Flask → FastAPI
  - Expanded project structure with `core/analog_state.py`, `core/folders.py`, etc.

- **CLAUDE.md Updates:**
  - Tech stack: added `twitchAPI`, `obsws-python`, `fastapi + uvicorn + Vue.js`
  - Project structure: added `web/` directory, `core/analog_state.py`, `core/obs_client.py`, etc.
  - Hardware Notes: new "Analog Control Sync (Jump Mode)" subsection

#### Implementation
- **Web UI Backend (Feature #10):**
  - `core/analog_state.py`: AnalogStateManager singleton with debounced persistence
  - `web/server.py`: FastAPI app with CORS, lifespan, WebSocket endpoint
  - `web/websocket/manager.py`: ConnectionManager for real-time event broadcast
  - `web/routes/config.py`: Config CRUD, validation, import/export
  - `web/routes/profiles.py`: Profile management (create, delete, activate)
  - `web/routes/k2.py`: K2 layout, state, LEDs, layer, analog, MIDI devices
  - `web/routes/integrations.py`: OBS/Spotify/Twitch status and connection
  - 21 REST endpoints + WebSocket with 9 event types
  - 51 new tests (19 analog_state + 32 web_api)

### Changed
- Web UI tech stack documentation from Flask to FastAPI + Vue.js

### Design Decisions
- **Jump mode over Pickup mode** for analog sync: User preference for precision over smoothness
  - Rationale: K2 is passive MIDI (cannot report state on connect)
  - Touching all 12 analog controls to sync is impractical
  - Jump provides predictable, exact response to user input

---

## [0.1.0] - 2024-XX-XX (Phase 1 MVP)

### Added
- Initial Phase 1 MVP implementation
- MIDI listener with auto-reconnect
- Mapping engine for JSON config → action resolution
- Actions: hotkey, volume, mouse scroll, system commands
- LED manager with color offset system (Red/Amber/Green)
- System tray integration
- MIDI learn and monitor tools
- Comprehensive test suite

### Technical Details
- K2 LED colors use note offset (not velocity): Red=+0, Amber=+36, Green=+72
- Fader throttling at ~30Hz to prevent pycaw overload
- ThreadPoolExecutor(max_workers=4) for non-blocking action execution
