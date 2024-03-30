# class to switch between States
class Robot:
    def __init__(self):
        pass

    def runAll(self):
        pass


# inheritance class, so different states can use the same attributes
class State:
    def __init__(self):
        pass


# starting state, calibrates colours
class ColourCalibration(State):
    def run(self):
        pass


# follows line, PID and I, accumulates data for Odometry, turn before collision with bottles, detects nodes
class Follower(State):
    def run(self):
        pass


# calculates Odometry, communicates with mothership, scans Node, calls dijkstra, resets many variables
class Node(State):

    def run(self):
        pass
