# K2 Deck — Roadmap & Plan

## 1. Version History

| Version | Date | Headline | Key Additions |
|---------|------|----------|---------------|
| v0.1.0 | 2025-02-02 | MVP | MIDI listener + auto-reconnect, mapping engine, hotkey actions, per-app volume (pycaw), mouse scroll, LED feedback, system tray, config hot-reload |
| v0.2.0 | 2025-02-03 | System Control | System commands (lock, sleep, shutdown), open URL, clipboard paste, multi-toggle, window focus/launch |
| v0.3.0 | 2025-02-04 | Rich Integrations | Conditional actions, software layers, Spotify API (9 actions), OBS WebSocket (5 actions), audio device switch, sound playback, TTS, counters, multi-K2 zones, SendInput migration, Web UI (FastAPI + Vue 3) |
| v0.4.0 | 2026-02-13 | OSC Bridge | OSC send actions (3 types), custom OSC 1.0 encoder, OscSender keyed singleton, Pure Data integration |
| v0.5.0 | 2026-02-13 | MCP + Timers | MCP server (10 tools for Claude Desktop), timer/countdown actions (3 types), REST trigger + timers endpoints |

Full changelog: [CHANGELOG.md](CHANGELOG.md)

## 2. Phase Status

### Phase 1: MVP — COMPLETE

All items delivered in v0.1.0:
- MIDI learn tool, MIDI listener with auto-reconnect
- Mapping engine with JSON configuration
- Hotkey actions (tap, hold, toggle modes)
- Per-app volume via pycaw
- LED feedback with tri-color control
- System tray background app
- Config hot-reload via watchdog

### Phase 2: Rich Integrations — COMPLETE

All items delivered across v0.2.0-v0.3.0:
- System commands, multi-toggle, window focus/launch
- Spotify API integration (9 action types)
- OBS WebSocket integration (5 action types)
- Conditional actions with context detection
- Software layers (3x controls)
- SendInput migration (pynput replaced for keyboard)

### Phase 3: Polish — COMPLETE

| Item | Status | Notes |
|------|--------|-------|
| Web UI for visual mapping editor | Built | 28 REST endpoints, WebSocket, Vue 3 SPA |
| Context-aware mode | Built | Conditional actions + profile auto-switch |
| Windows auto-start installer | Built | VBScript in Startup folder, tray toggle |
| README with setup guide | Built | Web UI, Spotify, OBS, troubleshooting sections |

### Unplanned Features Delivered

These were not in the original 3-phase plan but were added based on real usage:

| Feature | Version | Origin |
|---------|---------|--------|
| OSC bridge to Pure Data | v0.4.0 | Cross-project need (synthlab-mcp) |
| MCP server for Claude Desktop | v0.5.0 | AI-assisted workflow |
| Timer/countdown actions | v0.5.0 | Stream break reminders |
| Sound playback + TTS | v0.3.0 | Stream sound effects |
| Counter actions (persistent) | v0.3.0 | Kill/death counters for streaming |
| Audio device switching | v0.3.0 | Speakers/headphones toggle |
| Multi-K2 zone support | v0.3.0 | Dual-controller setup |
| Folder navigation (sub-pages) | v0.3.0 | More actions per button |
| Twitch API integration | v0.3.0 | Stream markers, clips, chat |
| Profile auto-switch | v0.3.0 | Auto-switch on focused app change |
| Profile export/import | v0.5.1 | Backup/share/restore profiles via Web UI |
| Single-instance guard | v0.5.1 | Windows named mutex prevents duplicate instances |

## 3. Current Metrics

| Metric | Count |
|--------|-------|
| Action types | 48 |
| REST API endpoints | 30 |
| WebSocket event types | 11 (9 server-to-client, 2 client-to-server) |
| MCP tools | 10 |
| Python source files | ~96 |
| Frontend source files (Vue + JS) | ~63 |
| Backend test files | 35 |
| Frontend test files | 30 |
| Backend tests | 671 passing, 7 skipped |
| Frontend coverage | 91%+ statements, 275 tests |

## 4. Planned Features

### High Priority

| Feature | Description | Complexity |
|---------|-------------|------------|
| ~~Windows auto-start~~ | ~~Startup shortcut or Windows service~~ | ~~Low~~ |
| Drag-and-drop config UI | Stream Deck-style: drag action cards onto K2 grid buttons | High |
| Encoder acceleration | Fast encoder turn = larger step increment, slow = fine control | Medium |
| Spotify state sync | Poll Spotify API to reflect current playing state on LEDs | Medium |
| ~~Profile export/import via UI~~ | ~~Download/upload profile JSON from Web UI~~ | ~~Low~~ |

### Medium Priority

| Feature | Description | Complexity |
|---------|-------------|------------|
| Web MIDI monitor improvements | Filter by event type, search, pause/resume, export log | Medium |
| Notification system | Toast notifications on action execution, error alerts | Low |
| LED pattern presets | Predefined LED patterns: all-green, chase, rainbow cycle | Medium |
| Twitch chat overlay | Display Twitch chat messages via TTS or on-screen overlay | Medium |
| Config validation UI | Real-time validation feedback when editing mappings in Web UI | Medium |

### Low Priority

| Feature | Description | Complexity |
|---------|-------------|------------|
| Cross-platform support | macOS/Linux (replace pycaw, pywin32, ctypes SendInput) | Very High |
| Plugin system | Third-party action modules loaded from a plugins directory | High |
| Mobile companion app | Phone app to trigger actions remotely via REST API | High |
| MIDI output actions | Send MIDI messages to other devices/apps from K2 Deck | Medium |
| Macro recorder | Record sequences of actions and replay on button press | Medium |

## 5. Technical Debt

### Code Quality

| Issue | Location | Severity | Notes |
|-------|----------|----------|-------|
| Hardcoded booleans in main app | `k2deck.py` | Low | Several feature flags inline rather than in config |
| MIDI stubs for testing | `tests/` | Low | Some tests use minimal stubs instead of proper mido mocks |
| K2Grid.vue untested | `web/frontend/` | Medium | Main grid component has no tests (imports all layout children) |
| 7 skipped backend tests | `tests/` | Low | Dangerous system operations (sleep, shutdown) — skipped for safety |
| ~~CLAUDE.md outdated~~ | Root | Resolved | Trimmed + linked to 5 docs (2026-02-15) |
| Old docs not yet pruned | `docs/archive/` | Low | 4 superseded docs archived, referenced only by CHANGELOG.md |

### Architecture Debt

| Issue | Impact | Mitigation |
|-------|--------|------------|
| Singleton state in tests | Test isolation | Reset patterns documented in Rules.md, but easy to forget |
| Lazy imports in routes | Silent failures | Try/except blocks swallow import errors — need better error reporting |
| Thread-based timers | Scalability | Fine for <20 timers, but asyncio would be cleaner long-term |
| No rate limiting on REST API | Security | Localhost-only mitigates risk, but no protection against local abuse |
| No authentication on Web UI | Security | Localhost-only binding, but any local process can access |
| ~~No single-instance guard~~ | Resolved | Windows named mutex in `core/instance_lock.py` (v0.5.1) |

### Testing Gaps

| Gap | Files Affected | Priority |
|-----|---------------|----------|
| K2Grid.vue integration test | 1 component + 8 children | Medium |
| End-to-end MIDI pipeline test | k2deck.py → mapping → action | Low |
| WebSocket reconnection test | websocket/manager.py | Low |
| Profile hot-reload race conditions | core/profile_switcher.py | Low |

## 6. Infrastructure Roadmap

| Item | Status | Target |
|------|--------|--------|
| CI/CD pipeline | Not started | GitHub Actions: lint + test on push |
| PyPI packaging | Not started | `pip install k2deck` |
| Windows installer (.exe) | Not started | PyInstaller or cx_Freeze |
| Documentation site | Not started | GitHub Pages from docs/ |
| Versioned releases | Manual | Automate with GitHub Releases + tags |
