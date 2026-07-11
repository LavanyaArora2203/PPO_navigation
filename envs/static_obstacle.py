"""
static_obstacle.py

Defines a static obstacle for the navigation environment.

A static obstacle has:
- Position
- Radius

It never moves during an episode.
"""

from __future__ import annotations

import numpy as np


class StaticObstacle:
    """
    Represents a static circular obstacle.
    """

    def __init__(
        self,
        position=(0.0, 0.0),
        radius=2.0,
    ):
        """
        Parameters
        ----------
        position : tuple(float, float)
            Initial obstacle position.

        radius : float
            Radius of the obstacle.
        """

        self.position = np.array(
            position,
            dtype=np.float32,
        )

        self.radius = radius

    # --------------------------------------------------
    # Get Position
    # --------------------------------------------------

    def get_position(self):
        """
        Returns the obstacle position.
        """

        return self.position.copy()

    # --------------------------------------------------
    # Set Position
    # --------------------------------------------------

    def set_position(
        self,
        x: float,
        y: float,
    ):
        """
        Manually set obstacle position.
        """

        self.position[:] = [x, y]

    # --------------------------------------------------
    # Collision Check
    # --------------------------------------------------

    def check_collision(
        self,
        robot_position,
        robot_radius,
    ):
        """
        Check whether the robot collides
        with this obstacle.

        Parameters
        ----------
        robot_position : array-like

        robot_radius : float

        Returns
        -------
        bool
        """

        robot_position = np.asarray(
            robot_position,
            dtype=np.float32,
        )

        distance = np.linalg.norm(
            self.position - robot_position
        )

        return distance <= (
            self.radius + robot_radius
        )

    # --------------------------------------------------
    # Reset
    # --------------------------------------------------

    def reset(self):
        """
        Static obstacles never move.

        Included for interface consistency.
        """

        pass

    # --------------------------------------------------
    # Update
    # --------------------------------------------------

    def update(self):
        """
        Static obstacle remains stationary.

        Included so both static and moving
        obstacles share a similar interface.
        """

        pass

    # --------------------------------------------------
    # String Representation
    # --------------------------------------------------

    def __repr__(self):

        return (
            f"StaticObstacle("
            f"position={self.position}, "
            f"radius={self.radius})"
        )