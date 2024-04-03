#!/usr/bin/env python3

import logging
import signal
import uuid
from time import sleep

import paho.mqtt.client as mqtt

from communication import GROUP_ID, TOPIC_EXPLORER, Communication


global client


def run(args: list[str]) -> None:
    global client

    client_id = GROUP_ID + "-" + str(uuid.uuid4())
    client = mqtt.Client(
        # Unique Client-ID to recognize our program
        client_id=client_id,
        # We want a clean session after disconnect or abort/crash
        clean_session=True,
        # Define MQTT protocol version
        protocol=mqtt.MQTTv311,
    )

    logging.basicConfig(
        # Define default mode
        level=logging.DEBUG,
        # Define default logging format
        format="%(asctime)s: %(message)s",
    )
    logger = logging.getLogger("RoboLab")

    c = Communication(client, logger)
    c.send_message(TOPIC_EXPLORER, {
        "from": "client",
        "type": "testPlanet",
        "payload": {
            "planetName": args[1] if len(args) > 1 else "Mebi",
        }
    })
    sleep(0.1)


def signal_handler(sig=None, frame=None, raise_interrupt=True):
    if client and client.is_connected():
        client.disconnect()
    if raise_interrupt:
        raise KeyboardInterrupt()


if __name__ == "__main__":
    from sys import argv

    signal.signal(signal.SIGINT, signal_handler)
    try:
        run(argv)
        signal_handler(raise_interrupt=False)
    except Exception as e:
        signal_handler(raise_interrupt=False)
        raise e
