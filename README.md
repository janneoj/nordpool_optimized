# ⚡ Nordpool Optimized

A Home Assistant custom component that creates a binary sensor indicating whether the current quarter-hour is among the cheapest electricity slots of the night/morning window.

## How it works

The sensor looks at a single overnight window that spans two data sources:

- **Window start** — a time in the current day's prices (`raw_today`), e.g. 22:00
- **Window end** — a time in the next day's prices (`raw_tomorrow`), e.g. 06:30

When tomorrow's prices are available (`tomorrow_valid` is `True`), slots from `window_start` to end-of-day and from midnight to `window_end` are combined, sorted by price, and the cheapest N slots are selected. When tomorrow's prices are not yet available, only today's slots from `window_start` to end-of-day are used.

The sensor turns `on` when the current quarter-hour slot (`hour × 4 + minute // 15`) is in the cheapest set.

## Requirements

- [Nordpool integration](https://github.com/custom-components/nordpool) installed and providing a sensor with `raw_today` and `raw_tomorrow` attributes.

## Installation with HACS

1. Open **HACS** in Home Assistant.
2. Select **Integrations** and open the three-dot menu in the top-right corner.
3. Select **Custom repositories**.
4. Add `https://github.com/janneoj/nordpool_optimized` as a repository with the category **Integration**.
5. Search for **Nordpool Optimized**, open it, and select **Download**.
6. Restart Home Assistant.

After the restart, go to **Settings → Devices & services → Add integration**, search for **Nordpool Optimized**, and complete the configuration flow.

## Manual installation

Copy the `nordpool_optimized` folder into your `custom_components` directory:

```
config/
└── custom_components/
    └── nordpool_optimized/
        ├── __init__.py
        ├── binary_sensor.py
        ├── config_flow.py
        ├── const.py
        ├── manifest.json
        ├── strings.json
        └── translations/
            └── en.json
```

Restart Home Assistant.

## Configuration

### UI (Config Flow)

Go to **Settings → Devices & Services → Add Integration** and search for **Nordpool Optimized**. Fill in the form:

| Field | Description | Default |
|-------|-------------|---------|
| Nordpool sensor | Entity ID of the Nordpool sensor | *(required)* |
| Sensor name | Friendly name for the binary sensor | `Nordpool Cheap Hour` |
| Cheap window duration | Length of the cheap window (hours + minutes) | `6 h 0 min` |
| Find continuous cheap hours | Select one cheapest uninterrupted block for the whole duration instead of the cheapest individual slots | `off` |
| Window start | Start time in current day's prices | `22:00` |
| Window end | End time in next day's prices | `06:30` |

### Continuous cheap hours

When **Find continuous cheap hours** is enabled, the sensor compares every possible uninterrupted block of the configured duration and selects the block with the lowest combined price. Prices are evaluated in 15-minute slots, so a duration of `6 h 0 min` selects 24 consecutive slots. The selected block can cross midnight between `window_start` and `window_end`.

When the option is disabled, the sensor instead selects the cheapest individual 15-minute slots. These slots do not need to be next to each other.

### YAML

```yaml
nordpool_optimized:
  - platform: nordpool_optimized
    nordpool_sensor: sensor.nordpool_kwh_fi_eur_3_10_0255
    name: "Cheap Electricity"
    cheap_hours: 6
    cheap_minutes: 0  # 0, 15, 30 or 45
    continuous_cheap_hours: false
    window_start: "22:00"
    window_end: "06:30"
```
