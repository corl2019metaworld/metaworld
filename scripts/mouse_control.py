"""
Use this script to control the env with your keyboard.
For this script to work, you need to have the PyGame window in focus.

See/modify `char_to_action` to set the key-to-action mapping.
"""
import sys
import gym

import numpy as np
from multiworld.envs.mujoco.sawyer_xyz.sawyer_door_hook import SawyerDoorHookEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_door import SawyerDoorEnv

from multiworld.envs.mujoco.sawyer_xyz.sawyer_pick_and_place import \
    SawyerPickAndPlaceEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_push_and_reach_env_two_pucks import (
    SawyerPushAndReachXYDoublePuckEnv,
    SawyerPushAndReachXYZDoublePuckEnv,
)

from multiworld.envs.mujoco.sawyer_xyz.sawyer_stack_6dof import SawyerStack6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_dial_turn_6dof import SawyerDialTurn6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_lever_pull import SawyerLeverPull6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_reach_push_pick_place_6dof import SawyerReachPushPickPlace6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_laptop_close_6dof import SawyerLaptopClose6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_stick_push_6dof import SawyerStickPush6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_stick_pull_6dof import SawyerStickPull6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_hammer_6dof import SawyerHammer6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_box_open_6dof import SawyerBoxOpen6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_bin_picking_6dof import SawyerBinPicking6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_peg_insertion_side_6dof import SawyerPegInsertionSide6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_peg_insertion_topdown_6dof import SawyerPegInsertionTopdown6DOFEnv
from multiworld.envs.mujoco.sawyer_xyz.sawyer_peg_unplug_side_6dof import SawyerPegUnplugSide6DOFEnv



from robosuite.devices import SpaceMouse
from multiworld.envs.mujoco.utils import rotation
from robosuite.utils.transform_utils import mat2quat
from multiworld.envs.env_util import quat_to_zangle, zangle_to_quat


import gym
import multiworld

space_mouse = SpaceMouse()
env = SawyerPegUnplugSide6DOFEnv(random_init=True, obs_type='with_goal')
NDIM = env.action_space.low.size
lock_action = False
obs = env.reset()
action = np.zeros(10)
closed = False

while True:
    done = False
    env.render()

    state = space_mouse.get_controller_state()
    dpos, rotation, grasp, reset = (
        state["dpos"],
        state["rotation"],
        state["grasp"],
        state["reset"],
    )

    # convert into a suitable end effector action for the environment
    # current = env.get_mocap_quat()

    # desired_quat = mat2quat(rotation)
    # current_z = quat_to_zangle(current)
    # desired_z = quat_to_zangle(desired_quat)

    # # drotation = current.T.dot(rotation)  # relative rotation of desired from current
    # # dquat = T.mat2quat(drotation)
    
    # print('current', current_z)
    # print('desired', desired_z)


    # print('diff unclipped', desired_z - current_z)
    # diff = desired_z - current_z
    # print('diff', diff)

    gripper = grasp
    if gripper == 1:
        closed = not closed

    obs, reward, done, _ = env.step(np.hstack([dpos/.005, 0, closed]))
    # print(obs)

    if done:
        obs = env.reset()
