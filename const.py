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


def format_entry_title(user_input: dict) -> str:
	"""Return the config entry title with the configured schedule recap."""
	name = user_input.get("name", DEFAULT_NAME)
	duration_value = user_input.get(CONF_CHEAP_DURATION, DEFAULT_CHEAP_DURATION)
	if isinstance(duration_value, dict):
		duration = f"{int(duration_value.get('hours', 0)):02d}:{int(duration_value.get('minutes', 0)):02d}"
	else:
		duration = str(duration_value)[:5]
	window_start = str(
		user_input.get(CONF_WINDOW_START, DEFAULT_WINDOW_START)
	)[:5]
	window_end = str(user_input.get(CONF_WINDOW_END, DEFAULT_WINDOW_END))[:5]
	continuity = (
		"continuous"
		if user_input.get(
			CONF_CONTINUOUS_CHEAP_HOURS, DEFAULT_CONTINUOUS_CHEAP_HOURS
		)
		else "separate"
	)
	return f"{name} ({window_start}-{window_end}, {duration}, {continuity})"
