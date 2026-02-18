"""Audio Device Management - List and switch default audio devices.

Uses Windows COM interfaces to change the default audio endpoint.
Based on the undocumented IPolicyConfig interface.

References:
- https://github.com/tartakynov/audioswitch
- https://www.codemachine.com/articles/how_windows_sets_default_audio_device.html
"""

import logging
from ctypes import HRESULT, c_int
from typing import NamedTuple

import comtypes
from comtypes import COMMETHOD, GUID, IUnknown
from pycaw.pycaw import AudioUtilities, IMMDeviceEnumerator

logger = logging.getLogger(__name__)


# ERole enumeration - audio endpoint roles
class ERole:
    eConsole = 0  # Games, system sounds, etc.
    eMultimedia = 1  # Music, movies, etc.
    eCommunications = 2  # Voice chat, calls


# EDataFlow enumeration
class EDataFlow:
    eRender = 0  # Output devices (speakers, headphones)
    eCapture = 1  # Input devices (microphones)
    eAll = 2


class AudioDevice(NamedTuple):
    """Represents an audio device."""

    id: str
    name: str
    is_default: bool


# IPolicyConfig interface definition
# This is an undocumented Windows COM interface
class IPolicyConfig(IUnknown):
    """Undocumented COM interface for audio policy configuration."""

    _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
    _methods_ = [
        # We need to define placeholder methods for vtable ordering
        COMMETHOD(
            [], HRESULT, "GetMixFormat", (["in"], comtypes.c_wchar_p, "pwstrDeviceId")
        ),
        COMMETHOD([], HRESULT, "GetDeviceFormat"),
        COMMETHOD([], HRESULT, "ResetDeviceFormat"),
        COMMETHOD([], HRESULT, "SetDeviceFormat"),
        COMMETHOD([], HRESULT, "GetProcessingPeriod"),
        COMMETHOD([], HRESULT, "SetProcessingPeriod"),
        COMMETHOD([], HRESULT, "GetShareMode"),
        COMMETHOD([], HRESULT, "SetShareMode"),
        COMMETHOD([], HRESULT, "GetPropertyValue"),
        COMMETHOD([], HRESULT, "SetPropertyValue"),
        # The method we actually need
        COMMETHOD(
            [],
            HRESULT,
            "SetDefaultEndpoint",
            (["in"], comtypes.c_wchar_p, "pwstrDeviceId"),
            (["in"], c_int, "eRole"),
        ),
        COMMETHOD([], HRESULT, "SetEndpointVisibility"),
    ]


# CPolicyConfigClient class ID
CLSID_CPolicyConfigClient = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")


def get_audio_devices(device_type: str = "output") -> list[AudioDevice]:
    """Get list of audio devices.

    Args:
        device_type: "output" for speakers/headphones, "input" for microphones.

    Returns:
        List of AudioDevice objects.
    """
    devices = []

    try:
        # Get the device enumerator
        device_enumerator = comtypes.CoCreateInstance(
            GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}"),
            IMMDeviceEnumerator,
            comtypes.CLSCTX_INPROC_SERVER,
        )

        # Determine flow direction
        flow = EDataFlow.eRender if device_type == "output" else EDataFlow.eCapture

        # Get default device ID
        default_device = device_enumerator.GetDefaultAudioEndpoint(flow, ERole.eConsole)
        default_id = default_device.GetId() if default_device else None

        # Enumerate all devices
        collection = device_enumerator.EnumAudioEndpoints(
            flow, 1
        )  # DEVICE_STATE_ACTIVE = 1
        count = collection.GetCount()

        for i in range(count):
            device = collection.Item(i)
            device_id = device.GetId()

            # Get friendly name via pycaw
            try:
                name = AudioUtilities.GetDeviceNameFromId(device_id) or f"Device {i}"
            except Exception:
                name = f"Audio Device {i}"

            devices.append(
                AudioDevice(
                    id=device_id, name=name, is_default=(device_id == default_id)
                )
            )

    except Exception as e:
        logger.error("Failed to enumerate audio devices: %s", e)
        # Fallback to pycaw's simpler method
        try:
            for device in AudioUtilities.GetAllDevices():
                devices.append(
                    AudioDevice(
                        id=device.id,
                        name=device.FriendlyName or "Unknown",
                        is_default=False,
                    )
                )
        except Exception as e2:
            logger.error("Fallback enumeration also failed: %s", e2)

    return devices


def set_default_audio_device(device_id: str, role: int | None = None) -> bool:
    """Set the default audio device.

    Args:
        device_id: The device ID string.
        role: Specific role to set (eConsole, eMultimedia, eCommunications).
              If None, sets for all roles.

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Create PolicyConfig instance
        policy_config = comtypes.CoCreateInstance(
            CLSID_CPolicyConfigClient, IPolicyConfig, comtypes.CLSCTX_ALL
        )

        if role is not None:
            # Set for specific role
            policy_config.SetDefaultEndpoint(device_id, role)
        else:
            # Set for all roles
            for r in [ERole.eConsole, ERole.eMultimedia, ERole.eCommunications]:
                policy_config.SetDefaultEndpoint(device_id, r)

        logger.info("Set default audio device: %s", device_id[:50])
        return True

    except Exception as e:
        logger.error("Failed to set default audio device: %s", e)
        return False


def set_default_audio_device_by_name(name: str, device_type: str = "output") -> bool:
    """Set default audio device by friendly name (partial match).

    Args:
        name: Partial name to match (case-insensitive).
        device_type: "output" or "input".

    Returns:
        True if device found and set, False otherwise.
    """
    devices = get_audio_devices(device_type)
    name_lower = name.lower()

    for device in devices:
        if name_lower in device.name.lower():
            logger.info("Found device '%s' matching '%s'", device.name, name)
            return set_default_audio_device(device.id)

    logger.warning("No device found matching '%s'", name)
    return False


def cycle_audio_devices(
    device_names: list[str], device_type: str = "output"
) -> str | None:
    """Cycle through a list of audio devices.

    Args:
        device_names: List of device name patterns to cycle through.
        device_type: "output" or "input".

    Returns:
        Name of the device switched to, or None if failed.
    """
    if not device_names:
        logger.warning("No device names provided to cycle")
        return None

    devices = get_audio_devices(device_type)
    if not devices:
        logger.warning("No audio devices found")
        return None

    # Find current default device
    current_default = next((d for d in devices if d.is_default), None)
    current_name = current_default.name.lower() if current_default else ""

    # Find which device in our list is current
    current_index = -1
    for i, pattern in enumerate(device_names):
        if pattern.lower() in current_name:
            current_index = i
            break

    # Get next device in cycle
    next_index = (current_index + 1) % len(device_names)
    next_pattern = device_names[next_index]

    # Find and set the next device
    for device in devices:
        if next_pattern.lower() in device.name.lower():
            if set_default_audio_device(device.id):
                logger.info("Cycled to: %s", device.name)
                return device.name
            break

    logger.warning("Could not cycle to device matching '%s'", next_pattern)
    return None
