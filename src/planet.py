#!/usr/bin/env python3

# ATTENTION: Do not import the ev3dev.ev3 module in this file.
from enum import IntEnum, unique
from typing import Final, Optional
from queue import PriorityQueue


@unique
class Direction(IntEnum):
    """The orientations on the planet set by the mother ship."""
    NORTH = 0
    EAST = 90
    SOUTH = 180
    WEST = 270


Weight = int
"""Weight of a given path (received from the server).

Value:   `-1` if blocked path
        > `0` for all other paths
        never `0`
"""
BLOCKED: Final = -1


class Planet:
    """The planet map representation with nodes, paths and their weights."""

    # DO NOT EDIT THE METHOD SIGNATURE
    def __init__(self):
        """Initialize the data structure."""
        self.paths = {}

    # DO NOT EDIT THE METHOD SIGNATURE
    def add_path(
        self,
        start: tuple[tuple[int, int], Direction],
        target: tuple[tuple[int, int], Direction],
        weight: Weight,
    ):
        """Add a bidirectional path from `start` to `end` with `weight`.

        Example:

        >>> planet.add_path(((0, 3), Direction.NORTH), ((0, 3), Direction.WEST), 1)
        """
        for (start, start_direction), (target, target_direction) \
                in ((start, target), (target, start)):
            try:
                record = self.paths[start]
            except KeyError:
                # No prior paths at node `start` registered.
                record = self.paths[start] = {}

            record[start_direction] = (target, target_direction, weight)

    # DO NOT EDIT THE METHOD SIGNATURE
    def get_paths(self) -> dict[
        tuple[int, int],
        dict[
            Direction,
            tuple[tuple[int, int], Direction, Weight]
        ]
    ]:
        """Returns all known paths.

        Example:

            {
                (0, 3): {
                    Direction.NORTH: ((0, 3), Direction.WEST, 1),
                    Direction.EAST: ((1, 3), Direction.WEST, 2),
                    Direction.WEST: ((0, 3), Direction.NORTH, 1)
                },
                (1, 3): {
                    Direction.WEST: ((0, 3), Direction.EAST, 2),
                    ...
                },
                ...
            }
        """
        return self.paths

    # DO NOT EDIT THE METHOD SIGNATURE
    def shortest_path(
        self,
        start: tuple[int, int],
        target: tuple[int, int],
    ) -> Optional[list[tuple[tuple[int, int], Direction]]]:
        """Returns (one of) the shortest known path between two nodes.

        If there is no known path between the two nodes, returns `None`.

        Examples:

        >>> shortest_path((0,0), (2,2))
        [((0, 0), Direction.EAST), ((1, 0), Direction.NORTH)]
        >>> shortest_path((0,0), (1,2))
        None
        """
        shortest_paths: list[tuple[tuple[int, int], Direction]] = []
        nodes_to_check: PriorityQueue[
            tuple[Weight, tuple[int, int], Optional[tuple[int, int]]]
        ] = PriorityQueue()
        try:
            nodes_to_check.put((0, start, None))
        except KeyError:
            # `start` not known, so no path can be found.
            return None

        while not nodes_to_check.empty():
            ...
