DOMAIN = "elsner_ws1000"
NAME = "Elsner WS1000"
PORT = 4242
CONF_HOST = "host"
DEFAULT_SCAN_INTERVAL = 1

PLATFORMS = ["cover", "sensor", "binary_sensor", "switch", "select", "number", "button"]

INIT_REPLY = bytes.fromhex(
    "00 1F 01 07 00 00 00 00 00 00 05 00 00 00 00 00 00 00 "
    "0E 02 01 02 02 00 00 00 00 00 00 00 00 00 00"
)
REQUEST_2 = bytes.fromhex(
    "00 24 00 07 00 00 00 00 00 00 05 00 00 00 00 00 00 00 "
    "13 00 00 01 00 00 00 37 00 00 01 00 02 06 FF FF FF FF 00 63"
)
WS1000_PREFIX = bytes.fromhex(
    "00 07 00 00 00 00 00 00 05 00 00 00 00 00 00 00"
)
WEATHER_REQUEST = bytes.fromhex(
    "00 18 00 07 00 00 00 00 00 00 05 00 00 00 00 00 00 00 "
    "07 00 00 08 01 16 00 63"
)
CONFIG_REQUEST = bytes.fromhex(
    "00 18 00 07 00 00 00 00 00 00 05 00 00 00 00 00 00 00 "
    "07 FF FF 04 02 01 00 63"
)
