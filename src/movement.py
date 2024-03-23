import ev3dev.ev3 as ev3
import sys
import select
import time


# initialising touch sensor
# ts = ev3.TouchSensor()
# using speaker
# sound = ev3.Sound()
# sound.speak('Hello Robolab!')

def following_line():
    # initialising colour sensor
    cs = ev3.ColorSensor()
    # using rgb-mode
    cs.mode = 'RGB-RAW'

    # preparing motors
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

    # function for changing speed on one side
    def change_speed(side, v):
        if side == "l":
            # speed for the motors on a sale 0 - 100
            m_left.duty_cycle_sp = v
            m_left.command = "run-direct"
        elif side == "r":
            m_right.duty_cycle_sp = v
            m_right.command = "run-direct"

    # changing speed on both wheels
    def speed(v_l, v_r):
        # motor_prep()
        # testing speed boundary's and adjusting speed if necessary
        v_l = max(min(v_l, 100), -100)
        v_r = max(min(v_r, 100), -100)
        # assigning speed
        m_left.duty_cycle_sp = v_l
        m_right.duty_cycle_sp = v_r
        # executing speed
        m_left.command = "run-direct"
        m_right.command = "run-direct"

    def colour_calibration():
        # average rgb
        avg_r = 0
        avg_g = 0
        avg_b = 0

        # measuring 100 times
        for x in range(100):
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
    # calculating offset -6 for sensor deviation minimization in Döbeln
    # offset_grey = (white_grey + black_grey) / 2
    offset_grey = 27
    # declaring proportional gain
    k_p = 1
    # integral gain
    k_i = 1 * 10 ** - 1
    # for summing up the error, hence integral
    integral = 0
    # time between two while iterations
    # initialising t_p, well use it with the meaning of x% of the possible wheel speed, here its 50%
    t_p = 20
    print("offset: ", offset_grey)

    # so we can move Robo again
    input("Press enter to start")
    motor_prep()

    # for stopping the process for testing
    print("Press enter to stop")
    x = 0
    while True:
        # this stops the loop if I press enter, IDK how it works
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = input()
            if line == '':
                break
        else:
            # calculating turn_speed and if turning is necessary
            # converting to greyscale / 2.55 to norm it from 0 to 100
            light_grey = (0.3 * cs.raw[0] + 0.59 * cs.raw[1] + 0.11 * cs.raw[2]) / 2.55
            # print("actual reading: ", light_grey)

            # calculating error, should be between 0 and 100
            err = light_grey - offset_grey
            # print("error: ", err)
            # calc integral
            integral = integral + err
            integral = max(min(10, integral), -10)
            # calculating turn of the wheels
            turn = k_p * err + k_i * integral
            # if x % 20 == 0:
            # print(k_p*err, k_i*integral)
            # x += 1
            # print("turn: ", turn)
            # driving with adjusted speed
            speed_left = t_p + turn
            speed_right = t_p - turn
            speed(speed_left, speed_right)
            # print("new speed left: ", speed_left)
            # print("new speed right: ", speed_right)
            # time.sleep(4)
