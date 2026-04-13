# ⚡ Nordpool Optimized

A Home Assistant custom component that creates a binary sensor indicating whether the current quarter-hour is among the cheapest electricity slots of the night/morning window. It replicates Jinja2 template logic as a native integration.

## How it works

The sensor looks at a configurable time window split into two parts:

- **Evening window** — slots taken from `raw_today` (e.g. 22:00–23:45)
- **Morning window** — slots taken from `raw_tomorrow` (e.g. 00:00–06:30)

When tomorrow's prices are available (`tomorrow_valid` is `True`), slots from both windows are combined, sorted by price, and the cheapest N slots are selected. When tomorrow's prices are not yet available, only today's morning window slots are used.

The sensor turns `on` when the current quarter-hour slot (`hour × 4 + minute // 15`) is in the cheapest set.

## Requirements

- [Nordpool integration](https://github.com/custom-components/nordpool) installed and providing a sensor with `raw_today` and `raw_tomorrow` attributes.

## Installation

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
| Number of cheap slots | How many quarter-hour slots are considered "cheap" | `24` (6 hours) |
| Evening window start | Slot index in `raw_today`, inclusive | `88` (22:00) |
| Evening window end | Slot index in `raw_today`, exclusive | `95` (23:45) |
| Morning window start | Slot index in `raw_tomorrow`, inclusive | `0` (00:00) |
| Morning window end | Slot index in `raw_tomorrow`, exclusive | `27` (06:30) |

### YAML

```yaml
nordpool_optimized:
  - platform: nordpool_optimized
    nordpool_sensor: sensor.nordpool_kwh_fi_eur_3_10_0255
    name: "Cheap Electricity"
    cheap_slots: 24
    evening_range_start: 88
    evening_range_end: 95
    morning_range_start: 0
    morning_range_end: 27
```

## Slot index reference

Slot indices represent quarter-hour periods. Each hour contains 4 slots.

| Slot | Time  |
|------|-------|
| 0    | 00:00 |
| 1    | 00:15 |
| 4    | 01:00 |
| 88   | 22:00 |
| 92   | 23:00 |
| 95   | 23:45 |

Formula: `slot = hour × 4 + minute // 15`
