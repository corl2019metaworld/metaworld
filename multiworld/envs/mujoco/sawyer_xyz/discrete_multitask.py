import gym
import gym.spaces
import numpy as np

from multiworld.core.multitask_env import MultitaskEnv


class DiscreteMultitask(MultitaskEnv, gym.Wrapper):
    """
    A MultitaskEnv wrapper which represents a World of a discrete, fixed-length
    set of tasks.

    Every call to `reset()`, the wrapper samples a new task uniformly from the
    provided set of tasks.

    Args:
        env(:obj:`TaskBased`): A `TaskBased` World to wrap
        tasks(list[object]): A list of task descriptor object conforming to
            `env.task_schema`.
    """

    def __init__(self, env, tasks):
        gym.Wrapper.__init__(self, env)

        # Validate and initialize tasks
        for t in tasks:
            self.env.validate_task(t)

        self._tasks = tasks
        self._task_idx = 0

        # Augment the observation space with a task one-hot
        base = self.env.observation_space.spaces.copy()
        base['task'] = gym.spaces.Discrete(len(self._tasks))
        self.observation_space = gym.spaces.Dict(base)

    def sample_goals(self, batch_size):
        sampled = np.random.randint(0, len(self._tasks) - 1, batch_size)
        goals = [
            self.env.goal_from_task(self._tasks[s]['goal']) for s in sampled
        ]
        return {
            'state_desired_goal': goals,
        }

    def get_goal(self):
        return self.env.get_goal()

    def compute_rewards(self, actions, obs):
        return self.env.compute_rewards(actions, obs)

    def get_diagnostics(self, paths, prefix=''):
        statistics = OrderedDict()
        return statistics

    def log_diagnostics(self, paths=None, logger=None):
        pass

    def step(self, action):
        o, r, d, i = self.env.step(action)
        return self._augment_observation(o), r, d, i

    def reset(self):
        self._task_idx = np.random.randint(0, len(self._tasks) - 1)
        self.env.task = self._tasks[self._task_idx]
        return self._augment_observation(self.env.reset())

    def _augment_observation(self, o):
        o['task'] = self._task_onehot()
        return o

    def _task_onehot(self):
        oh = np.zeros(len(self._tasks), dtype=np.int32)
        oh[self._task_idx] = 1
        return oh


if __name__ == '__main__':
    import time

    from .sawyer_window_open_6dof import SawyerWindowOpen6DOFEnv

    world = SawyerWindowOpen6DOFEnv()
    tasks = [world.task_schema.sample() for _ in range(10)]
    env = DiscreteMultitask(world, tasks)
    for _ in range(1000):
        env.reset()
        for _ in range(100):
            env.render()
            step = env.step(np.array([1, 0, 0, 1]))
            time.sleep(0.05)
