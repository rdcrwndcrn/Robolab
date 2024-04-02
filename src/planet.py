#!/usr/bin/env python3

# ATTENTION: Do not import the ev3dev.ev3 module in this file.
from enum import IntEnum, unique
from math import inf
from pprint import pprint
from random import choice
from typing import Final, Optional


@unique
class Direction(IntEnum):
    """The orientations on the planet set by the mother ship."""
    NORTH = 0
    EAST = 90
    SOUTH = 180
    WEST = 270


def opposite(direction: Direction) -> Direction:
    """Return the opposite direction of `direction`."""
    return (direction + 180) % 360


Weight = int
"""Weight of a given path (received from the server).

Value:   `-1` if blocked path
        > `0` for all other paths
        never `0`
"""
BLOCKED: Final[Weight] = -1


class Planet:
    """The planet map representation with nodes, paths and their weights."""

    __slots__ = ("_paths", "_known_node_directions")

    # DO NOT EDIT THE METHOD SIGNATURE
    def __init__(self) -> None:
        """Initialize the data structure."""
        # The registered existing paths on the planet, probably incomplete.
        self._paths: dict[
            tuple[int, int],
            dict[
                Direction,
                tuple[tuple[int, int], Direction, Weight]
            ]
        ] = {}
        # The directions available at all visited nodes.
        self._known_node_directions: dict[
            tuple[int, int],
            set[Direction]
        ] = {}

    def exploration_completed(self, current_node: tuple[int, int]) -> bool:
        """Return whether planet exploration is completed.

        This checks whether all reachable nodes from the `current_node`
        have full path information, i. e. all the paths to them have
        either been visited or the robot has received information about
        them from the server.

        Only useful after an initial call to `add_path` or
        `set_available_node_directions` as the `current_node` is assumed
        to be known on the map, else a `KeyError` is raised.
        """
        # Check whether there is no reachable unexplored node left.
        # TODO: Check whether really needed (also included in `next_direction`).
        return self._shortest_path(current_node) is None

    # DO NOT EDIT THE METHOD SIGNATURE
    def add_path(
        self,
        start: tuple[tuple[int, int], Direction],
        target: tuple[tuple[int, int], Direction],
        weight: Weight,
    ) -> None:
        """Add a bidirectional path from `start` to `end` with `weight`.

        Example:

        >>> planet.add_path(((0, 3), Direction.NORTH), ((0, 3), Direction.WEST), 1)
        """
        for (start, start_direction), (target, target_direction) \
                in ((start, target), (target, start)):
            try:
                record = self._paths[start]
            except KeyError:
                # No prior paths at node `start` registered.
                record = self._paths[start] = {}

            record[start_direction] = (target, target_direction, weight)

    def set_available_node_directions(
        self,
        node: tuple[int, int],
        directions: set[Direction],
    ) -> None:
        """Set which `directions` exist at `node`.

        This method should be called after the robot has scanned the
        paths at `node`, as it is assumed to have visited it.
        """
        self._known_node_directions[node] = directions

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
                    Direction.WEST: ((0, 3), Direction.NORTH, 1),
                },
                (1, 3): {
                    Direction.WEST: ((0, 3), Direction.EAST, 2),
                    ...
                },
                ...
            }
        """
        return self._paths

    def is_completely_explored(self, node: tuple[int, int]) -> bool:
        """Return whether the given `node` is fully explored.

        This checks whether `node` was already visited, so the number of
        paths from it is known, and this number matches the number of
        already completed paths at this node (either by the robot itself
        or with the help of the server) or if it was not visited, but
        all 4 possible directions are already fully explored, so a visit
        is unnecessary.

        It is assumed that `node` is valid, else a `KeyError` will be
        raised.
        """
        return (
            (visited := node in self._known_node_directions)
            and len(self._known_node_directions[node])
                == (completed_directions_number := len(self._paths[node]))
            or not visited
            and completed_directions_number == len(Direction)
        )

    def next_direction(
        self,
        start: tuple[int, int],
        target: Optional[tuple[int, int]] = None
    ) -> Optional[Direction]:
        """Return the next direction to head for from `start`.

        If `target` is not `None` and is known how to reach, this tries
        to head to it as fast as possible, else, the direction to the
        next unexplored path or the next unexplored direction is
        returned. If none of the above are found, `None` is returned,
        signalling the completion of exploration.

        Both `start` and `target` (if not `None`) are assumed to be
        valid coordinates, else a `KeyError` will be raised.
        """
        random_direction = choice([
            direction
            for direction in self._known_node_directions[start]
            if direction not in self._paths[start]
        ])
        if target is None and not self.is_completely_explored(start):
            # Choose randomly one of the remaining unexplored
            # directions.
            return random_direction
        else:
            shortest_path = self._shortest_path(start, target)

            if shortest_path is None and target is not None:
                # `target` not yet reachable, continue exploring normally.
                shortest_path = self._shortest_path(start)

            print(f"in next_direction({start = }, {target = }): {shortest_path = }")

            # Recheck in case `shortest_path` got updated.
            if shortest_path is None:
                # No direction found, exploration completed.
                return None
            elif not shortest_path:
                # Shortest path is empty (`[]`), meaning the `target` is
                # not reachable and the current node is not fully
                # explored, so choose one of the remaining unexplored
                # directions of it.
                return random_direction
            else:
                # Return the direction towards our next target.
                return shortest_path[0][1]

    def _shortest_path(
        self,
        start: tuple[int, int],
        target: Optional[tuple[int, int]] = None
    ) -> Optional[list[tuple[tuple[int, int], Direction]]]:
        """Return the shortest path either to `target` or the next unexplored node.

        If `target` is `None`, returns the shortest path from `start` to
        the next unexplored node, else the shortest path from `start` to
        `target`.

        If the `target` or the next unexplored node is the same as
        `start`, returns `[]`, else if no path is found, returns `None`.
        """
        if (start not in self._paths
                or target is not None and target not in self._paths):
            # We cannot know a path as we don't even know the node.
            return None

        # Stores the resulting predecessor nodes forming the shortest path to
        # the desired target node.
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

            min_node_paths = self._paths[min_node]

            # If this node is our target or meets our requirements, we
            # have found a shortest path and are finished.
            if (target is not None and min_node == target
                    or target is None
                    and not self.is_completely_explored(min_node)):
                # Set target to current node in case we are searching
                # for the next unexplored node.
                target = min_node
                break

            # Add or update this node's neighbors if shortest path to
            # them not already found and the path to them is not blocked.
            for direction, (neighbor, _, weight) in min_node_paths.items():
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
            # No target found (`while` loop not aborted).
            return None

        print(f"in _shortest_path({start = }, {target = }) {shortest_paths = } {nodes_to_check = }")
        pprint(self._paths)

        # Reconstruct shortest path.
        shortest_path: list[tuple[tuple[int, int], Direction]] = []
        # If `start` is the same as `target`, this results in an empty `list`.
        while (predecessor := shortest_paths[target])[0] is not None:
            # Insert at the beginning as unroll backwards.
            shortest_path.insert(0, predecessor)
            target = predecessor[0]

        return shortest_path

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
        return self._shortest_path(start, target)
