# -*- coding: utf-8 -*-
"""
Adapted from RL project  (July 2nd, 2024): the latest version (used to train on all the training contracts in Spyder)
"""

import gymnasium
from gymnasium import spaces
import numpy as np

import rl
from rl.env_data_preparation.contract_dynamics import ContractDynamics
from rl.config import rl_cur_parameters

from rl.utils import goal_rewarding, weighted_choice, sort_lists, \
    scale_value_continous, random_selection

# max_func_value_element=rl.config.rl_cur_parameters["max_func_value_element"]
# max_svar_value=rl.config.rl_cur_parameters["max_svar_value"]

class ContractEnv_33(gymnasium.Env):
    """
    usining combination of continous space and concrete space

    obs: , , , ,

    state variables, function-related identifier,  4 functions, target

    actions: functions

    static analysis is required

    variations:
        function-related identifier: consider constructor or not
        action slots: 4 action slots or 5 action slots
        normalization: yes or no


    """

    def __init__(self, contract_dynamics: ContractDynamics, conEnvData_wsa,
                 flag_model: int = 1, mode: str = 'train',
                 goal: int = 1, test: bool = False, goal_indicator: int = 2,
                 action_size: int = 51,num_state_variable:int=24):
        super(ContractEnv_33, self).__init__()

        self.env_name = "ContractEnv_33"

        self.solidity_name = ""
        self.contract_name = ""

        self.contract_dynamics = contract_dynamics
        self.conEnvData_wsa = conEnvData_wsa

        self.action_size = action_size

        self.num_reads = 3
        self.num_writes = 3
        self.num_state_var = num_state_variable
        self.flag_model = flag_model
        self.mode = mode  # train, test, and predict
        self.score = 0
        self.test = test

        self.goal_indicator = goal_indicator
        self.goals = self.conEnvData_wsa["target_functions_in_integer"]
        self.goal = self.goals[0]

        self.goal_reach_status = {goal: 0 for goal in self.goals}
        self.goal_consider_status = {goal: 0 for goal in self.goals}
        self.goal_weight_status = {goal: 1 for idx, goal in
                                   enumerate(self.goals)}
        self.goal_idx = 0  # record the times goal is reset( for weighted goal selection as some goal is hard to reach due to few sequences reaching them)

        self.previous_actions = []

        self.select_idx = 0
        self.select_times = 0

        self.num_functions = len(self.conEnvData_wsa["function_data"].keys())
        self.function_keys = list(self.conEnvData_wsa["function_data"].keys())
        self.function_keys = [int(e) for e in self.function_keys]

        # print(f'before function keys: {self.function_keys}')
        if 0 in self.function_keys:
            self.function_keys.remove(0)
        # print(f'after function keys: {self.function_keys}')

        self.valid_actions = self.function_keys

        function_value = self.conEnvData_wsa["function_value"]
        # scale to 0 and 1 (max max_func_value_element based on the given contract dataset)
        max_func_value_element = rl.config.rl_cur_parameters[
            "max_func_value_element"]
        self.function_for_identifier = [
            scale_value_continous(value, 0, max_func_value_element) for value in
            function_value]

        function_value_n0 = self.conEnvData_wsa["function_value_n0"]
        self.function_for_identifier_n0 = [
            scale_value_continous(value, 0, max_func_value_element) for value in
            function_value_n0]

        self.function_for_identifier_unnormalized = function_value

        self.action_space = spaces.Discrete(self.action_size)

        self.low_1 = 0
        self.high_1 = 1
        # Define the last 8 elements as integers between 0 and 20
        self.size = 1  # the size of function presentation
        if self.flag_model == 0:
            # does not normalize actions
            self.low_2 = 0
            self.high_2 = self.action_size

        elif self.flag_model in [1, 2, 3, 4, 5, 6]:

            # normalize actions
            self.low_2 = 0
            self.high_2 = 1

            if self.flag_model == 1:
                self.size = 1
            elif self.flag_model == 2:
                self.size = (1 + self.num_reads + self.num_writes)
            elif self.flag_model == 3:
                self.size = (1 + self.num_state_var)
            elif self.flag_model == 4:
                self.size = (
                            1 + self.num_state_var + self.num_reads + self.num_writes)
            elif self.flag_model == 5:
                self.size = (
                            1 + self.num_state_var + self.num_reads + self.num_writes)
            elif self.flag_model == 6:
                self.size = (
                            1 + self.num_state_var + self.num_reads + self.num_writes)

        # Create the observation space(only scale the values of the state variables to 0 and 1)
        if self.flag_model in [5, 6]:
            low = np.array([self.low_1] * 2 * self.num_state_var + [
                self.low_2] * self.size * 4)
            high = np.array([self.high_1] * 2 * self.num_state_var + [
                self.high_2] * self.size * 4)

        else:
            low = np.array([self.low_1] * 2 * self.num_state_var + [
                self.low_2] * self.size * 5)
            high = np.array([self.high_1] * 2 * self.num_state_var + [
                self.high_2] * self.size * 5)
        self.observation_space = spaces.Box(low=low, high=high,
                                            dtype=np.float32)

    def env_dynamics(self, action):
        reward = 0
        terminate = False
        if isinstance(action, np.ndarray):
            action = int(action)

        if action in self.previous_actions:
            reward = -1

        # ================
        # append new action
        if self.flag_model in [5, 6]:
            if len(self.previous_actions) >= 3:
                action = self.goal  # ignore the action at depth 4

        # correct
        reward_x,terminate=self.correct_1st_action(action)
        if reward_x!=-1:
            return reward_x,terminate

        self.previous_actions.append(action)
        cur_length = len(
            self.previous_actions)  # do not use self.depth as it is updated after reward is computed

        if self.mode in ['predict']:
            reward = 0
            if action not in self.valid_actions or action == 0:
                # not valid actions
                terminate = True
                return reward, terminate

            _, terminate = goal_rewarding(action, self.goal,
                                          self.previous_actions,
                                          self.goal_indicator, self.goals,
                                          mode='predict')

        else:
            if action not in self.valid_actions or action == 0:
                # not valid actions
                reward -= 1
                terminate = True
                return reward, terminate

            if not self.contract_dynamics.reach_to_the_goal(
                    self.previous_actions, self.goal):
                reward = -0.1  # think about whether should  terminate at this case
                terminate = True
            else:
                if self.mode == "train":
                    reward_, terminate = goal_rewarding(action, self.goal,
                                                        self.previous_actions,
                                                        self.goal_indicator,
                                                        self.goals)
                else:
                    reward_, terminate = goal_rewarding(action, self.goal,
                                                        self.previous_actions,
                                                        self.goal_indicator,
                                                        self.goals, mode='test')

                if reward_ >= 5:
                    self.goal_reach_status[self.goal] += 1
                    if self.mode == 'train':
                        print(
                            f'Goal reaching status:\n{self.goal_reach_status}')
                        print(
                            f'Goal consider status:{self.goal_consider_status}')
                reward += reward_

        if cur_length <= 4:
            max_svar_value = rl.config.rl_cur_parameters["max_svar_value"]
            if self.flag_model == 0:
                self.state[2 * self.num_state_var + cur_length - 1] = action

            elif self.flag_model == 1:
                self.state[
                    2 * self.num_state_var + cur_length - 1] = scale_value_continous(
                    action, 0, self.action_size)

            elif self.flag_model == 2:
                func_vector1 = \
                self.conEnvData_wsa["function_data"][str(action)][
                    'vector_rw_in_concate']

                func_vector1_1 = [scale_value_continous(action, 0,
                                                        self.action_size)] + \
                                 [scale_value_continous(v, 0, max_svar_value)
                                  for v in func_vector1]

                start_index = 2 * self.num_state_var + self.size * (
                            cur_length - 1)
                self.state[start_index:start_index + self.size] = func_vector1_1

            elif self.flag_model == 3:

                func_vector2 = \
                self.conEnvData_wsa["function_data"][str(action)][
                    'vector_in_index_rw']

                func_vector2_1 = [scale_value_continous(action, 0,
                                                        self.action_size)] + \
                                 [scale_value_continous(v, 0, 4) for v in
                                  func_vector2]

                start_index = 2 * self.num_state_var + self.size * (
                            cur_length - 1)
                self.state[start_index:start_index + self.size] = func_vector2_1

            elif self.flag_model in [4, 5, 6]:
                if not (self.flag_model in [5, 6] and len(
                        self.previous_actions) >= 4):
                    func_vector1 = \
                    self.conEnvData_wsa["function_data"][str(action)][
                        'vector_rw_in_concate']
                    func_vector2 = \
                    self.conEnvData_wsa["function_data"][str(action)][
                        'vector_in_index_rw']

                    func_vector1_1 = [scale_value_continous(action, 0,
                                                            self.action_size)] + \
                                     [scale_value_continous(v, 0,
                                                            max_svar_value) for
                                      v in func_vector1]
                    func_vector2_1 = [scale_value_continous(v, 0, 4) for v in
                                      func_vector2]
                    func_vector_1_2 = func_vector1_1 + func_vector2_1

                    start_index = 2 * self.num_state_var + self.size * (
                                cur_length - 1)
                    self.state[
                    start_index:start_index + self.size] = func_vector_1_2
                    # 15

        if cur_length >= 4:
            terminate = True
        # print(f'action:{action}; reward:{reward}; goal:{self.goal}; action seq:{self.previous_actions}')

        return reward, terminate

    def step(self, action):
        self.print_(f'action:{action}')
        reward = 0
        truncated = False
        info = {}

        reward, terminate = self.env_dynamics(action)

        # print(f'{self.previous_actions}')
        if terminate:
            self.done = True
            # print(f'end:{self.previous_actions}')

        self.score += reward
        observation = np.array(self.state)

        return observation, reward, self.done, truncated, info

    def select_goal(self):
        # ==================================================
        # #randomly select
        # self.goal=random_selection(self.goals)
        # self.goal_consider_status[self.goal]+=1
        # # print(f'Goal consider status:{self.goal_consider_status}')

        # ==================================================
        # weighted goal selection
        def goal_weight_computation(goal_reaching_status: dict):
            goal_reaching_times = [(key, times) for key, times in
                                   goal_reaching_status.items()]

            grt_d = sort_lists(goal_reaching_times, reverse=True)

            for idx in range(len(grt_d)):
                goal = grt_d[idx][0]
                weight = (idx + 1) * (2 + 1)
                self.goal_weight_status[goal] = weight
            print(f'Goal weights:')
            for goal, weight in self.goal_weight_status.items():
                print(f'\t{goal}:{weight}')

        self.goal_idx += 1
        if self.goal_idx >= 1000:
            self.goal_idx = 0
            goal_weight_computation(self.goal_reach_status)

        self.goal = weighted_choice(self.goals,
                                    [self.goal_weight_status[goal] for goal in
                                     self.goals])
        self.goal_consider_status[self.goal] += 1

    def reset(self, seed: int = None, options={}):
        max_svar_value = rl.config.rl_cur_parameters["max_svar_value"]
        self.score = 0
        self.previous_actions = []

        self.done = False

        # select a goal
        if self.mode == 'train':
            self.select_goal()

            # _,_,-,-,-,-,G,F
        if self.flag_model == 0:

            self.state = [scale_value_continous(idx, 0, max_svar_value) for idx
                          in
                          self.conEnvData_wsa["state_variables_selected"]] + \
                         self.function_for_identifier + [0] * 4 + [self.goal]
        elif self.flag_model == 1:

            self.state = [scale_value_continous(idx, 0, max_svar_value) for idx
                          in
                          self.conEnvData_wsa["state_variables_selected"]] + \
                         self.function_for_identifier + [0] * 4 + [
                             scale_value_continous(self.goal, 0,
                                                   self.action_size)]


        elif self.flag_model == 2:
            func_vector1 = self.conEnvData_wsa["function_data"][str(self.goal)][
                'vector_rw_in_concate']
            func_vector1_1 = [scale_value_continous(self.goal, 0,
                                                    self.action_size)] + \
                             [scale_value_continous(v, 0, max_svar_value) for v
                              in func_vector1]

            self.state = [scale_value_continous(idx, 0, max_svar_value) for idx
                          in
                          self.conEnvData_wsa["state_variables_selected"]] + \
                         self.function_for_identifier + [
                             0] * self.size * 4 + func_vector1_1

        elif self.flag_model == 3:

            func_vector2 = self.conEnvData_wsa["function_data"][str(self.goal)][
                'vector_in_index_rw']

            func_vector2_1 = [scale_value_continous(self.goal, 0,
                                                    self.action_size)] + \
                             [scale_value_continous(v, 0, 3) for v in
                              func_vector2]

            self.state = [scale_value_continous(idx, 0, max_svar_value) for idx
                          in
                          self.conEnvData_wsa["state_variables_selected"]] + \
                         self.function_for_identifier + [
                             0] * self.size * 4 + func_vector2_1

        elif self.flag_model in [4, 5, 6]:
            func_vector1 = self.conEnvData_wsa["function_data"][str(self.goal)][
                'vector_rw_in_concate']
            func_vector2 = self.conEnvData_wsa["function_data"][str(self.goal)][
                'vector_in_index_rw']

            func_vector1_1 = [scale_value_continous(self.goal, 0,
                                                    self.action_size)] + \
                             [scale_value_continous(v, 0, max_svar_value) for v
                              in func_vector1]
            func_vector2_1 = [scale_value_continous(v, 0, 3) for v in
                              func_vector2]
            func_vector_1_2 = func_vector1_1 + func_vector2_1



            if self.flag_model == 4:
                # there are 5 slots for actions. the last one is for the target
                self.state = [scale_value_continous(idx, 0, max_svar_value) for
                              idx in
                              self.conEnvData_wsa["state_variables_selected"]] + \
                             self.function_for_identifier + \
                             [
                                 0] * self.size * 4 + func_vector_1_2
            else:
                # there are 4 slots for actions. the last one is for the target
                if self.flag_model == 5:
                    # the function-based value considers constructor
                    self.state = [scale_value_continous(idx, 0, max_svar_value)
                                  for idx in
                                  self.conEnvData_wsa[
                                      "state_variables_selected"]] + \
                                 self.function_for_identifier + \
                                 [
                                     0] * self.size * 3 + func_vector_1_2
                else:
                    # the function-based value does not consider constructor
                    self.state = [scale_value_continous(idx, 0, max_svar_value)
                                  for idx in
                                  self.conEnvData_wsa[
                                      "state_variables_selected"]] + \
                                 self.function_for_identifier_n0 + \
                                 [
                                     0] * self.size * 3 + func_vector_1_2



        observation = np.array(self.state)
        # print(f'depth:{0};{len(self.state)};obs:{self.state[0:16]}')
        return observation, {}

    def print_(self, content: str):
        # if not self.test:
        #     print(content)
        pass

    def print_2(self, content: str):
        # if self.test:
        #     print(content)
        pass

    def action_masks(self):
        action_mask = np.zeros(self.action_space.n)
        for valid_action in self.valid_actions:
            if valid_action < len(action_mask):
                action_mask[
                    valid_action] = 1  # IndexError: index 20 is out of bounds for axis 0 with size 20
        return action_mask

    def correct_1st_action(self,action:int):
        if self.mode in ['test','predict']:
            if len(self.previous_actions)==0:
                if action not in self.conEnvData_wsa["start_functions_in_integer"]:
                    # make the first action correct
                    self.previous_actions = []
                    ele_1st=random_selection(self.conEnvData_wsa["start_functions_in_integer"])
                    self.previous_actions.append(ele_1st)


                    func_vector1_1st_action = self.conEnvData_wsa["function_data"][str(self.previous_actions[0])][
                        'vector_rw_in_concate']
                    func_vector2_1st_action = self.conEnvData_wsa["function_data"][str(self.previous_actions[0])][
                        'vector_in_index_rw']

                    func_vector1_1st_action_1 = [scale_value_continous(self.previous_actions[0], 0,
                                                            self.action_size)] + \
                                     [scale_value_continous(v, 0, max_svar_value) for v
                                      in func_vector1_1st_action]
                    func_vector2_1st_action_1 = [scale_value_continous(v, 0, 3) for v in
                                      func_vector2_1st_action]
                    func_vector_1st_action_1_2 = func_vector1_1st_action_1 + func_vector2_1st_action_1

                    reward=0.2
                    cur_length = len(
                        self.previous_actions)
                    start_index = 2 * self.num_state_var + self.size * (
                                cur_length - 1)
                    self.state[
                    start_index:start_index + self.size] = func_vector_1st_action_1_2
                    if self.mode in ['test']:
                        return reward, False
                    else:
                        return 0, False
        return -1, False



