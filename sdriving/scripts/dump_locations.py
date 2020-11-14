import argparse
import json
import math
from copy import deepcopy

import pandas as pd
import torch

from sdriving.scripts.rollout import RolloutSimulator
from sdriving.tsim import angle_normalize


class RolloutPositionDumper(RolloutSimulator):
    def __init__(self, fname: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fname = self.save_dir / fname
        self.episode_number = 0

        # Records will be saved in pickle format.
        # It will be a list of list of agent_positions, traffic_signals
        self.record = []
        self.cur_record = []

    def _action_observation_hook(
        self, action, observation, aids, *args, **kwargs
    ):
        self.cur_record.append(
            (
                deepcopy(self.env.world.vehicles),
                deepcopy(self.env.world.traffic_signals),
                self.env.paths[self.env.chosen_world]
                if hasattr(self.env, "paths")
                else (self.env.width, self.env.length),
            )
        )

    def _new_rollout_hook(self):
        if len(self.cur_record) > 0:
            self.record.append(self.cur_record)
        self.cur_record = []
        self.episode_number += 1

    def _post_completion_hook(self):
        torch.save(self.record, self.fname)

        print(f"Saved Record to {self.fname}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--save-dir", type=str, required=True)
    parser.add_argument("-f", "--fname", type=str, required=True)
    parser.add_argument("-m", "--model-save-path", type=str, default=None)
    parser.add_argument("-tep", "--num-test-episodes", type=int, default=1)
    parser.add_argument("--env", type=str, required=True)
    parser.add_argument("--env-kwargs", type=json.loads, default={})
    parser.add_argument(
        "--model-type", default=None, choices=["one_step", "two_step", None]
    )
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    simulator = RolloutPositionDumper(
        args.fname,
        args.env,
        args.env_kwargs,
        device,
        args.save_dir,
        args.model_save_path,
        args.model_type,
    )

    simulator.rollout(args.num_test_episodes, args.verbose, not args.no_render)