"""Binary sensor platform for Nordpool Optimized cheapest hour detection.

Replicates the following Jinja2 template logic as a native component:

  When tomorrow_valid is True:
    - Collect quarter-hour slots from raw_today[evening_range_start:evening_range_end]
    - Collect quarter-hour slots from raw_tomorrow[morning_range_start:morning_range_end]
  When tomorrow_valid is False:
    - Collect quarter-hour slots from raw_today[morning_range_start:morning_range_end]

  Sort by price, keep cheapest <cheap_slots> slots.
  Return True if current quarter-hour slot (hour*4 + minute//15) is in cheapest set.

Example configuration.yaml:
  binary_sensor:
    - platform: nordpool_optimized
      nordpool_sensor: sensor.nordpool_kwh_fi_eur_3_10_0255
      name: "Cheap Electricity"
      cheap_slots: 24          # default: 24 (= 6 hours)
      evening_range_start: 88  # default: 88  (22:00, inclusive)
      evening_range_end: 95    # default: 95  (23:45, exclusive)
      morning_range_start: 0   # default: 0   (00:00, inclusive)
      morning_range_end: 27    # default: 27  (06:30, exclusive)
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    PLATFORM_SCHEMA,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import homeassistant.util.dt as dt_util

from .const import (
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

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NORDPOOL_SENSOR): cv.entity_id,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_CHEAP_SLOTS, default=DEFAULT_CHEAP_SLOTS): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=96)
        ),
        vol.Optional(
            CONF_EVENING_RANGE_START, default=DEFAULT_EVENING_RANGE_START
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=95)),
        vol.Optional(
            CONF_EVENING_RANGE_END, default=DEFAULT_EVENING_RANGE_END
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=96)),
        vol.Optional(
            CONF_MORNING_RANGE_START, default=DEFAULT_MORNING_RANGE_START
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=95)),
        vol.Optional(
            CONF_MORNING_RANGE_END, default=DEFAULT_MORNING_RANGE_END
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=96)),
    }
)


def _sensor_from_config(hass: HomeAssistant, config: dict) -> "NordpoolCheapHourSensor":
    """Build a NordpoolCheapHourSensor from a flat config dict."""
    return NordpoolCheapHourSensor(
        hass=hass,
        name=config.get(CONF_NAME, DEFAULT_NAME),
        nordpool_sensor_id=config[CONF_NORDPOOL_SENSOR],
        cheap_slots=int(config.get(CONF_CHEAP_SLOTS, DEFAULT_CHEAP_SLOTS)),
        evening_range=(
            int(config.get(CONF_EVENING_RANGE_START, DEFAULT_EVENING_RANGE_START)),
            int(config.get(CONF_EVENING_RANGE_END, DEFAULT_EVENING_RANGE_END)),
        ),
        morning_range=(
            int(config.get(CONF_MORNING_RANGE_START, DEFAULT_MORNING_RANGE_START)),
            int(config.get(CONF_MORNING_RANGE_END, DEFAULT_MORNING_RANGE_END)),
        ),
    )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Nordpool Optimized binary sensor from YAML configuration."""
    async_add_entities([_sensor_from_config(hass, config)], update_before_add=False)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nordpool Optimized binary sensor from a config entry."""
    # Combine data and options so that an options-flow update takes effect
    config = {**config_entry.data, **config_entry.options}
    async_add_entities([_sensor_from_config(hass, config)], update_before_add=False)


class NordpoolCheapHourSensor(BinarySensorEntity):
    """Binary sensor that is True when the current 15-minute slot is among
    the cheapest N slots in the configured overnight window."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        nordpool_sensor_id: str,
        cheap_slots: int,
        evening_range: tuple[int, int],
        morning_range: tuple[int, int],
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = (
            f"nordpool_optimized_{nordpool_sensor_id}"
        )
        self._nordpool_sensor_id = nordpool_sensor_id
        self._cheap_slots = cheap_slots
        self._evening_range = evening_range  # applied to raw_today when tomorrow_valid
        self._morning_range = morning_range  # applied to raw_tomorrow (or raw_today as fallback)
        self._attr_is_on: bool | None = None
        self._attr_extra_state_attributes: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        """Set up update callbacks and perform initial calculation."""
        # Update whenever the Nordpool sensor changes (new prices published)
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._nordpool_sensor_id],
                self._handle_nordpool_update,
            )
        )
        # Update every minute so the sensor switches at the correct quarter-hour boundary
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._handle_time_update,
                timedelta(minutes=1),
            )
        )
        # Calculate state immediately on startup
        self._recalculate()

    @callback
    def _handle_nordpool_update(self, event: Any) -> None:
        """Handle Nordpool sensor state changes."""
        self._recalculate()
        self.async_write_ha_state()

    @callback
    def _handle_time_update(self, now: Any) -> None:
        """Handle periodic time-based updates (every minute)."""
        self._recalculate()
        self.async_write_ha_state()

    @staticmethod
    def _extract_price(item: Any) -> float | None:
        """Extract a numeric price from a raw_today / raw_tomorrow entry."""
        if isinstance(item, dict):
            value = item.get("value")
        else:
            value = item
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _collect_slots(
        self, raw_data: list, index_range: tuple[int, int]
    ) -> list[tuple[int, float]]:
        """Return (slot_index, price) pairs for the given index range."""
        result: list[tuple[int, float]] = []
        for i in range(*index_range):
            if i >= len(raw_data):
                _LOGGER.debug(
                    "Slot index %d out of range (data length %d), skipping",
                    i,
                    len(raw_data),
                )
                continue
            price = self._extract_price(raw_data[i])
            if price is None:
                _LOGGER.debug("No valid price at slot index %d", i)
                continue
            result.append((i, price))
        return result

    def _recalculate(self) -> None:
        """Determine if the current quarter-hour slot is among the cheapest."""
        nordpool_state = self.hass.states.get(self._nordpool_sensor_id)
        if nordpool_state is None or nordpool_state.state in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            _LOGGER.debug(
                "Nordpool sensor %s is unavailable", self._nordpool_sensor_id
            )
            self._attr_is_on = None
            self._attr_extra_state_attributes = {
                "error": "Nordpool sensor unavailable"
            }
            return

        attrs = nordpool_state.attributes
        raw_today: list = attrs.get("raw_today") or []
        raw_tomorrow: list = attrs.get("raw_tomorrow") or []
        tomorrow_valid: bool = bool(attrs.get("tomorrow_valid", False))

        if tomorrow_valid:
            # Overnight window: this evening (raw_today) + tomorrow morning (raw_tomorrow)
            slot_prices = self._collect_slots(raw_today, self._evening_range)
            slot_prices += self._collect_slots(raw_tomorrow, self._morning_range)
        else:
            # Fallback: only today's early-morning window
            slot_prices = self._collect_slots(raw_today, self._morning_range)

        if not slot_prices:
            _LOGGER.warning(
                "No usable price data from %s", self._nordpool_sensor_id
            )
            self._attr_is_on = False
            self._attr_extra_state_attributes = {
                "tomorrow_valid": tomorrow_valid,
                "error": "No price data in configured window",
            }
            return

        # Sort ascending by price and keep the N cheapest slots
        sorted_by_price = sorted(slot_prices, key=lambda x: x[1])
        cheapest_count = min(self._cheap_slots, len(sorted_by_price))
        cheapest_slots: set[int] = {
            item[0] for item in sorted_by_price[:cheapest_count]
        }

        # Current quarter-hour slot index (0–95)
        now = dt_util.now()
        current_slot = now.hour * 4 + now.minute // 15

        self._attr_is_on = current_slot in cheapest_slots
        self._attr_extra_state_attributes = {
            "current_slot": current_slot,
            "tomorrow_valid": tomorrow_valid,
            "cheapest_slots": sorted(cheapest_slots),
            "cheapest_prices": [
                {"slot": slot, "price": round(price, 5)}
                for slot, price in sorted_by_price[:cheapest_count]
            ],
        }
