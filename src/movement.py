import time
from ev3dev import ev3
import sys
import select


class Follower:
    # for saving colours
    colors = {}
    offset_grey = 0

    # initialising colour sensor
    cs = ev3.ColorSensor()
    # using rgb-mode
    cs.mode = 'RGB-RAW'
    # assigning ultrasonic sensor to us
    us = ev3.UltrasonicSensor()
    # continuous measurement in centimeters
    us.mode = 'US-DIST-CM'
    # assigning motors
    # right motor is on output D
    m_right = ev3.LargeMotor("outD")
    # left motor is on output A
    m_left = ev3.LargeMotor("outA")
    # initialising t_p, well use it with the meaning of x per mile of the possible wheel speed
    t_p = 220

    # for node scanning
    lines = []

    # for PID
    # declaring proportional gain
    k_p = 1.5
    # integral gain
    k_i = 1 * 10 ** - 5
    # derivative gain
    k_d = 7 * 10 ** -1
    # for summing up the error, hence integral
    all_err = []

    def __init__(self):
        pass

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

    def set_color(self):

        # initialising colour sensor
        cs = ev3.ColorSensor()
        # using rgb-mode
        cs.mode = 'RGB-RAW'
        calibrated_colors = ['black', 'white', 'red', 'blue']
        self.colors['black'] = [28.2, 34.43, 27.13]
        self.colors['white'] = [170.99, 248.61, 154.26]
        self.colors['red'] = [166.65, 31.74, 29.61]
        self.colors['blue'] = [24.43, 80.04, 79.23]
        '''
        # automated colour assigning
        for x in calibrated_colors:
            # wait, so we can move Robo and know which colour is next
            input(f"Press enter to read {x}.")
            # getting and saving rgb-values
            self.colors[x] = self.calibration()
            print(self.colors[x])
        '''
        # colour calc to calc the error and use that for PID calc
        # converting white and black to greyscale / 2.55 to norm it from 0 to 100
        white_grey = 0.3 * self.colors['white'][0] + 0.59 * self.colors['white'][1] + 0.11 * self.colors['white'][2]
        black_grey = 0.3 * self.colors['black'][0] + 0.59 * self.colors['black'][1] + 0.11 * self.colors['black'][2]
        print(f'black_grey: {black_grey},  white_grey: {white_grey}')

        # calculating offset
        self.offset_grey = ((white_grey + black_grey) / 2)
        print('offset_grey: ', self.offset_grey)

    def motor_prep(self):
        # IDK what these are doing, found them in the documentation
        self.m_left.reset()
        self.m_right.reset()
        self.m_left.stop_action = "brake"
        self.m_right.stop_action = "brake"

    def speed(self, v_l, v_r):
        # motor_prep()
        # testing speed boundary's and adjusting speed if necessary
        v_l = max(min(v_l, 1000), -1000)
        v_r = max(min(v_r, 1000), -1000)
        # assigning speed
        self.m_left.speed_sp = v_l
        self.m_right.speed_sp = v_r
        # executing commands
        self.m_left.command = "run-forever"
        self.m_right.command = "run-forever"

    def turn(self, degree):
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
        while 'running' in self.m_left.state or 'running' in self.m_right.state:
            time.sleep(0.1)
            # should continue if he found the line again
            # found_line = 0.3 * cs.raw[0] + 0.59 * cs.raw[1] + 0.11 * cs.raw[2]
            # if found_line > offset_grey:
            #    break

    def node_scan(self, degree):
        print("Scanning for lines")
        # motor prep so the position attribute from the motors is exact
        self.motor_prep()
        # 1860 * 2 ticks ~ 360 degree
        # opposite wheel directions are twice as fast
        ticks = 1860
        # ticks the wheels should to do
        self.m_left.position_sp = (1 / 2 * degree * ticks) / 360
        self.m_right.position_sp = -(1 / 2 * degree * ticks) / 360
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
            time.sleep(0.1)
            # should continue if he found the line again
            found_line = 0.3 * self.cs.raw[0] + 0.5 * self.cs.raw[1] + 0.11 * self.cs.raw[2]
            if found_line < self.offset_grey:
                print(f'found line at {self.m_left.position}')
                self.lines.append(self.m_left.position)

    def degree_to_celestial_direction(self):
        pass

    def node_state(self):
        # try to get into the mit of the node
        # to align the colour sensor
        self.m_left.position_sp = 200
        self.m_right.position_sp = 200
        # ticks per second, up to 1050
        self.m_left.speed_sp = 100
        self.m_right.speed_sp = 100
        # executing commands
        self.m_left.command = "run-to-rel-pos"
        self.m_right.command = "run-to-rel-pos"
        while 'running' in self.m_left.state or 'running' in self.m_right.state:
            time.sleep(0.1)
        # scan while turning back to the start position and save it into an array
        # array: Nord, East, South, West, from the positioning of the robot, not the card yet
        self.node_scan(360)
        self.degree_to_celestial_direction()
        # choosing line function
        self.follower_state()

    def follower_state(self):
        # for calc the derivative
        last_err = 0
        # so we can control the movement of Rob
        input("Press enter to start")
        self.motor_prep()
        # for stopping the process for testing
        print("Press enter to stop")

        while True:
            # this stops the loop if I press enter, IDK how it works
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                line = input()
                if line == '':
                    break
            else:
                # turn if bottle is less than 150 mm before Robo,
                # so we don't always measure, it may be more energy efficient??
                if self.us.value() < 150:
                    self.turn(175)
                # detects if the cs sees red
                r, g, b = self.cs.raw[0], self.cs.raw[1], self.cs.raw[2]
                if r > 1.5 * g and r > 2 * b:
                    print(f"I am now at red node: {self.cs.raw}")
                    # enter node state
                    self.node_state()
                # same for blue
                if b > 2 * r and b > 1.5 * g:
                    print(f"I am now at blue node: {self.cs.raw}")
                    self.node_state()
                # calculating turn_speed and if turning is necessary
                # converting to greyscale / 2.55 to norm it from 0 to 100
                light_grey = 0.3 * r + 0.5 * g + 0.11 * b
                print(f'light grey: {light_grey}')
                # print(f'actual reading: r={r}, b={b}, g={g}, light_grey={light_grey}')
                # calculating error
                err = light_grey - self.offset_grey
                # add err to integral array
                self.all_err.append(0.6 * err)
                # check if integral has to many values
                if len(self.all_err) > 5 * 10 ** 2:
                    # remove the first(first in first out)
                    self.all_err.pop(0)
                # calc integral
                integral = sum(self.all_err)
                # integral * k_i should not be bigger than +-10, that means an additional difference of 10 ticks
                integral_adjusted = min(max(integral, -1000000), 1000000)
                # calc derivative
                derivative = err - last_err
                # calc turn = k_p * err + k_i * integral + k_d * derivative
                turns = self.k_p * err + self.k_d * derivative
                if turns > 150:
                    turns += self.k_i * integral_adjusted
                # print(f'P: {k_p*err} and D:{k_i*integral}')
                # driving with adjusted speed
                # a white line
                new_speed_left = self.t_p + turns
                new_speed_right = self.t_p - turns
                self.speed(new_speed_left, new_speed_right)
                # print(f'new speed left: {new_speed_left}, new speed right: {new_speed_right}')
                # print()
                last_err = err
                # time.sleep(3)
