import time
from ev3dev import ev3
import sys
import select


def turn(degree):
    # sensor prep
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
    offset_grey = 200
    # 1860 * 2 ticks ~ 360 degree
    # opposite wheel directions are twice as fast
    # ticks the wheels should to do
    ticks = 1860
    m_left.position_sp = (1 / 2 * degree * ticks) / 360
    m_right.position_sp = -(1 / 2 * degree * ticks) / 360
    # ticks per second, up to 1050
    m_left.speed_sp = 150
    m_right.speed_sp = 150
    # executing commands
    m_left.command = "run-to-rel-pos"
    m_right.command = "run-to-rel-pos"
    # print(m_left.state.__repr__())
    # giving them time to execute
    x = 0
    while 'running' in m_left.state or 'running' in m_right.state:
        time.sleep(0.1)
        # should continue if he found the line again
        found_line = 0.3 * cs.raw[0] + 0.59 * cs.raw[1] + 0.11 * cs.raw[2]
        if found_line < offset_grey:
            x += 1
            print(f"found Line: {x}")

def following_line():
    # sensor prep
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

    # function for preparing the motors
    def motor_prep():
        # IDK what these are doing, found them in the documentation
        m_left.reset()
        m_right.reset()
        m_left.stop_action = "brake"
        m_right.stop_action = "brake"

    # changing speed on both wheels
    def speed(v_l, v_r):
        # motor_prep()
        # testing speed boundary's and adjusting speed if necessary
        v_l = max(min(v_l, 1000), -1000)
        v_r = max(min(v_r, 1000), -1000)
        # assigning speed
        m_left.speed_sp = v_l
        m_right.speed_sp = v_r
        # executing commands
        m_left.command = "run-forever"
        m_right.command = "run-forever"

    def turn(degree):
        # opposite wheel directions are twice as fast
        # 1860 * 2 ticks ~ 360 degree
        # ticks the wheels should to do
        ticks = 1860
        m_left.position_sp = (1 / 2 * degree * ticks) / 360
        m_right.position_sp = -(1 / 2 * degree * ticks) / 360
        # ticks per second, up to 1050
        m_left.speed_sp = 100
        m_right.speed_sp = 100
        # executing commands
        m_left.command = "run-to-rel-pos"
        m_right.command = "run-to-rel-pos"
        # print(m_left.state.__repr__())
        # giving them time to execute
        while 'running' in m_left.state or 'running' in m_right.state:
            time.sleep(0.1)
            # should continue if he found the line again
            # found_line = 0.3 * cs.raw[0] + 0.59 * cs.raw[1] + 0.11 * cs.raw[2]
            # if found_line > offset_grey:
            #    break

    def turn_node(grad):
        # 2280 ticks ~ 360 degree
        # opposite wheel directions are twice as fast
        # ticks the wheels should to do
        m_left.position_sp = (1 / 2 * grad * 1155) / 360
        m_right.position_sp = -(1 / 2 * grad * 1155) / 360
        # ticks per second, up to 1050
        m_left.speed_sp = 100
        m_right.speed_sp = 100
        # executing commands
        m_left.command = "run-to-rel-pos"
        m_right.command = "run-to-rel-pos"
        # print(m_left.state.__repr__())
        # to calc the degree where how fare it rotated when it detected a line
        # degree =
        # for saving the degrees of the lines
        lines = []
        # giving them time to execute
        while 'running' in m_left.state or 'running' in m_right.state:
            time.sleep(0.1)
            # search for lines
            found_line = 0.3 * cs.raw[0] + 0.59 * cs.raw[1] + 0.11 * cs.raw[2]
            if found_line > offset_grey:
                print(m_left.position())
                # lines.append(degree)
        return lines

    def degree_to_celestial_direction(lines):
        pass

    def node():
        # to align the colour sensor
        m_left.position_sp = 150
        m_right.position_sp = 150
        # ticks per second, up to 1050
        m_left.speed_sp = 100
        m_right.speed_sp = 100
        # executing commands
        m_left.command = "run-to-rel-pos"
        m_right.command = "run-to-rel-pos"
        # so it can not miss the line in front of it
        turn(-20)
        # scan while turning back to the start position and save it into an array
        # array: Nord, East, South, West, from the positioning of the robot, not the card yet
        # lines = turn_node(380)
        # lines = degree_to_celestial_direction(lines)
        # return lines

    def colour_calibration():
        # average rgb
        avg_r = 0
        avg_g = 0
        avg_b = 0

        # measuring 100 times
        for i in range(100):
            red, green, blue = cs.raw
            avg_r += red
            avg_g += green
            avg_b += blue

        avg_r /= 100
        avg_g /= 100
        avg_b /= 100
        return [avg_r, avg_g, avg_b]

    # for saving the calibrated colours
    colors = {}
    calibrated_colors = ['black', 'white', 'red', 'blue']
    colors['black'] = [25.01, 38.91, 23.39]
    colors['white'] = [254.63, 361.27, 194.94]
    colors['red'] = [168.09, 48.15, 28.1]
    colors['blue'] = [35.49, 123.36, 87.44]

    '''
    # automated colour assigning
    for x in calibrated_colors:
        # wait, so we can move Robo and know which colour is next
        input(f"Press enter to read {x}.")
        # getting and saving rgb-values
        colors[x] = colour_calibration()
        print(colors[x])
    '''

    # colour calc to calc the error and use that for PID calc
    # converting white and black to greyscale / 2.55 to norm it from 0 to 100
    white_grey = 0.3 * colors['white'][0] + 0.59 * colors['white'][1] + 0.11 * colors['white'][2]
    black_grey = 0.3 * colors['black'][0] + 0.59 * colors['black'][1] + 0.11 * colors['black'][2]
    print(f'black_grey: {black_grey},  white_grey: {white_grey}')

    # calculating offset
    offset_grey = ((white_grey + black_grey) / 2) + 30
    print('offset_grey: ', offset_grey)

    # declaring proportional gain
    k_p = 0.8
    # integral gain
    k_i = 2 * 10 ** - 5
    # derivative gain
    k_d = 7 * 10 ** -1
    # for summing up the error, hence integral
    all_err = []
    # for calc the derivative
    last_err = 0

    # so we can move Robo again
    input("Press enter to start")
    # initialising t_p, well use it with the meaning of x per mile of the possible wheel speed
    t_p = 300
    motor_prep()
    # speed(t_p, t_p)
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
            if us.value() < 150:
                turn(175)
            # detects if the cs sees red
            r, g, b = cs.raw[0], cs.raw[1], cs.raw[2]
            if (colors['red'][0] - 10 < r < colors['red'][0] + 10 and colors['red'][1] - 10 < g < colors['red'][1] + 10
                    and colors['red'][2] - 10 < b < colors['red'][2] + 10):
                # break loop to stop if it does
                node()
            # same for blue
            if (colors['blue'][0] - 10 < r < colors['blue'][0] + 10 and colors['blue'][1] - 10 < g < colors['blue'][1]
                    + 10 and colors['blue'][2] - 10 < b < colors['blue'][2] + 10):
                # break loop to stop if it does
                node()
            # calculating turn_speed and if turning is necessary
            # converting to greyscale / 2.55 to norm it from 0 to 100
            light_grey = 0.3 * r + 0.59 * g + 0.11 * b
            # print(f'actual reading: r={r}, b={b}, g={g}, light_grey={light_grey}')
            # calculating error
            err = light_grey - offset_grey
            # add err to integral array
            all_err.append(0.6 * err)
            # check if integral has to many values
            if len(all_err) > 5 * 10 ** 3:
                # remove the first(first in first out)
                all_err.pop(0)
            # calc integral
            integral = sum(all_err)
            # integral * k_i should not be bigger than +-30, that means an additional difference of 60 ticks
            integral_adjusted = min(max(integral, -3000000), 3000000)
            # calc derivative
            derivative = err - last_err
            # calc turn = k_p * err + k_i * integral + k_d * derivative
            turns = k_p * err + k_d * derivative
            if turns > 150:
                turns += k_i * integral_adjusted
            # print(f'P: {k_p*err} and D:{k_i*integral}')
            # driving with adjusted speed
            # a white line
            new_speed_left = t_p + turns
            new_speed_right = t_p - turns
            speed(new_speed_left, new_speed_right)
            # print(f'new speed left: {new_speed_left}, new speed right: {new_speed_right}')
            # print()
            last_err = err
            # time.sleep(3)
