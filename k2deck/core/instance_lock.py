"""Single-instance guard for K2 Deck using a Windows named mutex.

Prevents duplicate instances when auto-start VBS and manual launch
both try to run K2 Deck simultaneously.
"""

import getpass
import logging

import win32api
import win32event
import winerror

logger = logging.getLogger(__name__)

_FAIL_OPEN = object()  # Sentinel: mutex failed but allow startup anyway

MUTEX_NAME = f"Global\\K2Deck-{getpass.getuser()}"


def acquire_instance_lock():
    """Acquire a single-instance mutex.

    Returns:
        Mutex handle on success, None if another instance is running,
        or _FAIL_OPEN sentinel if mutex creation fails (fail-open).
    """
    try:
        mutex = win32event.CreateMutex(None, True, MUTEX_NAME)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            win32api.CloseHandle(mutex)
            return None
        return mutex
    except Exception as exc:
        logger.warning("Failed to create instance mutex: %s", exc)
        return _FAIL_OPEN


def release_instance_lock(lock) -> None:
    """Release the instance mutex.

    No-op if lock is None or _FAIL_OPEN.
    """
    if lock is None or lock is _FAIL_OPEN:
        return
    try:
        win32api.CloseHandle(lock)
    except Exception as exc:
        logger.warning("Failed to release instance mutex: %s", exc)
