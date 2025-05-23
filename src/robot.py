from dataclasses import asdict
import math
from logging import Logger
from queue import SimpleQueue, Empty
import time
from sys import exit
from typing import Any, Callable, Optional, Union

from ev3dev import ev3
from paho.mqtt.client import Client

from communication import (
    ClientMessageType, Communication, DirectionRecord, EndRecord, MessageRecord,
    PathRecord, PathStatus, PlanetRecord, ServerMessageType, StartRecord,
    TargetRecord, WeightedPathRecord,
)
from planet import BLOCKED, Direction, Planet, opposite


# class to switch between States
class Robot:
    def __init__(self, client: Client, logger: Logger):
        self.client = client
        self.logger = logger
        # Communication is initialized at first node.
        self.communication: Optional[Communication] = None
        self.planet = Planet()
        # for switching states
        # attribute where current states gets saved
        self.state = None

        # normal attributes
        # for saving colours
        self.colors = {}
        self.calibrated_colors = ['black', 'white']
        self.offset = 0
        # initialising colour sensor
        self.cs = ev3.ColorSensor()
        # using rgb-mode
        self.cs.mode = 'RGB-RAW'
        # assigning ultrasonic sensor to us
        self.us = ev3.UltrasonicSensor()
        # continuous measurement in centimeters
        self.us.mode = 'US-DIST-CM'
        # assigning motors
        # right motor is on output D
        self.m_right = ev3.LargeMotor("outD")
        # left motor is on output A
        self.m_left = ev3.LargeMotor("outA")

        # Odometrie
        # list for motor positions
        self.odo_motor_positions = []
        # wheels distance 7,6 cm in ticks
        self.a = (14.65 * 360) / (5.6 * math.pi)
        # for rounding
        self.current_node_colour = ''
        self.last_node_colour = ''
        # if path is blocked odo does not need to calc anything
        self.path_blocked = False
        # The coordinates and direction of last node; first set after receiving
        # `planet` message.
        self.start_record: StartRecord = StartRecord(0, 0, 0)
        # The target to reach.
        self.target: Optional[tuple[int, int]] = None

    def set_start_state(self, state):
        # for switching to start state
        self.switch_state(state)

    # run all , because after that the states changes themselves back and forth
    def runAll(self):
        # run the state object which lies in the state attribute
        self.state.run()

    # calling function to change attribute and giving the robot instance (self) to the new state
    def switch_state(self, new_state):
        self.state = new_state
        self.state.robot = self
        self.state.run()

    def motor_prep(self):
        self.m_left.reset()
        self.m_right.reset()
        self.m_left.stop_action = "brake"
        self.m_right.stop_action = "brake"
        time.sleep(0.1)

    # is not static
    @staticmethod
    def convert_to_grey(r, g, b):
        return 0.3 * r + 0.59 * g + 0.11 * b


# inheritance class state for saving the robot instance
class State:
    def __init__(self):
        self.robot = None


# starting state, calibrates colours
class ColourCalibration(State):
    def __init__(self, robot):
        State.__init__(self)
        self.robot = robot
        self.btn = ev3.Button()
        self.screen = ev3.Screen()
        self.ts = ev3.TouchSensor()

    def run(self):
        # running Colour calibration methods
        # measuring colour and saving them in dict
        self.measure_colours()
        # calc offset for PID
        self.calc_off()
        # for Odo
        self.robot.motor_prep()

        # switch to the follower state by creating follower instance
        # uses robot instance which lies in the robot attribute in Metaclass
        next_state = Follower(self.robot)
        # calling the switch method of robot class which needs new state as an instance
        self.robot.switch_state(next_state)

    # colour calibration with robo buttons and display, for calc offset
    #  there, but display does not show anything
    def measure_colours(self):
        # so we cant miss it
        ev3.Sound.beep()
        # robot is ready for calibration
        for x in self.robot.calibrated_colors:
            while not self.ts.value():
                time.sleep(0.1)
            ev3.Sound.beep()
            # getting and saving rgb-values
            self.robot.colors[x] = self.calibration()
            ev3.Sound.beep()
        time.sleep(4)

    # eliminate short period deviation in colour sensor
    # to help with measuring the colors in the colors dict
    def calibration(self):
        # average rgb
        avg_r = 0
        avg_g = 0
        avg_b = 0
        # measuring 100 times
        for i in range(100):
            red, green, blue, _ = self.robot.cs.bin_data("hhhh")
            avg_r += red
            avg_g += green
            avg_b += blue
        avg_r /= 100
        avg_g /= 100
        avg_b /= 100
        return [avg_r, avg_g, avg_b]

    # for calculating the offset
    def calc_off(self):
        # colour calc to calc the error and use that for PID
        # converting white and black to greyscale / 2.55 to norm it from 0 to 100
        white_grey = self.robot.convert_to_grey(self.robot.colors['white'][0], self.robot.colors['white'][1],
                                                self.robot.colors['white'][2])
        black_grey = self.robot.convert_to_grey(self.robot.colors['black'][0], self.robot.colors['black'][1],
                                                self.robot.colors['black'][2])
        # calculating offset
        self.robot.offset = (white_grey + black_grey) / 2

    # rgb to grey
    # after greyscale model optimised for human eyes


# follows line, PID and I, accumulates data for Odometry, turn before collision with bottles, detects nodes
class Follower(State):
    def __init__(self, robot):
        State.__init__(self)
        self.robot = robot
        # for PID
        # initialising t_p, well use it with the meaning of x per mile of the possible wheel speed
        self.t_p = 220
        # declaring proportional gain
        self.k_p = 5 * 10 ** -1
        # integral gain
        self.k_i = 4.5
        # second I controller for going slower in slopes 30
        self.ki = 12
        # derivative gain
        self.k_d = 3 * 10 ** -1
        # 40,92 ms per loop -> 1s has ~24,5 iterations
        # 60 iterations ~ 2,5 s
        self.i_length = 90
        # for summing up the error, hence integral
        self.all_err = []
        # constant to shrink error in interval
        self.k_err = 0.003
        # for calc the derivative
        self.last_err = 0
        # counter for iterations in while
        self.i = 0
        # counter for getting node colours
        self.c = 0

    def run(self):
        # line following loop
        self.robot.path_blocked = False
        self.robot.motor_prep()
        try:
            while True:
                # get rgb values for the iteration we are in
                r, g, b, _ = self.robot.cs.bin_data("hhhh")
                # check if Rob over red or blue
                self.check_for_node(r, g, b)
                # turn if bottle is less than 150 mm before Rob
                if self.robot.us.value() < 150:
                    self.robot.path_blocked = True
                    self.bottle_turn()
                # converting to greyscale / 2.55 to norm it from 0 to 100
                grey = self.robot.convert_to_grey(r, g, b)
                # calculating error
                err = grey - self.robot.offset
                # calc integral
                integral = self.calc_int(err)
                # calc derivative
                derivative = err - self.last_err
                # calc adjustments for little correction turns of wheels
                turns = self.k_p * err + self.k_i * integral + self.k_d * derivative
                # continuing with adjusted speed
                new_speed_left = self.t_p + turns - abs(integral) * self.ki
                new_speed_right = self.t_p - turns - abs(integral) * self.ki
                self.speed(new_speed_left, new_speed_right)
                # for derivative in next interation
                self.last_err = err
                # reset counters every 12 iteration, to differentiate blue nodes and "blueish" points on paths
                if self.i % 12 == 0:
                    self.i = 0
                    self.c = 0
                self.i += 1
                # logging motor position for odo
                self.robot.odo_motor_positions.append((self.robot.m_left.position, self.robot.m_right.position))

        finally:
            self.robot.motor_prep()
            print('aborting ...')

    # check if colour sensor is over red or blue
    def check_for_node(self, r, g, b):
        next_state = Node(self.robot)
        if r > 5 * b and r > 3 * g:
            self.c += 1
            if self.c > 1:
                # reset motor position of each motor for odo and to stop
                self.robot.motor_prep()
                self.turn(3)
                # save colour for odo
                # saving last node colour before overwriting curren node colour
                self.robot.last_node_colour = self.robot.current_node_colour
                # overwriting current node colour for odo
                self.robot.current_node_colour = 'red'
                # calling the switch method of robot class which needs new state as an instance
                self.robot.switch_state(next_state)
        elif 1.9 * b - 0.9 * r > 40:
            self.c += 1
            # print(f'found blue node: {r, g, b}, c = {self.c}')
            if self.c > 1:
                # reset motor position of each motor for odo and to stop
                self.robot.motor_prep()
                self.turn(2)
                # save colour for odo
                self.robot.last_node_colour = self.robot.current_node_colour
                self.robot.current_node_colour = 'blue'
                # calling the switch method of robot class which needs new state as an instance
                self.robot.switch_state(next_state)

    # basic turn function with degrees
    def turn(self, degree):
        self.robot.motor_prep()
        # opposite wheel directions are twice as fast
        # 1860 * 2 ticks ~ 360 degree
        # ticks the wheels should to do
        ticks = 1860
        self.robot.m_left.position_sp = (1 / 2 * degree * ticks) / 360
        self.robot.m_right.position_sp = -(1 / 2 * degree * ticks) / 360
        # ticks per second, up to 1050
        self.robot.m_left.speed_sp = 300
        self.robot.m_right.speed_sp = 300
        # executing commands
        self.robot.m_left.command = "run-to-rel-pos"
        self.robot.m_right.command = "run-to-rel-pos"
        # print(m_left.state.__repr__())
        # giving them time to execute
        while self.robot.m_right.is_running and self.robot.m_left.is_running:
            time.sleep(0.1)

    def bottle_turn(self):
        ev3.Sound.tone([(2500, 200, 100), (2600, 200, 100), (2400, 200)])
        degree = 100
        self.robot.motor_prep()
        # opposite wheel directions are twice as fast
        # 1860 * 2 ticks ~ 360 degree
        # ticks the wheels should to do
        ticks = 1860
        self.robot.m_left.position_sp = (1 / 2 * degree * ticks) / 360
        self.robot.m_right.position_sp = -(1 / 2 * degree * ticks) / 360
        # ticks per second, up to 1050
        self.robot.m_left.speed_sp = self.robot.m_right.speed_sp = 300
        # executing commands
        self.robot.m_left.command = self.robot.m_right.command = "run-to-rel-pos"
        while self.robot.m_right.is_running and self.robot.m_left.is_running:
            time.sleep(0.1)
        # now turn until found line and continue
        r, g, b, _ = self.robot.cs.bin_data("hhhh")
        found_line = self.robot.convert_to_grey(r, g, b)
        # turn again
        self.robot.m_left.position_sp = (1 / 2 * degree * ticks) / 360
        self.robot.m_right.position_sp = -(1 / 2 * degree * ticks) / 360
        self.robot.m_left.speed_sp = self.robot.m_right.speed_sp = 100
        # executing commands
        self.robot.m_left.command = self.robot.m_right.command = "run-to-rel-pos"
        # turn until found black
        while found_line > self.robot.offset:
            r, g, b, _ = self.robot.cs.bin_data("hhhh")
            found_line = self.robot.convert_to_grey(r, g, b)
            time.sleep(0.01)
        # stop it

    # function for calculating the integral
    def calc_int(self, error):
        # add err to integral array
        self.all_err.append(self.k_err * error)
        # check if integral has to many values - sliding window
        if len(self.all_err) > self.i_length:
            # remove the first (first in first out)
            self.all_err.pop(0)
        # calc integral
        integral = sum(self.all_err)
        product = self.k_i * integral
        integral_adjusted = min(max(product, -10), +10)
        return integral_adjusted

    # to change the speed on both wheels
    def speed(self, v_l, v_r):
        # testing speed boundary's and adjusting speed if necessary
        v_l = max(min(v_l, 1000), -1000)
        v_r = max(min(v_r, 1000), -1000)
        # assigning speed
        self.robot.m_left.speed_sp = v_l
        self.robot.m_right.speed_sp = v_r
        # executing commands
        self.robot.m_left.command = "run-forever"
        self.robot.m_right.command = "run-forever"


# matrix multiplication without numpy
def mat_rotate(angle, x, y):
    # rotation matrix
    angle = -angle
    rot = [[math.cos(angle), -math.sin(angle)],
           [math.sin(angle), math.cos(angle)]]

    # coordinate matrix
    coo = [[x],
           [y]]
    # Matrix multiplication.
    x, y = list(
        zip(
            *[
                [
                    sum(a * b
                        for a, b in zip(rot_row, coo_col))
                    for coo_col in zip(*coo)
                ]
                for rot_row in rot
            ]
        )
    )[0]
    return x, y


# calculates Odometry, communicates with mothership, scans Node, calls dijkstra, resets many variables
class Node(State):
    def __init__(self, robot):
        State.__init__(self)
        self.robot = robot
        # Using a synchronized queue to process server messages.
        self.message_queue: SimpleQueue[
            tuple[
                # The message handler.
                Callable[
                    [
                        Union[
                            PlanetRecord, WeightedPathRecord, DirectionRecord,
                            TargetRecord, MessageRecord, Any,
                        ],
                    ],
                    Any,
                ],
                    # The positional arguments to be passed to it.
                tuple,
                    # The keyword arguments to be passed to it.
                dict,
            ]
        ] = SimpleQueue()
        # The corrected information received from server.
        self.corrected_record: Optional[EndRecord] = None
        # The direction to continue driving in.
        self.selected_direction: Optional[Direction] = None
        # for node scanning
        self.lines = []
        # always the compass where the last scanned node hast lines 0 - no, 1 - yes, north, east, south, west
        # north is where Rob is looking before and after the scan
        self.nodes = [False, False, False, False]
        # for turning at the node
        self.north = []
        self.east = []
        self.south = []
        self.west = []
        # true incoming direction
        alpha = 0
        # needed for saving scanned lines after node scan in global directions
        self.alpha = 0
        # just for testing
        self.angles = []

    def run(self):
        # node methods:
        if self.robot.communication is not None:
            # Perform odometry only when needed (starting from second node).
            x, y, direction = self.round_odo()
        else:
            # Set dummy values for communication.
            x, y, direction = 0, 0, 0
        # move Robo to node mid
        self.move_to_position(300, 300, 145, 145)
        self.open_communication(x, y, direction)
        self.alpha = self.corrected_record.endDirection
        # scan for lines
        self.node_scan()
        # calculating where the lines are
        # array: Nord, East, South, West, from the positioning of the robot, not the card yet
        self.degree_to_celestial_direction()
        # Calculate the optimal new path based on current information.
        self.select_path()
        # Check if we are finished.
        self.check_if_finished()
        # Wait 3 seconds for new messages.
        self.handle_messages(timeout=3)
        # Stop reacting to any server message.
        self.close_communication()
        # If we have not received `done` message but still are finished, abort.
        if self.selected_direction is None:
            self.robot.logger.warning("Aborting without `done` message")
            exit(1)

        self.robot.start_record = StartRecord(
            startX=self.corrected_record.endX,
            startY=self.corrected_record.endY,
            startDirection=self.selected_direction,
        )
        # turn to the chosen line to continue
        self.choose_line()
        # print(f'{min(self.robot.odo_motor_positions)=} {max(self.robot.odo_motor_positions)=}')
        # print(f'{len(self.robot.odo_motor_positions)=}')
        # clear motor position array for odo
        self.robot.odo_motor_positions.clear()
        # print(f'{len(self.robot.odo_motor_positions)=}')

        # back to line following
        next_state = Follower(self.robot)
        # calling the switch method of robot class which needs new state as an instance
        self.robot.switch_state(next_state)

    def odometry(self):
        x = 0
        y = 0
        global_direction_change = 0
        for i, (left, right) in enumerate(self.robot.odo_motor_positions[1:]):
            d_l = left - self.robot.odo_motor_positions[i - 1][0]
            d_r = right - self.robot.odo_motor_positions[i - 1][1]
            if d_r == d_l:
                alpha = 0
                s = d_r
            else:
                alpha = (d_r - d_l) / self.robot.a
                s = (d_r + d_l) / alpha * math.sin(alpha / 2)
            x += s * math.sin(global_direction_change + alpha / 2)
            y += s * math.cos(global_direction_change + alpha / 2)
            global_direction_change += alpha
        x = -x * math.pi * 5.6 / 360 / 50
        y = y * math.pi * 5.6 / 360 / 50
        global_direction_change = global_direction_change * 180 / math.pi
        global_direction_change = round(-global_direction_change / 90) * 90
        global_direction_change = opposite(self.robot.start_record.startDirection + global_direction_change)
        x, y = mat_rotate(self.robot.start_record.startDirection * math.pi / 180, x, y)
        x += self.robot.start_record.startX
        y += self.robot.start_record.startY
        return x, y, global_direction_change

    # to round x and y from odometry and using red blue node rule for higher accuracy
    def round_odo(self) -> tuple[int, int, Direction]:
        # calc and get odo values
        # if path blocked -> returned to starting position
        if self.robot.path_blocked:
            x, y, alpha = (self.robot.start_record.startX,
                           self.robot.start_record.startY,
                           self.robot.start_record.startDirection)
        else:
            x, y, alpha = self.odometry()
            # Better rounding using the node colors.
            rounding_methods = (math.ceil, math.floor)
            _, (x, y) = min(
                map(
                    lambda point: (
                        math.sqrt(
                            (point[0] - x)**2
                            + (point[1] - y)**2
                        ),
                        point,
                    ),
                    filter(
                        lambda point: (
                            (-1)**(
                                point[0] - self.robot.start_record.startX
                                + point[1] - self.robot.start_record.startY
                            ) == int(
                                ((self.robot.current_node_colour
                                    == self.robot.last_node_colour)
                                    - 0.5)
                                * 2
                            )
                        ),
                        [
                            (x_method(x), y_method(y))
                            for x_method in rounding_methods
                            for y_method in rounding_methods
                        ]
                    )
                )
            )

        return x, y, alpha

    # move to position
    def move_to_position(self, v_l, v_r, s_l, s_r):
        self.robot.motor_prep()
        # try to get into the mit of the node
        # to align the colour sensor
        self.robot.m_left.position_sp = s_l
        self.robot.m_right.position_sp = s_r
        # ticks per second, up to 1050
        self.robot.m_left.speed_sp = v_l
        self.robot.m_right.speed_sp = v_r
        # executing commands
        self.robot.m_left.command = "run-to-rel-pos"
        self.robot.m_right.command = "run-to-rel-pos"
        while self.robot.m_right.is_running and self.robot.m_left.is_running:
            time.sleep(0.01)

    # function for scanning the node and noting motor position if black is found
    def node_scan(self):
        # print("Scanning for lines")
        # motor prep so the position attribute from the motors is exact
        self.robot.motor_prep()
        # 1860 * 2 ticks ~ 360 degree
        # opposite wheel directions are twice as fast
        ticks = 1840
        # ticks the wheels should to do
        self.robot.m_left.position_sp = -1 / 2 * ticks
        self.robot.m_right.position_sp = 1 / 2 * ticks
        # ticks per second, up to 1050
        self.robot.m_left.speed_sp = 400
        self.robot.m_right.speed_sp = 400
        # executing commands
        self.robot.m_left.command = "run-to-rel-pos"
        self.robot.m_right.command = "run-to-rel-pos"
        # giving them time to execute
        while self.robot.m_right.is_running and self.robot.m_left.is_running:
            r, g, b, _ = self.robot.cs.bin_data("hhhh")
            # should continue if he found the line again
            found_line = self.robot.convert_to_grey(r, g, b)
            if found_line < self.robot.offset:
                # print(f'{self.robot.m_right.position}')
                self.lines.append(self.robot.m_right.position)

    # function to turn the motor.position into a compass
    def degree_to_celestial_direction(self):
        # the motor position starts at 0 and after the scan it has 1000
        # if line found, then position gets noted in lines
        # idea: make 4 intervals and if at least one value is in it, there is a line
        # set all from previous node to false
        # whole thing needs to rotate for self.alpha + 180
        for x in self.lines:
            if x < 150:
                # north
                self.north.append(x)
                self.nodes[0] = True
            elif x < 380:
                # west
                self.west.append(x)
                self.nodes[3] = True
            elif x < 610:
                # south
                self.south.append(x)
                self.nodes[2] = True
            elif x < 840:
                # east
                self.east.append(x)
                self.nodes[1] = True
            elif x < 950:
                # north
                self.north.append(x)
                self.nodes[0] = True
        # says how many intervals we need to rotate, for example if incoming at west 270 its looking to the east before
        # and after scanning that's 90, and it needs to rotate 1 interval, that is from east to north
        swap = -int(((self.alpha - 180) % 360) / 90)
        # swap all values 1 interval in contrary to clock direction every iteration
        if swap > 0:
            for i in range(swap):
                self.north, self.east, self.south, self.west = self.east, self.south, self.west, self.north
                # same for where the lines are
                self.nodes[0], self.nodes[3], self.nodes[2], self.nodes[1] = (
                    self.nodes[3], self.nodes[2], self.nodes[1],
                    self.nodes[0])
        elif swap < 0:
            for i in range(0, swap, -1):
                self.north, self.west, self.south, self.east = self.west, self.south, self.east, self.north
                # same for where the lines are
                self.nodes[0], self.nodes[3], self.nodes[2], self.nodes[1] = (
                    self.nodes[3], self.nodes[2], self.nodes[1],
                    self.nodes[0])

    # so Rob can choose a line to continue from Node and move in position there
    def choose_line(self):
        line = self.selected_direction
        # getting the first motor position of the lane - that's the one on the left side
        if line == 0:
            # for Odometry, so we can calculate the end cardinal direction
            position = self.north[0]
        elif line == 90:
            position = self.east[0]
        elif line == 180:
            position = self.south[0]
        else:
            position = self.west[0]
        # turn to the path
        if (self.robot.m_right.position - position) < position:
            self.mp_turn(-self.robot.m_right.position + position + 30)
        else:
            self.mp_turn(position)

    # basic turn function with degrees
    def mp_turn(self, motor_position):
        # for good measures
        self.robot.motor_prep()
        self.robot.m_left.position_sp = -motor_position
        self.robot.m_right.position_sp = motor_position
        # ticks per second, up to 1050
        self.robot.m_left.speed_sp = 400
        self.robot.m_right.speed_sp = 400
        # executing commands
        self.robot.m_left.command = "run-to-rel-pos"
        self.robot.m_right.command = "run-to-rel-pos"
        # giving them time to execute
        while self.robot.m_right.is_running and self.robot.m_left.is_running:
            time.sleep(0.1)

    def open_communication(self, x: int, y: int, direction: Direction) -> None:
        """Set up message handlers and send required information.

        At the first node, set up communication and submit
        `ClientMessageType.READY` message, at all other nodes send
        `ClientMessageType.PATH` message including current estimated
        node information.
        """

        # A function to ensure each new message is enqueued with the
        # appropriate handler for synchronous processing.
        def handler_enqueuer(handler):
            def enqueue(*args, **kwargs):
                # Enqueue the handler with its desired arguments for
                # later synchronous execution.
                self.message_queue.put((handler, args, kwargs))

            return enqueue

        # Create a message handler registry, where each handler is
        # decorated with `handler_enqueuer` in order to enqueue the
        # handler including its arguments on each message.
        message_handlers = {
            msg_type: handler_enqueuer(handler)
            for msg_type, handler in {
                ServerMessageType.PLANET: self._handle_planet_message,
                ServerMessageType.PATH: self._handle_path_message,
                ServerMessageType.PATH_SELECT: self._handle_path_select_message,
                ServerMessageType.PATH_UNVEILED: self._handle_path_unveiled_message,
                ServerMessageType.DONE: self._handle_done_message,
                ServerMessageType.TARGET: self._handle_target_message,
            }.items()
        }

        if self.robot.communication is None:
            # First supply station.
            # Communication initialization.
            self.robot.communication = Communication(
                self.robot.client,
                self.robot.logger,
            )
            self.robot.communication.message_handlers = message_handlers
            self.robot.communication.send_message_type(ClientMessageType.READY)
        else:
            self.robot.communication.message_handlers = message_handlers
            self.robot.communication.send_message_type(
                ClientMessageType.PATH,
                PathRecord(
                    **asdict(self.robot.start_record),
                    endX=int(x),
                    endY=int(y),
                    endDirection=int(direction),
                    pathStatus=(
                        PathStatus.BLOCKED
                        if self.robot.path_blocked
                        else PathStatus.FREE
                    ),
                ),
            )

        # Handle initial bunch of messages to receive `path` or `planet`
        # messages.
        self.corrected_record = None
        while self.corrected_record is None:
            self.handle_messages(timeout=0.5)

    def handle_messages(self, timeout: float = 0) -> None:
        """Wait at most `timeout` seconds for new messages and handle them."""
        try:
            while True:
                handler, args, kwargs = self.message_queue.get(
                    block=True,
                    timeout=timeout,
                )
                handler(*args, **kwargs)
        except Empty:
            # `timeout` reached and no message arrived, finished.
            return

    def close_communication(self) -> None:
        """Stop handling messages."""
        self.robot.communication.message_handlers = {}
        # TODO: Signal end of communication in some way.
        ev3.Sound.tone([(200, 100, 100), (500, 200)])

    def _handle_planet_message(self, planet_record: PlanetRecord) -> None:
        self.corrected_record = EndRecord(
            endX=planet_record.startX,
            endY=planet_record.startY,
            # `startOrientation` is the direction where the robot currently
            # is looking to, but `endDirection` is the direction the path
            # we came from goes to, so save the opposite direction.
            endDirection=opposite(planet_record.startOrientation),
        )
        # The path we came from is most likely not to be used again in
        # the other direction, so mark it as blocked.
        origin = (
            (self.corrected_record.endX, self.corrected_record.endY),
            self.corrected_record.endDirection,
        )
        self.robot.planet.add_path(origin, origin, BLOCKED)

    def _handle_path_message(
            self,
            weighted_path_record: WeightedPathRecord,
    ) -> None:
        self.corrected_record = EndRecord(
            endX=weighted_path_record.endX,
            endY=weighted_path_record.endY,
            endDirection=weighted_path_record.endDirection,
        )
        self._handle_path_unveiled_message(weighted_path_record)

    def _handle_path_select_message(
            self,
            direction_record: DirectionRecord,
    ) -> None:
        self.selected_direction = direction_record.startDirection

    def _handle_path_unveiled_message(
            self,
            weighted_path_record: WeightedPathRecord,
    ) -> None:
        self.robot.planet.add_path(
            (
                (weighted_path_record.startX, weighted_path_record.startY),
                weighted_path_record.startDirection,
            ),
            (
                (weighted_path_record.endX, weighted_path_record.endY),
                weighted_path_record.endDirection,
            ),
            weighted_path_record.pathWeight,
        )

    def _handle_target_message(self, target_record: TargetRecord) -> None:
        self.robot.target = (target_record.targetX, target_record.targetY)

    def _handle_done_message(self, message_record: MessageRecord) -> None:
        self.close_communication()
        ev3.Sound.tone([(500, 200, 100), (700, 200, 100), (1000, 200, 100), (1200, 200, 100)])
        time.sleep(1)
        exit()

    def select_path(self) -> None:
        """Use `planet` to calculate the best new path."""
        # Add the available directions of current node.
        self.robot.planet.set_available_node_directions(
            (self.corrected_record.endX, self.corrected_record.endY),
            {
                direction
                for direction, available in zip(Direction, self.nodes)
                if available
            },
        )
        self.selected_direction = self.robot.planet.next_direction(
            (self.corrected_record.endX, self.corrected_record.endY),
            self.robot.target,
        )
        if self.selected_direction is None:
            # No path selected, probably finished.
            return

        # Publish selected path.
        self.robot.communication.send_message_type(
            ClientMessageType.PATH_SELECT,
            StartRecord(
                startX=int(self.corrected_record.endX),
                startY=int(self.corrected_record.endY),
                startDirection=int(self.selected_direction),
            )
        )

    def check_if_finished(self) -> None:
        """Check if exploration is completed or our target reached."""
        if ((self.corrected_record.endX, self.corrected_record.endY)
                == self.robot.target):
            # Target reached, publishing that.
            self.robot.communication.send_message_type(
                ClientMessageType.TARGET_REACHED,
                MessageRecord(message="I have reached my destination!"),
            )
        elif self.selected_direction is None:
            # Exploration completed, publish accordingly.
            self.robot.communication.send_message_type(
                ClientMessageType.EXPLORATION_COMPLETED,
                MessageRecord(message="Planet fully discovered!"),
            )
