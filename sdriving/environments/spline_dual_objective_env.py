import math
import random
from collections import deque
from itertools import product

import numpy as np
import torch

from gym.spaces import Box, Discrete, Tuple
from sdriving.environments.spline_env import (
    MultiAgentOneShotSplinePredictionEnvironment,
)
from sdriving.tsim import (
    SplineModel,
    get_2d_rotation_matrix,
)


class MultiAgentIntersectionSplineAccelerationDiscreteEnvironment(
    MultiAgentOneShotSplinePredictionEnvironment
):
    def __init__(self, *args, **kwargs):
        # The action and observation spaces are tuples containing each for
        # the 2 objectives
        super(MultiAgentOneShotSplinePredictionEnvironment, self).__init__(
            *args, **kwargs
        )

    def configure_action_space(self):
        self.max_accln = 1.5
        self.action_list = torch.arange(
            -self.max_accln, self.max_accln + 0.05, step=0.25
        ).unsqueeze(1)

    def get_observation_space(self):
        return (
            super().get_observation_space(),
            super(
                MultiAgentOneShotSplinePredictionEnvironment, self
            ).get_observation_space(),
        )

    def get_action_space(self):
        self.normalization_factor = torch.as_tensor([self.max_accln])
        return (super().get_action_space(), Discrete(self.action_list.size(0)))

    def get_reward(self, *args, **kwargs):
        return super(
            MultiAgentOneShotSplinePredictionEnvironment, self
        ).get_reward(*args, **kwargs)

    @torch.no_grad()
    def step(
        self,
        stage: int,  # Possible Values [0, 1]
        action: torch.Tensor,
        render: bool = False,
        **render_kwargs
    ):
        assert stage in [0, 1]

        if stage == 1:
            return super(
                MultiAgentOneShotSplinePredictionEnvironment, self
            ).step(action, render, **render_kwargs)

        action = self.discrete_to_continuous_actions(action)
        action = action.to(self.world.device)

        rot_mat, offset = self.transformation
        action = action.view(self.nagents, -1, 2)
        radii = action[..., 0:1] * self.width / 2
        theta = action[..., 1:2] * math.pi
        del_x = torch.cos(theta) * radii
        del_y = torch.sin(theta) * radii
        path = self.cached_path + torch.cat([del_x, del_y], dim=-1)
        action = torch.baddmm(offset, path, torch.inverse(rot_mat))

        self.dynamics = SplineModel(
            action, v_lim=torch.ones(self.nagents) * 8.0
        )

        return self.get_state()
