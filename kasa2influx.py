#!/usr/bin/python3
import asyncio
import logging
import time
from datetime import datetime

from loguru import logger
from kasa import SmartPlug, SmartStrip, exceptions
from influxdb import InfluxDBClient
from logging_loki import LokiHandler

from config import INFLUXDB_HOST, INFLUXDB_DATABASE, INFLUXDB_PASSWORD, INFLUXDB_PORT, INFLUXDB_USERNAME
from config import LOKI_ENABLE, LOKI_HOST
from config import DEVICE_CONFIG

DEVICE_READ_TIMEOUT_SECS = 5
DEVICE_READ_FREQUENCY_SECS = 15

# Setup logging to Loki if required.
if LOKI_ENABLE:
    handler = LokiHandler(
        url=LOKI_HOST,
        tags={
            "application": "kasa2influx",
            },
        version="1"
    )
    logger.add(handler, level="WARNING")

# Create client to interact with InfluxDB
client = InfluxDBClient(INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_USERNAME, INFLUXDB_PASSWORD, INFLUXDB_DATABASE)

logger.info("Starting kasa2influx.")
logger.debug("Creating device list...")

# Create a list for all devices to be stored in and populate this list
all_devices = []
for this_conf in DEVICE_CONFIG:
    dev_ip = this_conf['ip']
    all_devices.append(this_conf['type'](dev_ip))

logger.debug("Creating device list... DONE")

async def do_update():
    logger.debug("Requesting device updates...")
    # Fire an update on all known devices.
    update_time = datetime.utcnow().timestamp() * 1000
    futures = [asyncio.wait_for(dev.update(), timeout=DEVICE_READ_TIMEOUT_SECS) for dev in all_devices]
    logger.debug("Futures assembled, awaiting update...")

    future_exceptions = await asyncio.gather(*futures, return_exceptions = True) 

    logger.debug("Update complete, processing update information...")

    all_measurements = []
    for dev, dev_info, dev_exception in zip(all_devices, DEVICE_CONFIG, future_exceptions):

        dev_feed_name = dev_info['tags']['feed']
        dev_ip = dev_info['ip']

        if dev_feed_name is None:
            # Skip this device as it is not configured.
            continue

        if dev_exception is not None:
            # An exception has ocurred for this device!
            if type(dev_exception) is asyncio.exceptions.TimeoutError:
                continue # move onto next device, this error is ignored.
            else:
                #A different exception ocurred, log this error:
                logger.error(f"Unexpected exception when updating device: {type(dev_exception)}", extra={"tags": {"ip": dev_ip, "feed": str(dev_feed_name)}})

        else:
            # Device has responded so must be up, let's summarise the measurement:

            # Define a local function to build a measurement from a plug:
            def get_measurement_from_plug(dev: SmartPlug, additional_tags = None) -> dict:
                
                all_tags = dict()
                all_tags.update(dev_info['tags'])

                if additional_tags is not None:
                    all_tags.update(additional_tags)

                this_measurement = {
                    "measurement": "power",
                    "timestamp": update_time,
                    "tags": all_tags,
                    "fields": {
                        "state": int(dev.is_on),
                        "rssi": int(dev.rssi)
                    }
                }

                if dev.has_emeter:
                    logger.debug(f"Adding emeter data for device: {dev_feed_name}...")
                    power_dict = dev.emeter_realtime
                    voltage = power_dict['voltage_mv'] / 1000
                    current = power_dict['current_ma'] / 1000
                    power = power_dict['power_mw'] / 1000
                    total_wh = power_dict['total_wh']

                    this_measurement['fields'].update({
                        "voltage": voltage,
                        "current": current,
                        "power": power,
                        "wh_cumulative": total_wh,
                    })

                return this_measurement

            logger.debug(f"Device {dev_feed_name} is of type: {type(dev)}.")

            if type(dev) is SmartPlug:
                logger.debug(f"Device {dev_feed_name} is a smart plug.")
                this_measurement = get_measurement_from_plug(dev)

                all_measurements.append(this_measurement)

            elif type(dev) is SmartStrip:
                logger.debug(f"Device {dev_feed_name} is a smart strip.")
                dev: SmartStrip
    
                for n, plug in enumerate(dev.children):
                    if dev_info["channels"][n] is None:
                        logger.debug("Skipping channel, no name configured.")
                    else:
                        # Construct the feed name for this channel, combination of device feed and channel name.
                        channel_feed = f"{dev_feed_name}-{dev_info['channels'][n]}"
                        this_measurement = get_measurement_from_plug(plug, additional_tags={"feed": channel_feed})
                        all_measurements.append(this_measurement)
            
            else:
                logger.error("Unsupported Device Type")

    logger.debug(f"Processing complete, uploading {len(all_measurements)} results...")

    try:
        client.write_points(all_measurements)
        #print(all_measurements)
    except Exception as e:
        logger.exception("Exception whilst attempting to store to InfluxDB")


while True:
    start_time = time.time()
    asyncio.run(do_update())
    end_time = time.time()
    run_time = end_time - start_time
    logger.debug(f"Time to read all devices was {run_time} seconds.")
    next_time = DEVICE_READ_FREQUENCY_SECS + start_time
    sleep_time = next_time - time.time()
    logger.debug("Waiting for next reporting time...")
    time.sleep(sleep_time)
