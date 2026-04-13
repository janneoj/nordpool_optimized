"""Config flow for Nordpool Optimized."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NORDPOOL_SENSOR,
    CONF_CHEAP_SLOTS,
    CONF_EVENING_RANGE_START,
    CONF_EVENING_RANGE_END,
    CONF_MORNING_RANGE_START,
    CONF_MORNING_RANGE_END,
    DEFAULT_NAME,
    DEFAULT_CHEAP_SLOTS,
    DEFAULT_EVENING_RANGE_START,
    DEFAULT_EVENING_RANGE_END,
    DEFAULT_MORNING_RANGE_START,
    DEFAULT_MORNING_RANGE_END,
)

_STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NORDPOOL_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): selector.TextSelector(),
        vol.Optional(CONF_CHEAP_SLOTS, default=DEFAULT_CHEAP_SLOTS): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=96, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Optional(
            CONF_EVENING_RANGE_START, default=DEFAULT_EVENING_RANGE_START
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=95, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Optional(
            CONF_EVENING_RANGE_END, default=DEFAULT_EVENING_RANGE_END
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=96, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Optional(
            CONF_MORNING_RANGE_START, default=DEFAULT_MORNING_RANGE_START
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=95, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Optional(
            CONF_MORNING_RANGE_END, default=DEFAULT_MORNING_RANGE_END
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=96, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
    }
)


class NordpoolOptimizedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nordpool Optimized."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            sensor_id: str = user_input[CONF_NORDPOOL_SENSOR]
            if self.hass.states.get(sensor_id) is None:
                errors[CONF_NORDPOOL_SENSOR] = "sensor_not_found"
            else:
                await self.async_set_unique_id(sensor_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NordpoolOptimizedOptionsFlow:
        """Return the options flow handler."""
        return NordpoolOptimizedOptionsFlow(config_entry)


class NordpoolOptimizedOptionsFlow(config_entries.OptionsFlow):
    """Handle options (reconfigure) for Nordpool Optimized."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        current = self._config_entry.data

        if user_input is not None:
            sensor_id: str = user_input[CONF_NORDPOOL_SENSOR]
            if self.hass.states.get(sensor_id) is None:
                errors[CONF_NORDPOOL_SENSOR] = "sensor_not_found"
            else:
                return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NORDPOOL_SENSOR,
                    default=current.get(CONF_NORDPOOL_SENSOR, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_NAME,
                    default=current.get(CONF_NAME, DEFAULT_NAME),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_CHEAP_SLOTS,
                    default=current.get(CONF_CHEAP_SLOTS, DEFAULT_CHEAP_SLOTS),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=96, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_EVENING_RANGE_START,
                    default=current.get(CONF_EVENING_RANGE_START, DEFAULT_EVENING_RANGE_START),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=95, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_EVENING_RANGE_END,
                    default=current.get(CONF_EVENING_RANGE_END, DEFAULT_EVENING_RANGE_END),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=96, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_MORNING_RANGE_START,
                    default=current.get(CONF_MORNING_RANGE_START, DEFAULT_MORNING_RANGE_START),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=95, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_MORNING_RANGE_END,
                    default=current.get(CONF_MORNING_RANGE_END, DEFAULT_MORNING_RANGE_END),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=96, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
