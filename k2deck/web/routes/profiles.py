"""Profiles API Routes - CRUD for configuration profiles.

Endpoints:
- GET    /api/profiles              - List all profiles
- POST   /api/profiles              - Create new profile
- POST   /api/profiles/import       - Import profile from JSON file
- GET    /api/profiles/{name}       - Get specific profile
- PUT    /api/profiles/{name}       - Update profile
- DELETE /api/profiles/{name}       - Delete profile
- GET    /api/profiles/{name}/export - Export profile as JSON file
- PUT    /api/profiles/{name}/activate - Activate profile
"""

import json
import logging
import shutil
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Config directory
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

# Active profile tracking (in-memory for now)
_active_profile = "default"
_profile_lock = threading.Lock()  # Thread-safe access to _active_profile


class ProfileCreate(BaseModel):
    """Request body for creating a profile."""

    name: str
    copy_from: str | None = None  # Optional profile to copy from


class ProfileUpdate(BaseModel):
    """Request body for updating a profile."""

    config: dict[str, Any]


class ProfileInfo(BaseModel):
    """Profile information."""

    name: str
    active: bool
    path: str


class ProfileList(BaseModel):
    """List of profiles."""

    profiles: list[ProfileInfo]
    active: str


def _get_profile_path(name: str) -> Path:
    """Get path to a profile's config file.

    Args:
        name: Profile name.

    Returns:
        Path to config file.
    """
    return CONFIG_DIR / f"{name}.json"


def _validate_profile_name(name: str) -> None:
    """Validate a profile name.

    Args:
        name: Profile name to validate.

    Raises:
        HTTPException: If name is invalid.
    """
    if not name:
        raise HTTPException(status_code=400, detail="Profile name cannot be empty")

    if not name.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="Profile name can only contain letters, numbers, underscores, and hyphens",
        )

    if len(name) > 50:
        raise HTTPException(
            status_code=400, detail="Profile name cannot exceed 50 characters"
        )


def _list_profiles() -> list[str]:
    """List all available profile names.

    Returns:
        List of profile names.
    """
    if not CONFIG_DIR.exists():
        return []

    return [
        f.stem
        for f in CONFIG_DIR.glob("*.json")
        if f.is_file() and not f.name.startswith(".")
    ]


@router.get("")
async def list_profiles() -> ProfileList:
    """List all available profiles.

    Returns:
        List of profiles with active indicator.
    """
    profile_names = _list_profiles()

    with _profile_lock:
        active = _active_profile

    profiles = [
        ProfileInfo(
            name=name,
            active=(name == active),
            path=str(_get_profile_path(name)),
        )
        for name in sorted(profile_names)
    ]

    return ProfileList(profiles=profiles, active=active)


@router.post("")
async def create_profile(body: ProfileCreate) -> dict[str, str]:
    """Create a new profile.

    Args:
        body: Profile creation data.

    Returns:
        Success message.

    Raises:
        HTTPException: If profile already exists or creation fails.
    """
    _validate_profile_name(body.name)

    path = _get_profile_path(body.name)
    if path.exists():
        raise HTTPException(
            status_code=409, detail=f"Profile '{body.name}' already exists"
        )

    # Ensure config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if body.copy_from:
        # Copy from existing profile
        source_path = _get_profile_path(body.copy_from)
        if not source_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Source profile '{body.copy_from}' not found"
            )
        shutil.copy(source_path, path)
        logger.info("Created profile '%s' from '%s'", body.name, body.copy_from)
    else:
        # Create empty profile with default structure
        default_config = {
            "name": body.name,
            "description": f"Profile: {body.name}",
            "mappings": {"note_on": {}, "cc": {}},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)
        logger.info("Created empty profile '%s'", body.name)

    return {"message": f"Profile '{body.name}' created"}


@router.post("/import")
async def import_profile(file: UploadFile) -> dict[str, str]:
    """Import a profile from an uploaded JSON file.

    Creates a new profile from the uploaded config. Profile name is extracted
    from the JSON content (profile_name or name field), or derived from the
    filename.

    Args:
        file: Uploaded JSON file.

    Returns:
        Success message with created profile name.

    Raises:
        HTTPException: If file is invalid, profile already exists, or import fails.
    """
    # Validate filename extension
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a .json file")

    # Validate content type (if provided by client)
    if file.content_type and file.content_type not in (
        "application/json",
        "text/json",
        "text/plain",
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type: {file.content_type}. Expected application/json",
        )

    try:
        content = await file.read()

        if len(content) > 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 1MB)")

        config = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Config must be a JSON object")

    # Validate config structure
    from k2deck.web.routes.config import _validate_config

    result = _validate_config(config)
    if not result.valid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Config validation failed", "errors": result.errors},
        )

    # Extract profile name: try config fields, then filename
    name = config.get("profile_name") or config.get("name")
    if not name and file.filename:
        stem = Path(file.filename).stem
        name = stem.removeprefix("k2deck-") if stem.startswith("k2deck-") else stem
    if not name:
        raise HTTPException(
            status_code=400, detail="Cannot determine profile name from file"
        )

    _validate_profile_name(name)

    path = _get_profile_path(name)
    if path.exists():
        raise HTTPException(
            status_code=409, detail=f"Profile '{name}' already exists"
        )

    # Save
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {e}")

    logger.info("Imported profile '%s' from file '%s'", name, file.filename)

    return {"message": f"Profile '{name}' imported", "profile": name}


@router.get("/{name}")
async def get_profile(name: str) -> dict[str, Any]:
    """Get a specific profile's configuration.

    Args:
        name: Profile name.

    Returns:
        Profile configuration.

    Raises:
        HTTPException: If profile not found.
    """
    path = _get_profile_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in profile: {e}")


@router.put("/{name}")
async def update_profile(name: str, body: ProfileUpdate) -> dict[str, str]:
    """Update a profile's configuration.

    Args:
        name: Profile name.
        body: New configuration.

    Returns:
        Success message.

    Raises:
        HTTPException: If profile not found or update fails.
    """
    path = _get_profile_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(body.config, f, indent=2)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {e}")

    logger.info("Updated profile '%s'", name)

    # Trigger hot-reload if this is the active profile
    with _profile_lock:
        is_active = name == _active_profile

    if is_active:
        # TODO: Notify mapping engine to reload
        pass

    return {"message": f"Profile '{name}' updated"}


@router.delete("/{name}")
async def delete_profile(name: str) -> dict[str, str]:
    """Delete a profile.

    Args:
        name: Profile name.

    Returns:
        Success message.

    Raises:
        HTTPException: If profile not found, is active, or is default.
    """
    if name == "default":
        raise HTTPException(status_code=400, detail="Cannot delete the default profile")

    with _profile_lock:
        is_active = name == _active_profile

    if is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the active profile. Switch to another profile first.",
        )

    path = _get_profile_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")

    try:
        path.unlink()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete profile: {e}")

    logger.info("Deleted profile '%s'", name)

    return {"message": f"Profile '{name}' deleted"}


@router.put("/{name}/activate")
async def activate_profile(name: str) -> dict[str, str]:
    """Activate a profile.

    Args:
        name: Profile name to activate.

    Returns:
        Success message with previous profile.

    Raises:
        HTTPException: If profile not found.
    """
    global _active_profile

    path = _get_profile_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")

    with _profile_lock:
        previous = _active_profile
        _active_profile = name

    # Broadcast profile change
    from k2deck.web.websocket.manager import broadcast_profile_change

    broadcast_profile_change(name, previous)

    # TODO: Reload mapping engine with new profile

    logger.info("Activated profile '%s' (was: '%s')", name, previous)

    return {"message": f"Profile '{name}' activated", "previous": previous}


@router.get("/{name}/export")
async def export_profile(name: str) -> FileResponse:
    """Export a profile as a downloadable JSON file.

    Args:
        name: Profile name to export.

    Returns:
        JSON file download.

    Raises:
        HTTPException: If profile not found.
    """
    path = _get_profile_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")

    return FileResponse(
        path=str(path),
        filename=f"k2deck-{name}.json",
        media_type="application/json",
    )


def get_active_profile() -> str:
    """Get the currently active profile name.

    Returns:
        Active profile name.
    """
    with _profile_lock:
        return _active_profile


def set_active_profile(name: str) -> None:
    """Set the active profile (for internal use).

    Args:
        name: Profile name.
    """
    global _active_profile
    with _profile_lock:
        _active_profile = name
