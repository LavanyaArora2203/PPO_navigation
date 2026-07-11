"""
robot.py

Defines the robot used in the navigation environment.

The robot stores:
- Position
- Velocity
- Radius
- Maximum Speed

Functions
---------
move()
reset()
distance_to_goal()
"""

from __future__ import annotations

import numpy as np


class Robot:
    """
    Represents the navigation robot.

    Parameters
    ----------
    position : tuple[float, float]
        Initial robot position.

    radius : float
        Robot radius.

    max_speed : float
        Maximum movement speed.
    """

    def __init__(
        self,
        position=(0.0, 0.0),
        radius=1.0,
        max_speed=1.0,
    ):

        # Initial position
        self.initial_position = np.array(
            position,
            dtype=np.float32,
        )

        # Current position
        self.position = self.initial_position.copy()

        # Velocity vector (vx, vy)
        self.velocity = np.zeros(
            2,
            dtype=np.float32,
        )

        # Robot size
        self.radius = radius

        # Maximum speed
        self.max_speed = max_speed

    # -------------------------------------------------
    # Move Robot
    # -------------------------------------------------

    def move(self, action: int):
        """
        Moves the robot according to a discrete action.

        Actions
        -------
        0 : Up
        1 : Down
        2 : Left
        3 : Right
        """

        if action == 0:
            self.velocity[:] = [0.0, self.max_speed]

        elif action == 1:
            self.velocity[:] = [0.0, -self.max_speed]

        elif action == 2:
            self.velocity[:] = [-self.max_speed, 0.0]

        elif action == 3:
            self.velocity[:] = [self.max_speed, 0.0]

        else:
            raise ValueError(
                f"Invalid action {action}. "
                "Expected one of {0,1,2,3}."
            )

        self.position += self.velocity

    # -------------------------------------------------
    # Reset Robot
    # -------------------------------------------------

    def reset(self):
        """
        Reset robot to its initial position.
        """

        self.position = self.initial_position.copy()

        self.velocity = np.zeros(
            2,
            dtype=np.float32,
        )

    # -------------------------------------------------
    # Distance To Goal
    # -------------------------------------------------

    def distance_to_goal(self, goal_position):
        """
        Compute Euclidean distance to goal.

        Parameters
        ----------
        goal_position : array-like

        Returns
        -------
        float
        """

        goal_position = np.asarray(
            goal_position,
            dtype=np.float32,
        )

        return np.linalg.norm(
            self.position - goal_position
        )

    # -------------------------------------------------
    # Set Position
    # -------------------------------------------------

    def set_position(self, x, y):
        """
        Manually set robot position.
        """

        self.position[:] = [x, y]

    # -------------------------------------------------
    # Get Position
    # -------------------------------------------------

    def get_position(self):
        """
        Returns robot position.
        """

        return self.position.copy()

    # -------------------------------------------------
    # Get Velocity
    # -------------------------------------------------

    def get_velocity(self):
        """
        Returns robot velocity.
        """

        return self.velocity.copy()

    # -------------------------------------------------
    # String Representation
    # -------------------------------------------------

    def __repr__(self):

        return (
            f"Robot("
            f"position={self.position}, "
            f"velocity={self.velocity}, "
            f"radius={self.radius}, "
            f"max_speed={self.max_speed})"
        )