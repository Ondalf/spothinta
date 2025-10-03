import logging
import requests
import datetime as dt
import pytz

_LOGGER = logging.getLogger(__name__)

# From swagger:
# Supported regions: DK1, DK2, EE, FI, LT, LV, NO1, NO2, NO3, NO4, NO5, SE1, SE2, SE3, SE4 - Default region: FI
#
# Note: Most APIs impose a rate limit of one request per minute per IP address, with a maximum of 1,440 requests
# permitted within a 24-hour period. Upon exceeding this limit, the API will respond with HTTP status code 429
# (Too Many Requests). Failure to reduce the request rate within a reasonable timeframe may result in the
# temporary suspension of the associated IP address.
#
# API endpoint /TodayAndDayForward supports request params:
# region                string (default 'FI' if not set)
# priceResolution       integer($int32) (allowed 15, 60, default 15)
# HomeAssistant         boolean (default no)
# HomeAssistant15Min    boolean (default no)
# both HomeAssistant switches can be enabled, but 15min has higher priority
# all it does, it encloses the data to
# {"data":[{actual data},...]}
# default is
# [{actual data},...]

# NOTE: not all API definitions are in const.py because if someday someone needs to convert
# this to use some other endpoint, that would be just useless trash in wrong place...
API_BASE_URL = "https://api.spot-hinta.fi"

# Using "local time" 14:30 to figure out the latch every day, when to allow updating the API data
# NOTE: update does NOT happen at 14:30 -- rather 14:30-16:30 (2h main update timer and your HA
# start time in combination decides this so its fairly hopefully random)
FINNISH_TIMEZONE = pytz.timezone('Europe/Helsinki')
NEW_DATA_HOUR = 14
NEW_DATA_MINUTE = 30


class SpotHintaAPI:
    """Class for spot-hinta.fi API."""

    def __init__(self):
        # the data format is basically
        # _data_cache[region]{'raw_apidata','timestamp','min','max'}
        # just to avoid duplicates with VAT/NO_VAT
        self._data_cache = {}

    def _get_cache_data(self, region: str) -> dict:
        """
        Per region cache.
        Define the dataformat and initialize it.
        """
        if region not in self._data_cache:
            self._data_cache[region] = {
                '_data': None,       # Raw API-reply (includes datetime, rank and VAT/NO_VAT prices)
                'last_fetch': None,  # Last fetch
                'min_price': None,   # Min price for WHOLE dataset
                'max_price': None,   # Max price ^
            }
        return self._data_cache[region]

    def _get_price_keys(self):
        """Gets keys for matching API defined key names for tax/no_tax."""
        return {
            "VAT": "PriceWithTax",
            "NO_VAT": "PriceNoTax",
        }

    def calculate_current_price(self, region: str, price_resolution: int, price_type: str, now_dt: dt.datetime) -> float | None:
        """
        Calculates the current price based on cached data and the given timestamp,
        using the user's selected price type (VAT or NO_VAT).
        """

        keys = self._get_price_keys()
        # Fallback to VAT if not set (shouldn't happen)
        price_key_to_use = keys.get(price_type, keys["VAT"]) 

        cache = self._get_cache_data(region)
        data = cache['_data']

        if not data:
            return None

        current_price = None
        now_utc = now_dt.astimezone(dt.timezone.utc)

        # Iterate thru the cached values and find the current price
        # SHOULD be timezone agnostic, but unsure
        for item in data:
            try:
                item_dt_aware = dt.datetime.fromisoformat(item["DateTime"])
                item_dt_utc = item_dt_aware.astimezone(dt.timezone.utc)

                if item_dt_utc <= now_utc:
                    price_value = item.get(price_key_to_use) 

                    if price_value is not None:
                        current_price = float(price_value)
                    else:
                        current_price = None
                else:
                    break
            except Exception as e:
                _LOGGER.error(f"Error processing timestamp for {region}: {e}")

        # Fallback, if no price found, use last stored value
        if current_price is None:
            _LOGGER.warning(f"Unable to precisely determine current price for {region} using key {price_key_to_use}. Using last known price as fallback.")

            last_item = data[-1] if data else None
            if last_item:
                last_price_value = last_item.get(price_key_to_use)
                if last_price_value is not None:
                    try:
                        current_price = float(last_price_value)
                    except ValueError:
                        current_price = None

        return current_price


    def fetch_data(self, region: str, price_resolution: int, force_update: bool = False) -> bool:
        """
        Fetches data from the API OR reads it from the cache.
        The update necessity is assessed using the region's cache.
        Function supports force_update.
        """

        # Get the cache structure for the current region
        cache = self._get_cache_data(region)
        now_utc = dt.datetime.now(dt.timezone.utc)

        fetch_needed = force_update
        last_fetch_utc = cache.get('last_fetch')

        if not force_update:
            # Check if data exists (first load)
            if not cache.get('_data'):
                fetch_needed = True

            # Check if it's time to fetch new data (14:30 FI-time passed)
            elif last_fetch_utc:
                # Converting the last update timestamp to FI-time for comparison
                last_fetch_fi = last_fetch_utc.astimezone(FINNISH_TIMEZONE)
                now_fi = now_utc.astimezone(FINNISH_TIMEZONE)

                # Comparison logic
                fetch_time_today_fi = now_fi.replace(
                    hour=NEW_DATA_HOUR,
                    minute=NEW_DATA_MINUTE,
                    second=0,
                    microsecond=0
                )
                is_stale = (last_fetch_fi < fetch_time_today_fi)
                is_past_fetch_time = (now_fi >= fetch_time_today_fi)

                # So, if we need to update, fetch_needed is true
                if (is_stale and is_past_fetch_time) or (last_fetch_fi.date() < now_fi.date()):
                    _LOGGER.debug(f"Time to fetch new data for {region} (FI time).")
                    fetch_needed = True


        if fetch_needed:
            params = {
                "region": region,
                "priceResolution": price_resolution
            }
            endpoint = "/TodayAndDayForward"
            url = f"{API_BASE_URL}{endpoint}"

            _LOGGER.debug(f"Requesting API for {region}: {url} with params: {params}")

            try:
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()

                new_data = response.json()

                # Do not trust upstream to provide data sorted, so lets sort them ourselves...
                new_data.sort(key=lambda item: dt.datetime.fromisoformat(item["DateTime"]))
                _LOGGER.debug(f"API response data for {region} successfully sorted by DateTime.")

                # Store to cache
                cache['_data'] = new_data
                cache['last_fetch'] = dt.datetime.now(dt.timezone.utc) # Store UTC

                _LOGGER.debug(f"API response received successfully for {region}.")
                _LOGGER.debug(f"Stored {len(new_data)} price entries for {region}.")

            except requests.exceptions.RequestException as err:
                _LOGGER.error(f"FATAL: Error fetching API data for {region}: {err}")
                return False

        else:
            # If no fetch needed, just serve from cache - this is for debug purpose
            last_fetch_fi_str = last_fetch_utc.astimezone(FINNISH_TIMEZONE).strftime('%d.%m. %H:%M') if last_fetch_utc else 'Never'
            _LOGGER.debug(f"API call NOT made for {region}. Using cached data. (Last fetched: {last_fetch_fi_str})")

        # Process the data for the current region
        self._process_data(region)
        return bool(cache.get('_data'))


    def _process_data(self, region: str):
        """Processes the internally stored data for the specified region (calculates min/max)."""

        cache = self._get_cache_data(region)
        data = cache.get('_data')

        if not data:
            cache['min_price'] = None
            cache['max_price'] = None
            return

        # Min/Max are calculated only for VAT price
        # TODO: make this per sensors vat-key aware
        VAT_KEY = self._get_price_keys()["VAT"]

        # Grab prices in float format
        price_list = []
        for item in data:
            price_value = item.get(VAT_KEY)
            if price_value is not None:
                try:
                    price_list.append(float(price_value))
                except ValueError:
                    _LOGGER.warning(f"Non-numeric price found in data for {region}.")


        # Calculate min/max prices and store them to cache
        if price_list:
            cache['min_price'] = min(price_list)
            cache['max_price'] = max(price_list)
            _LOGGER.debug(f"Processed min/max prices for {region} (Key: {VAT_KEY}).")
        else:
            cache['min_price'] = None
            cache['max_price'] = None
