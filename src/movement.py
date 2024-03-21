import time
import ev3dev.ev3 as ev3


# using speaker
# sound = ev3.Sound()
# sound.speak('Hello Robolab!')

# m_right.stop()

def following_line():
    ## following line code
    # action before a motor changes speed

    # function for changing speed
    def change_speed(side, speed):
        if side == "l":
            # speed for the motors on a sale 0 - 100
            m_left.duty_cycle_sp = speed
            m_left.command = "run-direct"
            time.sleep(1)
        elif side == "r":
            m_right.duty_cycle_sp = speed
            m_right.command = "run-direct"
            time.sleep(1)

    # function for preparating the motors
    def motor_prep():
        # idk what these are doing, found them in the documentation
        m_left.reset()
        m_right.reset()
        m_left.stop_action = "brake"
        m_right.stop_action = "brake"

    # declaring touch sensor
    ts = ev3.TouchSensor()

    # line correction as long as I don't press the button
    while ts.value() != 1:
        # declaring colour sensor
        cs = ev3.ColorSensor()
        cs.mode = 'RGB-RAW'
        # print(cs.raw)
        c = cs.raw
        # for using the large motors
        # right motor is on output C
        m_right = ev3.LargeMotor("outC")
        # left motor is on output A
        m_left = ev3.LargeMotor("outA")

        if c[0] < 50 and c[1] < 80 and c[2] < 30:  # for the case the colour is black
            motor_prep()
            change_speed("l", 40)
            change_speed("r", 40)
            break
        elif c[0] > 250 and c[1] > 260 and c[2] > 180:  # for the case the color is white
            # to check later if its getting more white after correction => means wrong direction
            check = cs.raw
            motor_prep()
            change_speed("l", 20)
            change_speed("r", 40)
            break

        # blau: (32, 123, 93)
        # weiß: (267, 381, 197)
        # schwarz: (35, 67, 18)l
        # rot: (173, 54, 19)
