#!/usr/bin/env python3

# ATTENTION: Do not import the ev3dev.ev3 module in this file.
from enum import IntEnum, unique
from math import inf
from typing import Final, Optional


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
        """Return all known paths.

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
        """Return (one of) the shortest known path between two nodes.

        If there is no known path between the two nodes, returns `None`.
        If we already are at the `target` node, i. e. `start` is the
        same as `target`, returns an empty list `[]`.

        Examples:

        >>> shortest_path((0,0), (2,2))
        [((0, 0), Direction.EAST), ((1, 0), Direction.NORTH)]
        >>> shortest_path((0,0), (1,2))
        None
        """
        for node in (start, target):
            if node not in self.paths:
                # We cannot know a path as we don't even know the node.
                return None

        # Stores the resulting predecessor nodes forming the shortest path to
        # the current node.
        shortest_paths: dict[
            tuple[int, int],
            tuple[Optional[tuple[int, int]], Optional[Direction]]
        ] = {}
        # A dictionary keeping track of the new neighbor nodes to check,
        # storing the current sum of weights to the node, the node
        # coordinates and the previous node we came from.
        # This turns out to be a bit faster than using `heapq` in my
        # measurements. Also `queue.PriorityQueue` is not really applicable,
        # since we can't iterate over its elements in order to update already
        # added ones.
        nodes_to_check: dict[
            tuple[int, int],
            tuple[Weight, Optional[tuple[int, int]], Optional[Direction]]
        ] = {}
        # Start with the start node, coming from no other node.
        nodes_to_check[start] = (0, None, None)

        while nodes_to_check:   # while `nodes_to_check` is not empty
            # Find node with minimum weight.
            min_weight = inf
            min_node = None
            min_node_pred = None
            min_node_dir = None
            for node, (weight, predecessor, direction) in nodes_to_check.items():
                if weight < min_weight:
                    min_weight = weight
                    min_node = node
                    min_node_pred = predecessor
                    min_node_dir = direction

            # Shortest path to this node found, add it to our dict.
            shortest_paths[min_node] = (min_node_pred, min_node_dir)
            # ... and remove it from our checklist.
            del nodes_to_check[min_node]

            # If this node is our target, we have found a shortest path
            # and are finished.
            if min_node == target:
                break

            # Add or update this node's neighbors if shortest path to
            # them not already found and the path to them is not blocked.
            for direction, (neighbor, _, weight) in self.paths[min_node].items():
                if neighbor not in shortest_paths and weight != BLOCKED:
                    new_record = (min_weight + weight, min_node, direction)
                    try:
                        neighbor_record = nodes_to_check[neighbor]
                    except KeyError:
                        nodes_to_check[neighbor] = new_record
                    else:
                        if new_record[0] < neighbor_record[0]:
                            # Only update if weight is smaller.
                            nodes_to_check[neighbor] = new_record
        else:
            # Target not found (`while` loop not aborted).
            return None

        # Reconstruct shortest path.
        shortest_path: list[tuple[tuple[int, int], Direction]] = []
        # If `start` is the same as `target`, this results in an empty `list`.
        while (predecessor := shortest_paths[target])[0] is not None:
            # Insert at the beginning as unroll backwards.
            shortest_path.insert(0, predecessor)
            target = predecessor[0]

        return shortest_path
