"""Windows auto-start management for K2 Deck.

Creates/removes a VBScript file in the Windows Startup folder
that launches K2 Deck with the correct venv and arguments.
The VBS approach avoids a visible console window on login.
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

STARTUP_DIR = Path(
    os.environ.get("APPDATA", ""),
    "Microsoft",
    "Windows",
    "Start Menu",
    "Programs",
    "Startup",
)
STARTUP_FILENAME = "K2Deck.vbs"


def _get_startup_path() -> Path:
    """Get the full path to the startup VBS script."""
    return STARTUP_DIR / STARTUP_FILENAME


def is_autostart_enabled() -> bool:
    """Check if K2 Deck auto-start is enabled.

    Returns:
        True if the startup script exists in the Windows Startup folder.
    """
    return _get_startup_path().exists()


def enable_autostart(
    config_path: Path | None = None,
    device_name: str | None = None,
    debug: bool = False,
) -> None:
    """Enable K2 Deck auto-start on Windows login.

    Creates a VBScript in the Startup folder that activates the venv
    and runs ``python -m k2deck`` with the given arguments.

    Args:
        config_path: Custom config path (None = use default).
        device_name: Custom MIDI device name (None = use default "XONE:K2").
        debug: Enable debug logging on startup.

    Raises:
        OSError: If the startup directory doesn't exist or isn't writable.
    """
    python_exe = sys.executable
    project_dir = Path(__file__).resolve().parent.parent.parent

    # Build command arguments
    args = [str(python_exe), "-m", "k2deck"]
    if config_path is not None:
        args.extend(["--config", str(config_path)])
    if device_name is not None and device_name != "XONE:K2":
        args.extend(["--device", device_name])
    if debug:
        args.append("--debug")

    # Build VBS content using chr(34) for robust quoting
    # WshShell.Run(command, windowStyle, waitOnReturn)
    # windowStyle 0 = hidden window
    q = "chr(34)"
    parts = ' & " " & '.join(f'{q} & "{a}" & {q}' for a in args)
    cmd_expr = parts

    vbs_lines = [
        'Set WshShell = CreateObject("WScript.Shell")',
        f'WshShell.CurrentDirectory = "{project_dir}"',
        f"WshShell.Run {cmd_expr}, 0, False",
    ]
    vbs_content = "\r\n".join(vbs_lines) + "\r\n"

    startup_path = _get_startup_path()
    startup_path.write_text(vbs_content, encoding="utf-8")
    logger.info("Auto-start enabled: %s", startup_path)


def disable_autostart() -> None:
    """Disable K2 Deck auto-start.

    Removes the VBScript from the Startup folder.
    No-op if the file doesn't exist.
    """
    startup_path = _get_startup_path()
    if startup_path.exists():
        startup_path.unlink()
        logger.info("Auto-start disabled: removed %s", startup_path)
    else:
        logger.info("Auto-start already disabled (no file found)")
