# class to switch between States
class Robot:
    def __init__(self):
        # for switching states
        # attribute where current states gets saved
        self.state = None

    def set_start_state(self, state):
        # for switching to start state
        self.switch_state(state)

    # run all , because after that the states changes themselves back and forth
    def runAll(self):
        # run the state object which lies in the state attribute
        self.state.run()

    # calling function to change attribute and giving the robot instance (self) to the new state
    def switch_state(self, new_state):
        self.state = new_state
        self.state.robot = self


# inheritance class state for saving the robot instance
class State:
    def __init__(self):
        self.robot = None


# starting state, calibrates colours
class ColourCalibration(State):
    def __init__(self, robot):
        State.__init__(self)
        self.robot = robot

    def run(self):
        # running Colour calibration methods

        # switch to the follower state by creating follower instance
        # uses robot instance which lies in the robot attribute in Metaclass
        # TODO - Why save the same robot instance again?
        next_state = Follower(self.robot)
        # calling the switch method of robot class which needs new state as an instance
        self.robot.switch_state(next_state)


# follows line, PID and I, accumulates data for Odometry, turn before collision with bottles, detects nodes
class Follower(State):
    def __init__(self, robot):
        State.__init__(self)
        self.robot = robot

    def run(self):
        # line following loop

        next_state = Node(self.robot)
        # calling the switch method of robot class which needs new state as an instance
        self.robot.switch_state(next_state)


# calculates Odometry, communicates with mothership, scans Node, calls dijkstra, resets many variables
class Node(State):
    def __init__(self, robot):
        State.__init__(self)
        self.robot = robot

    def run(self):
        # node methods


        # back to line following
        next_state = Follower(self.robot)
        # calling the switch method of robot class which needs new state as an instance
        self.robot.switch_state(next_state)


def main():
    # create robot instance
    robot = Robot()
    # set start state in rob instance to color calibration state, which needs the instance if Robo
    robot.set_start_state(ColourCalibration(robot))
    # start by running runAll from robo class
    robot.runAll()


if __name__ == '__main__':
    main()
