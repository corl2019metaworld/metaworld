from collections import OrderedDict
import numpy as np
from gym.spaces import  Dict , Box


from multiworld.envs.env_util import get_stat_in_paths, \
    create_stats_ordered_dict, get_asset_full_path
from multiworld.core.multitask_env import MultitaskEnv
from multiworld.envs.mujoco.sawyer_xyz.base import SawyerXYZEnv

from pyquaternion import Quaternion
from multiworld.envs.mujoco.utils.rotation import euler2quat
from multiworld.envs.mujoco.sawyer_xyz.base import OBS_TYPE


class SawyerHandInsert6DOFEnv(SawyerXYZEnv):
    def __init__(
            self,
            hand_low=(-0.5, 0.40, -0.15),
            hand_high=(0.5, 1, 0.5),
            obj_low=(-0.1, 0.6, 0.02),
            obj_high=(0.1, 0.7, 0.02),
            random_init=False,
            obs_type='plain',
            tasks = [{'goal': np.array([0., 0.84, -0.08]),  'obj_init_pos':np.array([0, 0.6, 0.02]), 'obj_init_angle': 0.3}], 
            goal_low=(-0.1, 0.8, 0.05),
            goal_high=(0.1, 0.9, 0.3),
            hand_init_pos = (0, 0.6, 0.2),
            rotMode='fixed',#'fixed',
            multitask=False,
            multitask_num=1,
            if_render=True,
            **kwargs
    ):
        self.quick_init(locals())
        SawyerXYZEnv.__init__(
            self,
            frame_skip=5,
            action_scale=1./100,
            hand_low=hand_low,
            hand_high=hand_high,
            model_name=self.model_name,
            **kwargs
        )

        assert obs_type in OBS_TYPE
        if multitask:
            obs_type = 'with_goal_and_id'
        self.obs_type = obs_type

        if obj_low is None:
            obj_low = self.hand_low

        if goal_low is None:
            goal_low = self.hand_low

        if obj_high is None:
            obj_high = self.hand_high
        
        if goal_high is None:
            goal_high = self.hand_high

        self.random_init = random_init
        self.max_path_length = 150#150
        self.tasks = tasks
        self.num_tasks = len(tasks)
        self.rotMode = rotMode
        self.hand_init_pos = np.array(hand_init_pos)
        self.multitask = multitask
        self.multitask_num = multitask_num
        self._state_goal_idx = np.zeros(self.multitask_num)
        self.if_render = if_render
        if rotMode == 'fixed':
            self.action_space = Box(
                np.array([-1, -1, -1, -1]),
                np.array([1, 1, 1, 1]),
            )
        elif rotMode == 'rotz':
            self.action_rot_scale = 1./50
            self.action_space = Box(
                np.array([-1, -1, -1, -np.pi, -1]),
                np.array([1, 1, 1, np.pi, 1]),
            )
        elif rotMode == 'quat':
            self.action_space = Box(
                np.array([-1, -1, -1, 0, -1, -1, -1, -1]),
                np.array([1, 1, 1, 2*np.pi, 1, 1, 1, 1]),
            )
        else:
            self.action_space = Box(
                np.array([-1, -1, -1, -np.pi/2, -np.pi/2, 0, -1]),
                np.array([1, 1, 1, np.pi/2, np.pi/2, np.pi*2, 1]),
            )
        self.obj_and_goal_space = Box(
            np.hstack((obj_low, goal_low)),
            np.hstack((obj_high, goal_high)),
        )
        self.goal_space = Box(np.array(goal_low), np.array(goal_high))
        if not multitask and self.obs_type == 'with_goal_id':
            self.observation_space = Box(
                np.hstack((self.hand_low, obj_low, np.zeros(len(tasks)))),
                np.hstack((self.hand_high, obj_high, np.ones(len(tasks)))),
            )
        elif not multitask and self.obs_type == 'plain':
            self.observation_space = Box(
                np.hstack((self.hand_low, obj_low,)),
                np.hstack((self.hand_high, obj_high,)),
            )
        elif not multitask and self.obs_type == 'with_goal':
            self.observation_space = Box(
                np.hstack((self.hand_low, obj_low, goal_low)),
                np.hstack((self.hand_high, obj_high, goal_high)),
            )
        else:
            self.observation_space = Box(
                np.hstack((self.hand_low, obj_low, goal_low, np.zeros(multitask_num))),
                np.hstack((self.hand_high, obj_high, goal_high, np.zeros(multitask_num))),
            )
        self.reset()
        # self.observation_space = Dict([
        #     ('state_observation', self.hand_and_obj_space),
        #     ('state_desired_goal', self.goal_space),
        #     ('state_achieved_goal', self.goal_space),
        # ])


    def get_goal(self):
        return {
            'state_desired_goal': self._state_goal,
    }

    @property
    def model_name(self):     

        return get_asset_full_path('sawyer_xyz/sawyer_table_with_hole.xml')
        #return get_asset_full_path('sawyer_xyz/pickPlace_fox.xml')

    def viewer_setup(self):
        # top view
        # self.viewer.cam.trackbodyid = 0
        # self.viewer.cam.lookat[0] = 0
        # self.viewer.cam.lookat[1] = 1.0
        # self.viewer.cam.lookat[2] = 0.5
        # self.viewer.cam.distance = 0.6
        # self.viewer.cam.elevation = -45
        # self.viewer.cam.azimuth = 270
        # self.viewer.cam.trackbodyid = -1
        # side view
        self.viewer.cam.trackbodyid = 0
        self.viewer.cam.lookat[0] = 0.2
        self.viewer.cam.lookat[1] = 0.75
        self.viewer.cam.lookat[2] = 0.4
        self.viewer.cam.distance = 0.4
        self.viewer.cam.elevation = -55
        self.viewer.cam.azimuth = 180
        self.viewer.cam.trackbodyid = -1

    def step(self, action):
        if self.if_render:
            self.render()
        # self.set_xyz_action_rot(action[:7])
        if self.rotMode == 'euler':
            action_ = np.zeros(7)
            action_[:3] = action[:3]
            action_[3:] = euler2quat(action[3:6])
            self.set_xyz_action_rot(action_)
        elif self.rotMode == 'fixed':
            self.set_xyz_action(action[:3])
        elif self.rotMode == 'rotz':
            self.set_xyz_action_rotz(action[:4])
        else:
            self.set_xyz_action_rot(action[:7])
        self.do_simulation([action[-1], -action[-1]])
        # The marker seems to get reset every time you do a simulation
        self._set_goal_marker(self._state_goal)
        ob = self._get_obs()
        obs_dict = self._get_obs_dict()
        reward, reachDist = self.compute_reward(action, obs_dict)
        self.curr_path_length +=1
        #info = self._get_info()
        if self.curr_path_length == self.max_path_length:
            done = True
        else:
            done = False
        return ob, reward, done, {'reachDist': reachDist, 'goalDist': None, 'epRew' : reward, 'pickRew':None, 'success': float(reachDist <= 0.05)}
   
    def _get_obs(self):
        hand = self.get_endeff_pos()
        objPos =  self.data.get_geom_xpos('objGeom')
        flat_obs = np.concatenate((hand, objPos))
        if self.obs_type == 'with_goal_and_id':
            return np.concatenate([
                    flat_obs,
                    self._state_goal,
                    self._state_goal_idx
                ])
        elif self.obs_type == 'with_goal':
            return np.concatenate([
                    flat_obs,
                    self._state_goal
                ])
        elif self.obs_type == 'plain':
            return np.concatenate([flat_obs,])  # TODO ZP do we need the concat?
        else:
            return np.concatenate([flat_obs, self._state_goal_idx])

    def _get_obs_dict(self):
        hand = self.get_endeff_pos()
        objPos =  self.data.get_geom_xpos('objGeom')
        flat_obs = np.concatenate((hand, objPos))
        if self.multitask:
            assert hasattr(self, '_state_goal_idx')
            return np.concatenate([
                    flat_obs,
                    self._state_goal_idx
                ])
        return dict(
            state_observation=flat_obs,
            state_desired_goal=self._state_goal,
            state_achieved_goal=objPos,
        )

    def _get_info(self):
        pass
    
    def _set_goal_marker(self, goal):
        """
        This should be use ONLY for visualization. Use self._state_goal for
        logging, learning, etc.
        """
        self.data.site_xpos[self.model.site_name2id('goal')] = (
            np.concatenate((goal[:2], [self.obj_init_pos[-1]]))
        )

    def _set_objCOM_marker(self):
        """
        This should be use ONLY for visualization. Use self._state_goal for
        logging, learning, etc.
        """
        objPos =  self.data.get_geom_xpos('objGeom')
        self.data.site_xpos[self.model.site_name2id('objSite')] = (
            objPos
        )
    

    def _set_obj_xyz_quat(self, pos, angle):
        quat = Quaternion(axis = [0,0,1], angle = angle).elements
        qpos = self.data.qpos.flat.copy()
        qvel = self.data.qvel.flat.copy()
        qpos[9:12] = pos.copy()
        qpos[12:16] = quat.copy()
        qvel[9:15] = 0
        self.set_state(qpos, qvel)


    def _set_obj_xyz(self, pos):
        qpos = self.data.qpos.flat.copy()
        qvel = self.data.qvel.flat.copy()
        qpos[9:12] = pos.copy()
        qvel[9:15] = 0
        self.set_state(qpos, qvel)


    def sample_goals(self, batch_size):
        #Required by HER-TD3
        goals = []
        for i in range(batch_size):
            task = self.tasks[np.random.randint(0, self.num_tasks)]
            goals.append(task['goal'])
        return {
            'state_desired_goal': goals,
        }


    def sample_task(self):
        self.task_idx = np.random.randint(0, self.num_tasks)
        return self.tasks[self.task_idx]

    def adjust_initObjPos(self, orig_init_pos):
        #This is to account for meshes for the geom and object are not aligned
        #If this is not done, the object could be initialized in an extreme position
        diff = self.get_body_com('obj')[:2] - self.data.get_geom_xpos('objGeom')[:2]
        adjustedPos = orig_init_pos[:2] + diff

        #The convention we follow is that body_com[2] is always 0, and geom_pos[2] is the object height
        return [adjustedPos[0], adjustedPos[1],self.data.get_geom_xpos('objGeom')[-1]]


    def reset_model(self):
        self._reset_hand()
        task = self.sample_task()
        self._state_goal = np.array(task['goal'])
        self.obj_init_pos = self.adjust_initObjPos(task['obj_init_pos'])
        self.obj_init_angle = task['obj_init_angle']
        self.objHeight = self.data.get_geom_xpos('objGeom')[2]
        if self.random_init:
            goal_pos = np.random.uniform(
                self.obj_and_goal_space.low,
                self.obj_and_goal_space.high,
                size=(self.obj_and_goal_space.low.size),
            )
            while np.linalg.norm(goal_pos[:2] - self._state_goal[:2]) < 0.15:
                goal_pos = np.random.uniform(
                    self.obj_and_goal_space.low,
                    self.obj_and_goal_space.high,
                    size=(self.obj_and_goal_space.low.size),
                )
            self.obj_init_pos = np.concatenate((goal_pos[:2], [self.obj_init_pos[-1]]))
        self._set_goal_marker(self._state_goal)
        self._set_obj_xyz(self.obj_init_pos)
        #self._set_obj_xyz_quat(self.obj_init_pos, self.obj_init_angle)
        self.curr_path_length = 0
        # self.maxReachDist = np.linalg.norm(self.init_fingerCOM - np.array(self._state_goal))
        self.maxReachDist = np.abs(self.hand_init_pos[-1] - self._state_goal[-1])
        return self._get_obs()

    def _reset_hand(self):
        for _ in range(10):
            self.data.set_mocap_pos('mocap', self.hand_init_pos)
            self.data.set_mocap_quat('mocap', np.array([1, 0, 1, 0]))
            self.do_simulation([-1,1], self.frame_skip)
            #self.do_simulation(None, self.frame_skip)
        rightFinger, leftFinger = self.get_site_pos('rightEndEffector'), self.get_site_pos('leftEndEffector')
        self.init_fingerCOM  =  (rightFinger + leftFinger)/2
        self.pickCompleted = False

    def get_site_pos(self, siteName):
        _id = self.model.site_names.index(siteName)
        return self.data.site_xpos[_id].copy()

    def compute_rewards(self, actions, obsBatch):
        #Required by HER-TD3
        assert isinstance(obsBatch, dict) == True
        obsList = obsBatch['state_observation']
        rewards = [self.compute_reward(action, obs)[0] for  action, obs in zip(actions, obsList)]
        return np.array(rewards)

    def compute_reward(self, actions, obs):
        if isinstance(obs, dict):
            obs = obs['state_observation']

        objPos = obs[3:6]

        rightFinger, leftFinger = self.get_site_pos('rightEndEffector'), self.get_site_pos('leftEndEffector')
        fingerCOM  =  (rightFinger + leftFinger)/2

        goal = self._state_goal

        c1 = 1000 ; c2 = 0.01 ; c3 = 0.001
        # reachDist = np.linalg.norm(fingerCOM - goal)
        # reachDist = np.linalg.norm(fingerCOM - np.concatenate((goal[:-1], [self.hand_init_pos[-1]])))
        reachDist = np.linalg.norm(fingerCOM[:-1] - goal[:-1])
        reachRew = -reachDist
        reachDist_z = np.abs(fingerCOM[-1] - goal[-1])
        if reachDist < 0.05:
            reachNearRew = 1000*(self.maxReachDist - reachDist_z) + c1*(np.exp(-(reachDist_z**2)/c2) + np.exp(-(reachDist_z**2)/c3))
        else:
            reachNearRew = 0.
        # reachRew = c1*(self.maxReachDist - reachDist) + c1*(np.exp(-(reachDist**2)/c2) + np.exp(-(reachDist**2)/c3))
        # reachRew = max(reachRew, 0)
        reachNearRew = max(reachNearRew,0)
        # reachRew = -reachDist
        reward = reachRew + reachNearRew# - actions[-1]/50
        return [reward, reachDist]


    def get_diagnostics(self, paths, prefix=''):
        statistics = OrderedDict()
        return statistics

    def log_diagnostics(self, paths = None, logger = None):
        pass
