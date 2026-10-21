# Smart EV Charging

Experimental HACS-compatible Home Assistant custom integration for entity-driven EV charging.

## v0.1.0 scope

This first build is deliberately **read-only**. It reads house, charger and vehicle entities and calculates a preview target current, but it does not call the charger.

It creates its own controls and diagnostic entities so Node-RED/helpers can eventually be removed.

### Created controls

- Charging mode
- Main fuse
- Load margin
- Maximum charging current
- Minimum SOC
- Cloud pause duration
- Cloud pause threshold
- Battery support threshold
- Priority charging

### Created diagnostic/state sensors

- Status
- Limiting reason
- Debug
- Target current
- Available current
- Detected phases
- Session state
- Last decision
- Last command result

## Charger control models prepared in config flow

- Single charge-control switch
- Separate Start/Stop buttons
- No remote Start/Stop
- Current limit via Number entity or unsupported

The selected control entities are stored now, but v0.1.0 intentionally does not use them.

## Install for a first HiBerry test

1. Copy `custom_components/smart_ev_charging` to `/config/custom_components/`.
2. Restart Home Assistant.
3. Go to **Settings -> Devices & services -> Add integration**.
4. Search for **Smart EV Charging**.
5. Name the site `HiBerry` and select the existing entities.
6. Keep the charging mode at **Off** first and inspect the generated sensors.
7. Change the mode to **Manual** only to test the calculated read-only target current. No command is sent to the charger.

## Important v0.1.0 assumptions

- Grid phase sensors are expected in watts.
- Grid net power: positive = import, negative = export.
- Charger power is currently expected in watts.
- Phase current sensors are expected in amperes.
- Battery power is only exposed in debug in v0.1.0; no solar/battery control logic is enabled yet.
- Load balancing uses 230 V nominal phase voltage.

## Next steps

After validating HiBerry sensor mapping and load-balancing calculations:

1. add options flow / reconfiguration,
2. add charger adapter writes with command confirmation,
3. port start/stop/session state machine,
4. port solar-only mode and cloud pause,
5. port cheap-time and automatic modes,
6. add command watchdog and full diagnostics.
