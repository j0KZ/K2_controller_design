# K2 Deck

Turn your Allen & Heath Xone:K2 into a system-wide macro controller for Spotify, Discord, VS Code, and Brave.

## Features

- **Per-app volume control** via faders (Spotify, Discord, VS Code, Master)
- **Media keys** for Spotify (Play/Pause, Next, Previous)
- **Discord hotkeys** (Mute, Deafen) with LED feedback
- **VS Code shortcuts** (Run/Debug, Terminal, Sidebar, Format)
- **Brave shortcuts** (Tab switching, Refresh, Close tab, DevTools)
- **Mouse scroll** via encoders for Discord/VS Code
- **LED feedback** with toggle, flash, and static modes
- **Timer/Countdown** with completion callbacks (pomodoro, stream breaks)
- **OSC bridge** to Pure Data for audio synthesis control
- **Claude Desktop integration** via MCP (10 tools for full K2 control)
- **Auto-reconnect** when K2 is disconnected/reconnected
- **System tray** for background operation

## Requirements

- Windows 10/11
- Python 3.12+
- Allen & Heath Xone:K2 controller

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd K2_controller_design

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### 1. Discover your K2's MIDI mapping

```bash
python -m k2deck.tools.midi_learn
```

Press each control on your K2 to discover note/CC numbers. Use `[L]` to test LEDs, `[S]` to save mappings.

### 2. Update config with your mappings

Edit `k2deck/config/default.json` with the note/CC numbers discovered in step 1.

### 3. Run K2 Deck

```bash
python -m k2deck
```

The app runs in the system tray. Right-click the tray icon for options.

## Usage

### Commands

```bash
# Run main application
python -m k2deck

# Run with debug logging
python -m k2deck --debug

# Run MCP server (Claude Desktop integration)
python -m k2deck.mcp

# Run MIDI learn tool
python -m k2deck --learn
# or
python -m k2deck.tools.midi_learn

# Run with custom config
python -m k2deck --config path/to/config.json

# Run tests
pytest
```

### Column Layout

```
         COL 1          COL 2          COL 3          COL 4
         SPOTIFY        DISCORD        VS CODE        BRAVE/SYSTEM
         ───────        ───────        ───────        ────────────

ENC      Seek           Scroll         Scroll         Switch tabs
ENC push Like*          Mute mic       Cmd Palette    New tab

BTN A    Play/Pause     Mute mic       Run/Debug      Refresh
BTN B    Next           Deafen         Terminal       Close tab
BTN C    Prev           Screenshare*   Sidebar        DevTools

FADER    App vol        App vol        App vol        Master vol

BTN D    Shuffle*       DnD toggle*    Format doc     Bookmark

* = Phase 2 (requires API integration)
```

## Configuration

Configuration is in JSON format at `k2deck/config/default.json`.

### Key sections:

- `midi_channel`: Your K2's MIDI channel (default: 16)
- `mappings.note_on`: Button mappings
- `mappings.cc_absolute`: Fader/knob mappings
- `mappings.cc_relative`: Encoder mappings
- `led_defaults`: Default LED states on startup

### Action types:

| Type | Description |
|------|-------------|
| `hotkey` | Keyboard shortcut |
| `hotkey_relative` | Directional hotkey (CW/CCW) |
| `mouse_scroll` | Mouse scroll |
| `volume` | Per-app volume control |
| `media_key` | Media key (play, next, etc.) |
| `system` | System command (lock, screenshot) |
| `timer_start` | Start a countdown timer |
| `timer_stop` | Stop a running timer |
| `timer_toggle` | Toggle timer on/off |
| `osc_send` | Send OSC message (fader/pot) |
| `osc_send_relative` | Send OSC message (encoder) |
| `osc_send_trigger` | Send OSC bang/toggle (button) |
| `noop` | Placeholder (no action) |

### LED modes:

| Mode | Description |
|------|-------------|
| `toggle` | Toggle between on_color and off_color |
| `flash` | Flash N times then return to previous |
| `static` | Set color once |

## Claude Desktop Integration (MCP)

K2 Deck exposes 10 MCP tools so Claude can control your K2 via natural language:

- Read controller state, layout, LED colors, analog positions
- Set LEDs, switch layers, activate profiles
- Trigger any action (hotkeys, timers, sound, etc.)
- Check integration status (OBS, Spotify, Twitch)

### Setup

Add to `claude_desktop_config.json` (use the **venv Python**, not system Python — the venv has all required dependencies):

```json
"k2deck": {
    "command": "<path-to>/K2_controller_design/.venv/Scripts/python.exe",
    "args": ["<path-to>/K2_controller_design/k2deck/mcp/server.py"]
}
```

The MCP server auto-starts the K2 Deck web server if it's not already running.

## Discord Setup

Discord global hotkeys must be configured manually:

1. Open Discord Settings > Keybinds
2. Add these global shortcuts:
   - Toggle Mute: `Ctrl+Shift+M`
   - Toggle Deafen: `Ctrl+Shift+D`

## Hardware Notes

- K2 default MIDI channel is 15 (user's K2 may be on channel 16)
- **LED colors use NOTE OFFSET, not velocity:**
  - Red = base_note + 0
  - Amber = base_note + 36
  - Green = base_note + 72
- Latching layers must be OFF for free LED control
- Only ONE application can use the MIDI port at a time

## Troubleshooting

### "No MIDI devices found"
- Check K2 is connected via USB
- Try a different USB port
- Restart the K2

### "Could not open MIDI port"
- Another application (DAW, DJ software) has the K2 port open
- Close other MIDI applications and retry

### LEDs not working
- Ensure latching layers are OFF on the K2
- Run `midi_learn.py` and test LEDs with `[L]` command
- Verify note numbers in config match your K2

### Hotkeys not working in Discord
- Discord global hotkeys must be configured in Discord Settings
- Verify the key combinations match your config

## Project Structure

```
k2deck/
├── __main__.py            # Entry point
├── k2deck.py              # Main app + system tray
├── config/
│   └── default.json       # Default mapping profile
├── core/
│   ├── midi_listener.py   # MIDI input + auto-reconnect
│   ├── midi_output.py     # MIDI output (LEDs)
│   ├── mapping_engine.py  # Event → Action resolver
│   ├── throttle.py        # Rate limiter for CC
│   ├── timer_manager.py   # Countdown timer manager
│   └── osc.py             # OSC 1.0 encoder + UDP sender
├── actions/
│   ├── base.py            # Action ABC
│   ├── hotkey.py          # Keyboard simulation
│   ├── volume.py          # Per-app volume (pycaw)
│   ├── timer.py           # Timer start/stop/toggle
│   ├── osc_send.py        # OSC send to Pure Data
│   └── system.py          # System commands
├── feedback/
│   ├── led_colors.py      # Color constants
│   └── led_manager.py     # LED state machine
├── mcp/
│   ├── client.py          # HTTP client for REST API
│   └── server.py          # MCP server (10 tools)
├── web/
│   ├── server.py          # FastAPI + WebSocket
│   └── routes/            # REST API endpoints
├── tools/
│   └── midi_learn.py      # MIDI discovery tool
└── tests/                 # 643 tests
```

## License

MIT
