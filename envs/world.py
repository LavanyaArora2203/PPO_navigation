"""
world.py

Defines the 2D simulation world used by the navigation environment.
The world stores global parameters such as dimensions, robot size,
obstacle size, goal size, and episode length.

Author: Your Name
"""

from dataclasses import dataclass


@dataclass
class WorldConfig:
    """
    Configuration of the navigation world.

    Attributes
    ----------
    width : float
        Width of the world.

    height : float
        Height of the world.

    robot_radius : float
        Radius of the robot.

    obstacle_radius : float
        Default radius of obstacles.

    goal_radius : float
        Radius of the goal region.

    max_episode_steps : int
        Maximum number of simulation steps before the episode terminates.
    """

    width: float = 100.0
    height: float = 100.0

    robot_radius: float = 1.0
    obstacle_radius: float = 2.0
    goal_radius: float = 2.0

    max_episode_steps: int = 300


class World:
    """
    Represents the 2D navigation world.

    This class stores all global parameters of the environment.
    It does not contain robot or obstacle logic.
    """

    def __init__(self, config: WorldConfig | None = None):

        if config is None:
            config = WorldConfig()

        self.config = config

        self.width = config.width
        self.height = config.height

        self.robot_radius = config.robot_radius
        self.obstacle_radius = config.obstacle_radius
        self.goal_radius = config.goal_radius

        self.max_episode_steps = config.max_episode_steps

    def is_inside_world(self, x: float, y: float) -> bool:
        """
        Check whether a point lies inside the world boundaries.

        Parameters
        ----------
        x : float
            x-coordinate

        y : float
            y-coordinate

        Returns
        -------
        bool
            True if inside the world.
        """

        return (
            0.0 <= x <= self.width
            and
            0.0 <= y <= self.height
        )

    def clip_position(self, x: float, y: float):
        """
        Clips a position to remain inside the world.

        Returns
        -------
        tuple
            (x, y)
        """

        x = max(0.0, min(x, self.width))
        y = max(0.0, min(y, self.height))

        return x, y

    def get_size(self):
        """
        Returns world dimensions.

        Returns
        -------
        tuple
            (width, height)
        """

        return self.width, self.height

    def __str__(self):

        return (
            f"World("
            f"width={self.width}, "
            f"height={self.height}, "
            f"robot_radius={self.robot_radius}, "
            f"obstacle_radius={self.obstacle_radius}, "
            f"goal_radius={self.goal_radius}, "
            f"max_episode_steps={self.max_episode_steps})"
        )