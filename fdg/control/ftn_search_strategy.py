import ast

from copy import deepcopy


import fdg.global_config
from fdg.control.function_assignment import FunctionAssignment

from fdg.fwrg_manager import FWRG_manager
from fdg.output_data import print_data_for_bfs_strategy, print_data_for_dfs_strategy

from fdg.utils import get_ftn_seq_from_key_1




class FunctionSearchStrategy():
    def __init__(self,strategy_name:str):
        self.name=strategy_name
        self.world_states={}
        self.search_history={}
        self.current_state_key=''
        # print(f'search strategy: {self.name}')

    def save_states(self,key:str,states:list):
        if key in self.world_states.keys():
            self.world_states[key]+=states
        else:
            self.world_states[key]=states
    def get_states(self,key:str):
        if key in self.world_states.keys():
            return self.world_states[key]
        else:
            return []
    def delete_state(self,key:str):
        if key in self.world_states.keys():
            self.world_states.pop(key)

    def assign_states(self, dk_functions: list=None, current_state_key: str = None, fdfg: FWRG_manager = None,
                      states_dict: dict = {}, iteration:int=0) -> list:
        pass



    def termination(self,states_num:int=0,current_seq_length:int=0,sequence_depth_limit:int=0,iteration:int=0)->bool:
        ...



class Seq(FunctionSearchStrategy):
    def __init__(self):
        self.queue = []
        if len(fdg.global_config.sequences)>0:
            # assume that the sequenes are presented as string
            self.sequences=fdg.global_config.sequences
        else:self.sequences=[]

        super().__init__('seq')

    def initialize(self):
        ...


    def termination(self, states_num: int = 0, current_seq_length: int = 0, sequence_depth_limit: int = 0,
                    iteration: int = 0) -> bool:
        # need to test
        if states_num == 0: return True
        return False

    def assign_states(self, dk_functions: list = None, current_state_key: str = None, fdfg: FWRG_manager = None,
                      states_dict: dict = {}, iteration:int=0) -> list:
        """

        :param dk_functions:
        :param current_state_key:
        :param fdfg:
        :param states_dict:
        :return:
        """
        if len(states_dict)>0:
            for key, states in states_dict.items():

                if key not in self.world_states.keys():
                    self.world_states[key]=deepcopy(states)
                else:
                    self.world_states[key]+=deepcopy(states)
                self.queue.append(key)

        while True:
            if len(self.queue)==0: return {},False
            state_key=self.queue.pop(0)
            if state_key=='constructor':
                if len(self.sequences)==0:
                    return {},True
                return {'constructor':[seq[0] for seq in self.sequences]},True

            seq=get_ftn_seq_from_key_1(state_key)
            functions=[]
            for seq_ in self.sequences:
                if len(seq)==len(seq_):continue
                if len(seq)<len(seq_):
                    flag_add=True
                    for i in range(len(seq)):
                        if seq[i]!=seq_[i]:
                            flag_add=False
                            break
                    if flag_add:
                        functions.append(seq_[len(seq)])
            if len(functions)>0:
                return {state_key:functions},True


class DFS(FunctionSearchStrategy):
    def __init__(self):
        self.stack=[]
        self.preprocess_timeout = False
        self.preprocess_coverage = 0
        self.flag_one_start_function=False
        super().__init__('dfs')

    def initialize(self, flag_one_start_function:bool, preprocess_timeout:bool, preprocess_coverage:float, all_functions:list, fwrg_manager:FWRG_manager):
        self.flag_one_start_function=flag_one_start_function
        self.preprocess_timeout = preprocess_timeout
        self.preprocess_coverage = preprocess_coverage
        self.functionAssignment=FunctionAssignment(all_functions,fwrg_manager)


    def termination(self,states_num:int=0, current_seq_length: int = 0, sequence_depth_limit: int = 0,iteration:int=0)->bool:
        if iteration<=2:
            if states_num==0:return True
        return False





    def assign_states(self, dk_functions: list=None, states_dict: dict = {}, iteration:int=0) -> list:

        """
            save states, push state keys to the stack
            select a state by poping an item from the stack
            assign functions to be executed on the selected state
        :param dk_functions:
        :param current_state_key:
        :param fdfg:
        :param states_dict:
        :return:
        """
        if len(states_dict)>0:
            for key, states in states_dict.items():
                ftn_seq=get_ftn_seq_from_key_1(key)
                if len(ftn_seq)>=fdg.global_config.seq_len_limit:
                    continue # do not save these states as they will not be explored
                # save states
                self.world_states[key]=deepcopy(states)
                self.stack.append(key)

        print_data_for_dfs_strategy(self.stack)

        if self.flag_one_start_function:
            self.flag_one_start_function=False
            state_key = self.stack.pop()
            assign_functions = self.functionAssignment.assign_all_functions()

            return {state_key : assign_functions},True

        while True:
            if len(self.stack)==0:
                return {},None

            state_key=self.stack.pop()

            if self.preprocess_timeout or fdg.global_config.preprocessing_exception:
                if self.preprocess_coverage<50:
                    assigned_functions=self.functionAssignment.assign_functions_timeout(state_key, dk_functions, 7)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
                elif self.preprocess_coverage < 80:
                    assigned_functions = self.functionAssignment.assign_functions_timeout(state_key, dk_functions, 5)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
                else:
                    assigned_functions = self.functionAssignment.assign_functions_timeout(state_key, dk_functions, 3)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
            assigned_functions = self.functionAssignment.assign_functions(state_key, dk_functions)
            if len(assigned_functions) > 0:
                return {state_key: assigned_functions},True



class BFS(FunctionSearchStrategy):
    """
    no need to save states
    """
    def __init__(self):
        self.flag_one_start_function=False
        self.preprocess_timeout = False
        self.preprocess_coverage = 0
        self.queue=[]
        super().__init__('bfs')
        pass

    def initialize(self, flag_one_start_function:bool, preprocess_timeout:bool, preprocess_coverage:float, all_functions:list, fwrg_manager:FWRG_manager):
        self.flag_one_start_function=flag_one_start_function
        self.preprocess_timeout = preprocess_timeout
        self.preprocess_coverage = preprocess_coverage
        self.functionAssignment=FunctionAssignment(all_functions,fwrg_manager)

    def termination(self,states_num:int=0, current_seq_length: int = 0, sequence_depth_limit: int = 0,iteration:int=0)->bool:
        if iteration <= fdg.global_config.p1_dl+1:
            if states_num == 0: return True
        return False


    def assign_states(self, dk_functions: list=None, current_state_key: str = None, fwrg: FWRG_manager = None,
                      states_dict: dict = {},iteration:int=0) -> list:
        """
        assign functions for multiple states at the same time.
        :param deep_functions:
        :param current_state_key:
        :param fwrg:
        :param states_dict:
        :return:
        """

        if len(states_dict) > 0:
            for key, states in states_dict.items():
                ftn_seq = get_ftn_seq_from_key_1(key)
                if len(ftn_seq) >= fdg.global_config.seq_len_limit:
                    continue  # do not save these states as they will not be explored
                # save states
                self.world_states[key] = deepcopy(states)
                self.queue.append(key)

            # # put key containing fallback at the end of the queue
            # if len(ftn_seq)==1:
            #     temp=[]
            #     for item in self.queue:
            #         if 'fallback' in item:
            #             temp.append(item)
            #         else:
            #             temp=[item]+temp
            #     self.queue=temp


        print_data_for_bfs_strategy(self.queue)

        if self.flag_one_start_function:
            self.flag_one_start_function = False
            state_key = self.queue.pop(0)
            assign_functions = self.functionAssignment.assign_all_functions()

            return {state_key: assign_functions},True


        while True:
            if len(self.queue) == 0:
                return {},None

            state_key = self.queue.pop(0)
            if self.preprocess_timeout or  fdg.global_config.preprocessing_exception:
                if self.preprocess_coverage < 50:
                    assigned_functions = self.functionAssignment.assign_functions_timeout(state_key,dk_functions, 7)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
                elif self.preprocess_coverage < 80:
                    assigned_functions = self.functionAssignment.assign_functions_timeout(state_key,dk_functions, 5)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
                else:
                    assigned_functions = self.functionAssignment.assign_functions_timeout(state_key,dk_functions, 3)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
            assigned_functions = self.functionAssignment.assign_functions(state_key, dk_functions)
            if len(assigned_functions) > 0:
                return {state_key: assigned_functions},True



class RandomBaseline(FunctionSearchStrategy):
    """
    no need to save states
    """
    def __init__(self,percent_of_functions:int,functions:list):
        self.functionAssignment=FunctionAssignment(functions,None,select_percent=percent_of_functions)
        self.flag_one_start_function=False
        self.queue=[]
        super().__init__('baseline')

    def initialize(self, flag_one_start_function: bool):
        self.flag_one_start_function = flag_one_start_function

    def assign_states(self, dk_functions: list=None, states_dict: dict = {}) -> list:
        """
        apply BFS
        :param dk_functions:
        :param current_state_key:
        :param fwrg:
        :param states_dict:
        :return:
        """
        if len(states_dict) > 0:
            for key, states in states_dict.items():
                ftn_seq = get_ftn_seq_from_key_1(key)
                if len(ftn_seq) >= fdg.global_config.seq_len_limit:
                    continue  # do not save these states as they will not be explored
                # save states
                self.world_states[key] = deepcopy(states)
                self.queue.append(key)

        print_data_for_bfs_strategy(self.queue)

        if self.flag_one_start_function:
            self.flag_one_start_function = False
            state_key = self.queue.pop(0)
            assign_functions = self.functionAssignment.assign_all_functions()

            return {state_key: assign_functions}, True

        while True:
            if len(self.queue) == 0:
                return {}, None

            state_key = self.queue.pop(0)

            assigned_functions =self.functionAssignment.assign_functions_for_baseline()
            if len(assigned_functions) > 0:
                return {state_key: assigned_functions}, True




    def termination(self, states_num: int = None, current_seq_length: int = 0,
                    sequence_depth_limit: int = 0,iteration:int=0) -> bool:

        if iteration <= 1:
            if states_num == 0: return True
        else:
            if len(self.queue)==0:
                return True

        return False




