import time
import ev3dev.ev3 as ev3
import sys
import select

# using speaker
# sound = ev3.Sound()
# sound.speak('Hello Robolab!')

# m_right.stop()

def following_line():
    # initialising touch sensor
    ts = ev3.TouchSensor()

    # initialising colour sensor
    cs = ev3.ColorSensor()
    # using rgb-mode
    cs.mode = 'RGB-RAW'
    # use the value in a variable
    c = cs.raw

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
        m_left.duty_cycle_sp = v_l
        m_right.duty_cycle_sp = v_r
        m_left.command = "run-direct"
        m_right.command = "run-direct"

    # color calibration
    def colour_calibration():
        # average rgb
        avg_r = 0
        avg_g = 0
        avg_b = 0

        # measuring 100 times
        for x in range(100):
            r = cs.value(0)
            g = cs.value(1)
            b = cs.value(2)
            avg_r += r
            avg_g += g
            avg_b += b

        avg_r /= 100
        avg_g /= 100
        avg_b /= 100
        return avg_r, avg_g, avg_b

    # little wait function, so I can move the robot onto the colour

    input("Press enter to read red.")
    # getting the rgb values for red
    red = colour_calibration()
    red_rgb = list(red)
    print(red, c)

    input("Press enter to read blue.")
    # getting the rgb values for blue
    blue = colour_calibration()
    blue_rgb = list(blue)
    print(blue)

    input("Press enter to read black.")
    # getting the rgb values for blue
    black = colour_calibration()
    black_rgb = list(black)
    print(black)

    input("Press enter to read white")
    # getting the rgb values for white
    white = colour_calibration()
    white_rgb = list(white)
    print(white)

    # for the calculation of turn
    # declaring proportionality constant - does still need adjusting
    k_p = 0.1
    # calculating offset
    offset = [(white_rgb[0] - black_rgb[0]) / 2, (white_rgb[1] - black_rgb[1]) / 2,
              (white_rgb[2] - black_rgb[2]) / 2]
    offset_grey = 0.3 * offset[0] + 0.59 * offset[1] + 0.11 * offset[2]
    # initialising t_p, well use it with the meaning of x% of the possible wheel speed, here its 50%
    t_p = 50

    print("Press enter to stop Robo")
    while True:
        # apparently this stops the loop if I press enter
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = input()
            if line == '':
                break
        else:
            # calculating turn_speed and if turning is necessary
            # converting to greyscale
            light_grey = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]

            # calculating error
            err = light_grey - offset_grey
            # calculating turn of the wheels - norming has to be done
            turn = k_p * err

            # driving with adjusted speed
            speed_left = t_p + turn
            speed_right = t_p - turn
            speed(speed_left, speed_right)


