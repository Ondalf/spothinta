# [Spot-hinta](https://spot-hinta.fi) API integration for Home Assistant

NOTE: This is partial AI slop.

#### This integration provides a sensor with a `current_price` value. The sensor updates its state every 15 minutes, regardless of the internal data resolution.

---

#### First of all, big thanks to the API endpoint provider: https://spot-hinta.fi/

### Goal(s) I had in mind, when creating this
- **Just do the one job properly:** provide current price as a sensor
- **Lightweight:** keep Home Assistant happy with small metrics to store daily with 15min datapoints
- **Keep remote service happy:** ideally just a single call daily per sensor towards API
- Make this a direct replacement for [custom_components/nordpool](https://github.com/custom-components/nordpool) to provide current_price via another service
- Learn python AI assisted: for a oldschool non-AI C/C++ coder, this was an awful experience. Won't do AI or python again.

### What works
- Adding the integration as "hub" to Home Assistant
- Adding sensors to the "hub" via WebUI
  - Sensors get named as "Spot Price {region} [VAT,NO_VAT]"
  - Their entity IDs follow similar naming, ie. `sensor.spot_price_se4_vat`
- Calls to local cache, unless
  - Cache is empty (on startup)
  - Tomorrows values are likely available (14:30- finnish time)
- Units are hardcoded into EUR/kWh as per API output
- To hopefully avoid lots of conversion issues with datetime, internal timestamps are in UTC
  - There are timezone conversions when parsing and handling the API data
- This integration should be in HACS compatible format, but unable to test

### Example state data it provides
```YAML
state_class: measurement
region: FI
current_price: 0.00365
min_price: 0.00251
max_price: 0.07656
raw_data_entries: 96
unit_of_measurement: EUR/kWh
device_class: monetary
icon: mdi:flash
friendly_name: Spot Price FI VAT
```

### Things that are likely broken
- There are some oddities with min/max calculation
  - Values are calculated from whole dataset
  - They are using values from VAT keyed data only
- Unsure if cache is being wiped on updates
  - May need to figure out a way to wipe old values
  - Tomorrow price update confirmed the cached values doubled
- If plugin fails to load due DNS or similar issue, it will throw and not load
  - Likely will also fail if ethernet cable is unplugged during API update

### Things that are generally issues or TODO, but not big deals and not breaking/blocking
- Data race with cache on launch
  - Does separate calls towards API, if used VAT + NO_VAT at same region
    - Ideally it should do just one, since dataset stores both VAT/NO_VAT values with region as key
  - Likely will happen when prices update from API as well
- I cannot test or confirm, if this works, when the timezone for the machine is actually set to non-UTC
  - Open up issue/PR if its an issue!
- There are no checks, if tomorrows data exist properly
  - No fallbacks either to force data fetch. It will just update last value until next 14:30-
  - Needs also button or some sort of service to request force update data
    - Function supports calling with force
- The timezone conversions...

There are logger entries to see the updates. Also, tried to somewhat explain the parts of the code, what gets done where and how.
```yaml
logger:
  logs:
    custom_components.spothinta: debug
    custom_components.spothinta.sensor: debug
    custom_components.spothinta.spothinta_api: debug
```

If you use custom install of Home Assistant (Core), copy custom_components/spothinta to your current install, ie.
```bash
cd
git clone https://github.com/Ondalf/spothinta
mkdir -p ~/.homeassistant/custom_components/spothinta
cp spothinta/custom_components/spothinta/* ~/.homeassistant/custom_components/spothinta/
service homeassistant stop && service homeassistant start
```
Tested and written with HACore 2025.9.4 running within LXC inside ProxmoxVE 9 x86_64 (that somehow had timezone set to UTC vs. Europe/Helsinki). Your setup may differ, so adapt paths and service names to your needs.