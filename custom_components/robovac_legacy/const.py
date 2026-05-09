"""Constants for robovac_legacy."""

DOMAIN = "robovac_legacy"

CONF_LOCAL_CODE = "local_code"
CONF_REFRESH_FROM_CLOUD = "refresh_from_cloud"
CONF_DEVICE_IDS = "device_ids"

CONF_VACS = "vacs"

DEFAULT_SCAN_INTERVAL = 45

# RoboVac 11c hardware product code returned by Eufy cloud (`device.product.product_code`).
SUPPORTED_LEGACY_PRODUCT_CODES = frozenset({"T2103"})
