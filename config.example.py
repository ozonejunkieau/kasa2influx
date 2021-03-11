from kasa import SmartPlug, SmartStrip

INFLUXDB_HOST = 'influxdb.test'
INFLUXDB_PORT = 8086
INFLUXDB_USERNAME = 'user'
INFLUXDB_PASSWORD = 'pass'
INFLUXDB_DATABASE = 'db'

LOKI_ENABLE = False
LOKI_HOST = "http://loki.domain.test/loki/api/v1/push"

DEVICE_CONFIG = [
    {
        "ip": "192.168.1.70",
        "tags": {
            "tag_name": "tag_value",
        },
        "type": SmartPlug,
    },

    {
        "ip": "192.168.1.75",
        "tags": {
            "tag_name": "tag_value",
        },
        "channels": {
            0: "channel_name",
            1: None,
            2: None,
        },
        "type": SmartStrip,
    },

]