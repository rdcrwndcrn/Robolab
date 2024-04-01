#!/usr/bin/env python3

import logging
import os
import signal
import uuid

import ev3dev.ev3 as ev3
import paho.mqtt.client as mqtt

from communication import Communication, GROUP_ID
from odometry import Odometry
from planet import Direction, Planet
import robot as rob

client = None  # DO NOT EDIT


def run():
    # DO NOT CHANGE THESE VARIABLES
    #
    # The deploy-script uses the variable ``client`` to stop the MQTT
    # client after your program stops or crashes. Your script isn't able
    # to close the client after crashing.
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

    # Setup logging directory and file
    curr_dir = os.path.abspath(os.getcwd())
    if not os.path.exists(curr_dir + "/../logs"):
        os.makedirs(curr_dir + "/../logs")
    log_file = curr_dir + "/../logs/project.log"
    logging.basicConfig(
        filename=log_file,
        # Define default mode
        level=logging.DEBUG,
        # Define default logging format
        format="%(asctime)s: %(message)s",
    )
    logger = logging.getLogger("RoboLab")

    # ==================================================================
    # create robot instance
    robot = rob.Robot()
    # set start state in rob instance to color calibration state, which needs to be an instance of Robo
    robot.set_start_state(rob.ColourCalibration(robot))
    # start by running runAll from robo class
    robot.runAll()


# DO NOT EDIT
def signal_handler(sig=None, frame=None, raise_interrupt=True):
    if client and client.is_connected():
        client.disconnect()
    if raise_interrupt:
        raise KeyboardInterrupt()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    try:
        run()
        signal_handler(raise_interrupt=False)
    except Exception as e:
        signal_handler(raise_interrupt=False)
        raise e
