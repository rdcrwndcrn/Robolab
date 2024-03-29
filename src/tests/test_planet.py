#!/usr/bin/env python3

import unittest

from planet import Direction, Planet


class ExampleTestPlanet(unittest.TestCase):
    """Example test case illustrating the task."""

    def setUp(self):
        """Instantiate planet data structure and fill it with paths.

        +--+
        |  |
        +-0,3------+
           |       |
          0,2-----2,2 (target)
           |      /
        +-0,1    /
        |  |    /
        +-0,0-1,0
           |
        (start)
        """
        # Initialize your data structure here
        self.planet = Planet()
        self.planet.add_path(((0, 0), Direction.NORTH), ((0, 1), Direction.SOUTH), 1)
        self.planet.add_path(((0, 1), Direction.WEST), ((0, 0), Direction.WEST), 1)

    @unittest.skip('Example test, should not count in final test results.')
    def test_target_not_reachable_with_loop(self):
        """Check the case of a non-reachable target on a looped map.

        The shortest-path algorithm should not get stuck in a loop
        between two points while searching for a target not reachable
        nearby.

        Result: Target is not reachable.
        """
        self.assertIsNone(self.planet.shortest_path((0, 0), (1, 2)))


class TestRoboLabPlanet(unittest.TestCase):
    """Test `Planet` data structure and shortest path algorithm."""

    def setUp(self):
        """Instantiate planet data structure and fill it with paths.

        (0,2)---2---(2,2)-----2----(4,2)
          |           |              |
          |           1              1
          |           |              |
          2         (2,1)-----2----(4,1)--1--(5,1)
          |
          |
          |
        (0,0)------3------(3,0)-------2------(5,0)
          |                                    |
          1                                    1
          |                                    |
        (0,-1)---------------- -1------------(5,-1)
        """
        # Set to see full dictionary diffs.
        self.maxDiff = None
        # Initialize your data structure here
        self.planet = Planet()
        self.planet.add_path(((0, 0), Direction.NORTH), ((0, 2), Direction.SOUTH), 2)
        self.planet.add_path(((0, 0), Direction.EAST),  ((3, 0), Direction.WEST),  3)
        self.planet.add_path(((0, 0), Direction.SOUTH), ((0,-1), Direction.NORTH), 1)
        self.planet.add_path(((0, 2), Direction.EAST),  ((2, 2), Direction.WEST),  2)
        self.planet.add_path(((2, 2), Direction.SOUTH), ((2, 1), Direction.NORTH), 1)
        self.planet.add_path(((2, 2), Direction.EAST),  ((4, 2), Direction.WEST),  2)
        self.planet.add_path(((2, 1), Direction.EAST),  ((4, 1), Direction.WEST),  2)
        self.planet.add_path(((4, 2), Direction.SOUTH), ((4, 1), Direction.NORTH), 1)
        self.planet.add_path(((4, 1), Direction.EAST),  ((5, 1), Direction.WEST),  1)
        self.planet.add_path(((3, 0), Direction.EAST),  ((5, 0), Direction.WEST),  2)
        self.planet.add_path(((5, 0), Direction.SOUTH), ((5,-1), Direction.NORTH), 1)
        self.planet.add_path(((0,-1), Direction.EAST),  ((5,-1), Direction.WEST), -1)

    def test_integrity(self):
        """Check the result of `planet.get_paths()` to match expected structure."""
        self.assertEqual(self.planet.get_paths(), {
            (0, 0): {
                Direction.NORTH: ((0, 2), Direction.SOUTH, 2),
                Direction.SOUTH: ((0, -1), Direction.NORTH, 1),
                Direction.EAST: ((3, 0), Direction.WEST, 3),
            },
            (0, 2): {
                Direction.SOUTH: ((0, 0), Direction.NORTH, 2),
                Direction.EAST: ((2, 2), Direction.WEST, 2),
            },
            (0, -1): {
                Direction.NORTH: ((0, 0), Direction.SOUTH, 1),
                Direction.EAST: ((5, -1), Direction.WEST, -1),
            },
            (2, 2): {
                Direction.SOUTH: ((2, 1), Direction.NORTH, 1),
                Direction.EAST: ((4, 2), Direction.WEST, 2),
                Direction.WEST: ((0, 2), Direction.EAST, 2),
            },
            (2, 1): {
                Direction.NORTH: ((2, 2), Direction.SOUTH, 1),
                Direction.EAST: ((4, 1), Direction.WEST, 2),
            },
            (4, 1): {
                Direction.WEST: ((2, 1), Direction.EAST, 2),
                Direction.NORTH: ((4, 2), Direction.SOUTH, 1),
                Direction.EAST: ((5, 1), Direction.WEST, 1),
            },
            (4, 2): {
                Direction.WEST: ((2, 2), Direction.EAST, 2),
                Direction.SOUTH: ((4, 1), Direction.NORTH, 1),
            },
            (5, 1): {
                Direction.WEST: ((4, 1), Direction.EAST, 1),
            },
            (3, 0): {
                Direction.WEST: ((0, 0), Direction.EAST, 3),
                Direction.EAST: ((5, 0), Direction.WEST, 2),
            },
            (5, 0): {
                Direction.WEST: ((3, 0), Direction.EAST, 2),
                Direction.SOUTH: ((5, -1), Direction.NORTH, 1),
            },
            (5, -1): {
                Direction.NORTH: ((5, 0), Direction.SOUTH, 1),
                Direction.WEST: ((0, -1), Direction.EAST, -1),
            },
        })

    def test_empty_planet(self):
        """Check that an empty planet really is empty."""
        self.assertEqual(Planet().get_paths(), {})

    def test_target(self):
        """Check that the shortest-path algorithm implemented works.

        Requirement: Minimum distance is three nodes (two paths in list
                     returned).
        """
        self.fail('implement me!')

    def test_target_not_reachable(self):
        """Check non-reachable node cases.

        Should return that a target outside the map or at an unexplored
        node is not reachable.
        """
        self.fail('implement me!')

    def test_same_length(self):
        """Check algorithm in case of two paths of same length.

        The shortest-path algorithm should return a shortest path even
        if there are multiple shortest paths with the same length.

        Requirement: Minimum of two paths with same cost exists, only
                     one is returned by the logic implemented.
        """
        self.fail('implement me!')

    def test_target_with_loop(self):
        """Check the case of a reachable target on a looped map.

        The shortest-path algorithm should not get stuck in a loop
        between two points while searching for a target nearby.

        Result: Target is reachable.
        """
        self.fail('implement me!')

    def test_target_not_reachable_with_loop(self):
        """Check the case of a non-reachable target on a looped map.

        The shortest-path algorithm should not get stuck in a loop
        between two points while searching for a target not reachable
        nearby.

        Result: Target is not reachable.
        """
        self.fail('implement me!')


if __name__ == "__main__":
    unittest.main()
