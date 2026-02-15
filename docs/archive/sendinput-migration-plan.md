# K2 Deck: SendInput Migration & Feature Plan

## Problem Statement

Current pynput-based keyboard simulation is unreliable:
- Uses virtual key codes, not hardware scan codes
- Keys get stuck (especially Ctrl+Win combinations)
- Multi-action sequences only execute first action reliably
- Detectable by anti-cheat systems in games
- Not how professional tools (Stream Deck) do it

## Solution: Windows SendInput API with Hardware Scan Codes

Stream Deck and other professional tools use the Windows SendInput API with the `KEYEVENTF_SCANCODE` flag. This sends hardware-level input that:
- Is more reliable for complex key combinations
- Works with games and apps that ignore virtual key codes
- Properly releases keys without getting stuck
- Is the standard Windows way to simulate hardware input

---

## Phase 1: SendInput Core Module

### New File: `k2deck/core/keyboard.py`

```python
# Core SendInput implementation
- SendInput structure definitions (ctypes)
- Scan code mappings for all keys
- Key press/release functions
- Hotkey execution with proper timing
- Release all modifiers function
```

### Key Features:
1. **KEYEVENTF_SCANCODE flag** - Hardware-level simulation
2. **Proper key timing** - Small delays between press/release
3. **Modifier state tracking** - Know what's held down
4. **Thread safety** - Lock for concurrent access
5. **Retry mechanism** - If first attempt fails, retry once

### Scan Code Reference:
```
A-Z: 0x1E-0x32 (varies)
0-9: 0x02-0x0B
F1-F12: 0x3B-0x46
Ctrl: 0x1D (left), 0xE01D (right)
Alt: 0x38 (left), 0xE038 (right)
Shift: 0x2A (left), 0x36 (right)
Win: 0xE05B (left), 0xE05C (right)
Space: 0x39
```

---

## Phase 2: Replace pynput in hotkey.py

### Changes:
1. Import new `keyboard` module instead of pynput
2. Update `execute_hotkey()` to use SendInput
3. Update `release_all_modifiers()` to use SendInput
4. Keep same function signatures for compatibility
5. Delete pynput imports after migration complete

### Backward Compatibility:
- Same config format works
- Same action classes work
- Just different execution backend

---

## Phase 3: Hold vs Tap Behavior

### Config Format:
```json
{
  "name": "Push to Talk",
  "action": "hotkey",
  "keys": ["v"],
  "mode": "hold"  // NEW: "tap" (default), "hold", "toggle"
}
```

### Implementation:
1. Track button state in action class
2. On note_on: start holding keys
3. On note_off: release keys
4. For toggle: alternate on each press

---

## Phase 4: K2 Layer Support

### Hardware Behavior:
- K2 has 3 layers (buttons 15 cycles through them)
- Each layer can repeat: top section, faders, bottom section
- Physical buttons send same MIDI notes on all layers

### Implementation Options:

**Option A: Software Layers (Recommended)**
- Track current layer in K2 Deck
- Layer button (note 15) cycles `_current_layer`
- Mapping engine checks layer before resolving action
- Config format:
```json
{
  "note_on": {
    "36": {
      "layer_1": { "action": "hotkey", "keys": ["f1"] },
      "layer_2": { "action": "hotkey", "keys": ["f2"] },
      "layer_3": { "action": "spotify_play_pause" }
    }
  }
}
```

**Option B: Per-Layer Configs**
- Separate JSON files: `layer1.json`, `layer2.json`, `layer3.json`
- Layer button triggers profile switch
- Simpler but more files to maintain

---

## Phase 5: Additional Features

### 5.1 Audio Device Switching
```python
# k2deck/actions/audio_switch.py
from pycaw.pycaw import AudioUtilities, IMMDeviceEnumerator
# Switch default playback/recording device
```

### 5.2 OBS WebSocket Integration
```python
# k2deck/actions/obs.py
import obsws_python
# Scene switching, source toggle, recording/streaming
```

### 5.3 Conditional Actions
```json
{
  "name": "Context Aware",
  "action": "conditional",
  "conditions": [
    { "app_focused": "Discord.exe", "then": { "keys": ["ctrl", "shift", "m"] } },
    { "app_focused": "Code.exe", "then": { "keys": ["ctrl", "shift", "p"] } },
    { "default": { "keys": ["f1"] } }
  ]
}
```

---

## Phase 6: Web UI for Configuration

### Tech Stack:
- FastAPI backend (lightweight)
- Vue.js or vanilla JS frontend
- Websocket for live preview
- JSON editor with validation

### Features:
- Visual button mapping
- Drag-and-drop action assignment
- Live MIDI monitor
- Profile management
- Layer configuration

---

## Migration Checklist

### Files to Create:
- [x] `docs/sendinput-migration-plan.md` (this file)
- [ ] `k2deck/core/keyboard.py` - SendInput implementation
- [ ] `k2deck/core/layers.py` - Layer state management
- [ ] `k2deck/actions/audio_switch.py` - Audio device switching
- [ ] `k2deck/actions/obs.py` - OBS WebSocket
- [ ] `k2deck/actions/conditional.py` - Conditional actions

### Files to Modify:
- [ ] `k2deck/actions/hotkey.py` - Use keyboard.py instead of pynput
- [ ] `k2deck/actions/multi.py` - Use keyboard.py
- [ ] `k2deck/actions/spotify.py` - Use keyboard.py for media keys
- [ ] `k2deck/core/mapping_engine.py` - Add layer support
- [ ] `k2deck/config/default.json` - Add hold/tap modes

### Files to Delete (after migration):
- pynput imports in hotkey.py (keep pynput in requirements for mouse_scroll)

---

## Implementation Order

1. **keyboard.py** - Core SendInput module (FIRST)
2. **hotkey.py migration** - Replace pynput for hotkeys
3. **multi.py migration** - Fix Discord+Wispr toggle
4. **Test thoroughly** - Verify all actions work
5. **Hold vs Tap** - New behavior modes
6. **Layer support** - Software layers
7. **Additional features** - Audio, OBS, Conditional
8. **Web UI** - Last, after core is stable

---

## Risk Mitigation

- Keep pynput as fallback initially
- Test each change with real K2 hardware
- Commit after each working milestone
- Don't delete old code until new code proven

[ADJUSTED: optimistic -> realistic]
Buffer added for debugging scan codes and timing issues.
