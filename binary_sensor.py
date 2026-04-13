"""Binary sensor platform for Nordpool Optimized cheapest hour detection.

Replicates the following Jinja2 template logic as a native component:

  When tomorrow_valid is True:
    - Collect quarter-hour slots from raw_today[window_start:end-of-day]
    - Collect quarter-hour slots from raw_tomorrow[start-of-day:window_end]
  When tomorrow_valid is False:
    - Collect quarter-hour slots from raw_today[window_start:end-of-day]

  Sort by price, keep cheapest <cheap_slots> slots.
  Return True if current quarter-hour slot (hour*4 + minute//15) is in cheapest set.

Example configuration.yaml:
  binary_sensor:
    - platform: nordpool_optimized
      nordpool_sensor: sensor.nordpool_kwh_fi_eur_3_10_0255
      name: "Cheap Electricity"
      cheap_hours: 6
      cheap_minutes: 0
      window_start: "22:00"
      window_end: "06:30"
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
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
)
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import homeassistant.util.dt as dt_util

from .const import (
    CONF_NORDPOOL_SENSOR,
    CONF_CHEAP_HOURS,
    CONF_CHEAP_MINUTES,
    CONF_CHEAP_DURATION,
    CONF_CONTINUOUS_CHEAP_HOURS,
    CONF_WINDOW_START,
    CONF_WINDOW_END,
    DEFAULT_NAME,
    DEFAULT_CHEAP_HOURS,
    DEFAULT_CHEAP_MINUTES,
    DEFAULT_CONTINUOUS_CHEAP_HOURS,
    DEFAULT_WINDOW_START,
    DEFAULT_WINDOW_END,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NORDPOOL_SENSOR): cv.entity_id,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_CHEAP_HOURS, default=DEFAULT_CHEAP_HOURS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=24)
        ),
        vol.Optional(CONF_CHEAP_MINUTES, default=DEFAULT_CHEAP_MINUTES): vol.All(
            vol.Coerce(int), vol.In([0, 15, 30, 45])
        ),
        vol.Optional(
            CONF_CONTINUOUS_CHEAP_HOURS,
            default=DEFAULT_CONTINUOUS_CHEAP_HOURS,
        ): cv.boolean,
        vol.Optional(CONF_WINDOW_START, default=DEFAULT_WINDOW_START): cv.string,
        vol.Optional(CONF_WINDOW_END, default=DEFAULT_WINDOW_END): cv.string,
    }
)


def _time_to_slot(time_val: str) -> int:
    """Convert 'HH:MM' or 'HH:MM:SS' to a quarter-hour slot index (0–95)."""
    parts = str(time_val).split(":")
    return int(parts[0]) * 4 + int(parts[1]) // 15


def _sensor_from_config(
    hass: HomeAssistant, config: dict, entry_id: str | None = None
) -> "NordpoolCheapHourSensor":
    """Build a NordpoolCheapHourSensor from a flat config dict."""
    # Single window: raw_today[window_start..end-of-day] + raw_tomorrow[00:00..window_end]
    window_start_slot = _time_to_slot(config.get(CONF_WINDOW_START, DEFAULT_WINDOW_START))
    window_end_slot = _time_to_slot(config.get(CONF_WINDOW_END, DEFAULT_WINDOW_END))
    evening_range = (window_start_slot, 96)   # window_start → 23:45 in raw_today
    morning_range = (0, window_end_slot + 1)  # 00:00 → window_end in raw_tomorrow
    # cheap_duration is "HH:MM" from the UI dropdown; fall back to
    # flat cheap_hours/cheap_minutes for YAML-based platform setup.
    duration = config.get(CONF_CHEAP_DURATION)
    if isinstance(duration, str) and ":" in duration:
        parts = duration.split(":")
        cheap_hours = int(parts[0])
        cheap_minutes = int(parts[1])
    elif isinstance(duration, dict):
        cheap_hours = int(duration.get("hours", DEFAULT_CHEAP_HOURS))
        cheap_minutes = int(duration.get("minutes", DEFAULT_CHEAP_MINUTES))
    else:
        cheap_hours = int(config.get(CONF_CHEAP_HOURS, DEFAULT_CHEAP_HOURS))
        cheap_minutes = int(config.get(CONF_CHEAP_MINUTES, DEFAULT_CHEAP_MINUTES))
    cheap_slots = cheap_hours * 4 + cheap_minutes // 15
    continuous_cheap_hours = bool(
        config.get(CONF_CONTINUOUS_CHEAP_HOURS, DEFAULT_CONTINUOUS_CHEAP_HOURS)
    )
    return NordpoolCheapHourSensor(
        hass=hass,
        name=config.get(CONF_NAME, DEFAULT_NAME),
        nordpool_sensor_id=config[CONF_NORDPOOL_SENSOR],
        cheap_slots=max(1, cheap_slots),
        continuous_cheap_hours=continuous_cheap_hours,
        evening_range=evening_range,
        morning_range=morning_range,
        entry_id=entry_id,
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
    async_add_entities(
        [_sensor_from_config(hass, config, entry_id=config_entry.entry_id)],
        update_before_add=False,
    )


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
        continuous_cheap_hours: bool,
        evening_range: tuple[int, int],
        morning_range: tuple[int, int],
        entry_id: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._attr_name = name
        # Use the config-entry ID (guaranteed unique per entry) when available,
        # falling back to the sensor ID for YAML-based platform setup.
        self._attr_unique_id = (
            f"nordpool_optimized_{entry_id}" if entry_id
            else f"nordpool_optimized_{nordpool_sensor_id}"
        )
        self._nordpool_sensor_id = nordpool_sensor_id
        self._cheap_slots = cheap_slots
        self._continuous_cheap_hours = continuous_cheap_hours
        self._evening_range = evening_range  # applied to raw_today when tomorrow_valid
        self._morning_range = morning_range  # applied to raw_tomorrow (or raw_today as fallback)
        self._attr_is_on: bool | None = None
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._planned_tomorrow_date: date | None = None
        self._planned_tomorrow_prices: list[tuple[int, float]] = []

    @property
    def icon(self) -> str:
        """Return an icon for the entity detail and device pages."""
        return "mdi:chart-box" if self._attr_is_on else "mdi:chart-box-outline"

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
        # Calculate state immediately on startup
        self._recalculate()
        self.async_write_ha_state()

    @callback
    def _handle_nordpool_update(self, event: Any) -> None:
        """Handle Nordpool sensor state changes."""
        self._recalculate(event.data.get("new_state"))
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

    @staticmethod
    def _slot_state_list(day_start: Any, active_slots: set[int]) -> list[dict[str, Any]]:
        """Return 96 timestamped 15-minute slots with 0/1 values for a day."""
        slot_states: list[dict[str, Any]] = []
        for slot in range(96):
            slot_start = day_start + timedelta(minutes=slot * 15)
            slot_end = slot_start + timedelta(minutes=15)
            slot_states.append(
                {
                    "start": slot_start.isoformat(),
                    "end": slot_end.isoformat(),
                    "value": 1 if slot in active_slots else 0,
                }
            )
        return slot_states

    @staticmethod
    def _pick_cheapest_contiguous_slots(
        slot_prices: list[tuple[str, int, float]],
        cheap_slots: int,
    ) -> list[tuple[str, int, float]]:
        """Pick the contiguous block with the lowest total price."""
        if not slot_prices:
            return []

        block_size = min(max(1, cheap_slots), len(slot_prices))
        if block_size == len(slot_prices):
            return slot_prices

        window_sum = sum(price for _day, _slot, price in slot_prices[:block_size])
        best_sum = window_sum
        best_start = 0

        for idx in range(block_size, len(slot_prices)):
            window_sum += slot_prices[idx][2] - slot_prices[idx - block_size][2]
            if window_sum < best_sum:
                best_sum = window_sum
                best_start = idx - block_size + 1

        return slot_prices[best_start : best_start + block_size]

    def _recalculate(self, nordpool_state: Any | None = None) -> None:
        """Determine if the current quarter-hour slot is among the cheapest."""
        if nordpool_state is None:
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
        now = dt_util.now()
        current_slot = now.hour * 4 + now.minute // 15
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        promoted_today_prices = (
            self._planned_tomorrow_prices
            if self._planned_tomorrow_date == today_start.date()
            else []
        )

        today_slot_prices: list[tuple[int, float]] = []
        tomorrow_slot_prices: list[tuple[int, float]] = []

        if current_slot < self._morning_range[1] and promoted_today_prices:
            # Morning after day rollover: promote yesterday's planned tomorrow
            # slots into today's plan.
            today_slot_prices = promoted_today_prices
            slot_prices = [("today", slot, price) for slot, price in today_slot_prices]
        elif current_slot < self._morning_range[1]:
            # Fallback for startup/restart without a cached rollover plan.
            today_slot_prices = self._collect_slots(raw_today, self._morning_range)
            slot_prices = [("today", slot, price) for slot, price in today_slot_prices]
        elif tomorrow_valid:
            # Evening: this evening (raw_today) + tomorrow morning (raw_tomorrow).
            today_slot_prices = self._collect_slots(raw_today, self._evening_range)
            tomorrow_slot_prices = self._collect_slots(raw_tomorrow, self._morning_range)
            slot_prices = [("today", slot, price) for slot, price in today_slot_prices]
            slot_prices += [
                ("tomorrow", slot, price) for slot, price in tomorrow_slot_prices
            ]
        else:
            # Evening fallback while tomorrow prices are still unavailable.
            today_slot_prices = self._collect_slots(raw_today, self._evening_range)
            slot_prices = [("today", slot, price) for slot, price in today_slot_prices]

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

        if self._continuous_cheap_hours:
            selected_slots = self._pick_cheapest_contiguous_slots(
                slot_prices,
                self._cheap_slots,
            )
        else:
            # Sort ascending by price and keep the N cheapest slots.
            sorted_by_price = sorted(slot_prices, key=lambda x: x[2])
            cheapest_count = min(self._cheap_slots, len(sorted_by_price))
            selected_slots = sorted_by_price[:cheapest_count]

        cheapest_today_slots: set[int] = {
            slot for day, slot, _price in selected_slots
            if day == "today"
        }
        cheapest_tomorrow_slots: set[int] = {
            slot for day, slot, _price in selected_slots
            if day == "tomorrow"
        }

        if current_slot >= self._morning_range[1] and tomorrow_valid:
            self._planned_tomorrow_date = tomorrow_start.date()
            self._planned_tomorrow_prices = [
                (slot, price)
                for day, slot, price in selected_slots
                if day == "tomorrow"
            ]
        elif self._planned_tomorrow_date is not None and self._planned_tomorrow_date < today_start.date():
            self._planned_tomorrow_date = None
            self._planned_tomorrow_prices = []

        self._attr_is_on = current_slot in cheapest_today_slots
        self._attr_extra_state_attributes = {
            "current_slot": current_slot,
            "tomorrow_valid": tomorrow_valid,
            "continuous_cheap_hours": self._continuous_cheap_hours,
            "cheapest_slots_today": sorted(cheapest_today_slots),
            "cheapest_slots_tomorrow": sorted(cheapest_tomorrow_slots),
            "slot_states_today": self._slot_state_list(
                today_start, cheapest_today_slots
            ),
            "slot_states_tomorrow": (
                self._slot_state_list(tomorrow_start, cheapest_tomorrow_slots)
                if tomorrow_valid
                else []
            ),
            "cheapest_prices": [
                {"day": day, "slot": slot, "price": round(price, 5)}
                for day, slot, price in selected_slots
            ],
        }
