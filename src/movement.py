from functools import wraps
from math import pi, sin, cos
from time import sleep, monotonic_ns

from ev3dev import ev3

from communication import (
    ClientMessageType, Communication, DirectionRecord, MessageRecord,
    PlanetRecord, ServerMessageType, TargetRecord, WeightedPathRecord,
)


class Robot:

    def __init__(self, client, logger):
        self.client = client
        self.logger = logger
        # Communication can only start at the first supply station.
        # The value `None` implies no supply station has been reached so
        # far and is changed at the first node.
        self.communication = None
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
        # initialising t_p, well use it with the meaning of x per mile of the possible wheel speed
        self.t_p = 400

        # for node scanning
        self.lines = []
        # always the compass where the last scanned node hast lines 0 - no, 1 - yes, north, east, south, west
        # north is where Rob is looking before and after the scan
        self.nodes = [False, False, False, False]

        # for PID
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

        # Odometrie
        # list for motor positions
        self.odo_motor_positions = []
        # wheels distance 7,6 cm in ticks
        self.a = (7.6 * 360) / (3.2 * math.pi)

        # for turning at the node
        self.north = []
        self.east = []
        self.south = []
        self.west = []

    '''all 3 states are defined in the following 3 methods'''

    # function to get all colour values and start line following
    def start_state(self):
        # hardcoded for faster testing, will be deleted for exam
        self.colors['black'] = [19.23, 22.58, 6.13]
        self.colors['white'] = [240.02, 258.32, 82.18]

        # measuring colour and saving them in dict
        self.measure_colours()
        # calc offset for PID
        self.calc_off()
        # start driving
        self.follower_state()
        # for Odo
        self.motor_prep()

    # scan while turning back to the start position and save it into an array
    def node_state(self):
        # calc odometry
        # x, y, alpha = self.odometry()
        # norming odo
        # alpha = alpha * 180 / math.pi
        # x = x / 360 * 3.2 * math.pi
        # y = y / 360 * 3.2 * math.pi
        # print(f'{x=}, {y=}, {alpha=}')
        # reset counter
        self.c = 0
        # move Robo to node mid
        self.move_to_position(400, 400, 240, 240)
        # scan
        # TODO just for testing - remove
        # interval = self.i_length
        # k_i = self.k_i
        # ki = self.ki
        # t_p = self.t_p
        # self.i_length = float(input(f'{interval=} Enter new interval length '))
        # self.k_i = float(input(f'{k_i=} Enter new k_i value ')) * 10 ** -1
        # self.ki = float(input(f'{ki=} Enter new ki value ')) * 10 ** 0
        # self.t_p = float(input(f'{t_p=} Enter new t_p value '))
        self.node_scan()
        # calculating where the lines are
        # array: Nord, East, South, West, from the positioning of the robot, not the card yet
        self.degree_to_celestial_direction()
        # Wait for communication end
        self.wait_for_communication_timeout()
        # turn to the chosen line to continue
        self.choose_line()
        # continue following
        self.follower_state()
        # clear motor position array for odo
        self.odo_motor_positions.clear()
        # reset error sum/integral for I
        self.all_err = []
        # reset motor positions for turns
        self.north = []
        self.east = []
        self.south = []
        self.west = []

    def follower_state(self):
        input("Press enter to start")

        try:
            while True:
                # turn if bottle is less than 150 mm before Rob
                if self.us.value() < 150:
                    self.turn(175)
                # get rgb values for the iteration we are in
                r, g, b, _ = self.cs.bin_data("hhhh")
                # check if Rob over red or blue
                self.check_for_node(r, g, b)
                # converting to greyscale / 2.55 to norm it from 0 to 100
                grey = self.convert_to_grey(r, g, b)
                # calculating error
                err = grey - self.offset
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
                # for testing TODO remove
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
                self.odo_motor_positions.append((self.m_left.position, self.m_right.position))
        finally:
            self.motor_prep()
            print('aborting ...')

    '''functions below this are only helping the first two function'''

    # eliminate short period deviation in colour sensor
    # to help with measuring the colors in the colors dict
    def calibration(self):
        # average rgb
        avg_r = 0
        avg_g = 0
        avg_b = 0
        # measuring 100 times
        for i in range(100):
            red, green, blue, _ = self.cs.bin_data("hhhh")
            avg_r += red
            avg_g += green
            avg_b += blue
        avg_r /= 100
        avg_g /= 100
        avg_b /= 100
        return [avg_r, avg_g, avg_b]

    # rgb to grey
    # after greyscale model optimised for human eyes
    @staticmethod
    def convert_to_grey(r, g, b):
        return 0.3 * r + 0.59 * g + 0.11 * b

    # check if colour sensor is over red or blue
    def check_for_node(self, r, g, b):
        if r > 5 * b and r > 3 * g:
            # print(f'found red node: {r, g, b}, c = {self.c}')
            self.c += 1
            if self.c > 1:
                # reset motor position of each motor for odo and to stop
                self.motor_prep()
                # self.turn(7)
                self.node_state()
        elif 1.9 * b - 0.9 * r > 40:
            self.c += 1
            # print(f'found blue node: {r, g, b}, c = {self.c}')
            if self.c > 1:
                # reset motor position of each motor for odo and to stop
                self.motor_prep()
                self.turn(4)
                self.node_state()

    # colour calibration function
    def measure_colours(self):
        for x in self.calibrated_colors:
            # wait, so we can move Robo and know which colour is next - TODO change input to button on ev3 brick
            # input(f"Press enter to read {x}.")
            # getting and saving rgb-values
            self.colors[x] = self.calibration()
            print(self.colors[x])

    # for calculating the offset
    def calc_off(self):
        # colour calc to calc the error and use that for PID
        # converting white and black to greyscale / 2.55 to norm it from 0 to 100
        white_grey = self.convert_to_grey(self.colors['white'][0], self.colors['white'][1], self.colors['white'][2])
        black_grey = self.convert_to_grey(self.colors['black'][0], self.colors['black'][1], self.colors['black'][2])
        # calculating offset
        self.offset = (white_grey + black_grey) / 2

    def motor_prep(self):
        self.m_left.reset()
        self.m_right.reset()
        self.m_left.stop_action = "brake"
        self.m_right.stop_action = "brake"
        sleep(0.1)

    # to change the speed on both wheels
    def speed(self, v_l, v_r):
        # testing speed boundary's and adjusting speed if necessary
        v_l = max(min(v_l, 1000), -1000)
        v_r = max(min(v_r, 1000), -1000)
        # assigning speed
        self.m_left.speed_sp = v_l
        self.m_right.speed_sp = v_r
        # executing commands
        self.m_left.command = "run-forever"
        self.m_right.command = "run-forever"

    # move to position
    def move_to_position(self, v_l, v_r, s_l, s_r):
        self.motor_prep()
        # try to get into the mit of the node
        # to align the colour sensor
        self.m_left.position_sp = s_l
        self.m_right.position_sp = s_r
        # ticks per second, up to 1050
        self.m_left.speed_sp = v_l
        self.m_right.speed_sp = v_r
        # executing commands
        self.m_left.command = "run-to-rel-pos"
        self.m_right.command = "run-to-rel-pos"
        while self.m_right.is_running and self.m_left.is_running:
            time.sleep(0.01)

    # so Rob can choose a line to continue from Node and move in position there
    def choose_line(self):
        # for knowing which one to continue on - 0 for north, 1 for east, 2 for south, 3 for west
        line = int(input('Choose the path: 0 for north, 1 for east, 2 for south, 3 for west '))
        # TODO - add connection to Planet
        # getting the first motor position of the lane - that's the one on the left side
        if line == 0:
            position = self.north[0]
        elif line == 1:
            position = self.east[0]
        elif line == 2:
            position = self.south[0]
        else:
            position = self.west[0]
        # turn to the path
        # print(f'position: {position}')
        self.mp_turn(position)
        # follow it
        self.follower_state()

    # basic turn function with degrees
    def turn(self, degree):
        self.motor_prep()
        # opposite wheel directions are twice as fast
        # 1860 * 2 ticks ~ 360 degree
        # ticks the wheels should to do
        ticks = 1860
        self.m_left.position_sp = (1 / 2 * degree * ticks) / 360
        self.m_right.position_sp = -(1 / 2 * degree * ticks) / 360
        # ticks per second, up to 1050
        self.m_left.speed_sp = 300
        self.m_right.speed_sp = 300
        # executing commands
        self.m_left.command = "run-to-rel-pos"
        self.m_right.command = "run-to-rel-pos"
        # print(m_left.state.__repr__())
        # giving them time to execute
        while self.m_right.is_running and self.m_left.is_running:
            self.odo_motor_positions.append((self.m_left.position, self.m_right.position))
            sleep(0.1)
            # should continue if he found the line again
            # found_line = 0.3 * cs.raw[0] + 0.59 * cs.raw[1] + 0.11 * cs.raw[2]
            # if found_line > offset:
            #    break

    # basic turn function with degrees
    def mp_turn(self, motor_position):
        # for good measures
        self.motor_prep()
        self.m_left.position_sp = motor_position
        self.m_right.position_sp = - motor_position
        # ticks per second, up to 1050
        self.m_left.speed_sp = 300
        self.m_right.speed_sp = 300
        # executing commands
        self.m_left.command = "run-to-rel-pos"
        self.m_right.command = "run-to-rel-pos"
        # giving them time to execute
        while self.m_right.is_running and self.m_left.is_running:
            self.odo_motor_positions.append((self.m_left.position, self.m_right.position))
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
        if self.i % 17 == 0:  # TODO remove
            print(f'{self.i}th {integral=}')
        # that means an additional difference of 20 ticks, before k_i
        integral_adjusted = min(max(product, -10), +10)
        return integral_adjusted

    # function for scanning the node and noting motor position if black is found
    def node_scan(self):
        # print("Scanning for lines")
        # motor prep so the position attribute from the motors is exact
        self.motor_prep()
        # 1860 * 2 ticks ~ 360 degree
        # opposite wheel directions are twice as fast
        ticks = 1840
        # ticks the wheels should to do
        self.m_left.position_sp = 1 / 2 * ticks
        self.m_right.position_sp = -1 / 2 * ticks
        # ticks per second, up to 1050
        self.m_left.speed_sp = 220
        self.m_right.speed_sp = 220
        # executing commands
        self.m_left.command = "run-to-rel-pos"
        self.m_right.command = "run-to-rel-pos"
        # giving them time to execute
        while 'running' in self.m_left.state or 'running' in self.m_right.state:
            time.sleep(0.005)
            r, g, b, _ = self.cs.bin_data("hhhh")
            # should continue if he found the line again
            found_line = self.convert_to_grey(r, g, b)
            if found_line > self.offset:  # TODO change > to < if line black
                # print(f'{found_line=}')
                self.lines.append(self.m_left.position)  # TODO change it to degrees with Odometrie

    # function to turn the motor.position into a compass
    def degree_to_celestial_direction(self):
        # the motor position starts at 0 and after the scan it has 1000
        # if line found, then position gets noted in lines
        # idea: make 4 intervals and if at least one value is in it, there is a line
        # set all from previous node to false
        # print(f'lines found on position: {self.lines}')  # TODO change to global compass Odometrie
        for x in range(4):
            self.nodes[x] = False
        for x in self.lines:
            if x < 150:
                # north
                self.north.append(x)
                self.nodes[0] = True
            elif x < 380:
                # east
                self.east.append(x)
                self.nodes[1] = True
            elif x < 610:
                # south
                self.south.append(x)
                self.nodes[2] = True
            elif x < 840:
                # west
                self.west.append(x)
                self.nodes[3] = True
            elif x < 950:
                # north
                self.north.append(x)
                self.nodes[0] = True
        # print(f'{self.lines=}')
        # print('<150 = north, <380 = east, <610 = south, <840 = west>')
        # print(f'{self.north=} {self.east=} {self.south=} {self.west=}')
        print(f'{self.nodes=}')
        # clear list for next node
        self.lines.clear()

    def odometry(self):
        x = 0
        y = 0
        global_direction_change = 0
        for i, (left, right) in enumerate(self.odo_motor_positions[1:]):
            d_l = left - self.odo_motor_positions[i - 1][0]
            d_r = right - self.odo_motor_positions[i - 1][1]
            if d_r == d_l:
                alpha = 0
                s = d_r
            else:
                alpha = (d_r - d_l) / self.a
                s = (d_r + d_l) / alpha * sin(alpha / 2)
            x += s * sin(alpha / 2 + global_direction_change)
            y += s * cos(alpha / 2 + global_direction_change)
            global_direction_change += alpha
        return x, y, global_direction_change

    def open_communication(self):
        """Set up message handlers, send and set communication timeout.

        At the first node, set up communication and submit
        `ClientMessageType.READY` message, at all other nodes send
        `ClientMessageType.PATH` message including current estimated
        node information.
        """
        # A wrapper to ensure `self.reset_communication_timeout` is called
        # at the arrival of any new message.
        def timeout_wrapper(handler):
            # This decorator makes the wrapper look like the wrapped function
            # for better error messages.
            @wraps(handler)
            def timeout_wrapped(*args, **kwargs):
                self.reset_communication_timeout()
                return handler(*args, **kwargs)
            return timeout_wrapped

        # Create a message handler registry, where each handler is
        # decorated with `timeout_wrapper` in order to reset the
        # communication timeout on each message.
        message_handlers = {
            msg_type: timeout_wrapper(handler)
            for msg_type, handler in {
                ServerMessageType.PLANET: self._handle_planet_message,
                ServerMessageType.PATH: self._handle_path_message,
                ServerMessageType.PATH_SELECT: self._handle_path_select_message,
                ServerMessageType.PATH_UNVEILED: self._handle_path_unveiled_message,
                ServerMessageType.DONE: self._handle_done_message,
                ServerMessageType.TARGET: self._handle_target_message,
            }.items()
        }

        if self.communication is None:
            # First supply station.
            # Communication initialization.
            self.communication = Communication(self.client, self.logger)
            self.communication.message_handlers = message_handlers
            self.communication.send_message_type(ClientMessageType.READY)
        else:
            self.communication.message_handlers = message_handlers
            # TODO: Publish path message.

        # Start timeout.
        self.reset_communication_timeout()

    def reset_communication_timeout(self):
        """Set a 3 second timeout signalling the communication end."""
        self.timeout = monotonic_ns() + 3_000_000    # + 3 s

    def wait_for_communication_timeout(self):
        """Wait until `self.timeout` is reached and reset message handlers."""
        while monotonic_ns() < self.timeout:
            sleep(0.1)

        # Stop handling messages.
        self.communication.message_handlers = {}

    def _handle_planet_message(self, planet_record: PlanetRecord):
        # TODO: Set start coordinates and direction.
        pass

    def _handle_path_message(self, weighted_path_record: WeightedPathRecord):
        pass

    def _handle_path_select_message(self, direction_record: DirectionRecord):
        pass

    def _handle_path_unveiled_message(self, weighted_path_record: WeightedPathRecord):
        pass

    def _handle_target_message(self, target_record: TargetRecord):
        pass

    def _handle_done_message(self, message_record: MessageRecord):
        pass
