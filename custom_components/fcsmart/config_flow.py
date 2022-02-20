"""Config flow for Hello World integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant

from .const import *  # pylint:disable=unused-import

from .const import CLOUD_SERVERS

_LOGGER = logging.getLogger(__name__)

from .core.fingercrystal_cloud import (
    FiotCloud,
    FcCloudException,
    FcCloudAccessDenied,
)


async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # Validate the data can be used to set up a connection.

    # This is a simple example to show an error in the UI for a short hostname
    # The exceptions are defined at the end of this file, and are used in the
    # `async_step_user` method below.
    errors = {}
    if len(data["username"]) < 3:
        raise InvalidHost

    fcc = await FiotCloud.from_token(hass, data, login=False)
    try:
        await fcc.async_login()
        await fcc.async_stored_auth(fcc.user_id, save=True)
    except (FcCloudException, FcCloudAccessDenied) as exc:
        errors['base'] = 'cannot_login'
        _LOGGER.error('Setup fingercrystal cloud for user: %s failed: %s', fcc.username, exc)
    return data


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hello World."""

    VERSION = 1
    # Pick one of the available connection classes in homeassistant/config_entries.py
    # This tells HA if it should be asking for updates, or it'll be notified of updates
    # automatically. This example uses PUSH, as the dummy hub will notify HA of
    # changes.
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # This goes through the steps to take the user through the setup process.
        # Using this it is possible to update the UI and prompt for additional
        # information. This example provides a single form (built from `DATA_SCHEMA`),
        # and when that has some validated input, it calls `async_create_entry` to
        # actually create the HA config entry. Note the "title" value is returned by
        # `validate_input` above.
        errors = {}
        if user_input is None:
            user_input = {}
        else:
            try:
                data = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=f"FcSmart: {user_input['username']}", data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidHost:
                # The error string is set here, and should be translated.
                # This example does not currently cover translations, see the
                # comments on `DATA_SCHEMA` for further details.
                # Set the error on the `host` field, not the entire form.
                errors["host"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME, default=user_input.get(CONF_USERNAME, vol.UNDEFINED)): str,
                vol.Required(CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, vol.UNDEFINED)): str,
                vol.Required(CONF_SERVER_COUNTRY, default=user_input.get(CONF_SERVER_COUNTRY, 'cn')):
                    vol.In(CLOUD_SERVERS),
            }),
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""
