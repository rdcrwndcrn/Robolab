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

            (0,2)---2---(2,2)-----2----(4,2)--------------+
              |           |              |                |
              |           1              1                |
              |           |              |                |
              2         (2,1)-----2----(4,1)--1--(5,1)    8
              |           |                               |
              |           2-----+                         |
              |                 |                         |
            (0,0)------3------(3,0)-------2------(5,0)----+  (6,0)--(7,0)
              |                                    |           |      |
              1                                    1           1      3
              |                                    |           |      |
            (0,-1)---------------- -1------------(5,-1)      (6,-1)---+
        """
        # Set to see full dictionary diffs.
        self.maxDiff = None
        # Initialize your data structure here.
        self.planet = Planet()
        self.planet.add_path(((0, 0), Direction.NORTH), ((0, 2), Direction.SOUTH), 2)
        self.planet.add_path(((0, 0), Direction.EAST),  ((3, 0), Direction.WEST),  3)
        self.planet.add_path(((0, 0), Direction.SOUTH), ((0,-1), Direction.NORTH), 1)
        self.planet.add_path(((0, 2), Direction.EAST),  ((2, 2), Direction.WEST),  2)
        self.planet.add_path(((2, 2), Direction.SOUTH), ((2, 1), Direction.NORTH), 1)
        self.planet.add_path(((2, 2), Direction.EAST),  ((4, 2), Direction.WEST),  2)
        self.planet.add_path(((2, 1), Direction.EAST),  ((4, 1), Direction.WEST),  2)
        self.planet.add_path(((2, 1), Direction.SOUTH), ((3, 0), Direction.NORTH), 2)
        self.planet.add_path(((4, 2), Direction.SOUTH), ((4, 1), Direction.NORTH), 1)
        self.planet.add_path(((4, 2), Direction.EAST),  ((5, 0), Direction.EAST),  8)
        self.planet.add_path(((4, 1), Direction.EAST),  ((5, 1), Direction.WEST),  1)
        self.planet.add_path(((3, 0), Direction.EAST),  ((5, 0), Direction.WEST),  2)
        self.planet.add_path(((5, 0), Direction.SOUTH), ((5,-1), Direction.NORTH), 1)
        self.planet.add_path(((0,-1), Direction.EAST),  ((5,-1), Direction.WEST), -1)

        self.planet.add_path(((6,-1), Direction.NORTH), ((6, 0), Direction.SOUTH), 1)
        self.planet.add_path(((6,-1), Direction.EAST),  ((7, 0), Direction.SOUTH), 3)
        self.planet.add_path(((6, 0), Direction.EAST),  ((7, 0), Direction.WEST),  1)

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
                Direction.SOUTH: ((3, 0), Direction.NORTH, 2),
            },
            (4, 1): {
                Direction.WEST: ((2, 1), Direction.EAST, 2),
                Direction.NORTH: ((4, 2), Direction.SOUTH, 1),
                Direction.EAST: ((5, 1), Direction.WEST, 1),
            },
            (4, 2): {
                Direction.WEST: ((2, 2), Direction.EAST, 2),
                Direction.SOUTH: ((4, 1), Direction.NORTH, 1),
                Direction.EAST: ((5, 0), Direction.EAST, 8),
            },
            (5, 1): {
                Direction.WEST: ((4, 1), Direction.EAST, 1),
            },
            (3, 0): {
                Direction.WEST: ((0, 0), Direction.EAST, 3),
                Direction.EAST: ((5, 0), Direction.WEST, 2),
                Direction.NORTH: ((2, 1), Direction.SOUTH, 2),
            },
            (5, 0): {
                Direction.WEST: ((3, 0), Direction.EAST, 2),
                Direction.SOUTH: ((5, -1), Direction.NORTH, 1),
                Direction.EAST: ((4, 2), Direction.EAST, 8),
            },
            (5, -1): {
                Direction.NORTH: ((5, 0), Direction.SOUTH, 1),
                Direction.WEST: ((0, -1), Direction.EAST, -1),
            },
            (6, -1): {
                Direction.NORTH: ((6, 0), Direction.SOUTH, 1),
                Direction.EAST: ((7, 0), Direction.SOUTH, 3),
            },
            (6, 0): {
                Direction.SOUTH: ((6, -1), Direction.NORTH, 1),
                Direction.EAST: ((7, 0), Direction.WEST, 1),
            },
            (7, 0): {
                Direction.WEST: ((6, 0), Direction.EAST, 1),
                Direction.SOUTH: ((6, -1), Direction.EAST, 3),
            },
        })

    def test_empty_planet(self):
        """Check that an empty planet really is empty."""
        self.assertEqual(Planet().get_paths(), {})

    def test_already_at_target(self):
        """Check the case were start and end node are the same."""
        self.assertEqual(self.planet.shortest_path((0, 0), (0, 0)), [])

    def test_target(self):
        """Check that the shortest-path algorithm implemented works.

        Requirement: Minimum distance is three nodes (two paths in list
                     returned).
        """
        # Includes blocked path.
        self.assertEqual(
            self.planet.shortest_path((0, -1), (5, 0)),
            [
                ((0, -1), Direction.NORTH),
                ((0, 0), Direction.EAST),
                ((3, 0), Direction.EAST),
            ],
        )
        # Should choose the shortest among two possible options.
        self.assertEqual(
            self.planet.shortest_path((2, 2), (3, 0)),
            [
                ((2, 2), Direction.SOUTH),
                ((2, 1), Direction.SOUTH),
            ],
        )
        # Also take a way with much more nodes if it is shorter; there are
        # two possible paths of equal cost.
        self.assertIn(self.planet.shortest_path((5, 0), (4, 2)), [
            [
                ((5, 0), Direction.WEST),
                ((3, 0), Direction.NORTH),
                ((2, 1), Direction.EAST),
                ((4, 1), Direction.NORTH),
            ],
            [
                ((5, 0), Direction.WEST),
                ((3, 0), Direction.NORTH),
                ((2, 1), Direction.NORTH),
                ((2, 2), Direction.EAST),
            ],
        ])

    def test_reversed_path(self):
        """Check that the shortest paths are the same in both directions."""
        # This test requires that there is only one shortest path.
        self.assertEqual(
            self.planet.shortest_path((5, -1), (2, 1)),
            [
                ((5, -1), Direction.NORTH),
                ((5, 0), Direction.WEST),
                ((3, 0), Direction.NORTH),
            ],
        )
        self.assertEqual(
            self.planet.shortest_path((2, 1), (5, -1)),
            [
                ((2, 1), Direction.SOUTH),
                ((3, 0), Direction.EAST),
                ((5, 0), Direction.SOUTH),
            ],
        )

    def test_target_not_reachable(self):
        """Check non-reachable node cases.

        Should return that a target outside the map or at an unexplored
        node is not reachable.
        """
        self.assertIsNone(self.planet.shortest_path((5, -1), (5, 2)))
        self.assertIsNone(self.planet.shortest_path((6, -1), (5, -1)))

    def test_start_unknown(self):
        """Check the case that the start node is not known."""
        self.assertIsNone(self.planet.shortest_path((-2, 0), (-1, 0)))

    def test_same_length(self):
        """Check algorithm in case of two paths of same length.

        The shortest-path algorithm should return a shortest path even
        if there are multiple shortest paths with the same length.

        Requirement: Minimum of two paths with same cost exists, only
                     one is returned by the logic implemented.
        """
        # There are three possible paths with same cost.
        self.assertIn(self.planet.shortest_path((0, 0), (4, 1)), [
            [
                ((0, 0), Direction.NORTH),
                ((0, 2), Direction.EAST),
                ((2, 2), Direction.EAST),
                ((4, 2), Direction.SOUTH),
            ],
            [
                ((0, 0), Direction.NORTH),
                ((0, 2), Direction.EAST),
                ((2, 2), Direction.SOUTH),
                ((2, 1), Direction.EAST),
            ],
            [
                ((0, 0), Direction.EAST),
                ((3, 0), Direction.NORTH),
                ((2, 1), Direction.EAST),
            ],
        ])

    def test_target_with_loop(self):
        """Check the case of a reachable target on a looped map.

        The shortest-path algorithm should not get stuck in a loop
        between two points while searching for a target nearby.

        Result: Target is reachable.
        """
        self.assertIsNotNone(self.planet.shortest_path((2, 2), (5, 1)))

    def test_target_not_reachable_with_loop(self):
        """Check the case of a non-reachable target on a looped map.

        The shortest-path algorithm should not get stuck in a loop
        between two points while searching for a target not reachable
        nearby.

        Result: Target is not reachable.
        """
        self.assertIsNone(self.planet.shortest_path((6, -1), (5, -1)))
        self.assertIsNone(self.planet.shortest_path((0, 0), (7, 0)))


if __name__ == "__main__":
    unittest.main()
