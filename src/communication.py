#!/usr/bin/env python3

# Attention: Do not import the ev3dev.ev3 module in this file
import json
import ssl
from logging import Logger
from typing import Any

from paho.mqtt.client import Client, MQTTMessage


# The MQTT quality of service used for all publishing/subscribing.
QoS = 2

# Authentication data.
GROUP_ID = "102"
PASSWORD = "stas6KE6Wj"
HOST = "mothership.inf.tu-dresden.de"
PORT = 8883

# Topics.
TOPIC_EXPLORER = "explorer/" + GROUP_ID
# The template for accessing the topics for a given planet.
TOPIC_PLANET_TEMPLATE = "planet/{}/" + GROUP_ID


class Communication:
    """MQTT communication client for a planet discovery robot."""

    # DO NOT EDIT THE METHOD SIGNATURE
    def __init__(self, mqtt_client: Client, logger: Logger):
        """Initialize communication module, connect to server, subscribe."""
        # DO NOT CHANGE THE SETUP HERE
        self.client = mqtt_client
        self.client.tls_set(tls_version=ssl.PROTOCOL_TLS)
        self.client.on_message = self.safe_on_message_handler

        # ==============================================================

        # DEBUG
        self.client.enable_logger()

        self.client.username_pw_set(GROUP_ID, password=PASSWORD)
        self.client.connect(HOST, port=PORT)

        self.client.subscribe(TOPIC_EXPLORER, qos=QoS)
        self.client.loop_start()

        self.logger = logger

    # DO NOT EDIT THE METHOD SIGNATURE
    def on_message(self, client: Client, data: Any, message: MQTTMessage):
        """Callback to handle if any message arrived."""
        payload = json.loads(message.payload.decode("utf-8"))
        self.logger.debug(json.dumps(payload, indent=2))

    # DO NOT EDIT THE METHOD SIGNATURE
    #
    # In order to keep the logging working you must provide a topic
    # string and an already encoded JSON-Object as message.
    def send_message(self, topic: str, message: Any):
        """Sends given message to specified channel."""
        self.logger.debug("Send to: " + topic)
        self.logger.debug(json.dumps(message, indent=2))

    # DO NOT EDIT THE METHOD SIGNATURE OR BODY
    #
    # This helper method encapsulated the original `on_message`` method
    # and handles exceptions thrown by threads spawned by `paho-mqtt``.
    def safe_on_message_handler(self, client: Client, data: Any, message: MQTTMessage):
        """Handle exceptions thrown by the paho library."""
        try:
            self.on_message(client, data, message)
        except:
            import traceback

            traceback.print_exc()
            raise
