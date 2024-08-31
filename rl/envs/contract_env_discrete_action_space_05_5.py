# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 23:39:11 2024

@author: admin
"""



# -*- coding: utf-8 -*-
from rl.env_data_preparation.contract_dynamics import ContractDynamics
from rl.env_data_preparation.fwrg_manager import FWRG_manager
from rl.utils import scale_value_continous, random_selection, weighted_choice, sort_lists, goal_rewarding

"""
require static analysis from source code

@author: SERC
"""

import gymnasium
from gymnasium import spaces
import numpy as np


def mask_fn(env:gymnasium.Env) -> np.ndarray:
    # Do whatever you'd like in this function to return the action mask
    # for the current env. In this example, we assume the env has a
    # helpful method we can rely on.
    return env.valid_action_mask()

def scale_values(input_values, scale_factor):
    scaled_values = [value % (scale_factor + 1) for value in input_values]
    return scaled_values



class ContractEnv_55(gymnasium.Env):
    """
    
    
    obs: [max_svar_value]*8+[9]*(8+1)+[4]*(8+1)+[4]*(8+1)*6 (temporarily use max_svar_value as the maximum integer to denote a state variable)
    
   state variables, function-related identifier, constructor/write record, 4 functions, target, given function
    
    action: 0,1(given a function, make decision to choose)
    
    assume that the type of the state variables are not available, (i.e., only the bytecode)
    
    
    consider 8 state variables
    
    
    training: randomly select a goal when reset() is invoked
    """
    def __init__(self, contract_dynamics: ContractDynamics, conEnvData_wsa, goal=1, test:bool=False, goal_indicator:int=2, num_state_svar:int=16, flag_model:int=5, mode:str= 'train',max_svar_value:int=80,max_func_value_element:int=30):
        super(ContractEnv_55, self).__init__()
        
        self.env_name="ContractEnv_55"
        self.contract_name=''
        self.solidity_name=''
        
        self.contract_dynamics = contract_dynamics
        self.conEnvData_wsa = conEnvData_wsa
        self.num_reads=3
        self.num_writes=3
        
        self.num_state_var=num_state_svar
        self.flag_model=flag_model
        print(f'flag_model={self.flag_model}')
        self.mode=mode
        
        self.score=0
        self.test=test
        
        self.goal_indicator=goal_indicator
        self.goals=self.conEnvData_wsa["target_functions_in_integer"]       
        self.goal=goal      
        
        self.goal_reach_status={goal:0 for goal in self.goals}
        self.goal_consider_status={goal:0 for goal in self.goals}
        self.goal_weight_status={goal:1 for idx,goal in enumerate(self.goals)}
        
        self.goal_idx=0  # record the times goal is reset( for weighted goal selection as some goal is hard to reach due to few sequences reaching them)
        
       
                
        self.fwrg_manager=None
        self.obtain_fwrg_graph() 
        print(f'self.fwrg_manager.start_functions:{self.fwrg_manager.start_functions}')
    
        self.previous_actions=[]
        self.func_seq=[]

        self.max_svar_value=max_svar_value
        self.max_func_value_element= max_func_value_element
        
        self.select_idx=0
        self.select_times=0   

        self.num_functions=len(self.conEnvData_wsa["function_data"].keys())

        self.function_keys=list(self.conEnvData_wsa["function_data"].keys())
        self.function_keys=[int(e) for e in self.function_keys]
        # print(f'before function keys: {self.function_keys}')
        if 0 in self.function_keys:
            self.function_keys.remove(0)
        self.max_function_int_value=max(self.function_keys)+1
        print(f'function keys: {self.function_keys}; len:{len(self.function_keys)}') 
        
        function_value=self.conEnvData_wsa["function_value"]            
       
        # scale to 0 and 1 (max max_func_value_element on a small set of contracts)
        self.function_for_identifier=[scale_value_continous(value,0,self.max_func_value_element) for value in function_value]
        
        function_value_n0=self.conEnvData_wsa["function_value_n0"]            

        self.function_for_identifier_n0=[scale_value_continous(value,0,self.max_func_value_element) for value in function_value_n0]
        
        # print(f'self.function_for_identifier: {self.function_for_identifier}')
        # print(f'self.function_for_identifier_n0: {self.function_for_identifier_n0}')
        
        self.function_for_identifier_unnormalized=function_value
        
        self.action_space = spaces.Discrete(2)
        self.action_size =self.action_space.n
        if self.flag_model==0:
            # state variables, function identifier, constructor/rw record,4 functions,given function
            # presentation: function idx and function vector (r+w format)
            #
            self.observation_space = spaces.MultiDiscrete(
                [self.max_svar_value]*self.num_state_var+   # state variables
                [self.max_func_value_element]*self.num_state_var+ # serve as a feature
                [self.max_function_int_value]+
                [4]*self.num_state_var+
                [self.max_function_int_value]+
                [4]*self.num_state_var+
                [self.max_function_int_value]+
                [4]*self.num_state_var+
                [self.max_function_int_value]+
                [4]*self.num_state_var+
                [self.max_function_int_value]+
                [4]*self.num_state_var+
                [self.max_function_int_value]+
                [4]*self.num_state_var
                ) 
        elif self.flag_model==1:
            low = np.array([0] * 2*self.num_state_var + [0] * 6*(1+self.num_state_var))
            high = np.array([1] * 2*self.num_state_var + [1] * 6*(1+self.num_state_var))
            self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)           
            
        elif self.flag_model==2:
            # use a single integer to present a function (not normalized)
            self.observation_space = spaces.MultiDiscrete(
                [self.max_svar_value]*self.num_state_var+   # state variables
                [self.max_func_value_element]*self.num_state_var+ # serve as a feature
                [self.max_function_int_value]*6
                )
        elif self.flag_model==3:
            # use a single integer to present a function
            low = np.array([0] * 2*self.num_state_var + [0] * 6)
            high = np.array([1] * 2*self.num_state_var + [1] * 6)
            self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)
            
        elif self.flag_model==4:
            # function presentation: integer and function vector (in RW format)
            self.observation_space = spaces.MultiDiscrete(
                [self.max_svar_value] * self.num_state_var +  # state variables
                [self.max_func_value_element] * self.num_state_var +  # serve as a feature
                [self.max_function_int_value]+
                [self.max_svar_value]*(self.num_reads+self.num_writes)+
                [self.max_function_int_value]+
                [self.max_svar_value]*(self.num_reads+self.num_writes)+
                [self.max_function_int_value]+
                [self.max_svar_value]*(self.num_reads+self.num_writes)+
                [self.max_function_int_value]+
                [self.max_svar_value]*(self.num_reads+self.num_writes)+
                [self.max_function_int_value]+
                [self.max_svar_value]*(self.num_reads+self.num_writes)+
                [self.max_function_int_value]+
                [self.max_svar_value]*(self.num_reads+self.num_writes)
            )
        elif self.flag_model in [5,7]:
            # function presentation: integer and function vector (in RW format)
            # model 5 has the best performance (consider model 7 like model 5)
            low = np.array([0] * 2*self.num_state_var + [0] * 6*(1+self.num_writes+self.num_reads))
            high = np.array([1] * 2*self.num_state_var + [1] * 6*(1+self.num_writes+self.num_reads))
            self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)
        elif self.flag_model==6:
            low = np.array([0] * 2*self.num_state_var + [0] * 6*(1+self.num_state_var+self.num_writes+self.num_reads))
            high = np.array([1] * 2*self.num_state_var + [1] * 6*(1+self.num_state_var+self.num_writes+self.num_reads))
            self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)
        
        print(f'self.action_space:{self.action_space.n}; self.observation_space.shape:{self.observation_space.shape}')
        print(f'goals:{self.goals}')



    def env_dynamics(self, action):
        reward= 0
        terminate = False

        if isinstance(action, np.ndarray):
            action = int(action)         
            
        # append new action
        self.previous_actions.append(action)        
      
        cur_length = len(self.func_seq)  # do not use self.depth as it is updated after reward is computed
            
        
        if self.mode in ['train','test']:
            if not self.contract_dynamics.is_prefix(self.func_seq):
                self.print_(f'invalid:{self.func_seq}')
                # invalid sequence
                if action==0:
                    reward=0
                    
                elif action==1:                
                    reward=-0.1
                    terminate=True
                    self.print_(f'terminate with reward {reward}')
                    
            else:
                self.print_(f'valid:{self.func_seq}')
                if action==1:
                    if self.mode=='train':    
                        reward,terminate=goal_rewarding(action,self.goal,self.func_seq,self.goal_indicator,self.goals,flag_test=self.test)
                    else:
                        reward,terminate=goal_rewarding(action,self.goal,self.func_seq,self.goal_indicator,self.goals,flag_test=self.test,mode='test')
                        
                    if reward>=5:
                        self.goal_reach_status[self.goal]+=1                   
                        if self.mode in ['train']:
                            print(f'Goal reaching status:\n{self.goal_reach_status}')
                            print(f'Goal consider status:{self.goal_consider_status}')  
            
        elif self.mode=='predict':
            if action==0:
                reward=0
            elif action==1:
                reward,terminate=goal_rewarding(action,self.goal,self.func_seq,self.goal_indicator,self.goals,mode='predict')
                reward=0
        else:pass

        # update the state by adding the kept function to the function sequence portion
        if len(self.func_seq)<=4 and action==1:
           if self.flag_model==0:
               start_idx_1=2*self.num_state_var+(1+self.num_state_var)*(cur_length-1)
               self.state[start_idx_1:start_idx_1+(1+self.num_state_var)]=[self.select_function_key]+self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_in_index_rw']
           
           elif self.flag_model==1:
               start_idx_1=2*self.num_state_var+(1+self.num_state_var)*(cur_length-1)
               func_vector = self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_in_index_rw']
               func_vector_1 = [scale_value_continous(self.select_function_key, 0, self.max_function_int_value)] +\
                               [ scale_value_continous(v, 0, 4) for v in func_vector]
               self.state[start_idx_1:start_idx_1+(1+self.num_state_var)]=func_vector_1
           
           # one integer to present a function
           elif self.flag_model==2:
               start_idx_1=2*self.num_state_var+(cur_length-1)
               self.state[start_idx_1]=self.select_function_key
           elif self.flag_model==3:
               start_idx_1=2*self.num_state_var+(cur_length-1)
               self.state[start_idx_1]=scale_value_continous(self.select_function_key,0, self.max_function_int_value)
              
           # uese r+w (concatenation) to present a function
           elif self.flag_model==4:
               start_idx_1 = 2*self.num_state_var+ (1+self.num_reads+self.num_writes)*(cur_length - 1)
               self.state[start_idx_1:start_idx_1+(1+self.num_reads+self.num_writes)] = [self.select_function_key]+self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_rw_in_concate']
 
           elif self.flag_model in [5,7]:
               start_idx_1 = 2*self.num_state_var + (1+self.num_reads+self.num_writes) * (cur_length - 1)
               func_vector = self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_rw_in_concate']
               func_vector_1 = [scale_value_continous(self.select_function_key, 0, self.max_function_int_value)] +\
                               [ scale_value_continous(v, 0, self.max_svar_value) for v in func_vector]

               self.state[start_idx_1:start_idx_1+7]= func_vector_1

           elif self.flag_model==6:
               start_idx_1 = 2*self.num_state_var + (1+self.num_reads+self.num_writes+self.num_state_var)* (cur_length - 1)
               func_vector1 = self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_rw_in_concate']
               func_vector2 = self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_in_index_rw']
               
               func_vector1_1 = [scale_value_continous(self.select_function_key, 0, self.max_function_int_value)] +\
                               [scale_value_continous(v, 0, self.max_svar_value) for v in func_vector1]
               func_vector2_1 = [scale_value_continous(v, 0, 4) for v in func_vector2]
               func_vector_1_2=func_vector1_1+func_vector2_1
               self.state[start_idx_1:start_idx_1+(1+self.num_reads+self.num_writes+self.num_state_var)]= func_vector_1_2

        # update self.func_seq: replace the last one or append a selected one
        if not terminate:
           if action==0:
               # prepare for the next function
               self.select_function(position=len(self.func_seq))
               self.func_seq[cur_length-1]=self.select_function_key # replace the last selected function
           elif action==1:
               # prepare for the next function to append
               self.select_function(position=len(self.func_seq)+1)
               self.func_seq.append(self.select_function_key)  # append the selected function with the newly selected one
           

           # append the selected function to the end of the state
           if self.flag_model==0:
               self.state[-(1+self.num_state_var):]=[self.select_function_key]+self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_in_index_rw']
           
           elif self.flag_model==1:
               func_vector = self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_in_index_rw']
               func_vector_1 = [scale_value_continous(self.select_function_key, 0, self.max_function_int_value)] +\
                               [ scale_value_continous(v, 0, 4) for v in func_vector]
               self.state[-(1+self.num_state_var):]=func_vector_1
           
           elif self.flag_model==2:
               self.state[-1]=self.select_function_key
           elif self.flag_model==3:
               self.state[-1]= scale_value_continous(self.select_function_key,0, self.max_function_int_value)
    
           
           elif self.flag_model==4:
               self.state[-(1+self.num_reads+self.num_writes):] =[self.select_function_key]+ self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_rw_in_concate']
           elif self.flag_model in [5,7]:
               # use the key and the vector together to denote a function
               func_vector = self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_rw_in_concate']

               func_vector_1=[scale_value_continous(self.select_function_key, 0, self.max_function_int_value)] + [
                                scale_value_continous(v, 0, self.max_svar_value) for v in func_vector]
               self.state[-(1+self.num_reads+self.num_writes):] =  func_vector_1
           elif self.flag_model==6:
               
               func_vector1 = self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_rw_in_concate']
               func_vector2 = self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_in_index_rw']
               
               func_vector1_1 = [scale_value_continous(self.select_function_key, 0, self.max_function_int_value)] +\
                               [ scale_value_continous(v, 0, self.max_svar_value) for v in func_vector1]
               func_vector2_1 = [ scale_value_continous(v, 0, 4) for v in func_vector2]
               func_vector_1_2=func_vector1_1+func_vector2_1
               self.state[-(1+self.num_reads+self.num_writes+self.num_state_var):]= func_vector_1_2


        if len(self.func_seq)>4:
            # the case when action is 1 on the fourth function, which can result in appending a function to self.func_seq
            terminate=True

        # print(f'action:{action}; reward:{reward}; goal:{self.goal}; func_seq:{self.func_seq}')    
        return reward, terminate
    
               
    def step(self, action):
        self.print_(f'action:{action}')
        reward=0       
        truncated=False
        info={}
        
        if isinstance(action, np.ndarray):
            action_integer = int(action)
        else:
            action_integer = action
    
        reward, terminate = self.env_dynamics(action_integer)       
            

        if terminate:
            self.done = True
            
        if self.select_times>=6*self.num_functions:
            self.done=True
          
        self.score += reward

        observation =  np.array(self.state)
        
        return observation, reward, self.done,truncated ,info


        
    def obtain_fwrg_graph(self): 
        """
        obtain the candidate sequences to allow the agent to choose
        """
        
        func_r_in_condi={int(func_key):data["reads"] for func_key,data in self.conEnvData_wsa["function_data"].items() if int(func_key) not in [0]}
        func_w={int(func_key):data["writes"] for func_key,data in self.conEnvData_wsa["function_data"].items() if int(func_key) not in [0]}

        fwrg_manager = FWRG_manager(self.conEnvData_wsa["start_functions_in_integer"],self.conEnvData_wsa["target_functions_in_integer"],func_r_in_condi,func_w)
        fwrg_manager.obtain_sequences()

        self.fwrg_manager=fwrg_manager
        #
        # for key,data in self.conEnvData_wsa["function_data"].items():
        #     print(f'{key}:{data["name"]}')
        # print(f'graph:')
        # for k,v in self.fwrg_manager.updateFWRG.fwrg_targets_augmented.items():
        #     print(f'{k}:{v}')
        #
        # print(f'target: number of sequences reaching it')
        # for k,v in self.contract_dynamics.goal_sequences_counts.items():
        #     print(f'{k}:{v}')
                
            
        # the graph is limited by the capability of identifying the reads and writes of the state variables
        # randomly selecting a function randomly in some degree is necessary
       
      
    def select_function(self,position:int=0):


        # ==================================================
        # select based on a graph and partially on the goal
        #-------------------
        # randomly select a function
        one_function = [random_selection(self.function_keys)]
        self.print_for_debug(f'\tone function: {one_function}')

        #-------------------
        # find possible functions for a target based on a graph
        if position == 0 or len(self.func_seq) == 1 and position == 1:
            # happens when calling reset() or replacing the first function in self.func_seq
            if len(self.fwrg_manager.start_functions) > 0:
                one_start_function = [random_selection(self.fwrg_manager.start_functions)]
            else:
                print(f'{self.contract_name} does not have start functions')
                one_start_function = []
            one_child = one_start_function
            self.print_for_debug(f'\tchildren: {self.fwrg_manager.start_functions}')

        elif len(self.func_seq) == position:
            # replace the current function(or the last function in self.func_seq)
            parent_func = self.func_seq[-2]
            children = self.fwrg_manager.get_children_fwrg_T_A(parent_func)
            if len(children) > 0:
                one_child = [random_selection(children)]
            else:
                one_child = []
            self.print_for_debug(f'\tchildren: {children}')

        elif len(self.func_seq) == position - 1:
            # prepare for the next function(or the function appended to self.func_seq)
            if position>=4:
                pass
            else:
                parent_func = self.func_seq[-1]
                children = self.fwrg_manager.get_children_fwrg_T_A(parent_func)
                if len(children) > 0:
                    one_child = [random_selection(children)]
                else:
                    one_child = []
                self.print_for_debug(f'\tchildren: {children}')

        else:
            assert False


        #-------------------
        # find more potential functions for a target based on the sequences that lead to the target
        if self.mode in ['test']:
            goal_children=[]
        else:
            if position > 0:
                # prepare for children that are possible to reach the target
                goal_children = [goal_seq[position - 1] for goal_seq in self.contract_dynamics.goal_sequences[self.goal] if
                                 len(goal_seq) >= position]
                goal_children = list(set(goal_children))
    
                self.print_for_debug(f'\tgoal children: {goal_children}')
                # if is_equal(goal_children,[1,2,3,4,5,6,7,8,9,10,11]):
                #     print(f'xx')
            else:
                goal_sequences = self.contract_dynamics.goal_sequences[self.goal]
                goal_children = [seq[0] for seq in goal_sequences if len(seq) > 0]
                goal_children = list(set(goal_children))
                self.print_for_debug(f'\tgoal children: {goal_children}')

        

        # ------------------------------
        # selction function 3
        if position == 0 or position == 1:
            # the first function
            if self.mode in ['test', 'predict']:
                if len(one_child) > 0:
                    self.select_function_key = one_child[0]
                    self.print_for_debug(
                        f'\tselect:{self.select_function_key}(one_child )')
                else:
                    self.select_function_key = one_function[0]
                    self.print_for_debug(
                        f'\tselect:{self.select_function_key}(one_function )')


            else:
                if len(goal_children) > 0:
                    if self.select_times % 2 == 0:
                        self.select_function_key = random_selection(goal_children)
                        self.print_for_debug(f'\tselect:{self.select_function_key}(goal_children)')
                    else:
                        self.select_function_key = random_selection(one_child + goal_children + one_function)
                        self.print_for_debug(
                            f'\tselect:{self.select_function_key}(one_child + goal_children+one_function )')

                else:
                    if self.select_times % 2 == 0 and len(one_child) > 0:
                        self.select_function_key = one_child[0]
                        self.print_for_debug(f'\tselect:{self.select_function_key}( one_child[0])')
                    else:
                        self.select_function_key = random_selection(one_function + one_child)
                        self.print_for_debug(f'\tselect:{self.select_function_key}( one_function + one_child)')
        else:
            if position >= 4:
                # select the last funciton
                self.select_function_key = self.goal  # the maximum depth, the last chance, so directly try the goal itself
                self.print_for_debug(f'\tselect:{self.select_function_key}(select the goal {self.goal} at posiiton >=4)')
            else:
                if self.mode in ['test', 'predict']:
                    self.select_function_key = random_selection(
                        one_function + one_child)
                    self.print_for_debug(
                        f'\tselect:{self.select_function_key}(one_function + one_child)')

                else:

                    if len(goal_children) > 0:
                        if self.select_times % 2 == 0:
                            self.select_function_key = random_selection(goal_children)
                            self.print_for_debug(f'\tselect:{self.select_function_key}(goal_children)')
                        else:
                            self.select_function_key = random_selection(one_function + one_child + goal_children)
                            self.print_for_debug(
                                f'\tselect:{self.select_function_key}(one_function + one_child + goal_children)')

                    else:

                        if self.select_times % 2 == 0 and len(one_child) > 0:
                            self.select_function_key = one_child[0]
                            self.print_for_debug(f'\tselect:{self.select_function_key}( one_child[0])')
                        else:
                            self.select_function_key = random_selection(one_function + one_child)
                            self.print_for_debug(f'\tselect:{self.select_function_key}(one_function + one_child)')

        self.select_times += 1

    def select_goal(self):

        #================================================== 
        # weighted goal selection
        def goal_weight_computation(goal_reaching_status:dict):
            goal_reaching_times=[(key,times) for key,times in goal_reaching_status.items()]
            grt_d=sort_lists(goal_reaching_times,reverse=True)
            for idx in range(len(grt_d)):                
                goal=grt_d[idx][0] 
                weight=(idx+1)*(2+1)
                self.goal_weight_status[goal]=weight
            print(f'Goal weights:') 
            for goal,weight in self.goal_weight_status.items():
                print(f'\t{goal}:{weight}')
        
        self.goal_idx+=1         
        if self.goal_idx==1000:
            self.goal_idx=0 
            goal_weight_computation(self.goal_reach_status)
            
        self.goal=weighted_choice(self.goals,[self.goal_weight_status[goal] for goal in self.goals])
        self.goal_consider_status[self.goal]+=1        
       
        pass

    def reset(self,seed:int=None,options={}):        
        
        self.score = 0
        self.done = False
        self.previous_actions = []
        self.select_function_key=0
        self.select_times=0
        self.select_idx=0
        self.func_seq=[]

        # select a goal
        if self.mode=='train':
            self.select_goal()
        
        # select a function
        self.select_function()
        self.func_seq.append(self.select_function_key)
        
        # _,_,-,-,-,-,G,F
        if self.flag_model==0:
            self.state=[idx for idx in self.conEnvData_wsa["state_variables_selected"]]+\
                self.function_for_identifier_unnormalized+[0]*(self.num_state_var+1)*4+\
               [self.goal]+self.conEnvData_wsa["function_data"][str(self.goal)]['vector_in_index_rw']+\
                [self.select_function_key]+  self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_in_index_rw']

        elif self.flag_model==1:
            goal_vector=self.conEnvData_wsa["function_data"][str(self.goal)]['vector_in_index_rw']
            func_vector=self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_in_index_rw']
            
            self.state=[scale_value_continous(idx,0,self.max_svar_value) for idx in self.conEnvData_wsa["state_variables_selected"]]+\
                self.function_for_identifier+[0]*4*((1+self.num_state_var))+\
                    [scale_value_continous(self.goal,0, self.max_function_int_value)]+[scale_value_continous(v,0, 4) for v in goal_vector] + \
                    [scale_value_continous(self.select_function_key,0, self.max_function_int_value)]+[scale_value_continous(v,0, 4) for v in func_vector]

        elif self.flag_model==2:
            self.state=[idx for idx in self.conEnvData_wsa["state_variables_selected"]]+\
                self.function_for_identifier_unnormalized+[0]*4+\
                [self.goal]+\
                    [self.select_function_key]
        elif self.flag_model==3:
            self.state=[scale_value_continous(idx,0,self.max_svar_value) for idx in self.conEnvData_wsa["state_variables_selected"]]+\
                self.function_for_identifier+[0]*4+\
                    [scale_value_continous(self.goal,0, self.max_function_int_value)]+\
                        [scale_value_continous(self.select_function_key,0, self.max_function_int_value)]

                    
        elif self.flag_model==4:
            self.state=[idx for idx in self.conEnvData_wsa["state_variables_selected"]]+\
                self.function_for_identifier_unnormalized+ \
                    [0]*(1+self.num_reads+self.num_writes)*4+ [self.goal]+self.conEnvData_wsa["function_data"][str(self.goal)]['vector_rw_in_concate'] + \
                        [self.select_function_key]+self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_rw_in_concate']

        elif self.flag_model in [5,7]:
            # use the key and the vector together to denote a function
            goal_vector=self.conEnvData_wsa["function_data"][str(self.goal)]['vector_rw_in_concate']
            func_vector=self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_rw_in_concate']
            if self.flag_model==5:
                self.state = [scale_value_continous(idx,0,self.max_svar_value) for idx in self.conEnvData_wsa["state_variables_selected"]] + \
                             self.function_for_identifier + \
                             [0] * (1+self.num_reads+self.num_writes) * 4 +\
                             [scale_value_continous(self.goal,0, self.max_function_int_value)]+[scale_value_continous(v,0, self.max_svar_value) for v in goal_vector] + \
                             [scale_value_continous(self.select_function_key,0, self.max_function_int_value)]+[scale_value_continous(v,0, self.max_svar_value) for v in func_vector]
            else:
                self.state = [scale_value_continous(idx,0,self.max_svar_value) for idx in self.conEnvData_wsa["state_variables_selected"]] + \
                             self.function_for_identifier_n0 + \
                             [0] * (1+self.num_reads+self.num_writes) * 4 +\
                             [scale_value_continous(self.goal,0, self.max_function_int_value)]+[scale_value_continous(v,0, self.max_svar_value) for v in goal_vector] + \
                             [scale_value_continous(self.select_function_key,0, self.max_function_int_value)]+[scale_value_continous(v,0, self.max_svar_value) for v in func_vector]

        
        elif self.flag_model==6:
            func_vector1 = self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_rw_in_concate']
            func_vector2 = self.conEnvData_wsa["function_data"][str(self.select_function_key)]['vector_in_index_rw']
            
            func_vector1_1 = [scale_value_continous(self.select_function_key, 0, self.max_function_int_value)] +\
                            [ scale_value_continous(v, 0, self.max_svar_value) for v in func_vector1]
            func_vector2_1 = [ scale_value_continous(v, 0, 4) for v in func_vector2]
            func_vector_1_2=func_vector1_1+func_vector2_1
            
            
            func_vector1_g = self.conEnvData_wsa["function_data"][str(self.goal)]['vector_rw_in_concate']
            func_vector2_g = self.conEnvData_wsa["function_data"][str(self.goal)]['vector_in_index_rw']
            
            func_vector1_1_g = [scale_value_continous(self.goal, 0, self.max_function_int_value)] +\
                            [ scale_value_continous(v, 0, self.max_svar_value) for v in func_vector1_g]
            func_vector2_1_g = [ scale_value_continous(v, 0, 4) for v in func_vector2_g]
            func_vector_1_2_g=func_vector1_1_g+func_vector2_1_g
            
            self.state = [scale_value_continous(idx,0,self.max_svar_value) for idx in self.conEnvData_wsa["state_variables_selected"]] + \
                         self.function_for_identifier + [0] * ((1+self.num_reads+self.num_writes+self.num_state_var))* 4 +\
                         func_vector_1_2_g+ func_vector_1_2


        observation = np.array(self.state)
        # print(f'depth:{0};{len(self.state)};obs:{self.state}')
        return observation,{}
    
    def print_(self, content:str):
        # if not self.test:
        #     print(content)
        pass
    
    def print_2(self,content:str):
        # if not self.test:
        #     print(content)
        pass
    
    def print_for_debug(self, content:str):
        # if self.goal==2:
        #     print(content)
        pass
    
    def valid_action_mask(self):
      action_mask = np.zeros(self.action_space.n)
      for valid_action in [0,1]:
        action_mask[valid_action]=1
      return action_mask

