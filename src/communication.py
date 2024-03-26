#!/usr/bin/env python3

# Attention: Do not import the ev3dev.ev3 module in this file
import json
import ssl
import paho.mqtt.client as mqtt
import logging

class Communication:
    """
    Class to hold the MQTT client communication
    Feel free to add functions and update the constructor to satisfy your requirements and
    thereby solve the task according to the specifications
    """

    # DO NOT EDIT THE METHOD SIGNATURE
    def __init__(self, mqtt_client, logger):
        """
        Initializes communication module, connect to server, subscribe, etc.
        :param mqtt_client: paho.mqtt.client.Client
        :param logger: logging.Logger
        """
        # DO NOT CHANGE THE SETUP HERE
        self.client = mqtt_client
        self.client.tls_set(tls_version=ssl.PROTOCOL_TLS)
        self.client.on_message = self.safe_on_message_handler

        # Add your client setup here
        self.client.username_pw_set('102',
                               password='stas6KE6Wj')  # Your group credentials, see the python skill-test for your group password
        self.client.connect('mothership.inf.tu-dresden.de', port=8883)
        self.client.subscribe('explorer/102', qos=2)  # Subscribe to topic explorer/xxx

        self.logger = logger
        print(self.client.is_connected())

    # DO NOT EDIT THE METHOD SIGNATURE
    def on_message(self, client, data, message):
        """
        Handles the callback if any message arrived
        :param client: paho.mqtt.client.Client
        :param data: Object
        :param message: Object
        :return: void
        """
        payload = json.loads(message.payload.decode('utf-8'))
        self.logger.debug(json.dumps(payload, indent=2))

        # YOUR CODE FOLLOWS (remove pass, please!)
        data = json.loads(message.payload.decode("utf-8"))
        print(json.dumps(data, indent=2))
        print("Nachricht erhalten:", str(message.payload.decode("utf-8")))


    # DO NOT EDIT THE METHOD SIGNATURE
    #
    # In order to keep the logging working you must provide a topic string and
    # an already encoded JSON-Object as message.
    def send_message(self, topic, message):
        """
        Sends given message to specified channel
        :param topic: String
        :param message: Object
        :return: void
        """
        self.logger.debug('Send to: ' + topic)
        self.logger.debug(json.dumps(message, indent=2))

        # YOUR CODE FOLLOWS (remove pass, please!)
        print(self.client.is_connected())
        self.client.publish(topic, json.dumps(message, indent=2))
        print("Nachricht gesendet:", message)

        # Callback für den Empfang von Nachrichten registrieren
        self.client.on_message = Communication.on_message
        self.client.subscribe('explorer/102', qos=2)
        data = json.loads(message.payload.decode('utf-8'))
        print(json.dumps(data, indent=2))
        print("\n")

    # DO NOT EDIT THE METHOD SIGNATURE OR BODY
    #
    # This helper method encapsulated the original "on_message" method and handles
    # exceptions thrown by threads spawned by "paho-mqtt"
    def safe_on_message_handler(self, client, data, message):
        """
        Handle exceptions thrown by the paho library
        :param client: paho.mqtt.client.Client
        :param data: Object
        :param message: Object
        :return: void
        """
        try:
            self.on_message(client, data, message)
        except:
            import traceback
            traceback.print_exc()
            raise

#Communication.__init__(self,paho.mqtt.client.Client, logging.Logger)
#Communication.on_message(self,paho.mqtt.client.Client, data, message)
#Communication.send_message(self,"explorer/102",message = {"from": "client","type": "testPlanet","payload": {"planetName": "Mebi"}})
#Communication.safe_on_message_handler(self,paho.mqtt.client.Client,data,message)

#x1 = Communication(paho.mqtt_client.Client, logging.Logger)



