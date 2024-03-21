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
    def change_speed(side, speed, t):
        if side == "l":
            # speed for the motors on a sale 0 - 100
            m_left.duty_cycle_sp = speed
            m_left.command = "run-direct"
            time.sleep(t)
        elif side == "r":
            m_right.duty_cycle_sp = speed
            m_right.command = "run-direct"
            time.sleep(t)

    # changing speed simultaneously
    def speed(v, t):
        motor_prep()
        m_left.duty_cycle_sp = v
        m_right.duty_cycle_sp = v
        m_left.command = "run-direct"
        m_right.command = "run-direct"
        time.sleep(t)

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
        # right motor is on output C
        m_right = ev3.LargeMotor("outC")
        # left motor is on output A
        m_left = ev3.LargeMotor("outA")
        print("checking for colours", c)
        if c[0] < 100 and c[1] < 130 and c[2] < 100:  # for the case the colour is black
            print("its black")
            speed(20, 2)
        elif c[0] > 220 and c[1] > 300 and c[2] > 150:  # for the case the color is white
            # to check later if its getting more white after correction => means wrong direction
            print("its white")
            check = cs.raw
            # turning left
            change_speed("l", 15, 1)
            change_speed("r", 20, 1)
            print("turning left")
            # getting new colour for checking
            c = cs.raw
            if c[0] > check[0] and c[1] > check[1] and c[2] > check[2]:
                # direction correction
                print("correction")
                # turning right
                change_speed("l", 20, 2)
                change_speed("r", 16, 2)
                # trying to get it leveled
                change_speed("l", 20, 1)
                change_speed("r", 24, 1)
        else:
            print("no white and no black")
            speed(30, 1)

        # blau: (32, 123, 93)
        # weiß: (267, 381, 197)
        # schwarz: (35, 67, 18)l
        # rot: (173, 54, 19)
