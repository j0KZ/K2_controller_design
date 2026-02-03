"""MIDI Learn Tool - Discover K2 controls and test LEDs.

Usage:
    python -m k2deck.tools.midi_learn
    python tools/midi_learn.py
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import mido

# LED color offsets (note number offsets, NOT velocity)
COLOR_OFFSETS = {"red": 0, "amber": 36, "green": 72}


def list_midi_devices() -> tuple[list[str], list[str]]:
    """List available MIDI input and output devices."""
    inputs = mido.get_input_names()
    outputs = mido.get_output_names()
    return inputs, outputs


def find_k2_device(devices: list[str]) -> str | None:
    """Auto-detect K2 device by name."""
    for device in devices:
        if "XONE" in device.upper() or "K2" in device.upper():
            return device
    return None


def format_timestamp() -> str:
    """Format current time for logging."""
    return datetime.now().strftime("%H:%M:%S")


def format_midi_message(msg: mido.Message) -> str:
    """Format MIDI message for display."""
    ts = format_timestamp()
    channel = msg.channel + 1 if hasattr(msg, "channel") else "—"

    if msg.type == "note_on":
        return f"[{ts}] NOTE ON  | ch:{channel:>2} | note:{msg.note:>3} | vel:{msg.velocity:>3}"
    elif msg.type == "note_off":
        return f"[{ts}] NOTE OFF | ch:{channel:>2} | note:{msg.note:>3} | vel:{msg.velocity:>3}"
    elif msg.type == "control_change":
        # Detect relative vs absolute CC
        val = msg.value
        if val == 1:
            direction = "  (CW)"
        elif val == 127:
            direction = "  (CCW)"
        elif 2 <= val <= 63:
            direction = f"  (CW x{val})"
        elif 65 <= val <= 126:
            direction = f"  (CCW x{128-val})"
        else:
            direction = ""
        return f"[{ts}] CC      | ch:{channel:>2} | cc:{msg.control:>3}  | val:{val:>3}{direction}"
    else:
        return f"[{ts}] {msg.type.upper():8} | {msg}"


def test_led(output_port: mido.ports.BaseOutput, base_note: int, channel: int) -> None:
    """Test LED colors on a button."""
    print(f"\n[LED TEST] Testing button at note {base_note}")

    colors = [("red", 0), ("amber", 36), ("green", 72)]
    for color_name, offset in colors:
        note = base_note + offset
        print(f"  Sending Note On {note} ({color_name})...", end=" ", flush=True)
        msg = mido.Message("note_on", channel=channel, note=note, velocity=127)
        output_port.send(msg)
        response = input("LED lit? [y/n/q]: ").strip().lower()
        if response == "q":
            return
        # Turn off
        off_msg = mido.Message("note_off", channel=channel, note=note, velocity=0)
        output_port.send(off_msg)
        time.sleep(0.1)

    print("  LED test complete for this button.")


def all_leds_off(output_port: mido.ports.BaseOutput, channel: int) -> None:
    """Turn off all LEDs (notes 0-127 for all color offsets)."""
    print("Turning off all LEDs...")
    for base in range(0, 48):  # Typical button range
        for offset in [0, 36, 72]:
            note = base + offset
            if 0 <= note <= 127:
                msg = mido.Message("note_off", channel=channel, note=note, velocity=0)
                output_port.send(msg)
    print("Done.")


def save_controls(controls: list[dict], filepath: Path) -> None:
    """Save discovered controls to JSON."""
    data = {
        "discovered_at": datetime.now().isoformat(),
        "controls": controls,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(controls)} controls to {filepath}")


def main() -> None:
    """Main entry point for MIDI learn tool."""
    print("=" * 50)
    print("K2 Deck MIDI Learn Tool")
    print("=" * 50)
    print()

    # List devices
    print("Scanning MIDI devices...")
    inputs, outputs = list_midi_devices()

    if not inputs:
        print("ERROR: No MIDI input devices found.")
        print("Check that your K2 is connected via USB.")
        sys.exit(1)

    print(f"\nInput devices ({len(inputs)}):")
    for i, name in enumerate(inputs):
        print(f"  [{i}] {name}")

    print(f"\nOutput devices ({len(outputs)}):")
    for i, name in enumerate(outputs):
        print(f"  [{i}] {name}")

    # Auto-detect K2
    input_device = find_k2_device(inputs)
    output_device = find_k2_device(outputs)

    if input_device:
        print(f"\n✓ Auto-detected input: {input_device}")
    else:
        print("\nK2 not auto-detected. Select input device number: ", end="")
        try:
            idx = int(input().strip())
            input_device = inputs[idx]
        except (ValueError, IndexError):
            print("Invalid selection.")
            sys.exit(1)

    if output_device:
        print(f"✓ Auto-detected output: {output_device}")
    else:
        print("K2 output not auto-detected. Select output device number: ", end="")
        try:
            idx = int(input().strip())
            output_device = outputs[idx]
        except (ValueError, IndexError):
            print("Invalid selection.")
            sys.exit(1)

    # Open ports
    print(f"\nOpening input: {input_device}")
    try:
        input_port = mido.open_input(input_device)
    except Exception as e:
        print(f"ERROR: Could not open input port: {e}")
        print("Another application might be using this device.")
        sys.exit(1)

    print(f"Opening output: {output_device}")
    try:
        output_port = mido.open_output(output_device)
    except Exception as e:
        print(f"ERROR: Could not open output port: {e}")
        input_port.close()
        sys.exit(1)

    # Learn mode
    print("\n" + "=" * 50)
    print("[LEARN MODE] Press any control on the K2.")
    print("Commands: [L]=LED test, [A]=All LEDs off, [S]=Save, [Q]=Quit")
    print("=" * 50 + "\n")

    discovered: list[dict] = []
    last_note: int | None = None
    last_channel: int = 15  # Default channel (0-indexed)

    try:
        while True:
            # Check for MIDI messages (non-blocking with timeout)
            msg = input_port.receive(block=False)
            if msg:
                print(format_midi_message(msg))

                # Track discovered controls
                if msg.type == "note_on" and msg.velocity > 0:
                    last_note = msg.note
                    last_channel = msg.channel
                    control = {
                        "type": "note_on",
                        "channel": msg.channel + 1,
                        "note": msg.note,
                        "label": "unknown",
                    }
                    if control not in discovered:
                        discovered.append(control)

                elif msg.type == "control_change":
                    last_channel = msg.channel
                    cc_type = "cc_relative" if msg.value in (1, 127) or (2 <= msg.value <= 63) or (65 <= msg.value <= 126) else "cc_absolute"
                    control = {
                        "type": cc_type,
                        "channel": msg.channel + 1,
                        "cc": msg.control,
                        "label": "unknown",
                    }
                    # Avoid duplicates
                    if not any(c.get("cc") == msg.control and c.get("type") == cc_type for c in discovered):
                        discovered.append(control)

            # Check for keyboard commands
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch().decode("utf-8", errors="ignore").upper()

                if key == "Q":
                    print("\nQuitting...")
                    break

                elif key == "L":
                    if last_note is not None:
                        test_led(output_port, last_note, last_channel)
                    else:
                        print("Press a button first to test its LED.")

                elif key == "A":
                    all_leds_off(output_port, last_channel)

                elif key == "S":
                    filepath = Path("k2_discovered_controls.json")
                    save_controls(discovered, filepath)

            time.sleep(0.01)  # Small delay to prevent busy loop

    except KeyboardInterrupt:
        print("\n\nInterrupted.")

    finally:
        # Ask to save on exit
        if discovered:
            print(f"\nDiscovered {len(discovered)} controls.")
            save_choice = input("Save to k2_discovered_controls.json? [y/n]: ").strip().lower()
            if save_choice == "y":
                save_controls(discovered, Path("k2_discovered_controls.json"))

        input_port.close()
        output_port.close()
        print("Ports closed. Goodbye!")


if __name__ == "__main__":
    main()
