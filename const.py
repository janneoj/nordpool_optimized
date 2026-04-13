"""Constants for Nordpool Optimized."""

DOMAIN = "nordpool_optimized"

# Configuration keys
CONF_NORDPOOL_SENSOR = "nordpool_sensor"
CONF_CHEAP_SLOTS = "cheap_slots"
CONF_EVENING_RANGE_START = "evening_range_start"
CONF_EVENING_RANGE_END = "evening_range_end"
CONF_MORNING_RANGE_START = "morning_range_start"
CONF_MORNING_RANGE_END = "morning_range_end"

# Defaults matching the original Jinja2 template:
#   range(88, 95) from raw_today  = 22:00–23:30 (quarter-hour indices)
#   range(0, 27)  from raw_tomorrow = 00:00–06:30
DEFAULT_NAME = "Nordpool Cheap Hour"
DEFAULT_CHEAP_SLOTS = 24           # 6 hours worth of 15-minute slots
DEFAULT_EVENING_RANGE_START = 88   # inclusive start in raw_today (22:00)
DEFAULT_EVENING_RANGE_END = 95     # exclusive end  in raw_today  (up to 23:45)
DEFAULT_MORNING_RANGE_START = 0    # inclusive start in raw_tomorrow (00:00)
DEFAULT_MORNING_RANGE_END = 27     # exclusive end  in raw_tomorrow  (up to 06:30)
