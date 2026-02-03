"""MIDI Monitor - Raw passthrough for debugging.

Simple tool that prints all MIDI messages without any processing.
Useful for debugging and verifying MIDI communication.
"""

import sys
import time
from datetime import datetime

import mido


def main() -> None:
    """Run the MIDI monitor."""
    print("=" * 50)
    print("K2 Deck MIDI Monitor")
    print("=" * 50)
    print()

    # List devices
    inputs = mido.get_input_names()

    if not inputs:
        print("ERROR: No MIDI input devices found.")
        sys.exit(1)

    print("Available MIDI inputs:")
    for i, name in enumerate(inputs):
        print(f"  [{i}] {name}")

    # Find K2 or let user select
    k2_device = None
    for name in inputs:
        if "XONE" in name.upper() or "K2" in name.upper():
            k2_device = name
            break

    if k2_device:
        print(f"\nAuto-detected: {k2_device}")
    else:
        print("\nSelect device number: ", end="")
        try:
            idx = int(input().strip())
            k2_device = inputs[idx]
        except (ValueError, IndexError):
            print("Invalid selection.")
            sys.exit(1)

    # Open port
    print(f"\nOpening: {k2_device}")
    try:
        port = mido.open_input(k2_device)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("Monitoring MIDI messages. Press Ctrl+C to quit.")
    print("=" * 50 + "\n")

    try:
        while True:
            for msg in port.iter_pending():
                ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{ts}] {msg}")
            time.sleep(0.001)
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        port.close()
        print("Port closed.")


if __name__ == "__main__":
    main()
