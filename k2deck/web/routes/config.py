"""Config API Routes - CRUD for active configuration.

Endpoints:
- GET  /api/config           - Get active profile config
- PUT  /api/config           - Update config (hot-reload)
- POST /api/config/validate  - Validate config without saving
- GET  /api/config/export    - Export config as JSON file
- POST /api/config/import    - Import config from JSON
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Config directory
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class ConfigUpdate(BaseModel):
    """Request body for config update."""

    config: dict[str, Any]


class ValidationResult(BaseModel):
    """Response for config validation."""

    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


def _get_active_profile() -> str:
    """Get the name of the active profile.

    Returns:
        Active profile name (default: "default").
    """
    # TODO: Get from profile manager when implemented
    return "default"


def _get_config_path(profile: str) -> Path:
    """Get path to a profile's config file.

    Args:
        profile: Profile name.

    Returns:
        Path to config file.
    """
    return CONFIG_DIR / f"{profile}.json"


def _load_config(profile: str) -> dict[str, Any]:
    """Load config from disk.

    Args:
        profile: Profile name.

    Returns:
        Config dict.

    Raises:
        HTTPException: If config not found or invalid.
    """
    path = _get_config_path(profile)

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in config: {e}")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {e}")


def _save_config(profile: str, config: dict[str, Any]) -> None:
    """Save config to disk.

    Args:
        profile: Profile name.
        config: Config dict to save.

    Raises:
        HTTPException: If save fails.
    """
    path = _get_config_path(profile)

    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


def _validate_config(config: dict[str, Any]) -> ValidationResult:
    """Validate a config dict.

    Args:
        config: Config to validate.

    Returns:
        ValidationResult with errors/warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Basic structure checks
    if not isinstance(config, dict):
        errors.append("Config must be a JSON object")
        return ValidationResult(valid=False, errors=errors)

    # Check for required sections
    if "mappings" not in config:
        warnings.append("No 'mappings' section found")

    # Validate mappings
    mappings = config.get("mappings", {})
    if not isinstance(mappings, dict):
        errors.append("'mappings' must be an object")
    else:
        # Check note_on and cc sections
        note_on = mappings.get("note_on", {})
        cc = mappings.get("cc", {})

        if not isinstance(note_on, dict):
            errors.append("'mappings.note_on' must be an object")
        if not isinstance(cc, dict):
            errors.append("'mappings.cc' must be an object")

        # Validate individual mappings
        for section_name, section in [("note_on", note_on), ("cc", cc)]:
            if isinstance(section, dict):
                for key, mapping in section.items():
                    if not isinstance(mapping, dict):
                        errors.append(f"Mapping '{section_name}.{key}' must be an object")
                    elif "action" not in mapping and not any(
                        k.startswith("layer_") for k in mapping.keys()
                    ):
                        warnings.append(
                            f"Mapping '{section_name}.{key}' has no 'action' or layer-specific actions"
                        )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


@router.get("")
async def get_config() -> dict[str, Any]:
    """Get the active profile's configuration.

    Returns:
        Complete config dict for active profile.
    """
    profile = _get_active_profile()
    return _load_config(profile)


@router.put("")
async def update_config(body: ConfigUpdate) -> dict[str, str]:
    """Update the active profile's configuration.

    Validates config before saving. Triggers hot-reload.

    Args:
        body: New config data.

    Returns:
        Success message.

    Raises:
        HTTPException: If validation fails or save fails.
    """
    # Validate first
    result = _validate_config(body.config)
    if not result.valid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Config validation failed", "errors": result.errors},
        )

    # Save
    profile = _get_active_profile()
    _save_config(profile, body.config)

    # Trigger hot-reload
    # TODO: Notify mapping engine to reload
    logger.info("Config updated for profile '%s'", profile)

    return {"message": f"Config updated for profile '{profile}'"}


@router.post("/validate")
async def validate_config(body: ConfigUpdate) -> ValidationResult:
    """Validate a config without saving.

    Args:
        body: Config to validate.

    Returns:
        Validation result with errors/warnings.
    """
    return _validate_config(body.config)


@router.get("/export")
async def export_config() -> FileResponse:
    """Export active config as downloadable JSON file.

    Returns:
        JSON file download.
    """
    profile = _get_active_profile()
    path = _get_config_path(profile)

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")

    return FileResponse(
        path=str(path),
        filename=f"k2deck-{profile}.json",
        media_type="application/json",
    )


@router.post("/import")
async def import_config(file: UploadFile) -> dict[str, str]:
    """Import config from uploaded JSON file.

    Args:
        file: Uploaded JSON file.

    Returns:
        Success message.

    Raises:
        HTTPException: If file is invalid or import fails.
    """
    # Validate filename extension
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a .json file")

    # Validate content type (if provided by client)
    if file.content_type and file.content_type not in (
        "application/json",
        "text/json",
        "text/plain",  # Some browsers may send this
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type: {file.content_type}. Expected application/json",
        )

    try:
        content = await file.read()

        # Reject excessively large files (max 1MB for config)
        if len(content) > 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 1MB)")

        config = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    # Validate
    result = _validate_config(config)
    if not result.valid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Config validation failed", "errors": result.errors},
        )

    # Save
    profile = _get_active_profile()
    _save_config(profile, config)

    logger.info("Config imported for profile '%s'", profile)

    return {"message": f"Config imported to profile '{profile}'"}
