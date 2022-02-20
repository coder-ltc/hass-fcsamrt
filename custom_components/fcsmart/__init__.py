"""The fcsmart integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import hub
from .const import DOMAIN
from .core.fingercrystal_cloud import (
    FiotCloud,
    FcCloudException,
    FcCloudAccessDenied,
)

_LOGGER = logging.getLogger(__name__)

# List of platforms to support. There should be a matching .py file for each,
# eg <cover.py> and <sensor.py>
PLATFORMS: list[str] = ["lock", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hello World from a config entry."""

    fcc = await FiotCloud.from_token(hass, entry.data, login=False)
    dvs = []
    try:
        await fcc.async_login()
        await fcc.async_stored_auth(fcc.user_id, save=True)
        dvs = await fcc.async_get_devices(renew=True) or []
    except (FcCloudException, FcCloudAccessDenied) as exc:
        _LOGGER.error('Setup fingercrystal cloud for user: %s failed: %s', fcc.username, exc)

    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub.Hub(hass, entry.data, fcc, dvs)

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
