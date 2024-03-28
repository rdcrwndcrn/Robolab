#!/usr/bin/env python3

# Attention: Do not import the ev3dev.ev3 module in this file
import ssl
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum, unique
from json import dumps, loads
from logging import Logger
from typing import Any, Final

from paho.mqtt.client import Client, MQTTMessage

from planet import Direction


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


@unique
class MessageTypes(StrEnum):
    """The types of messages that are recognized when sent or received."""
    READY = "ready"
    PLANET = "planet"
    PATH = "path"
    PATH_UNVEILED = "pathUnveiled"
    PATH_SELECT = "pathSelect"
    TARGET = "target"
    TARGET_REACHED = "targetReached"
    EXPLORATION_COMPLETED = "explorationCompleted"
    DONE = "done"


class PathStatus(StrEnum):
    """The possible values for the path status."""
    BLOCKED = "blocked"
    FREE = "free"


# An inheritable `typing.NamedTuple` alternative.
# NOTE: Cannot enable `slots` parameter as it prohibits multiple inheritance
#       (or at least makes it less usable).
FrozenDataClass = dataclass(frozen=True)


@FrozenDataClass
class StartCoordinatesRecord:
    """Starting coordinates."""
    startX: int
    startY: int


@FrozenDataClass
class DirectionRecord:
    """Starting direction."""
    # Not a base class of `StartRecord` in order to retain field ordering.
    startDirection: Direction


@FrozenDataClass
class StartRecord(DirectionRecord, StartCoordinatesRecord):
    """Conjunction of start coordinates and direction."""


@FrozenDataClass
class EndRecord:
    """Ending coordinates and direction."""
    endX: int
    endY: int
    endDirection: Direction


@FrozenDataClass
class PlanetRecord(StartCoordinatesRecord):
    """Initial planet information."""
    planetName: str
    # Attention: Not `startDirection`!
    startOrientation: Direction


@FrozenDataClass
class PathRecord(EndRecord, StartRecord):
    """Path data."""
    pathStatus: PathStatus


@FrozenDataClass
class WeightedPathRecord(PathRecord):
    """Path data including weight."""
    pathWeight: int


@FrozenDataClass
class MessageRecord:
    """Message data."""
    message: str


@FrozenDataClass
class TargetRecord:
    """Target coordinates."""
    targetX: int
    targetY: int


# The payload record types corresponding to the message types received
# from the server.
SERVER_MESSAGE_RECORD_TYPES = {
    MessageTypes.PLANET: PlanetRecord,
    MessageTypes.PATH: WeightedPathRecord,
    MessageTypes.PATH_SELECT: DirectionRecord,
    MessageTypes.PATH_UNVEILED: WeightedPathRecord,
    MessageTypes.TARGET: TargetRecord,
    MessageTypes.DONE: MessageRecord,
}


class Communication:
    """MQTT communication client for a planet discovery robot."""

    # DO NOT EDIT THE METHOD SIGNATURE
    def __init__(self, mqtt_client: Client, logger: Logger):
        """Initialize communication, connect to server, subscribe."""
        # DO NOT CHANGE THE SETUP HERE
        self._client = mqtt_client
        self._client.tls_set(tls_version=ssl.PROTOCOL_TLS)
        self._client.on_message = self.safe_on_message_handler

        # ==============================================================

        # Here the class user can specify the callbacks which are
        # executed when the specified message is received.
        self.message_handlers: Mapping[MessageTypes, Callable] = {}

        self._client.enable_logger()    # DEBUG

        self._client.username_pw_set(GROUP_ID, password=PASSWORD)
        self._client.connect(HOST, port=PORT)

        self._client.subscribe(TOPIC_EXPLORER, qos=QOS)
        self._client.loop_start()

        self._logger = logger

    # DO NOT EDIT THE METHOD SIGNATURE
    def on_message(self, client: Client, data: Any, message: MQTTMessage):
        """Callback to handle if any message arrived."""
        payload = loads(message.payload.decode("utf-8"))
        self._logger.debug(dumps(payload, indent=2))
        if payload["from"] != "server":
            # Ignore any non server message (to not reprocess sent messages).
            return

        message_type = payload["type"]

        def _noop(*args, **kwargs): pass

        def _wrapped_planet_callback(*args, **kwargs):
            self._handle_planet_message(*args, **kwargs)
            return self.message_handlers.get(
                MessageTypes.PLANET, _noop
            )(*args, **kwargs)

        (self.message_handlers | {
            # Handle planet messages specially.
            MessageTypes.PLANET: _wrapped_planet_callback,
        }).get(message_type, _noop)(
            SERVER_MESSAGE_RECORD_TYPES.get(
                message_type,
                lambda **record: record
            )(**payload["payload"])
        )

    def _handle_planet_message(self, planet_record: PlanetRecord):
        # Ready message sent, now receiving planet name.
        # This is assumed to happen only once.
        self._topic_planet = TOPIC_PLANET_TEMPLATE.format(planet_record.planetName)
        self._client.subscribe(self._topic_planet, QOS)

    # DO NOT EDIT THE METHOD SIGNATURE
    #
    # In order to keep the logging working you must provide a topic
    # string and an already encoded JSON-Object as message.
    def send_message(self, topic: str, message: Any):
        """Sends given message to specified channel."""
        self._logger.debug("Publishing to: " + topic)
        self._logger.debug(dumps(message, indent=2))

        self._client.publish(topic, dumps(message), QOS)

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
