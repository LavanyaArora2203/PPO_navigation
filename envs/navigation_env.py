import gymnasium as gym
import numpy as np

from gymnasium import spaces


class NavigationEnv(gym.Env):

    metadata = {"render_modes": ["human"]}

    def __init__(self):

        super().__init__()

        self.action_space = spaces.Discrete(4)

        self.observation_space = spaces.Box(
            low=0,
            high=100,
            shape=(4,),
            dtype=np.float32
        )
        self.robot_speed = 1.0

        self.robot_position = np.zeros(2, dtype=np.float32)
        self.goal_position = np.zeros(2, dtype=np.float32)

        self.max_steps = 300
        self.current_step = 0
        self.observation_space = spaces.Box(
            low=np.array([
                0.0, 0.0,          # Robot Position
                0.0, 0.0,          # Goal Position
                0.0, 0.0,          # Obstacle Position
                -5.0, -5.0         # Obstacle Velocity
            ], dtype=np.float32),

            high=np.array([
                100.0, 100.0,
                100.0, 100.0,
                100.0, 100.0,
                5.0, 5.0
            ], dtype=np.float32),

            dtype=np.float32
        )

    def reset(self, seed=None, options=None):

        super().reset(seed=seed)

        self.robot_position = np.array([10, 10], dtype=np.float32)
        self.goal_position = np.array([90, 90], dtype=np.float32)

        self.current_step = 0

        # observation = np.concatenate(
        #     (self.robot_position, self.goal_position)
        # )
        observation = self._get_observation()
        info = {}

        return observation, info

    def step(self, action):

        self.current_step += 1
        if action == 0:
        # Up
            self.robot_position[1] += self.robot_speed

        elif action == 1:
        # Down
            self.robot_position[1] -= self.robot_speed

        elif action == 2:
        # Left
            self.robot_position[0] -= self.robot_speed

        elif action == 3:
        # Right
            self.robot_position[0] += self.robot_speed

    # ---------------------------------
    # Keep Robot Inside World
    # ---------------------------------

        self.robot_position[0] = np.clip(
            self.robot_position[0],
            0,
            self.world_width
        )

        self.robot_position[1] = np.clip(
        self.robot_position[1],
        0,
        self.world_height
    )

        observation = self._get_observation()

        reward = 0.0

        terminated = False

        truncated = self.current_step >= self.max_steps

        info = {}

        return (
            observation,
            reward,
            terminated,
            truncated,
            info
        )

    def render(self):

        print(
            f"Robot: {self.robot_position}, "
            f"Goal: {self.goal_position}"
        )

    def close(self):
        pass
    def _get_observation(self):
        """
    Creates the observation returned to the PPO agent.

    Observation Format:

    [
        robot_x,
        robot_y,

        goal_x,
        goal_y,

        obstacle_x,
        obstacle_y,

        obstacle_vx,
        obstacle_vy
    ]
    """

        observation = np.concatenate([
            self.robot_position,
            self.goal_position,
            self.obstacle_position,
            self.obstacle_velocity
        ]).astype(np.float32)

        return observation

    