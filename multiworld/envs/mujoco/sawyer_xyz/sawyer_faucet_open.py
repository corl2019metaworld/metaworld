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

class SawyerFaucetOpen6DOFEnv(SawyerXYZEnv):
    def __init__(
            self,
            hand_low=(-0.5, 0.40, -0.15),
            hand_high=(0.5, 1, 0.5),
            obj_low=(-0.05, 0.8, 0.05),
            obj_high=(0.05, 0.85, 0.05),
            random_init=False,
            obs_type='plain',
            # tasks = [{'goal': np.array([0, 0.88, 0.1]), 'obj_init_pos':np.array([0., 0.88, 0.15]), 'obj_init_qpos':0.}], 
            tasks = [{'goal': np.array([0.1, 0.8, 0.115]), 'obj_init_pos':np.array([0, 0.8, 0.05])}], 
            goal_low=None,
            goal_high=None,
            hand_init_pos = (0, 0.6, 0.2),
            rotMode='fixed',#'fixed',
            multitask=False,
            multitask_num=None,
            if_render=False,
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
            np.array(obj_low),
            np.array(obj_high),
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


    def get_goal(self):
        return {
            'state_desired_goal': self._state_goal,
    }

    @property
    def model_name(self):     

        return get_asset_full_path('sawyer_xyz/sawyer_faucet.xml')
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
        self.viewer.cam.lookat[0] = 0.4
        self.viewer.cam.lookat[1] = 0.75
        self.viewer.cam.lookat[2] = 0.4
        self.viewer.cam.distance = 0.4
        self.viewer.cam.elevation = -55
        self.viewer.cam.azimuth = 180
        self.viewer.cam.trackbodyid = -1
        # self.viewer.cam.trackbodyid = 0
        # self.viewer.cam.lookat[0] = 0
        # self.viewer.cam.lookat[1] = 0.4
        # self.viewer.cam.lookat[2] = 0.4
        # self.viewer.cam.distance = 0.4
        # self.viewer.cam.elevation = -55
        # self.viewer.cam.azimuth = 90
        # self.viewer.cam.trackbodyid = -1

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
        reward, reachDist, pullDist = self.compute_reward(action, ob)
        self.curr_path_length +=1
        #info = self._get_info()
        if self.curr_path_length == self.max_path_length:
            done = True
        else:
            done = False
        return ob, reward, done, {'reachDist': reachDist, 'goalDist': pullDist, 'epRew' : reward, 'pickRew':None, 'success': float(pullDist <= 0.05)}
   

    def get_angle(self):
        return np.array([self.data.get_joint_qpos('joint')])

    def get_mocap_quat(self):
        return self.data.get_mocap_quat('mocap')

    def _get_obs(self):
        hand = self.get_endeff_pos()
        objPos = self.get_site_pos('handleStartOpen')
        # angle = self.get_angle()
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
        objPos =  self.get_site_pos('handleStartOpen')
        flat_obs = np.concatenate((hand, objPos))
        return dict(
            state_observation=flat_obs,
            state_desired_goal=self._state_goal,
            state_achieved_goal=objPos,
        )

    def _get_info(self):
        pass

    def _set_objCOM_marker(self):
        """
        This should be use ONLY for visualization. Use self._state_goal for
        logging, learning, etc.
        """
        objPos =  self.data.get_geom_xpos('handle')
        self.data.site_xpos[self.model.site_name2id('objSite')] = (
            objPos
        )
    
    def _set_goal_marker(self, goal):
        """
        This should be use ONLY for visualization. Use self._state_goal for
        logging, learning, etc.
        """
        self.data.site_xpos[self.model.site_name2id('goal_open')] = (
            goal[:3]
        )
        self.data.site_xpos[self.model.site_name2id('goal_close')] = (
            np.array([10.0, 10.0, 10.0])
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
        qpos[9] = pos
        qvel[9] = 0
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
        task_idx = np.random.randint(0, self.num_tasks)
        return self.tasks[task_idx]


    def reset_model(self):
        self._reset_hand()
        task = self.sample_task()
        self._state_goal = np.array(task['goal'])
        self.obj_init_pos = task['obj_init_pos']
        # self.obj_init_qpos = task['obj_init_qpos']
        if self.random_init:
            goal_pos = np.random.uniform(
                self.obj_and_goal_space.low,
                self.obj_and_goal_space.high,
                size=(self.obj_and_goal_space.low.size),
            )
            # self.obj_init_qpos = goal_pos[-1]
            self.obj_init_pos = goal_pos[:3]
            final_pos = goal_pos.copy()
            final_pos += np.array([0.1, -0.015, 0.065])
            self._state_goal = final_pos

        # self._set_obj_xyz(self.obj_init_qpos)
        # self.sim.model.body_pos[self.model.body_name2id('box')] = self.obj_init_pos
        # print(button_pos)
        self.sim.model.body_pos[self.model.body_name2id('faucet')] = self.obj_init_pos
        self.sim.model.body_pos[self.model.body_name2id('faucetBase')] = self.obj_init_pos
        self._set_goal_marker(self._state_goal)
        self.maxPullDist = np.linalg.norm(self._state_goal - self.obj_init_pos)
        self.curr_path_length = 0
        #Can try changing this
        return self._get_obs()

    def _reset_hand(self):
        for _ in range(10):
            self.data.set_mocap_pos('mocap', self.hand_init_pos)
            self.data.set_mocap_quat('mocap', np.array([1, 0, 1, 0]))
            self.do_simulation([-1,1], self.frame_skip)
            #self.do_simulation(None, self.frame_skip)
        rightFinger, leftFinger = self.get_site_pos('rightEndEffector'), self.get_site_pos('leftEndEffector')
        self.init_fingerCOM  =  (rightFinger + leftFinger)/2
        self.reachCompleted = False

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

        pullGoal = self._state_goal

        pullDist = np.linalg.norm(objPos - pullGoal)
        reachDist = np.linalg.norm(objPos - fingerCOM)  
        # reachDistxy = np.linalg.norm(objPos[:-1] - fingerCOM[:-1])    
        # zDist = np.linalg.norm(fingerCOM[-1] - self.init_fingerCOM[-1])   
        # if reachDistxy < 0.05: #0.02  
        #     reachRew = -reachDist 
        # else: 
        #     reachRew =  -reachDistxy - zDist  
        reachRew = -reachDist

        def reachCompleted():
            if reachDist < 0.05:
                return True
            else:
                return False

        if reachCompleted():
            self.reachCompleted = True
        else:
            self.reachCompleted = False

        def pullReward():
            c1 = 1000 ; c2 = 0.01 ; c3 = 0.001
            # c1 = 10 ; c2 = 0.01 ; c3 = 0.001
            if self.reachCompleted:
                pullRew = 1000*(self.maxPullDist - pullDist) + c1*(np.exp(-(pullDist**2)/c2) + np.exp(-(pullDist**2)/c3))
                pullRew = max(pullRew,0)
                return pullRew
            else:
                return 0
            # pullRew = 1000*(self.maxPullDist - pullDist) + c1*(np.exp(-(pullDist**2)/c2) + np.exp(-(pullDist**2)/c3))
            # pullRew = max(pullRew,0)
            # return pullRew
        # pullRew = -pullDist
        pullRew = pullReward()
        reward = reachRew + pullRew# - actions[-1]/50
        # reward = pullRew# - actions[-1]/50
      
        return [reward, reachDist, pullDist] 

    def get_diagnostics(self, paths, prefix=''):
        statistics = OrderedDict()
        return statistics

    def log_diagnostics(self, paths = None, logger = None):
        pass

if __name__ == '__main__':  
    import time 
    env = SawyerFaucetOpen6DOFEnv()    
    for _ in range(1000):   
        env.reset()
        # env._set_obj_xyz(1.5708*2)
        for _ in range(10):
            env.data.set_mocap_pos('mocap', np.array([-0.15, 0.7, 0.115]))
            env.data.set_mocap_quat('mocap', np.array([1, 0, 1, 0]))
            env.do_simulation([-1,1], env.frame_skip)
        for _ in range(100): 
            env.render()
            # env.step(env.action_space.sample()) 
            env.step(np.array([1., 0., 0., 1.])) 
            # env.step(np.array([np.random.uniform(low=-1., high=1.), np.random.uniform(low=-1., high=1.), 0.]))    
            time.sleep(0.05)
        print(np.linalg.norm(env.get_site_pos('handleStartOpen') - env._state_goal))
