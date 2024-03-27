import time
from ev3dev import ev3


class Robot:

    def __init__(self):  # TODO - variables can be saved in simulator_config_example.json
        # for saving colours
        self.colors = {}
        self.calibrated_colors = ['black', 'white']
        self.offset_grey = 0

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
        self.t_p = 220

        # for node scanning
        self.lines = []
        # always the compass where the last scanned node hast lines 0 - no, 1 - yes, north, east, south, west
        # north is where Rob is looking before and after the scan
        self.nodes = [False, False, False, False]

        # for PID
        # declaring proportional gain
        self.k_p = 1.5
        # integral gain
        self.k_i = 3 * 10 ** - 5
        # derivative gain
        self.k_d = 7 * 10 ** -1
        # for summing up the error, hence integral
        self.all_err = []
        # for calc the derivative
        self.last_err = 0

    '''all 3 states are defined in the following 3 methods'''

    # function to get all colour values and start line following
    def start_state(self):
        # hardcoded for faster testing, will be deleted for exam
        self.colors['black'] = [27.18, 31.75, 23.77]
        self.colors['white'] = [208.92, 246.4, 97.24]

        # measuring colour and saving them in dict
        # self.measure_colours()
        # calc offset for PID
        self.calc_off()
        # start driving
        self.follower_state()

    # scan while turning back to the start position and save it into an array
    def node_state(self):
        # for testing
        self.offset_grey = 120
        # move Robo to node mid
        # self.move_to_position(100, 100, 300, 300)
        # scan
        self.node_scan()
        # turn to the chosen line to continue
        self.chose_line()
        # calculating where the lines are
        # array: Nord, East, South, West, from the positioning of the robot, not the card yet
        self.degree_to_celestial_direction()
        # choosing line function
        self.follower_state()

    def follower_state(self):
        # so we can control the movement of Rob
        input("Press enter to start")
        self.motor_prep()
        # for stopping the process for testing
        print("Press enter to stop")

        try:
            while True:
                # turn if bottle is less than 150 mm before Robo - TODO test if 15cm is too much
                if self.us.value() < 150:
                    self.turn(175)
                # get rgb values for the iteration we are in
                r, g, b = self.cs.raw
                # check if Rob over red or blue
                self.check_for_node(r, g, b)
                # converting to greyscale / 2.55 to norm it from 0 to 100
                grey = self.convert_to_grey(r, g, b)
                # calculating error
                err = grey - self.offset_grey
                # calc integral
                integral = self.calc_int(err)
                # calc derivative
                derivative = err - self.last_err
                # calc adjustments for little correction turns of wheels
                turns = self.k_p * err + self.k_i * integral + self.k_d * derivative
                # continuing with adjusted speed
                new_speed_left = self.t_p + turns
                new_speed_right = self.t_p - turns
                self.speed(new_speed_left, new_speed_right)
                # for derivative in next interation
                self.last_err = err
                # so we may save energy
                time.sleep(0.01)
        finally:
            self.motor_prep()
            print(' aborting ...')

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
            red, green, blue = self.cs.raw
            avg_r += red
            avg_g += green
            avg_b += blue

        avg_r /= 100
        avg_g /= 100
        avg_b /= 100
        return [avg_r, avg_g, avg_b]

    # rgb to grey
    # calibrated by Milan's method for colour sensor 1, more robust with blue and red detection
    @staticmethod
    def milan_grey(r, g, b):
        return 0.9 * r, 0.75 * g, 1.9 * b

    # rgb to grey
    # after greyscale model optimised for human eyes
    @staticmethod
    def convert_to_grey(r, g, b):
        return 0.3 * r + 0.59 * g + 0.11 * b

    # check if colour sensor is over red or blue
    def check_for_node(self, red, green, blue):
        # correct colours with the milan methode
        r, g, b = self.milan_grey(red, green, blue)
        if r - b > 40 and r - g > 30:
            print(f'found red node: {r, g, b}')
            self.node_state()
        elif b - r > 40:
            print(f'found blue node: {r, g, b}')
            self.node_state()

    # colour calibration function
    def measure_colours(self):
        for x in self.calibrated_colors:
            # wait, so we can move Robo and know which colour is next
            input(f"Press enter to read {x}.")
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
        self.offset_grey = (white_grey + black_grey) / 2

    def motor_prep(self):
        self.m_left.reset()
        self.m_right.reset()
        self.m_left.stop_action = "brake"
        self.m_right.stop_action = "brake"

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
            time.sleep(0.1)

    # so Rob can choose a line to continue from Node and move in position there - TODO
    def chose_line(self):
        pass

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
        self.m_left.speed_sp = 100
        self.m_right.speed_sp = 100
        # executing commands
        self.m_left.command = "run-to-rel-pos"
        self.m_right.command = "run-to-rel-pos"
        # print(m_left.state.__repr__())
        # giving them time to execute
        while self.m_right.is_running and self.m_left.is_running:
            time.sleep(0.1)
            # should continue if he found the line again
            # found_line = 0.3 * cs.raw[0] + 0.59 * cs.raw[1] + 0.11 * cs.raw[2]
            # if found_line > offset_grey:
            #    break

    # function for calculating the integral
    def calc_int(self, error):
        # add err to integral array
        self.all_err.append(error)
        # check if integral has to many values
        if len(self.all_err) > 5 * 10 ** 2:
            # remove the first (first in first out)
            self.all_err.pop(0)
        # calc integral
        integral = sum(self.all_err)
        # integral * k_i should not be bigger than +-10, that means an additional difference of 10 ticks
        integral_adjusted = min(max(integral, -1000000), 1000000)
        return integral_adjusted

    # function for scanning the node and noting motor position if black is found
    def node_scan(self):
        print("Scanning for lines")
        # motor prep so the position attribute from the motors is exact
        self.motor_prep()
        # 1860 * 2 ticks ~ 360 degree
        # opposite wheel directions are twice as fast
        ticks = 1840
        # ticks the wheels should to do
        self.m_left.position_sp = 1 / 2 * ticks
        self.m_right.position_sp = -1 / 2 * ticks
        # ticks per second, up to 1050
        self.m_left.speed_sp = 150
        self.m_right.speed_sp = 150
        # executing commands
        self.m_left.command = "run-to-rel-pos"
        self.m_right.command = "run-to-rel-pos"
        # print(m_left.state.__repr__()
        # for knowing where the line was detected
        # rotation =
        # giving them time to execute
        while 'running' in self.m_left.state or 'running' in self.m_right.state:
            time.sleep(0.01)
            r, g, b = self.cs.raw
            # should continue if he found the line again
            found_line = self.convert_to_grey(r, g, b)
            if found_line < self.offset_grey:
                self.lines.append(self.m_left.position)

    # function to turn the motor.position into a compass
    def degree_to_celestial_direction(self):
        # the motor position starts at 0 and after the scan it has 1000
        # if line found, then position gets noted in lines
        # idea: make 4 intervals and if at least one value is in it, there is a line
        # set all from previous node to false
        for x in range(4):
            self.nodes[x] = False
        for x in self.lines:
            if x < 170:
                self.nodes[0] = True
            elif x < 400:
                self.nodes[1] = True
            elif x < 630:
                self.nodes[2] = True
            elif x < 860:
                self.nodes[3] = True
            elif x < 950:
                self.nodes[0] = True
        print(self.nodes)
