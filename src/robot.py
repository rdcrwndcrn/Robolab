import ev3dev.ev3 as ev3
import sys
import select
import time


# state where I save all the data, maybe there's a better way to do this
class Robot:
    # sensors and motors
    cs = ev3.ColorSensor()
    # using rgb-mode
    cs.mode = 'RGB-RAW'
    # assigning ultrasonic sensor to us
    us = ev3.UltrasonicSensor()
    # continuous measurement in centimeters
    us.mode = 'US-DIST-CM'
    # assigning motors
    # right motor is on output C
    m_right = ev3.LargeMotor("outD")
    # left motor is on output A
    m_left = ev3.LargeMotor("outA")
    # initialising t_p, well use it with the meaning of x per mile of the possible wheel speed
    t_p = 300

    # dict for colours and rgb values
    colors = {}
    calibrated_colors = ['black', 'white', 'blue', 'red']
    white_grey = 0
    black_grey = 0
    offset = 0

    # declaring proportional gain
    k_p = 0.9
    # integral gain
    k_i = 0 * 10 ** - 5
    # derivative gain
    k_d = 5 * 10 ** -1
    # for summing up the error, hence integral
    all_err = []
    # for calc the derivative
    last_err = 0

    # gets executed when the class is called and initializes an object
    def __init__(self):
        # so the first state is calibrate
        self.currentState = CalibrateColours()

    # this loop, it runs the state machine
    def run_all(self):
        # while the current state is a state, run the state
        while isinstance(self.currentState, State):
            # to execute run in the state
            self.currentState = self.currentState.run(self)

    def motor_prep(self):
        # from doc, so must be important
        self.m_left.reset()
        self.m_right.reset()
        self.m_left.stop_action = "brake"
        self.m_right.stop_action = "brake"

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


# for state machine
class State:
    # abstract class, so this method has to be implemented by subclasses, these are the really states for Robo
    def run(self, robot):
        raise NotImplementedError("Subclasses must implement this method.")


class CalibrateColours(State):
    # this is the first state, so we can calibrate the colours, everything in run gets executed if we are in this state
    def run(self, robot):
        # all calibration is in the function, the others get executed there as well
        CalibrateColours.activ_colour_calibration(robot)

    @staticmethod
    def colour_calibration(robot):
        # average rgb
        avg_r = 0
        avg_g = 0
        avg_b = 0

        # measuring 100 times
        for i in range(100):
            red, green, blue = robot.cs.raw
            avg_r += red
            avg_g += green
            avg_b += blue

        avg_r /= 100
        avg_g /= 100
        avg_b /= 100
        return [avg_r, avg_g, avg_b]

    @staticmethod
    def calc_greyscale(r, g, b):
        # colour calc to calc the error and use that for PID calc
        # converting white and black to greyscale / 2.55 to norm it from 0 to 100
        grey = 0.3 * r + 0.59 * g + 0.11 * b
        return grey

    @staticmethod
    def activ_colour_calibration(robot):
        for x in robot.calibrated_colors:
            # wait, so we can move Robo and know which colour is next
            input(f"Press enter to read {x}.")
            # getting and saving rgb-values
            robot.colors[x] = CalibrateColours.colour_calibration(robot)
            print(robot.colors[x])
            # calcu greyscale values for black and white for offset
            grey = CalibrateColours.calc_greyscale(robot.colors[x][0], robot.colors[x][1], robot.colors[x][2])
            print(f'{x} grey: {grey}')
            # saving it
            robot.offset = CalibrateColours.calc_offset(robot)
            # calling all methods in this method is not relly elegant, but it works for now
            return Follower()

    @staticmethod
    def calc_offset(robot):
        # + 40 so the robot does not drive over the black line
        offset = ((robot.white_grey + robot.black_grey) / 2) + 40
        print(f'offset_grey: {offset}')
        return offset


class Follower(State):

    def run(self, robot):
        self.follow_line(robot)

    @staticmethod
    def follow_line(robot):
        while True:
            # this stops the loop if I press enter
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                line = input()
                if line == '':
                    break
            else:
                # turn if bottle is less than 150 mm before Robo,
                # so we don't always measure, it may be more energy efficient??
                if robot.us.value() < 150:
                    return Turn()
                # detects if the cs sees red
                r, g, b = robot.cs.raw
                # does not work that well, should be calibrated
                if r > g * 1.5 and r > b * 1.5:
                    # break loop to stop if it does
                    return Node()
                # same for blue
                if b > r * 1.5 and b > g * 1.5:
                    return Node()
                # calculating turn_speed and if turning is necessary
                # converting to greyscale / 2.55 to norm it from 0 to 100
                light_grey = 0.3 * r + 0.59 * g + 0.11 * b
                # print(f'actual reading: r={r}, b={b}, g={g}, light_grey={light_grey}')
                # calculating error
                err = light_grey - robot.offset
                # add err to integral array
                robot.all_err.append(err)
                # check if integral has to many values
                if len(robot.all_err) > 5 * 10 ** 2:
                    # remove the first(first in first out)
                    robot.all_err.pop(0)
                # calc integral
                integral = sum(robot.all_err)
                # integral * k_i should not be bigger than +-30, that means an additional difference of 60 ticks
                integral_adjusted = min(max(integral, -3000000), 3000000)
                # calc derivative
                derivative = err - robot.last_err
                # calc turn = k_p * err + k_i * integral + k_d * derivative
                turns = robot.k_p * err + robot.k_d * derivative
                if turns > 150:
                    turns += robot.k_i * integral_adjusted
                # print(f'P: {k_p*err} and D:{k_i*integral}')
                # driving with adjusted speed
                # a white line
                new_speed_left = robot.t_p + turns
                new_speed_right = robot.t_p - turns
                robot.speed(new_speed_left, new_speed_right)
                # print(f'new speed left: {new_speed_left}, new speed right: {new_speed_right}')
                # print()
                robot.last_err = err
                time.sleep(0.01)


class Turn(State):
    # I hope for every bottle the degree approach works
    degree = 175

    def run(self, robot):
        self.turn(Turn.degree, robot)

    @staticmethod
    def turn(degree, robot):
        # 2280 ticks ~ 360 degree
        # opposite wheel directions are twice as fast
        # ticks the wheels should to do
        robot.m_left.position_sp = (1 / 2 * degree * 1155) / 360
        robot.m_right.position_sp = -(1 / 2 * degree * 1155) / 360
        # ticks per second, up to 1050
        robot.m_left.speed_sp = 100
        robot.m_right.speed_sp = 100
        # executing commands
        robot.m_left.command = "run-to-rel-pos"
        robot.m_right.command = "run-to-rel-pos"
        # print(m_left.state.__repr__())
        # giving them time to execute
        while 'running' in robot.m_left.state or 'running' in robot.m_right.state:
            time.sleep(0.1)
            # should continue if he found the line again
            # found_line = 0.3 * self.cs.raw[0] + 0.59 * self.cs.raw[1] + 0.11 * self.cs.raw[2]
            # if found_line > offset_grey:
            #    break
        # tried error minimization with gyro, but too imprecise
        return Follower()


# explores possible routes from node, calls communication, maybe Dijkstra
class Node(State):

    def run(self, robot):
        self.node(robot)

    @staticmethod
    def node(robot):
        pass
