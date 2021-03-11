# kasa2influx

This script is used for collecting state and energy information from the TP-Link Kasa devices. It's been tested with:

* HS110
* KP115
* HS100 (_State Only_)
* KP303 (_State Only_)

## Installation
NOTE: Python 3.7 or greater is required.

```
git clone
python3.9 -m venv _venv
source _venv/bin/activate
pip install -r requirements.txt
cp config.example.py config.py
nano config.py # Edit to configure
cp kasa2influx.service /usr/lib/systemd/system/
nano /usr/lib/systemd/system/kasa2influx.service
systemctl enable kasa2influx
systemctl start kasa2influx
systemctl status kasa2influx
```
## Configuration
Each device can have adjustable tags added, this is all done via the `config.py` file.

## Logging
This is configured to use the Grafana Loki service for log aggregation, this can be disabled in the configuration file.