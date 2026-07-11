"""
moving_obstacle.py

Defines a moving circular obstacle.

The obstacle contains:
- Position
- Velocity
- Direction
- Radius

Functions
---------
update_position()
bounce_from_wall()
reset()

Author: Your Name
"""

from __future__ import annotations

import numpy as np


class MovingObstacle:
    """
    Represents a moving circular obstacle.
    """

    def __init__(
        self,
        world_width: float,
        world_height: float,
        position=(50.0, 50.0),
        direction=(1.0, 0.0),
        speed=1.0,
        radius=2.0,
    ):
        """
        Parameters
        ----------
        world_width : float
            Width of world.

        world_height : float
            Height of world.

        position : tuple
            Initial position.

        direction : tuple
            Initial movement direction.

        speed : float
            Movement speed.

        radius : float
            Obstacle radius.
        """

        self.world_width = world_width
        self.world_height = world_height

        self.initial_position = np.array(
            position,
            dtype=np.float32,
        )

        self.position = self.initial_position.copy()

        self.direction = np.array(
            direction,
            dtype=np.float32,
        )

        # Normalize direction
        norm = np.linalg.norm(self.direction)

        if norm != 0:
            self.direction /= norm

        self.speed = speed

        self.radius = radius

        self.velocity = self.direction * self.speed

    # -------------------------------------------------
    # Update Position
    # -------------------------------------------------

    def update_position(self):
        """
        Move the obstacle by one timestep.
        """

        self.position += self.velocity

        self.bounce_from_wall()

    # -------------------------------------------------
    # Bounce From Walls
    # -------------------------------------------------

    def bounce_from_wall(self):
        """
        Reverse direction when obstacle
        reaches world boundaries.
        """

        # Left wall
        if self.position[0] <= self.radius:
            self.position[0] = self.radius
            self.velocity[0] *= -1

        # Right wall
        elif self.position[0] >= (
            self.world_width - self.radius
        ):
            self.position[0] = (
                self.world_width - self.radius
            )
            self.velocity[0] *= -1

        # Bottom wall
        if self.position[1] <= self.radius:
            self.position[1] = self.radius
            self.velocity[1] *= -1

        # Top wall
        elif self.position[1] >= (
            self.world_height - self.radius
        ):
            self.position[1] = (
                self.world_height - self.radius
            )
            self.velocity[1] *= -1

    # -------------------------------------------------
    # Reset
    # -------------------------------------------------

    def reset(self):
        """
        Reset obstacle to initial position.
        """

        self.position = self.initial_position.copy()

        direction = self.direction.copy()

        norm = np.linalg.norm(direction)

        if norm != 0:
            direction /= norm

        self.velocity = direction * self.speed

    # -------------------------------------------------
    # Set Position
    # -------------------------------------------------

    def set_position(self, x, y):

        self.position[:] = [x, y]

    # -------------------------------------------------
    # Get Position
    # -------------------------------------------------

    def get_position(self):

        return self.position.copy()

    # -------------------------------------------------
    # Get Velocity
    # -------------------------------------------------

    def get_velocity(self):

        return self.velocity.copy()

    # -------------------------------------------------
    # Check Collision
    # -------------------------------------------------

    def check_collision(
        self,
        robot_position,
        robot_radius,
    ):
        """
        Check collision with robot.
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

    # -------------------------------------------------
    # String Representation
    # -------------------------------------------------

    def __repr__(self):

        return (
            f"MovingObstacle("
            f"position={self.position}, "
            f"velocity={self.velocity}, "
            f"radius={self.radius})"
        )