import ast
import math
from copy import deepcopy


import fdg.global_config
from fdg.control.function_assignment import FunctionAssignment
from fdg.fwrg_manager import FWRG_manager
from fdg.output_data import print_data_for_mine_strategy, print_data_for_bfs_strategy, print_data_for_dfs_strategy
from fdg.utils import get_ftn_seq_from_key, random_indices, get_key, get_ftn_seq_from_key_1, str_without_space_line, \
    get_key_1_prefix

from mythril.laser.plugin.plugins.dependency_pruner import get_writes_annotation_from_ws




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

    def assign_states(self, deep_functions: list=None, current_state_key: str = None, fdfg: FWRG_manager = None,
                      states_dict: dict = {},iteration:int=0) -> list:
        pass



    def termination(self,states_num:int=0,current_seq_length:int=0,sequence_depth_limit:int=0,iteration:int=0)->bool:
        ...

class Seq(FunctionSearchStrategy):
    def __init__(self):
        self.queue = []

        # # 0x00c0443f42932d9efe27e64409b21d2e48928d66.sol	0.5.8	JarvisExchange
        # self.sequences = [
        #     ['setController(address)', 'withdrawToken(address,uint256,uint256)']
        # ]

        # 0x9afb9d7ed0f6c054ec76ea61d5cabc384d4dcb25.sol	0.4.26	ConverterFactory
        self.sequences = [
            ['transferOwnership(address)', 'acceptOwnership()']
        ]
        #0x2caf5a42ec2d6747ec696714bf913b174d94fdf0.sol	0.5.17	LexLocker
        # contain GT, and function signature with 3 bytes
        self.sequences = [
            ['updateJudgmentReward(uint256)']
        ]

        if len(fdg.global_config.sequences)>0:
            # assume that the sequenes are presented as string
            self.sequences=ast.literal_eval(fdg.global_config.sequences)
        else:self.sequences=[]

        super().__init__('seq')

    def initialize(self, main_path_sf: dict, main_path_df: dict, fdfg_manager: FWRG_manager):
        ...





    def termination(self, states_num: int = 0, current_seq_length: int = 0, sequence_depth_limit: int = 0,
                    iteration: int = 0) -> bool:
        # need to test
        if states_num == 0: return True
        if iteration>2:
            if len(self.queue) == 0:
                return True
        return False

    def assign_states(self, deep_functions: list = None, current_state_key: str = None, fdfg: FWRG_manager = None,
                      states_dict: dict = {},iteration:int=0) -> list:
        """

        :param deep_functions:
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
                    for i in range(len(seq)):
                        if seq[i]!=seq_[i]:break
                    functions.append(seq_[len(seq)])
            if len(functions)>0:
                return {state_key:functions},True



class Mine(FunctionSearchStrategy):
    def __init__(self):

        self.proprocess_timeout=False
        self.preprocess_coverage=0


        self.state_storage={}
        self.write_slots_genesis_states=[]
        self.state_write_slots={}
        self.state_priority={}

        self.cur_queue=[]
        self.d1=[]
        self.d2=[]
        self.d3=[]



        self.flag_consider_states=False  # indicate that the generated states are queued (only for some states one depth deeper than the starting states)
        self.flag_one_state_at_depth1=False
        super().__init__('mine')


    def initialize(self,flag_one_state_depth1:bool,preprocess_timeout:bool, preprocess_coverage:float,all_functions:list,fwrg_manager:FWRG_manager):


        self.flag_one_state_at_depth1=flag_one_state_depth1
        self.preprocess_timeout=preprocess_timeout
        self.preprocess_coverage=preprocess_coverage

        self.functionAssignment=FunctionAssignment(all_functions,fwrg_manager)
        self.fwrg_manager=fwrg_manager

    def update_states(self, states_dict:dict)->list:
        address = fdg.global_config.contract_address.value
        sequences=[]
        for key,states in states_dict.items():
            for state in states:
                ftn_seq=get_ftn_seq_from_key_1(key)
                if 'constructor' not in ftn_seq:
                    if ftn_seq not in sequences:
                        sequences.append(ftn_seq)
                    self.world_states[key]=[deepcopy(state)]
                else:
                    for slot in list(state.accounts[address].storage.printable_storage.keys()):
                        if slot not in self.write_slots_genesis_states:
                            self.write_slots_genesis_states.append(slot)

                    print(f'self.write_slots_genesis_states={self.write_slots_genesis_states}')

                self.state_storage[key] = state.accounts[address].storage.printable_storage
                self.state_write_slots[key]=get_writes_annotation_from_ws(state)

        return sequences



    def get_priority_value(self,key:str)->int:
        def value(data:list)->int:
            if len(data)==1:
                if data[0]:return 3
                else: return 2
            elif len(data)==2:
                if data.count(True)==2:
                    return 3
                elif data.count(True)==1:
                    return 2
                else:return 1
            elif len(data)==3:
                if data.count(True)==3:
                    return 4
                elif data.count(True)==2:
                    return 3
                elif data.count(True)==0:
                    return 1
                else:return 2
            else:
                return 0


        values=[]
        ftn_seq = get_ftn_seq_from_key_1(key)
        flag_simple_sv=False
        if len(ftn_seq) in self.state_write_slots[key].keys():
            write_slots = self.state_write_slots[key][len(ftn_seq)]
            for slot in write_slots:
                v=0
                if slot.symbolic:
                    v += 1
                else:
                    if not flag_simple_sv:
                        flag_simple_sv=True
                    v += 3

                if slot not in self.state_storage[key].keys():
                    continue
                # check the value written
                write = self.state_storage[key][slot]
                if write.symbolic:
                    v += 1
                else:
                    if not str(write.value)=='0':
                        v += 3

                # check with the genesis state
                d_v=[]
                if slot not in self.write_slots_genesis_states:
                    d_v.append(True)
                else:
                    d_v.append(False)
                # check with previous depths except for depth 0
                for i in range(1, len(ftn_seq)):
                    if i in self.state_write_slots[key].keys():
                        w_slots = self.state_write_slots[key][i]
                        if slot not in w_slots:
                            d_v.append(True)
                        else:
                            d_v.append(False)
                v+=value(d_v)
                values.append(v)
        if len(values)==0:
            return 0
        else:
            final_v = max(values)
            if len(values)>=2:
                final_v+=1

            if len(ftn_seq)==3:
                if flag_simple_sv:
                    final_v=final_v-1
                else:
                    final_v= final_v-2
            elif  len(ftn_seq)==2:
                if not flag_simple_sv:
                    final_v= max(values) - 1


            # check if there are repeated functions in ftn_seq
            if len(ftn_seq) > len(list(set(ftn_seq))):
                final_v-=3
            return final_v

    def compute_order_priority(self, state_keys:list)->list:
        # count based on the key prefix
        count = {}
        for key in state_keys:
            key_prefix = get_key_1_prefix(key)
            if key_prefix not in count.keys():
                count[key_prefix] = [key]
            else:
                count[key_prefix] += [key]

        # compute priority values
        left_key_value_pairs=[]
        for key_prefix, keys in count.items():
            if len(keys) == 1:
                v = self.get_priority_value(keys[0])
                self.state_priority[keys[0]] = v
                left_key_value_pairs.append((keys[0],v))
                continue

            # get state keys with different priority values that share the same function sequence (key prefix)
            key_value_pairs=[]
            for key in keys:
                v = self.get_priority_value(key)
                self.state_priority[key] = v
                key_value_pairs.append((key,v))

            key_value_pairs.sort(key=lambda x: x[1],reverse=True)
            cur_value = -1
            for key, value in key_value_pairs:
                if not cur_value == value:
                    left_key_value_pairs.append((key,value))
                    cur_value = value
        left_key_value_pairs.sort(key=lambda x:x[1],reverse=True)
        return left_key_value_pairs

    def order_states(self,state_keys:list):
        """
        the elements in the list may be a dict type
        :param state_keys:
        :return:
        """
        temp=[]
        for sk in state_keys:
            if isinstance(sk,dict):
                temp.append(list(sk.keys())[0])
            else:
                temp.append(sk)
        temp = [(item, self.state_priority[item]) for item in temp]
        temp.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in temp]





    def termination(self, states_num: int = 0, current_seq_length: int = 0, sequence_depth_limit: int = 0,
                    iteration: int = 0) -> bool:
        # print(f'{states_num}:{len(self.d1)}:{len(self.d2)}:{len(self.d3)}:{len(self.cur_queue)}:{iteration}')
        if iteration <= 2:
            if states_num == 0: return True

        return False




    def assign_states(self, deep_functions: list = None,  states_dict: dict = {},iteration:int=0) -> list:
        """

        :param deep_functions:
        :param fwrg:
        :param states_dict:
        :return:
        """
        if self.preprocess_timeout or fdg.global_config.preprocessing_exception:
            if self.preprocess_coverage<50:
                # execute 70% of functions+ functions assigned based on the partial graph
                return self.assign_states_timeout(states_dict,7)
            elif self.preprocess_coverage<80:
                # execute 50% of functions+ functions assigned based on the partial graph
                return self.assign_states_timeout(states_dict,5)
            else:
                # execute 30% of functions + functions assigned based on the partial graph
                return self.assign_states_timeout(states_dict, 3)
        return self.assign_states_normal(deep_functions,states_dict)


    def remove_trivial_state_key(self,state_keys:list):
        """
        find the state keys that have the same function sequence but ended with different indices
        keep one state key if they have the same priority value.
        :param state_keys:
        :return:
        """
        left_keys=[]
        count={}

        for key in state_keys:
            key_prefix=get_key_1_prefix(key)
            if key_prefix not in count.keys():
                count[key_prefix]=[key]
            else:
                count[key_prefix]+=[key]
        for key_prefix,keys  in count.items():
            if len(keys)==1:
                left_keys.append(keys[0])
                continue
            key_value_pairs=[(key,self.state_priority[key]) for key in keys]
            key_value_pairs.sort(key=lambda x:x[1])
            cur_value=-1
            for key,value in key_value_pairs:
                if not cur_value==value:
                    left_keys.append(key)
                    cur_value=value
        return left_keys






    def assign_states_normal(self, deep_functions: list = None, states_dict: dict = {}) -> list:
        """

        :param deep_functions:
        :param fwrg:
        :param states_dict:
        :return:
        """

        if len(states_dict) > 0:
            sequences = self.update_states(states_dict)

            order_state_keys = self.compute_order_priority(list(states_dict.keys()))

            seq_len = len(sequences[0])
            if len(order_state_keys)>0:
                # arrange states at the end of depth 1
                if seq_len == 1:
                    d1_queue = [item for item, _ in order_state_keys]
                    self.cur_queue = [d1_queue.pop(0)] + self.cur_queue

                    # priority children that are depth-k functions
                    to_cur_queue = []
                    depth_k=[ftn for ftn,_ in deep_functions]
                    for state_key in d1_queue:
                        ftn_seq = get_ftn_seq_from_key_1(state_key)
                        children = self.fwrg_manager.get_children_bf_update(ftn_seq[-1])
                        child_dk = [child for child in children if child in depth_k]
                        if len(child_dk) > 0:
                            to_cur_queue.append({state_key: {'to_execute': child_dk}})
                            self.d1.append({state_key: {'not_to_execute': child_dk}})
                        else:
                            self.d1.append(state_key)
                    if len(to_cur_queue) > 0:
                        self.cur_queue = to_cur_queue + self.cur_queue
                else:
                    # put stats with priority value >5 to current queue
                    to_cur_queue = []
                    to_dx_queue = []
                    if self.flag_consider_states:
                        # consider if there are states with priority value > 5
                        for s_key, value in order_state_keys:
                            if value > 5:
                                to_cur_queue.append(s_key)
                            else:
                                to_dx_queue.append(s_key)
                    else:
                        # do not consider the generated states currently
                        to_dx_queue = [item for item, _ in order_state_keys]

                    # put
                    if len(to_dx_queue) > 0:
                        if seq_len == 2:
                            self.d2+=to_dx_queue
                            self.d2=self.remove_trivial_state_key(self.d2)
                            self.d2=self.order_states(self.d2)

                        elif seq_len == 3:
                            self.d3+=to_dx_queue
                            self.d3 = self.remove_trivial_state_key(self.d3)
                            self.d3 = self.order_states(self.d3)
                        else:
                            pass

                    # reorder the states in the current queue
                    if len(to_cur_queue) > 0:
                        self.cur_queue = to_cur_queue + self.cur_queue
                        # print(f'old cur_queue:{self.cur_queue}')
                        self.cur_queue=self.order_states(self.cur_queue)
                        # print(f'new cur_queue:{self.cur_queue}')

        # ---------------
        print_data_for_mine_strategy(self.cur_queue, self.d1, self.d2, self.d3, self.state_write_slots, self.state_priority, self.state_storage)
        # --------------

        if self.flag_one_state_at_depth1:
            self.flag_one_state_at_depth1=False # only consider once
            state_key=self.cur_queue.pop(0)
            assign_functions= self.functionAssignment.assign_all_functions()

            return {state_key: assign_functions},True

        # assign a state and the functions to be executed on it
        while True:
            if len(self.cur_queue) == 0:
                # find a state with the highest priority value
                keys_ary=[]
                if len(self.d1) > 0:
                    if isinstance(self.d1[0],dict):
                        keys_ary.append(list(self.d1[0].keys())[0])
                    else:
                        keys_ary.append(self.d1[0])
                else:
                    keys_ary.append('')
                if len(self.d2) > 0:
                    keys_ary.append(self.d2[0])
                else:
                    keys_ary.append('')
                if len(self.d3) > 0:
                    keys_ary.append(self.d3[0])
                else:
                    keys_ary.append('')
                key_priority_value=[self.state_priority[key] if len(key)>0 else 0 for key in keys_ary ]
                index=key_priority_value.index(max(key_priority_value))
                if index==0:
                    if key_priority_value[0]>0:
                        self.cur_queue = [self.d1.pop(0)]
                elif index==1:
                    if key_priority_value[1] > 0:
                        self.cur_queue = [self.d2.pop(0)]
                elif index==2:
                    if key_priority_value[2] > 0:
                        self.cur_queue = [self.d3.pop(0)]


            if len(self.cur_queue)==0: return {},None

            # assign functions
            state_key = ''
            to_execute_children = []
            not_to_execute = []
            pop_item = self.cur_queue.pop(0)
            if isinstance(pop_item, dict):
                for key, value in pop_item.items():
                    state_key = key
                    if 'to_execute' in value.keys():
                        self.flag_consider_states = False
                        to_execute_children = value['to_execute']
                    elif 'not_to_execute' in value.keys():
                        self.flag_consider_states = True
                        not_to_execute = value['not_to_execute']
            else:
                self.flag_consider_states = True
                state_key = pop_item

            assigned_children=self.functionAssignment.assign_functions(state_key,deep_functions,to_execute_children,not_to_execute)
            if len(assigned_children)>0:
                return {state_key: assigned_children},self.flag_consider_states

    def assign_states_timeout(self, states_dict: dict = {},percent_of_functions:int=1) -> list:
        """

        :param deep_functions:
        :param fwrg:
        :param states_dict:
        :return:
        """

        if len(states_dict) > 0:
            sequences = self.update_states(states_dict)
            order_state_keys = self.compute_order_priority(list(states_dict.keys()))
            seq_len = len(sequences[0])

            # put stats with priority value >5 to current queue
            to_cur_queue=[]
            to_dx_queue=[]

            # consider if there are states with priority value > 5
            for s_key,value in order_state_keys:
                if value>5:
                    to_cur_queue.append(s_key)
                else:
                    to_dx_queue.append(s_key)
            # save low-priority states based on length
            if len(to_dx_queue)>0:
                if seq_len==1:
                    self.d1=to_dx_queue
                elif seq_len==2:
                    self.d2+=to_dx_queue
                    self.d2 = self.remove_trivial_state_key(self.d2)
                    self.d2 = self.order_states(self.d2)
                elif seq_len==3:
                    self.d3+=to_dx_queue
                    self.d3 = self.remove_trivial_state_key(self.d3)
                    self.d3= self.order_states(self.d3)
                else:
                    pass

            # reorder the states in the current queue
            if len(to_cur_queue)>0:
                self.cur_queue = to_cur_queue + self.cur_queue
                # print(f'old cur_queue:{self.cur_queue}')
                self.cur_queue=self.order_states(self.cur_queue)
                # print(f'new cur_queue:{self.cur_queue}')

        # ---------------
        print_data_for_mine_strategy(self.cur_queue, self.d1, self.d2, self.d3, self.state_write_slots, self.state_priority,
                                     self.state_storage)
        # --------------

        if self.flag_one_state_at_depth1:
            self.flag_one_state_at_depth1=False
            if len(self.cur_queue)==0:
                state_key = self.d1.pop(0)
            else:
                state_key = self.cur_queue.pop(0)
            assign_functions = self.functionAssignment.assign_all_functions()

            return {state_key : assign_functions},True


            # assign a state and the functions to be executed on it
        while True:
            if len(self.cur_queue) == 0:
                keys_ary = []
                if len(self.d1) > 0:
                    keys_ary.append(self.d1[0])
                else:
                    keys_ary.append('')
                if len(self.d2) > 0:
                    keys_ary.append(self.d2[0])
                else:
                    keys_ary.append('')
                if len(self.d3) > 0:
                    keys_ary.append(self.d3[0])
                else:
                    keys_ary.append('')
                key_priority_value = [self.state_priority[key] if len(key) > 0 else 0 for key in keys_ary]
                index = key_priority_value.index(max(key_priority_value))
                if index == 0:
                    if key_priority_value[0] > 0:
                        self.cur_queue = [self.d1.pop(0)]
                elif index == 1:
                    if key_priority_value[1] > 0:
                        self.cur_queue = [self.d2.pop(0)]
                elif index == 2:
                    if key_priority_value[2] > 0:
                        self.cur_queue = [self.d3.pop(0)]


            if len(self.cur_queue)==0:return {},None

            state_key=self.cur_queue.pop(0)
            assigned_functions=self.functionAssignment.assign_functions_timeout(state_key, percent_of_functions)
            if len(assigned_functions)>0:
                return {state_key: assigned_functions},True



    def find_a_state_for_dk(self,state_keys:list,dk_functions:list,fwrg:FWRG_manager)->list:
        if len(self.d3)==0: return []
        for state_key in state_keys:
            ftn_seq=get_ftn_seq_from_key_1(state_key)
            for dk in dk_functions:
                parents=fwrg.get_parents_frwg(dk)
                if ftn_seq[-1] in parents:
                    if ftn_seq[0] in parents or ftn_seq[1] in parents:
                        return [state_key]
        return []



class DFS(FunctionSearchStrategy):
    def __init__(self):
        self.stack=[]
        self.preprocess_timeout = False
        self.preprocess_coverage = 0
        self.flag_one_state_at_depth1=False
        super().__init__('dfs')

    def initialize(self,flag_one_state_depth1:bool,preprocess_timeout:bool, preprocess_coverage:float,all_functions:list,fwrg_manager:FWRG_manager):
        self.flag_one_state_at_depth1=flag_one_state_depth1
        self.preprocess_timeout = preprocess_timeout
        self.preprocess_coverage = preprocess_coverage
        self.functionAssignment=FunctionAssignment(all_functions,fwrg_manager)


    def termination(self,states_num:int=0, current_seq_length: int = 0, sequence_depth_limit: int = 0,iteration:int=0)->bool:
        if iteration<=2:
            if states_num==0:return True
        return False





    def assign_states(self, deep_functions: list=None, states_dict: dict = {},iteration:int=0) -> list:

        """
            save states, push state keys to the stack
            select a state by poping an item from the stack
            assign functions to be executed on the selected state
        :param deep_functions:
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

        if self.flag_one_state_at_depth1:
            self.flag_one_state_at_depth1=False
            state_key = self.stack.pop()
            assign_functions = self.functionAssignment.assign_all_functions()

            return {state_key : assign_functions},True

        while True:
            if len(self.stack)==0:
                return {},None

            state_key=self.stack.pop()

            if self.preprocess_timeout or fdg.global_config.preprocessing_exception:
                if self.preprocess_coverage<50:
                    assigned_functions=self.functionAssignment.assign_functions_timeout(state_key, 7)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
                elif self.preprocess_coverage < 80:
                    assigned_functions = self.functionAssignment.assign_functions_timeout(state_key, 5)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
                else:
                    assigned_functions = self.functionAssignment.assign_functions_timeout(state_key, 3)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
            assigned_functions = self.functionAssignment.assign_functions(state_key,deep_functions)
            if len(assigned_functions) > 0:
                return {state_key: assigned_functions},True



class BFS(FunctionSearchStrategy):
    """
    no need to save states
    """
    def __init__(self):
        self.flag_one_state_at_depth1=False
        self.preprocess_timeout = False
        self.preprocess_coverage = 0
        self.queue=[]
        super().__init__('bfs')
        pass

    def initialize(self,flag_one_state_depth1:bool,preprocess_timeout:bool, preprocess_coverage:float,all_functions:list,fwrg_manager:FWRG_manager):
        self.flag_one_state_at_depth1=flag_one_state_depth1
        self.preprocess_timeout = preprocess_timeout
        self.preprocess_coverage = preprocess_coverage
        self.functionAssignment=FunctionAssignment(all_functions,fwrg_manager)

    def termination(self,states_num:int=0, current_seq_length: int = 0, sequence_depth_limit: int = 0,iteration:int=0)->bool:
        if iteration <= 2:
            if states_num == 0: return True

        return False


    def assign_states(self, deep_functions: list=None, current_state_key: str = None, fwrg: FWRG_manager = None,
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

        if self.flag_one_state_at_depth1:
            self.flag_one_state_at_depth1 = False
            state_key = self.queue.pop(0)
            assign_functions = self.functionAssignment.assign_all_functions()

            return {state_key: assign_functions},True


        while True:
            if len(self.queue) == 0:
                return {},None

            state_key = self.queue.pop(0)
            if self.preprocess_timeout or  fdg.global_config.preprocessing_exception:
                if self.preprocess_coverage < 50:
                    assigned_functions = self.functionAssignment.assign_functions_timeout(state_key, 7)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
                elif self.preprocess_coverage < 80:
                    assigned_functions = self.functionAssignment.assign_functions_timeout(state_key, 5)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
                else:
                    assigned_functions = self.functionAssignment.assign_functions_timeout(state_key, 3)
                    if len(assigned_functions) > 0:
                        return {state_key: assigned_functions},True
                    continue
            assigned_functions = self.functionAssignment.assign_functions(state_key, deep_functions)
            if len(assigned_functions) > 0:
                return {state_key: assigned_functions},True





class RandomBaseline(FunctionSearchStrategy):
    """
    no need to save states
    """
    def __init__(self,percent_of_functions:int,functions:list):
        self.functionAssignment=FunctionAssignment(functions,None,select_percent=percent_of_functions)
        self.flag_one_state_at_depth1=False
        self.queue=[]
        super().__init__('baseline')

    def initialize(self, flag_one_state_depth1: bool):
        self.flag_one_state_at_depth1 = flag_one_state_depth1

    def assign_states(self, deep_functions: list=None, states_dict: dict = {}) -> list:
        """
        apply BFS
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

        print_data_for_bfs_strategy(self.queue)

        if self.flag_one_state_at_depth1:
            self.flag_one_state_at_depth1 = False
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
        #
        # if iteration > 1:  # only check stack after iteration > 2
        #     if len(self.queue) == 0:
        #         return True

        return False




