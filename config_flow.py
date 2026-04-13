"""Config flow for Nordpool Optimized."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NORDPOOL_SENSOR,
    CONF_CHEAP_DURATION,
    CONF_CONTINUOUS_CHEAP_HOURS,
    CONF_WINDOW_START,
    CONF_WINDOW_END,
    DEFAULT_NAME,
    DEFAULT_CHEAP_DURATION,
    DEFAULT_CONTINUOUS_CHEAP_HOURS,
    DEFAULT_WINDOW_START,
    DEFAULT_WINDOW_END,
)

def _quarter_hour_times() -> list[str]:
    """Return all 96 quarter-hour time strings (HH:MM) for 00:00..23:45."""
    return [
        f"{h:02d}:{m:02d}"
        for h in range(24)
        for m in (0, 15, 30, 45)
    ]


def _duration_options() -> list[str]:
    """Return quarter-hour duration strings from 00:15 to 12:00."""
    options = []
    for h in range(13):
        for m in (0, 15, 30, 45):
            if h == 0 and m == 0:
                continue
            if h == 12 and m > 0:
                break
            options.append(f"{h:02d}:{m:02d}")
    return options


def _normalize_time(value: str) -> str:
    """Normalise HH:MM:SS or HH:MM to HH:MM so it matches dropdown options."""
    return str(value)[:5]


def _normalize_duration(value) -> str:
    """Normalise DurationSelector dict or HH:MM string to HH:MM."""
    if isinstance(value, dict):
        h = int(value.get("hours", 0))
        m = int(value.get("minutes", 0))
        return f"{h:02d}:{m:02d}"
    return _normalize_time(str(value))


_QUARTER_HOUR_TIMES = _quarter_hour_times()
_DURATION_OPTIONS = _duration_options()

_STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NORDPOOL_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): selector.TextSelector(),
        vol.Optional(
            CONF_CHEAP_DURATION, default=DEFAULT_CHEAP_DURATION
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=_DURATION_OPTIONS,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(
            CONF_CONTINUOUS_CHEAP_HOURS,
            default=DEFAULT_CONTINUOUS_CHEAP_HOURS,
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_WINDOW_START, default=DEFAULT_WINDOW_START
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=_QUARTER_HOUR_TIMES,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(
            CONF_WINDOW_END, default=DEFAULT_WINDOW_END
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=_QUARTER_HOUR_TIMES,
                mode=selector.SelectSelectorMode.DROPDOWN,
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
        current = {**self._config_entry.data, **self._config_entry.options}

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
                    CONF_CHEAP_DURATION,
                    default=_normalize_duration(current.get(CONF_CHEAP_DURATION, DEFAULT_CHEAP_DURATION)),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_DURATION_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_CONTINUOUS_CHEAP_HOURS,
                    default=bool(
                        current.get(
                            CONF_CONTINUOUS_CHEAP_HOURS,
                            DEFAULT_CONTINUOUS_CHEAP_HOURS,
                        )
                    ),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_WINDOW_START,
                    default=_normalize_time(current.get(CONF_WINDOW_START, DEFAULT_WINDOW_START)),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_QUARTER_HOUR_TIMES,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_WINDOW_END,
                    default=_normalize_time(current.get(CONF_WINDOW_END, DEFAULT_WINDOW_END)),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_QUARTER_HOUR_TIMES,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
