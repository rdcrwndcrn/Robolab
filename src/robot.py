from typing import Any, Callable, Union
from ev3dev import ev3
import math
from functools import wraps
from logging import Logger
from queue import SimpleQueue, Empty
import time

from paho.mqtt.client import Client

from communication import (
    ClientMessageType, Communication, DirectionRecord, MessageRecord,
    PlanetRecord, ServerMessageType, TargetRecord, WeightedPathRecord,
)


# class to switch between States
class Robot:
    def __init__(self, client: Client, logger: Logger):
        self.client = client
        self.logger = logger
        # Communication is initialized at first node.
        self.communication = None
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
        self.a = (7.6 * 360) / (3.2 * math.pi)
        # for rounding
        self.current_node_colour = ''
        self.last_node_colour = ''
        # for calculating the entry global compass direction
        self.start_compass = 0
        # if path is blocked odo does not need to calc anything
        self.path_blocked = False

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

    def run(self):
        # running Colour calibration methods
        print("starting ColourCalibration")
        # hardcoded for faster testing, will be deleted for exam
        self.robot.colors['black'] = [46.38, 45.25, 11.16]
        self.robot.colors['white'] = [280.72, 273.67, 95.07]
        # measuring colour and saving them in dict
        # self.measure_colours()
        # calc offset for PID
        self.calc_off()
        # for Odo
        self.robot.motor_prep()

        # switch to the follower state by creating follower instance
        # uses robot instance which lies in the robot attribute in Metaclass
        next_state = Follower(self.robot)
        # calling the switch method of robot class which needs new state as an instance
        self.robot.switch_state(next_state)

    # colour calibration with robo buttons and display, for calc offset - TODO not really working, values inputs
    #  there, but display does not show anything
    def measure_colours(self):
        for x in self.robot.calibrated_colors:
            # to wait for a button input
            input(f'Press enter to read {x}')

            '''
            while True:
                # so we cant forget which colour we start with
                self.screen.draw.text((0, 0), f'Press any button to read {x}')
                self.screen.update()
                if self.btn.any():
                    # so it won't detect one input as two and measure black and white at the same spot
                    time.sleep(1)
                    break
                    '''
            # getting and saving rgb-values
            self.robot.colors[x] = self.calibration()
            print(self.robot.colors[x])

        # telling us that everything worked
        self.screen.draw.text((0, 0), f'Im ready. Put me on!')
        self.screen.update()

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
        self.t_p = 400
        # declaring proportional gain
        self.k_p = 6 * 10 ** -1
        # integral gain
        self.k_i = 6 * 10 ** -1
        # second I controller for going slower in slopes
        self.ki = 30
        # derivative gain
        self.k_d = 2 * 10 ** -1
        # 40,92 ms per loop -> 1s has ~24,5 iterations
        # 60 iterations ~ 2,5 s
        self.i_length = 60
        # for summing up the error, hence integral
        self.all_err = []
        # constant to shrink error in interval
        self.k_err = 0.004
        # for calc the derivative
        self.last_err = 0
        # counter for iterations in while
        self.i = 0
        # counter for getting node colours
        self.c = 0

    def run(self):
        # line following loop
        self.robot.path_blocked = False
        input("to start Follower press enter")
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
                    self.turn(175)
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
                # just for testing
                # if self.i % 17 == 0:
                #    print(f' {new_speed_right=} {new_speed_left=}')
                #    print(f'{turns=} {self.k_p*err=} {self.k_i*integral=} {integral=} {self.ki*integral=}')
                self.last_err = err
                # print(f'actual value: {grey}')
                # print(f'right {new_speed_right} left {new_speed_left}')
                # print()
                # reset counters every 17 iteration, to differentiate blue nodes and "blueish" points on paths
                if self.i % 17 == 0:
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
            # print(f'found red node: {r, g, b}, c = {self.c}')
            self.c += 1
            if self.c > 2:
                # reset motor position of each motor for odo and to stop
                self.robot.motor_prep()
                # self.turn(7)
                # save colour for odo
                print('found red node')
                # saving last node colour before overwriting curren node colour
                self.robot.last_node_colour = self.robot.current_node_colour
                # overwriting current node colour for odo
                self.robot.current_node_colour = 'red'
                # calling the switch method of robot class which needs new state as an instance
                self.robot.switch_state(next_state)
        elif 1.9 * b - 0.9 * r > 40:
            self.c += 1
            # print(f'found blue node: {r, g, b}, c = {self.c}')
            if self.c > 2:
                # reset motor position of each motor for odo and to stop
                self.robot.motor_prep()
                # self.turn(4)
                # save colour for odo
                print('found red node')
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
        # just for testing
        # if self.i % 17 == 0:
        #    print(f'{self.i}th {integral=}')
        # that means an additional difference of 20 ticks, before k_i
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


# just for testing
def histogram(values, count_bin=10):
    min_value = min(values)
    max_value = max(values)
    bin_width = (max_value - min_value) / count_bin
    bin_width = [min_value + i * bin_width for i in range(count_bin + 1)]
    bins = [0] * count_bin
    for value in values:
        bin_index = int((value - min_value) / bin_width)
        if bin_index == count_bin:
            bin_index -= 1
        bins[bin_index] += 1
    for b, count in zip(bin_width, bins):
        print(b, count)


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
                        ]
                    ],
                    Any,
                ],
                # The positional arguments to be passed to it.
                tuple,
                # The keyword arguments to be passed to it.
                dict,
            ]
        ] = SimpleQueue()
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
        self.compass = 0
        # needed for saving scanned lines after node scan in global directions
        self.alpha = 0
        # just for testing
        self.angles = []

    def run(self):
        print("starting node state")
        # node methods:
        # odometry
        self.round_odo()
        # move Robo to node mid
        self.move_to_position(350, 350, 240, 240)
        self.open_communication()
        # just for testing
        # interval = self.i_length
        # k_i = self.k_i
        # ki = self.ki
        # t_p = self.t_p
        # self.i_length = float(input(f'{interval=} Enter new interval length '))
        # self.k_i = float(input(f'{k_i=} Enter new k_i value ')) * 10 ** -1
        # self.ki = float(input(f'{ki=} Enter new ki value ')) * 10 ** 0
        # self.t_p = float(input(f'{t_p=} Enter new t_p value '))
        # scan for lines
        self.node_scan()
        # calculating where the lines are
        # array: Nord, East, South, West, from the positioning of the robot, not the card yet
        self.degree_to_celestial_direction()
        # turn to the chosen line to continue
        self.choose_line()
        # print(f'{min(self.robot.odo_motor_positions)=} {max(self.robot.odo_motor_positions)=}')
        # print(f'{len(self.robot.odo_motor_positions)=}')
        # clear motor position array for odo
        self.robot.odo_motor_positions.clear()
        # print(f'{len(self.robot.odo_motor_positions)=}')

        # Stop reacting to any server message.
        self.close_communication()

        # back to line following
        next_state = Follower(self.robot)
        # calling the switch method of robot class which needs new state as an instance
        self.robot.switch_state(next_state)

    def odometry(self):
        x = 0
        y = 0
        global_direction_change = 0
        # just for debugging
        angles = []
        for i, (left, right) in enumerate(self.robot.odo_motor_positions[1:]):
            d_l = left - self.robot.odo_motor_positions[i - 1][0]
            d_r = right - self.robot.odo_motor_positions[i - 1][1]
            if d_r == d_l:
                alpha = 0
                s = d_r
            else:
                alpha = (d_r - d_l) / self.robot.a
                s = (d_r + d_l) / alpha * math.sin(alpha / 2)
            angles.append(alpha)
            x += s * math.sin(global_direction_change + alpha / 2)
            y += s * math.cos(global_direction_change + alpha / 2)
            global_direction_change += alpha
        # just for debugging
        # histogram(angles)
        return x, y, global_direction_change

    # to round x and y from odometry and using red blue node rule for higher accuracy
    def round_odo(self):
        # calc and get odo values
        x, y, alpha = self.odometry()
        # converting scale to cm and degree
        alpha = alpha * 180 / math.pi
        x = x / 360 * 3.2 * math.pi
        y = y / 360 * 3.2 * math.pi
        print(f'before correction {x=}, {y=}, alpha={alpha}')
        # drove orthogonal that means one coordinate is zero, probably the smaller one
        if (self.robot.last_node_colour == 'blue' and self.robot.current_node_colour == 'red' or
                self.robot.last_node_colour == 'red' and self.robot.current_node_colour == 'blue'):
            if x > y:
                print(f'we drove orthogonal, rounding one value to zero...')
                y = 0
            else:
                x = 0
        x = round(x / 50) * 50
        y = round(y / 50) * 50
        alpha = round(alpha / 90) * 90
        # saving it for correcting line scan to global coordinates
        self.alpha = alpha
        # 0 for north, 90 for east, 180 for south 270 for west TODO add connection to communication
        # start angle plus angle we drove plus correction because otherwise we would get the angle where robo is looking
        # after he found the next node, but we need the incoming direction global compass thingy angle
        self.compass = (self.robot.start_compass + alpha + 180) % 360  # cyclic group
        print(f'{x=} {y=} {self.compass=}')

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
        self.robot.m_left.speed_sp = 250
        self.robot.m_right.speed_sp = 250
        # executing commands
        self.robot.m_left.command = "run-to-rel-pos"
        self.robot.m_right.command = "run-to-rel-pos"
        # giving them time to execute
        while self.robot.m_right.is_running and self.robot.m_left.is_running:
            r, g, b, _ = self.robot.cs.bin_data("hhhh")
            # should continue if he found the line again
            found_line = self.robot.convert_to_grey(r, g, b)
            if found_line < self.robot.offset:
                # print(f'{found_line=}')
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
        swap = int((self.alpha % 360) / 90)
        print(f'{swap=}')
        print(f'{self.nodes=}')
        print(f'{self.north=} {self.east=} {self.south=} {self.west=}')
        # swap all values 1 interval in contrary to clock direction every iteration
        for i in range(swap):
            self.north, self.east, self.south, self.west = self.east, self.south, self.west, self.north
            # same for where the lines are
            self.nodes[0], self.nodes[1], self.nodes[2], self.nodes[3] = (self.nodes[1], self.nodes[2], self.nodes[3],
                                                                          self.nodes[0])
        print(f'{self.nodes=}')  # TODO add connection to planet

    # so Rob can choose a line to continue from Node and move in position there
    def choose_line(self):
        # for knowing which one to continue on - 0 for north, 1 for east, 2 for south, 3 for west
        line = int(input('Choose the path: 0 for north, 90 for east, 180 for south, 270 for west'))
        # TODO - add connection to Planet
        # getting the first motor position of the lane - that's the one on the left side
        if line == 0:
            # for Odometry so we can calculate the end cardinal direction
            self.robot.start_compass = 0
            position = self.north[0]
        elif line == 90:
            self.robot.start_compass = 90
            position = self.east[0]
        elif line == 180:
            self.robot.start_compass = 180
            position = self.south[0]
        else:
            self.robot.start_compass = 270
            position = self.west[0]
        # turn to the path
        self.mp_turn(position)

    # basic turn function with degrees
    def mp_turn(self, motor_position):
        # for good measures
        self.robot.motor_prep()
        self.robot.m_left.position_sp = -motor_position
        self.robot.m_right.position_sp = motor_position
        # ticks per second, up to 1050
        self.robot.m_left.speed_sp = 300
        self.robot.m_right.speed_sp = 300
        # executing commands
        self.robot.m_left.command = "run-to-rel-pos"
        self.robot.m_right.command = "run-to-rel-pos"
        # giving them time to execute
        while self.robot.m_right.is_running and self.robot.m_left.is_running:
            time.sleep(0.1)

    def open_communication(self) -> None:
        """Set up message handlers, send and set communication timeout.

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
            # TODO: Publish path message.

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

    def _handle_planet_message(self, planet_record: PlanetRecord) -> None:
        # TODO: Set start coordinates and direction.
        pass

    def _handle_path_message(self, weighted_path_record: WeightedPathRecord) -> None:
        pass

    def _handle_path_select_message(self, direction_record: DirectionRecord) -> None:
        pass

    def _handle_path_unveiled_message(self, weighted_path_record: WeightedPathRecord) -> None:
        pass

    def _handle_target_message(self, target_record: TargetRecord) -> None:
        pass

    def _handle_done_message(self, message_record: MessageRecord) -> None:
        pass
