import ev3dev.ev3 as ev3
import sys
import select
import time


# initialising touch sensor
# ts = ev3.TouchSensor()
# using speaker
# sound = ev3.Sound()
# sound.speak('Hello Robolab!')
# ev3.Sound.tone([(200, 100, 100), (500, 200)])  # list of (frequency (Hz), duration (ms), delay to next (ms)) tuples

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
    # right motor is on output C
    m_right = ev3.LargeMotor("outC")
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
        # 2280 ticks ~ 360 degree
        # opposite wheel directions are twice as fast
        # ticks the wheels should to do
        m_left.position_sp = (1 / 2 * degree * 1155) / 360
        m_right.position_sp = -(1 / 2 * degree * 1155) / 360
        # ticks per second, up to 1050
        m_left.speed_sp = 100
        m_right.speed_sp = 100
        # executing commands
        m_left.command = "run-to-rel-pos"
        m_right.command = "run-to-rel-pos"
        # print(m_left.state.__repr__())
        # giving them time to execute
        print()
        while 'running' in m_left.state or 'running' in m_right.state:
            time.sleep(0.1)
        # tried error minimization with gyro, but too imprecise

    def colour_calibration():
        # average rgb
        avg_r = 0
        avg_g = 0
        avg_b = 0

        # measuring 100 times
        for i in range(100):
            r, g, b = cs.raw
            avg_r += r
            avg_g += g
            avg_b += b

        avg_r /= 100
        avg_g /= 100
        avg_b /= 100
        return [avg_r, avg_g, avg_b]

    # for saving the calibrated colours
    colors = {}
    calibrated_colors = ['red', 'blue', 'black', 'white']

    # automated colour assigning
    # for x in calibrated_colors:
    # wait, so we can move Robo and know which colour is next
    #    input(f"Press enter to read {x}.")
    # getting and saving rgb-values
    #    colors[x] = colour_calibration()
    #    print(colors[x])

    colors['white'] = [29.33, 51.74, 16.13]
    colors['black'] = [110.05, 102.14, 32.0]
    # for the calculation of turn
    # converting white and black to greyscale / 2.55 to norm it from 0 to 100
    white_grey = (0.3 * colors['white'][0] + 0.59 * colors['white'][1] + 0.11 * colors['white'][2]) / 2.55
    black_grey = (0.3 * colors['black'][0] + 0.59 * colors['black'][1] + 0.11 * colors['black'][2]) / 2.55
    # calculating offset
    # offset_grey = (white_grey + black_grey) / 2
    offset_grey = 27
    # declaring proportional gain
    k_p = 2
    # integral gain
    k_i = 1 * 10 ** - 1
    # for summing up the error, hence integral
    integral = 0
    # print("offset: ", offset_grey)
    # so we can move Robo again
    input("Press enter to start")
    # initialising t_p, well use it with the meaning of x per mile of the possible wheel speed
    t_p = 300
    # starting the motors
    motor_prep()
    speed(t_p, t_p)
    # for stopping the process for testing
    print("Press enter to stop")
    # x = 0
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
                turn(180)

            # calculating turn_speed and if turning is necessary
            # converting to greyscale / 2.55 to norm it from 0 to 100
            light_grey = (0.3 * cs.raw[0] + 0.59 * cs.raw[1] + 0.11 * cs.raw[2]) / 2.55
            # print("actual reading: ", light_grey)

            # calculating error, should be b

            # print(k_p*err, k_i*integral)
            # x += 1
            # print("turn: ", turn)
            # driving with adjusted speed
            # speed_left = t_p + turns
            # speed_right = t_p - turns
            # speed(speed_left, speed_right)
            # print("new speed left: ", speed_left)
            # print("new speed right: ", speed_right)
            # time.sleep(4)
