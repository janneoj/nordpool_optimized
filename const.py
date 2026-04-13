"""Constants for Nordpool Optimized."""

DOMAIN = "nordpool_optimized"

# Configuration keys
CONF_NORDPOOL_SENSOR = "nordpool_sensor"
CONF_CHEAP_HOURS = "cheap_hours"
CONF_CHEAP_MINUTES = "cheap_minutes"
CONF_CHEAP_DURATION = "cheap_duration"   # UI: "HH:MM" duration string
CONF_CONTINUOUS_CHEAP_HOURS = "continuous_cheap_hours"
CONF_WINDOW_START = "window_start"       # time in raw_today where the window begins
CONF_WINDOW_END = "window_end"           # time in raw_tomorrow where the window ends

DEFAULT_NAME = "Nordpool Cheap Hour"
DEFAULT_CHEAP_HOURS = 6             # fallback for YAML
DEFAULT_CHEAP_MINUTES = 0           # fallback for YAML
DEFAULT_CHEAP_DURATION = "06:00"    # UI default
DEFAULT_CONTINUOUS_CHEAP_HOURS = False
DEFAULT_WINDOW_START = "22:00"   # window begins at 22:00 in raw_today
DEFAULT_WINDOW_END = "06:30"     # window ends at 06:30 in raw_tomorrow
