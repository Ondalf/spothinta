"""Config flow for Spot-hinta.fi integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_REGION,
    CONF_RESOLUTION,
    CONF_PRICE_TYPE,
    SUPPORTED_REGIONS,
    PRICE_RESOLUTION,
    DEFAULT_PRICE_TYPE,
    PRICE_TYPE_OPTIONS_MAP
)

_LOGGER = logging.getLogger(__name__)

# Configs for webui
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        # Region select (dropdown)
        vol.Required(CONF_REGION, default=SUPPORTED_REGIONS[3]): vol.In(SUPPORTED_REGIONS),
        # Resolution select (15, 60) - used for API calls
        vol.Required(CONF_RESOLUTION, default=PRICE_RESOLUTION): vol.In( [15, 60] ),
        # Price type select (dropdown for VAT/NO_VAT)
        vol.Required(CONF_PRICE_TYPE, default=DEFAULT_PRICE_TYPE): vol.In(PRICE_TYPE_OPTIONS_MAP),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_REGION]}_{user_input[CONF_PRICE_TYPE]}"
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Spot Price ({user_input[CONF_REGION]}) - {user_input[CONF_PRICE_TYPE]}",
                data=user_input
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
