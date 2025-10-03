from __future__ import annotations

import logging
from datetime import timedelta
import datetime as dt

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import (
    DOMAIN,
    CONF_REGION,
    DEFAULT_REGION,
    CONF_RESOLUTION,
    PRICE_RESOLUTION,
    CONF_PRICE_TYPE,
    DEFAULT_PRICE_TYPE
)
from .spothinta_api import SpotHintaAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up SpotHinta sensors from a config entry"""

    region = entry.data.get(CONF_REGION, DEFAULT_REGION)
    price_resolution = entry.data.get(CONF_RESOLUTION, PRICE_RESOLUTION)
    price_type = entry.data.get(CONF_PRICE_TYPE, DEFAULT_PRICE_TYPE)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if 'api' not in hass.data[DOMAIN]:
        hass.data[DOMAIN]['api'] = SpotHintaAPI()

    api: SpotHintaAPI = hass.data[DOMAIN]['api']

    coordinator = SpotHintaDataUpdateCoordinator(hass, api, region, price_resolution)

    await coordinator.async_config_entry_first_refresh()

    async_add_entities([
        SpotHintaSensor(coordinator, region, price_type),
    ])

class SpotHintaDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for updating API data for a specific region"""

    def __init__(self, hass, api: SpotHintaAPI, region: str, price_resolution: int):
        self.api = api
        self.region = region
        self.price_resolution = price_resolution

        self.data = {
            '_data': [],              # The data itself is stored here
            'last_fetch': None,       # Last fetch timestamp
            'last_refresh_utc': None, # Last refresh (this is the one that updates every 15 minutes)
            'current_price': 0.0,     # Placeholder for current price
            'min_price': 0.0,         # Placeholder for minimum price
            'max_price': 0.0,         # Placeholder for maximum price
        }

        # This defines the interval how often API updates are called (but in reality they run once)
        # Why I picked 120 minutes - it fetches the data from spot-hinta API on startup and refers
        # to cache until next day 14:30 finnish time, which makes it forcefully allow ONE call thru
        # to update the data from remote. Otherwise ALL calls goes to cache.
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{region}",
            update_interval=timedelta(minutes=120),
        )

    async def _async_update_data(self):
        """Fetch the latest data from the API for the stored region."""
        try:
            success = await self.hass.async_add_executor_job(
                self.api.fetch_data, self.region, self.price_resolution
            )

            if not success:
                raise UpdateFailed(f"API fetch returned non-successful result for {self.region}.")

            self.last_update = dt.datetime.now(dt.timezone.utc)

            return self.api._get_cache_data(self.region)

        except Exception as err:
            raise UpdateFailed(f"Error fetching Spot-hinta.fi data for region {self.region}: {err}")


class SpotHintaSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SpotHinta sensor"""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 5

    def __init__(self, coordinator: SpotHintaDataUpdateCoordinator, region: str, price_type: str, entity_category: EntityCategory | None = None):
        super().__init__(coordinator)
        self._price_type = price_type
        self._attr_entity_category = entity_category

        # Get a little creative to allow ANY region + VAT/NO_VAT to avoid collisions
        self._attr_unique_id = f"{DOMAIN}_{region}_{price_type}_price"
        self._attr_name = f"Spot Price {region} {price_type}"


    @property
    def state(self):
        """Returns the sensor state (the current price)."""
        price = self.coordinator.data.get('current_price')
        return float(price) if price is not None else None
        
    @property
    def icon(self) -> str:
        return "mdi:flash"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement this sensor expresses itself in."""
        return "EUR/kWh"

    @property
    def extra_state_attributes(self):
        """Returns extra state attributes."""
        data = self.coordinator.data

        # for debugging
        #last_exec_dt = self.coordinator.last_update
        #last_exec_utc = last_exec_dt.isoformat() if last_exec_dt else None

        return {
            "region": self.coordinator.region,
            "current_price": data.get('current_price'),
            "min_price": data.get('min_price'),
            "max_price": data.get('max_price'),

            # for debugging
            #"last_fetch_utc": data.get('last_fetch'),
            #"last_exec_utc": last_exec_utc,
            #"last_refresh_utc": data.get('last_refresh_utc'),
            #"raw_data_entries": len(data.get('_data', []))
        }

    async def async_added_to_hass(self) -> None:
        """Create timer that runs exactly every quarter."""

        await super().async_added_to_hass()

        self.async_on_remove(
            async_track_time_change(
                self.hass,
                self.async_update_state,
                minute=[0, 15, 30, 45],
                second=0
            )
        )
        # Do immediate update
        await self.async_update_state(dt.datetime.now())


    async def async_update_state(self, now):
        """Calculate new price and update it to sensor."""

        # Grab new price via cache
        new_price = await self.hass.async_add_executor_job(
            self.coordinator.api.calculate_current_price,
            self.coordinator.region,
            self.coordinator.price_resolution,
            self._price_type,
            dt.datetime.now()
        )

        # Update coordinator price information
        self.coordinator.data['current_price'] = new_price

        # And its timestamp (not really needed though)
        self.coordinator.data['last_refresh_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()

        # Let HA know state of sensor changed
        self.async_write_ha_state()

        _LOGGER.debug(f"Sensor state updated for {self.coordinator.region}/{self._price_type} at {now.strftime('%H:%M:%S')}. New price: {new_price}")
