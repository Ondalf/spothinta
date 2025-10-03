# Common constants
DOMAIN = "spothinta"
ATTRIBUTION = "Tiedot tarjoaa api.spot-hinta.fi"
SERVICE_UPDATE_PRICES = "update_prices"
PRICE_RESOLUTION = 15 # default 15 min

# Some keys
CONF_RESOLUTION = "price_resolution"
CONF_PRICE_TYPE = "price_type"
CONF_REGION = "region"

# According to API documentation, these are supported
SUPPORTED_REGIONS = [
    "DK1", "DK2", "EE", "FI", "LT", "LV",
    "NO1", "NO2", "NO3", "NO4", "NO5",
    "SE1", "SE2", "SE3", "SE4"
]
DEFAULT_REGION = "FI"

# API reports both VAT and NO_VAT prices
SUPPORTED_PRICE_TYPES = [
    "VAT", "NO_VAT"
]
DEFAULT_PRICE_TYPE = "VAT"

# This one is just for webui to give longer explanation for the radio button
PRICE_TYPE_OPTIONS_MAP = {
    "VAT": "Price including VAT",
    "NO_VAT": "Price excluding VAT",
}
