#!/usr/bin/env python3

# Attention: Do not import the ev3dev.ev3 module in this file
import logging
import ssl
from collections.abc import Callable, Mapping
from enum import StrEnum
from json import dumps, loads
from logging import Logger
from typing import Any, Final

from paho.mqtt.client import Client, MQTTMessage


# The MQTT quality of service used for all publishing/subscribing.
QOS: Final = 2

# Authentication data.
GROUP_ID: Final = "102"
PASSWORD: Final = "stas6KE6Wj"
HOST: Final = "mothership.inf.tu-dresden.de"
PORT: Final = 8883

# Topics.
TOPIC_EXPLORER: Final = "explorer/" + GROUP_ID
# The template for accessing the topics for a given planet.
TOPIC_PLANET_TEMPLATE: Final = "planet/{}/" + GROUP_ID


class MessageTypes(StrEnum):
    """The types of messages that can be sent or received."""
    READY = "ready"
    PLANET = "planet"
    PATH = "path"
    PATH_UNVEILED = "pathUnveiled"
    PATH_SELECT = "pathSelect"
    TARGET = "target"
    TARGET_REACHED = "targetReached"
    EXPLORATION_COMPLETED = "explorationCompleted"
    DONE = "done"


class Communication:
    """MQTT communication client for a planet discovery robot."""

    # DO NOT EDIT THE METHOD SIGNATURE
    def __init__(self, mqtt_client: Client, logger: Logger):
        """Initialize communication, connect to server, subscribe."""
        # DO NOT CHANGE THE SETUP HERE
        self.client = mqtt_client
        self.client.tls_set(tls_version=ssl.PROTOCOL_TLS)
        self.client.on_message = self.safe_on_message_handler

        # ==============================================================

        # Here the class user can specify the callbacks which are
        # executed when the specified message is received.
        self.message_type_handlers: Mapping[MessageTypes, Callable[..., Any]] = {}

        self.client.enable_logger()    # DEBUG

        self.client.username_pw_set(GROUP_ID, password=PASSWORD)
        self.client.connect(HOST, port=PORT)

        self.client.subscribe(TOPIC_EXPLORER, qos=QOS)
        self.client.loop_start()

        self.logger = logger

    # DO NOT EDIT THE METHOD SIGNATURE
    def on_message(self, client: Client, data: Any, message: MQTTMessage):
        """Callback to handle if any message arrived."""
        payload = loads(message.payload.decode("utf-8"))
        self.logger.debug(dumps(payload, indent=2))
        if payload["from"] != "server":
            # Ignore any non server message (to not reprocess sent messages).
            return

        message_type = payload["type"]

        self.message_type_handlers.get(
            message_type, lambda *args, **kwargs: ...
        )(
            {
                MessageTypes.PLANET: self._handle_planet_message,
                MessageTypes.PATH: self._handle_path_message,
                MessageTypes.PATH_SELECT: self._handle_path_select_message,
                MessageTypes.PATH_UNVEILED: self._handle_path_unveiled_message,
                MessageTypes.TARGET: self._handle_target_message,
                MessageTypes.DONE: self._handle_done_message,
            }.get(
                message_type,
                lambda payload: payload,
            )(payload["payload"])
        )

    def _handle_planet_message(self, payload: Any):
        # Ready message sent, now receiving planet name.
        self._topic_planet = TOPIC_PLANET_TEMPLATE.format(payload["planetName"])
        self.client.subscribe(self._topic_planet, QOS)

    def _handle_path_message(self, payload: Any):
        ...

    def _handle_path_unveiled_message(self, payload: Any):
        ...

    def _handle_path_select_message(self, payload: Any):
        ...

    def _handle_target_message(self, payload: Any):
        ...

    def _handle_done_message(self, payload: Any):
        ...

    # DO NOT EDIT THE METHOD SIGNATURE
    #
    # In order to keep the logging working you must provide a topic
    # string and an already encoded JSON-Object as message.
    def send_message(self, topic: str, message: Any):
        """Sends given message to specified channel."""
        self.logger.debug("Publishing to: " + topic)
        self.logger.debug(dumps(message, indent=2))

        self.client.publish(topic, dumps(message), QOS)

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
