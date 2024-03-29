#!/usr/bin/env python3

# Attention: Do not import the ev3dev.ev3 module in this file
import ssl
from collections.abc import Callable, Mapping
from dataclasses import dataclass, asdict
from json import dumps, loads
from logging import Logger
from typing import Any, Final, Union

from paho.mqtt.client import Client, MQTTMessage

# Using Python 3.12 library version instead of Python 3.9 in order to
# use `StrEnum`. Use a subdirectory to avoid name clashes.
from python312stdlib.enum import StrEnum, unique
from planet import Direction


# This type is not yet defined in  Python 3.9` types`.
NoneType = type(None)

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
class ServerMessageType(StrEnum):
    """The types of messages that are recognized when received from server."""
    PLANET = "planet"
    PATH = "path"
    PATH_UNVEILED = "pathUnveiled"
    PATH_SELECT = "pathSelect"
    TARGET = "target"
    DONE = "done"


@unique
class ClientMessageType(StrEnum):
    """The valid types of messages to be sent."""
    READY = "ready"
    PATH = "path"
    PATH_SELECT = "pathSelect"
    TARGET_REACHED = "targetReached"
    EXPLORATION_COMPLETED = "explorationCompleted"


@unique
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
    ServerMessageType.PLANET: PlanetRecord,
    ServerMessageType.PATH: WeightedPathRecord,
    ServerMessageType.PATH_SELECT: DirectionRecord,
    ServerMessageType.PATH_UNVEILED: WeightedPathRecord,
    ServerMessageType.TARGET: TargetRecord,
    ServerMessageType.DONE: MessageRecord,
}

# The payload record types corresponding to the message types received
# sent by the client.
CLIENT_MESSAGE_RECORD_TYPES = {
    ClientMessageType.READY: NoneType,
    ClientMessageType.PATH: PathRecord,
    ClientMessageType.PATH_SELECT: StartRecord,
    ClientMessageType.TARGET_REACHED: MessageRecord,
    ClientMessageType.EXPLORATION_COMPLETED: MessageRecord,
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
        # The callback takes --- if the message type is recognized and in
        # `ServerMessageType` --- the corresponding record type, else it
        # should take whatever the server sends as payload in this message.
        self.message_handlers: (Mapping[
            Union[ServerMessageType, str],
            Callable[
                [
                    Union[
                        PlanetRecord, WeightedPathRecord, DirectionRecord,
                        TargetRecord, MessageRecord, Any,
                    ]
                ],
                Any,
            ],
        ]) = {}

        self._client.enable_logger()    # DEBUG

        self._client.username_pw_set(GROUP_ID, password=PASSWORD)
        self._client.connect(HOST, port=PORT)

        self._client.subscribe(TOPIC_EXPLORER, qos=QOS)
        self._client.loop_start()

        self._logger = logger

    # DO NOT EDIT THE METHOD SIGNATURE
    def on_message(self, client: Client, data: Any, message: MQTTMessage):
        """Callback to handle if any message from the server arrived."""
        payload = loads(message.payload.decode("utf-8"))
        self._logger.debug(dumps(payload, indent=2))
        if payload["from"] != "server":
            # Ignore any non server message (to not reprocess sent messages).
            return

        message_type = payload["type"]

        # A function taking anything and doing nothing.
        # Used in the dictionary search below as default values in case the
        # searched key wasn't found to avoid if-else branching.
        def _noop(*args, **kwargs): pass

        # Prepends our `_handle_planet_message` handler in order to be executed
        # before the user specified callback (or, if no callback, the `_noop`)
        # is executed, in case the `ServerMessageType.PLANET` message was
        # received.
        def _wrapped_planet_callback(*args, **kwargs):
            self._handle_planet_message(*args, **kwargs)
            return self.message_handlers.get(
                ServerMessageType.PLANET, _noop
            )(*args, **kwargs)

        # Find the user specified callback for the given message type
        # (in case of `ServerMessageType.PLANET`, execute our handler before
        # the user callback to do additional communication handling)
        # and call it with the record type corresponding to the message type
        # filled with the actual values, or just with the unchanged message
        # payload in case of an unknown message type.
        (self.message_handlers | {
            # Handle planet messages specially.
            ServerMessageType.PLANET: _wrapped_planet_callback,
        }).get(message_type, _noop)(
            SERVER_MESSAGE_RECORD_TYPES.get(
                message_type,
                # A dummy function to pass the raw message payload to
                # the user callback in case the received message type is
                # not in `ServerMessageType`.
                lambda **record: record
            )(**payload["payload"])
        )

    def _handle_planet_message(self, planet_record: PlanetRecord):
        # Ready message sent, now receiving planet name.
        # This is assumed to happen only once.
        self._topic_planet = TOPIC_PLANET_TEMPLATE.format(planet_record.planetName)
        self._client.subscribe(self._topic_planet, QOS)

    def send_message_type(
        self,
        message_type: ClientMessageType,
        # NOTE: Type union operator `|` not supported in Python 3.9.
        record: Union[StartRecord, PathRecord, MessageRecord, NoneType] = None
    ):
        """Send the given message `record` of `message_type` to the right topic.

        If `record` is not an instance of the record type mapped by
        `CLIENT_MESSAGE_RECORD_TYPES`, no message will be sent; the call will
        be ignored.
        """
        if not isinstance(record, CLIENT_MESSAGE_RECORD_TYPES[message_type]):
            self._logger.error(
                f"Invalid {record = } for {message_type = } in"
                f" `{self.__class__.__name__}.send_message_type`"
            )
            return

        if message_type in (
            ClientMessageType.READY,
            ClientMessageType.TARGET_REACHED,
            ClientMessageType.EXPLORATION_COMPLETED
        ):
            topic = TOPIC_EXPLORER
        else:
            topic = self._topic_planet

        self.send_message(topic, {
                "from": "client",
                "type": message_type,
            } | (
                {} if record is None else {"payload": asdict(record)}
            )
        )

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
