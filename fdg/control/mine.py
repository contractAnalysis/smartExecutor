from copy import deepcopy

import fdg
from fdg.control.ftn_search_strategy import FunctionSearchStrategy
from fdg.control.function_assignment import FunctionAssignment
from fdg.control.weight_computation import compute, \
    turn_write_features_to_a_value
from fdg.expression_slot import is_slot_in_a_list, \
    identify_slot_from_symbolic_slot_expression, common_elements

from fdg.fwrg_manager import FWRG_manager
from fdg.output_data import print_data_for_mine_strategy_1, \
    print_data_for_mine_strategy, my_print
from fdg.utils import get_ftn_seq_from_key_1, get_key_1_prefix, \
    random_select_from_list
from mythril.laser.plugin.plugins.dependency_pruner import \
    get_writes_annotation_from_ws



class Mine(FunctionSearchStrategy):
    def __init__(self):
        self.preprocess_timeout=False
        self.preprocess_coverage=0

        self.state_storage={}
        self.written_slots_in_depth_str={} # the writes from all depths in str version

        self.queue=[]
        self.state_key_assigned_at_last=""
        # self.parent_state_keys = {}
        self.flag_one_state_at_depth1=False
        super().__init__('mine')


    def initialize(self,flag_one_state_depth1:bool,preprocess_timeout:bool, preprocess_coverage:float,all_functions:list,fwrg_manager:FWRG_manager):
        self.flag_one_state_at_depth1=flag_one_state_depth1
        self.preprocess_timeout=preprocess_timeout
        self.preprocess_coverage=preprocess_coverage

        self.functionAssignment=FunctionAssignment(all_functions,fwrg_manager)
        self.fwrg_manager=fwrg_manager


    def assign_states(self, dk_functions: list = None, states_dict: dict = {}, iteration:int=0) -> list:
        """

        :param dk_functions:
        :param fwrg:
        :param states_dict:
        :return:
        """
        if self.preprocess_timeout or fdg.global_config.preprocessing_exception:
            if self.preprocess_coverage<50:
                # execute 70% of functions+ functions assigned based on the partial graph
                return self.assign_states_timeout(dk_functions, states_dict, 7)
            elif self.preprocess_coverage<80:
                # execute 50% of functions+ functions assigned based on the partial graph
                return self.assign_states_timeout(dk_functions, states_dict, 5)
            elif self.preprocess_coverage<90:
                # execute 50% of functions+ functions assigned based on the partial graph
                return self.assign_states_timeout(dk_functions, states_dict, 3)
            else:
                # execute 10% of functions + functions assigned based on the partial graph
                return self.assign_states_timeout(dk_functions, states_dict, 1)
        return self.assign_states_normal(dk_functions, states_dict)

    def assign_states_normal(self, dk_functions: list = None, states_dict: dict = {}) -> list:
        """

        :param dk_functions:
        :param fwrg:
        :param states_dict:
        :return: a state and the functions to be executed on it
        a flag indicating whether this state can be deleted or not.
        """
        if len(dk_functions)==0:return {}, None
        if len(states_dict) > 0:

            # save the new states
            self.update_states(states_dict)
            self.filter_states()

        # ---------------
        print_data_for_mine_strategy(self.queue)

        # --------------
        # case 1
        # assign the only state
        if self.flag_one_state_at_depth1:
            self.flag_one_state_at_depth1=False # only consider once
            state_key=self.queue.pop(0)
            assign_functions= self.functionAssignment.assign_all_functions()
            self.state_key_assigned_at_last=state_key
            return {state_key: assign_functions},True

        # --------------
        # case 2
        # assign a state and the functions to be executed on it
        while True:
            if len(self.queue) == 0:
                return {}, None

            to_execute_children = []
            not_to_execute = []
            flag_can_be_deleted=True

            # pick up a state from the queue
            targets=[dk for dk,_ in dk_functions]
            state_key = self.pickup_a_state(targets)  # order the states in self.queue and pick up the one has the highest weight

            # assign functions
            assigned_children=self.functionAssignment.assign_functions(state_key,dk_functions,to_execute_children,not_to_execute)
            if len(assigned_children)>0:
                self.state_key_assigned_at_last = state_key
                return {state_key: assigned_children},flag_can_be_deleted

    def assign_states_timeout(self, dk_functions: list = None, states_dict: dict = {}, percent_of_functions:int=1) -> list:
        """

        :param dk_functions:
        :param fwrg:
        :param states_dict:
        :return:
        """
        if len(states_dict) > 0:
            # save the new states
            self.update_states(states_dict)
            self.filter_states()


        # ---------------
        print_data_for_mine_strategy(self.queue)

        # --------------
        # case 1
        # assign the only state
        if self.flag_one_state_at_depth1:
            self.flag_one_state_at_depth1=False # only consider once
            state_key=self.queue.pop(0)
            assign_functions= self.functionAssignment.assign_all_functions()
            self.state_key_assigned_at_last = state_key
            return {state_key: assign_functions},True

        # --------------
        # case 2
        # assign a state and the functions to be executed on it
        while True:
            if len(self.queue) == 0:
                return {}, None

            # pick up a state from the queue
            targets=[dk for dk,_ in dk_functions]
            random_selected_functions=self.functionAssignment.select_functions_randomly(percent_of_functions)
            # for func in random_selected_functions:
            #     if func not in targets:
            #         targets.append(func)
            print(f'randomly selected functions: {random_selected_functions}')

            state_key = self.pickup_a_state(targets)  # order the states in self.queue and pick up the one has the highest weight

            # assign functions
            assigned_functions=self.functionAssignment.assign_functions_timeout_mine(state_key, dk_functions,random_selected_functions)
            if len(assigned_functions)>0:
                self.state_key_assigned_at_last = state_key
                return {state_key: assigned_functions},True

    def termination(self, states_num: int = 0, current_seq_length: int = 0, sequence_depth_limit: int = 0,
                    iteration: int = 0) -> bool:
        # print(f'{states_num}:{len(self.d1)}:{len(self.d2)}:{len(self.d3)}:{len(self.cur_queue)}:{iteration}')
        if iteration <= 2:
            if states_num == 0: return True

        return False

    def update_states(self, states_dict:dict)->list:
        """
        save states
        """
        address = fdg.global_config.contract_address.value

        for key,states in states_dict.items():
            for state in states:
                ftn_seq=get_ftn_seq_from_key_1(key)
                if 'constructor' not in ftn_seq:
                    self.world_states[key]=[deepcopy(state)]
                    self.queue.append(key)
                    self.state_storage[key] = state.accounts[
                        address].storage.printable_storage

                    # # save the parent state key for a state
                    # if len(self.state_key_assigned_at_last) > 0:
                    #     if key not in self.parent_state_keys.keys():
                    #         self.parent_state_keys[key] = self.state_key_assigned_at_last
                    #     else:
                    #         my_print(f'Why a state has two or more parent state keys')
                    #         self.parent_state_keys[key] = self.state_key_assigned_at_last

                    # get written slots for this state
                    # get written slots from its parent, the key of which is saved in self.state_key_assigned_at_last
                    written_slots_all_steps = deepcopy(self.get_written_slots_in_depth_str(self.state_key_assigned_at_last))

                    # get the current writes from the dependency pruner
                    written_slots=get_writes_annotation_from_ws(state)
                    # self.state_write_slots[key]= written_slots

                    writes_str=[]
                    if len(ftn_seq) in written_slots.keys():
                        writes=written_slots[len(ftn_seq)]
                        writes_str=[identify_slot_from_symbolic_slot_expression(s) for s in writes]
                        writes_str=list(set(writes_str))

                    if len(ftn_seq) not in written_slots_all_steps.keys():
                        written_slots_all_steps[len(ftn_seq)]=writes_str
                        self.written_slots_in_depth_str[key]=written_slots_all_steps
                    else:
                        written_slots_all_steps[len(ftn_seq)] = writes_str
                        self.written_slots_in_depth_str[
                            key] = written_slots_all_steps


                else:
                    slots=state.accounts[address].storage.printable_storage.keys()

                    # save the slots in str version
                    slots_str=[identify_slot_from_symbolic_slot_expression(s) for s in slots]
                    if key not in self.written_slots_in_depth_str.keys():
                        self.written_slots_in_depth_str[key]={0:slots_str}


                    self.state_storage[key] = state.accounts[address].storage.printable_storage

    def filter_states(self):
        """
        for states generated from the same function sequence, only one is considered if two or more write the same state variables in the last step
        """
        def two_list_equal(lst1:list,lst2:list)->bool:
            if len([e for e in lst1 if e not in lst2])>0:
                return False
            elif len([e for e in lst2 if e not in lst1])>0:
                return False
            else:
                return True

        # for key in state_keys:
        #     self.queue.append(key)
        # count based on the key prefix
        count = {}
        for key in self.queue:
            key_prefix = get_key_1_prefix(key)
            if '#' in key_prefix: # a state at depth 2 or deeper
                if key_prefix.startswith('fallback') and key_prefix.endswith('fallback'):
                    continue
                else:
                    if key_prefix.endswith('fallback#fallback'):
                        continue

            if key_prefix not in count.keys():
                count[key_prefix] = [key]
            else:
                count[key_prefix] += [key]

        self.queue=[]
        # compute priority values
        for key_prefix, keys in count.items():
            if len(keys) == 1:
                self.queue.append(keys[0])
            else:
                # get state keys with different priority values that share the same function sequence (key prefix)
                key_recent_writes_pairs = []
                for key in keys:
                    seq_len=len(get_ftn_seq_from_key_1(key))
                    if seq_len in self.written_slots_in_depth_str[key].keys():
                        recent_writes = self.written_slots_in_depth_str[key][seq_len]
                    else:
                        recent_writes=[]

                    key_recent_writes_pairs.append((key, recent_writes))

                # sort the based on weights in descending order
                key_recent_writes_pairs.sort(key=lambda x: len(x[1]), reverse=True)

                # only keep states that have different writes
                cur_writes = []
                for idx,(key, recent_writes) in enumerate(key_recent_writes_pairs):
                    if idx<=2:
                        self.queue.append(key)
                        cur_writes = recent_writes  # update cur_writes
                    else:
                        # only keep keys that have weights different than -1
                        if not two_list_equal(cur_writes,recent_writes):
                            self.queue.append(key)
                            cur_writes = recent_writes   # update cur_writes

    def get_written_slots_in_depth_str(self, state_key:str):
        if state_key not in self.written_slots_in_depth_str.keys():
            return {}
        else:
            return self.written_slots_in_depth_str[state_key]

    def pickup_a_state(self,targets:list):
        """
        order states in self.queue
        return the first state in self.queue
        """

        def evaluate_state(state_key: str, reads_in_conditions_of_targets: dict):
            written_slot_by_state=get_storage_written_slots_str(state_key)
            data = []
            for dk, reads in reads_in_conditions_of_targets.items():
                if len(reads) > 0:
                    count_common = common_elements(reads,written_slot_by_state)
                    data.append(len(count_common) / len(reads))

            my_print(f'evaluation raw data:{data}')
            v = 0
            for ele in data:
                v += ele
            my_print(f'evaluation value:{v}')
            return v

        def get_storage_written_slots_str(state_key:str)->[str]:
            my_print(f'-- {state_key} --')

            # ------------------------
            # consider all the writes without repeated elements
            written_slots_str= [identify_slot_from_symbolic_slot_expression(s) for s in
                     self.state_storage[state_key].keys()]
            my_print(f'\thave slots written:{written_slots_str}')

            written_slots_str_all=self.get_written_slots_in_depth_str(state_key)
            my_print(f'\thave slots written:{written_slots_str_all}')

            return written_slots_str

        if len(self.queue)==1:
            return self.queue.pop(0)

        reads_in_conditions_of_targets = {
            dk: self.fwrg_manager.fwrg.get_reads_in_conditions(dk) for
            dk in targets}

        my_print(f'\n==== Reads in conditions for targets====')
        for key,value in reads_in_conditions_of_targets.items():
            my_print(f'\t{key}:{value}')

        my_print(f'\n==== evaluation on the storage writes ====')
        state_key_value_pairs=[(key,evaluate_state(key,reads_in_conditions_of_targets)) for key in self.queue]
        state_key_value_pairs.sort(key=lambda x: x[1], reverse=True)
        self.queue = [key for key, _ in state_key_value_pairs]
        # print data
        my_print(f'-- summary --')
        for key,value in state_key_value_pairs:
            my_print(f'\t{key}: {value}')

        high_v=state_key_value_pairs[0][1]
        state_key_value_pairs_candi=[(idx,key) for idx, (key,value) in enumerate(state_key_value_pairs) if value==high_v]

        if len(state_key_value_pairs_candi)==1:
            my_print(f'select {state_key_value_pairs_candi[0][1]} based on the evaluation of the writes in state storage')
            return self.queue.pop(0)

        # begin tie break
        win_idx=self.break_a_tie(state_key_value_pairs_candi,targets)
        return self.queue.pop(win_idx)

    def break_a_tie(self,index_key_pairs:list,targets:list)->int:
        def most_recent_new_writes(state_key:str):
            written_slots_str=self.get_written_slots_in_depth_str(state_key)
            func_seq=get_ftn_seq_from_key_1(state_key)

            recent_writes=written_slots_str[len(func_seq)] if len(func_seq) in written_slots_str.keys() else []
            previous_writes=[]
            for depth, writes in written_slots_str.items():
                if depth==len(func_seq):continue
                for w in writes:
                    if w not in previous_writes:
                        previous_writes.append(w)

            new_recent_writes=[w for w in recent_writes if w not in previous_writes]
            return new_recent_writes

        def most_recent_writes(state_key:str):
            my_print(f'-- {state_key} --')
            written_slots_str = self.get_written_slots_in_depth_str(state_key)
            my_print(f'\trecent writes:{written_slots_str}')
            func_seq=get_ftn_seq_from_key_1(state_key)
            if len(func_seq) in written_slots_str.keys():
                return written_slots_str[len(func_seq)]
            else:
                return []


        def evaluate_recent_writes(state_key: str, reads_in_conditions_of_targets: dict):
            recent_writes=most_recent_writes(state_key)

            data = []
            for dk, reads in reads_in_conditions_of_targets.items():
                if len(reads) > 0:
                    count_common = common_elements(reads, recent_writes)
                    data.append(len(count_common) / len(reads))

            my_print(f'evaluation raw data:{data}')
            v = 0
            for ele in data:
                v += ele
            my_print(f'evaluation value:{v}')
            return v

        # begin tie break

        def break_by_new_recent_writes(idx_key_pairs:list):
            # check based on the new recent writes
            idx_key_new_recent_writes = [(idx, key, most_recent_new_writes(key))
                                         for
                                         idx, key in idx_key_pairs]
            idx_key_new_recent_writes.sort(key=lambda x: len(x[2]),
                                           reverse=True)

            my_print(f'\n==== new recent writes ====')
            for idx, key, new_recent_writes in idx_key_new_recent_writes:
                my_print(f'\t{key}: {new_recent_writes}')

            max_new_writes = len(idx_key_new_recent_writes[0][2])
            idx_key_new_recent_writes_candi = [(idx, key) for
                                               idx, key, new_writes in
                                               idx_key_new_recent_writes if
                                               len(new_writes) == max_new_writes]
            if len(idx_key_new_recent_writes_candi) == 1:
                my_print(f'select {idx_key_new_recent_writes_candi[0][1]} based on new recent writes')
                return idx_key_new_recent_writes_candi[0][0],idx_key_new_recent_writes_candi
            elif len(idx_key_new_recent_writes_candi) == 0:
                idx_key_new_recent_writes_candi = [(idx, key) for idx, key, _ in
                                                   idx_key_new_recent_writes]
            return None,idx_key_new_recent_writes_candi

        def break_by_recent_writes(idx_key_pairs:list, targets):
            # evaluate the recent writes to targets (a way to consider repeated writes)
            reads_in_conditions_of_targets = {
                dk: self.fwrg_manager.fwrg.get_reads_in_conditions(dk) for
                dk in targets}

            my_print(f'\n==== evaluation on the recent writes ====')
            idx_key_recent_writes = [(idx, key, evaluate_recent_writes(key,
                                                                       reads_in_conditions_of_targets))
                                     for idx, key in idx_key_pairs]
            idx_key_recent_writes.sort(key=lambda x: x[2], reverse=True)
            # print
            my_print(f'-- summary --')
            for idx, key, value in idx_key_recent_writes:
                my_print(f'\t{key}: {value}')

            max_value = idx_key_recent_writes[0][2]
            idx_key_recent_writes_candi = [(idx, key) for idx, key, value in
                                           idx_key_recent_writes if
                                           value == max_value]
            if len(idx_key_recent_writes_candi) == 1:
                my_print(f'select {idx_key_recent_writes_candi[0][1]} based on the evaluation of the recent writes')
                return idx_key_recent_writes_candi[0][0],idx_key_recent_writes_candi
            else:
                return None,idx_key_recent_writes_candi

        def break_by_depth(idx_key_pairs:list):
            def state_depth(state_key:str)->int:
                return len(get_ftn_seq_from_key_1(state_key))

            idx_key_depth = [(idx, key, state_depth(key)) for idx,key in idx_key_pairs]
            idx_key_depth.sort(key=lambda x:x[2],reverse=False)
            small_depth=idx_key_depth[0][2]
            idx_key_depth_candi=[(idx,key) for idx,key,depth in idx_key_depth if depth==small_depth]
            if len(idx_key_depth_candi)==1:
                my_print(f'select {idx_key_depth_candi[0][1]} based on depth')
                return idx_key_depth_candi[0][0],idx_key_depth_candi
            else:
                return None,idx_key_depth_candi

        def break_num_reached_dk_functions(idx_key_pairs:list,targets:list):
            def num_reached_dk_functions(state_key:str,targets:list)->int:
                return len(self.functionAssignment.get_targets_be_reached(get_ftn_seq_from_key_1(state_key)[-1], targets, 1))


            idx_key_num_dk = [(idx, key, num_reached_dk_functions(key,targets)) for idx,key in idx_key_pairs]
            idx_key_num_dk.sort(key=lambda x:x[2],reverse=True)
            max_num=idx_key_num_dk[0][2]
            if max_num==0:
                return None,[(idx,key) for idx,key,num in idx_key_num_dk]

            idx_key_num_dk_candi=[(idx,key) for idx,key,num in idx_key_num_dk if num==max_num]
            if len(idx_key_num_dk_candi)==1:
                my_print(f'select {idx_key_num_dk_candi[0][1]} based on the number of dk functions that can be reached directly')
                return idx_key_num_dk_candi[0][0],idx_key_num_dk_candi
            else:
                return None,idx_key_num_dk_candi

        def select_randomly(idx_key_pairs: list) -> int:
            # randomly select one
            selected = random_select_from_list(
                [idx for idx, _ in idx_key_pairs], 1)
            # print
            for idx, key in idx_key_pairs:
                if idx == selected[0]:
                    my_print(f'select {key} based on random policy')
            return selected[0]

        # ------------- new recent writes -----------------
        win_idx,new_recent_writes_candi=break_by_new_recent_writes(index_key_pairs)
        if win_idx is not None: return win_idx

        # ------------- recent writes -----------------
        win_idx, recent_writes_candi = break_by_recent_writes(
            new_recent_writes_candi, targets)
        if win_idx is not None: return win_idx

        # ------------- depth -----------------
        win_idx, depth_candi = break_by_depth(recent_writes_candi)
        if win_idx is not None: return win_idx

        win_idx, num_dk_candi=break_num_reached_dk_functions(depth_candi,targets)
        if win_idx is not None: return win_idx

        # -------------- random policy ----------------
        return select_randomly(num_dk_candi)




class Mine1(FunctionSearchStrategy):
    def __init__(self):
        self.preprocess_timeout=False
        self.preprocess_coverage=0

        self.state_storage={}
        self.write_slots_genesis_states=[]
        self.state_write_slots={}
        self.state_priority={}

        self.queue=[]
        self.state_key_assigned_at_last=""
        self.save_half_considered_states={} # the states that are assigned but not fully considered. (some children are not considered yet)
        self.state_key_history={}

        self.flag_one_state_at_depth1=False
        super().__init__('mine1')

    def initialize(self,flag_one_state_depth1:bool,preprocess_timeout:bool, preprocess_coverage:float,all_functions:list,fwrg_manager:FWRG_manager):
        self.flag_one_state_at_depth1=flag_one_state_depth1
        self.preprocess_timeout=preprocess_timeout
        self.preprocess_coverage=preprocess_coverage

        self.functionAssignment=FunctionAssignment(all_functions,fwrg_manager)
        self.fwrg_manager=fwrg_manager

    def assign_states(self, dk_functions: list = None, states_dict: dict = {}, iteration:int=0) -> list:
        """

        :param dk_functions:
        :param fwrg:
        :param states_dict:
        :return:
        """
        if self.preprocess_timeout or fdg.global_config.preprocessing_exception:
            if self.preprocess_coverage<50:
                # execute 70% of functions+ functions assigned based on the partial graph
                return self.assign_states_timeout(dk_functions, states_dict, 7)
            elif self.preprocess_coverage<80:
                # execute 50% of functions+ functions assigned based on the partial graph
                return self.assign_states_timeout(dk_functions, states_dict, 5)
            else:
                # execute 30% of functions + functions assigned based on the partial graph
                return self.assign_states_timeout(dk_functions, states_dict, 3)
        return self.assign_states_normal(dk_functions, states_dict)

    def assign_states_normal(self, dk_functions: list = None, states_dict: dict = {}) -> list:
        """

        :param dk_functions:
        :param fwrg:
        :param states_dict:
        :return: a state and the functions to be executed on it
        a flag indicating whether this state can be deleted or not.
        """

        if len(states_dict) > 0:

            # save the new states
            self.update_states(states_dict)
            # compute the weights for the new states
            self.compute_weights_for_states_from_same_seq(
                list(states_dict.keys()))

        # ---------------
        print_data_for_mine_strategy_1(self.queue, self.state_write_slots,
                                       self.state_priority,
                                       self.state_storage)

        # --------------
        # case 1
        # assign the only state
        if self.flag_one_state_at_depth1:
            self.flag_one_state_at_depth1=False # only consider once
            state_key=self.queue.pop(0)
            assign_functions= self.functionAssignment.assign_all_functions()
            self.state_key_assigned_at_last=state_key
            return {state_key: assign_functions},True

        # --------------
        # case 2
        # assign a state and the functions to be executed on it
        while True:
            if len(self.queue) == 0:
                return {}, None

            to_execute_children = []
            not_to_execute = []
            flag_can_be_deleted=True

            # pick up a state from the queue
            state_key = self.pickup_a_state(dk_functions)  # order the states in self.queue and pick up the one has the highest weight

            ftn_seq=get_ftn_seq_from_key_1(state_key)

            if len(ftn_seq)==1:
                if state_key in self.save_half_considered_states.keys():
                    # the second time to assign this state
                    to_execute_children = self.save_half_considered_states[state_key]['to_execute']
                    not_to_execute =  self.save_half_considered_states[state_key]['not_to_execute']

                else:
                    # the first time to assign this state
                    children = self.fwrg_manager.get_children_fwrg_T_A( ftn_seq[-1])

                    # only consider children that are targets or can lead to target
                    children=[child for child in children if self.functionAssignment.can_reach_targets(child,[dk for dk,_ in dk_functions],fdg.global_config.seq_len_limit-1-1)]
                    if len(children)>3:
                        to_execute_children_w_cov=[(dk,cov) for dk,cov in dk_functions if dk in children]
                        if len(to_execute_children_w_cov)>3:
                            # select the fi
                            to_execute_children_w_cov.sort(key=lambda x:x[1],reverse=True)
                            to_execute_children=[child for child,_ in to_execute_children_w_cov[0:3]]
                        else:
                            to_execute_children=[child for child,_ in to_execute_children_w_cov]
                    else:
                        to_execute_children=children

                    not_to_execute = [child for child in children if
                                      child not in to_execute_children]
                    if len(not_to_execute) > 0:
                        self.save_half_considered_states[state_key] = {
                            "to_execute": not_to_execute,
                            "not_to_execute": to_execute_children
                        }
                        # reduce 1 from the weight of this state
                        self.state_priority[state_key] = [weight - 1 for weight
                                                          in
                                                          self.state_priority[
                                                              state_key]]
                        self.queue.append(
                            state_key)  # add the state back to self.queue
                        flag_can_be_deleted = False

            # assign functions
            assigned_children=self.functionAssignment.assign_functions(state_key,dk_functions,to_execute_children,not_to_execute)
            if len(assigned_children)>0:
                self.state_key_assigned_at_last = state_key
                return {state_key: assigned_children},flag_can_be_deleted
            # else:
            #     print(f'no function is assigned for state {state_key}')

    def assign_states_timeout(self, dk_functions: list = None, states_dict: dict = {}, percent_of_functions:int=1) -> list:
        """

        :param dk_functions:
        :param fwrg:
        :param states_dict:
        :return:
        """
        if len(states_dict) > 0:
            # save the new states
            self.update_states(states_dict)
            # compute the weights for the new states
            self.compute_weights_for_states_from_same_seq(
                list(states_dict.keys()))

        # ---------------
        print_data_for_mine_strategy_1(self.queue, self.state_write_slots,
                                       self.state_priority,
                                       self.state_storage)

        # --------------
        # case 1
        # assign the only state
        if self.flag_one_state_at_depth1:
            self.flag_one_state_at_depth1=False # only consider once
            state_key=self.queue.pop(0)
            assign_functions= self.functionAssignment.assign_all_functions()
            self.state_key_assigned_at_last = state_key
            return {state_key: assign_functions},True

        # --------------
        # case 2
        # assign a state and the functions to be executed on it
        while True:
            if len(self.queue) == 0:
                return {}, None

            # pick up a state from the queue
            state_key = self.pickup_a_state(dk_functions)  # order the states in self.queue and pick up the one has the highest weight

            # assign functions
            assigned_functions=self.functionAssignment.assign_functions_timeout(state_key, dk_functions, percent_of_functions)
            if len(assigned_functions)>0:
                self.state_key_assigned_at_last = state_key
                return {state_key: assigned_functions},True

    def termination(self, states_num: int = 0, current_seq_length: int = 0, sequence_depth_limit: int = 0,
                    iteration: int = 0) -> bool:
        # print(f'{states_num}:{len(self.d1)}:{len(self.d2)}:{len(self.d3)}:{len(self.cur_queue)}:{iteration}')
        if iteration <= 2:
            if states_num == 0: return True

        return False

    def update_states(self, states_dict:dict)->list:
        """
        save states
        """
        address = fdg.global_config.contract_address.value

        for key,states in states_dict.items():
            for state in states:
                ftn_seq=get_ftn_seq_from_key_1(key)
                if 'constructor' not in ftn_seq:
                    self.world_states[key]=[deepcopy(state)]

                else:
                    for slot in list(state.accounts[address].storage.printable_storage.keys()):
                        if slot not in self.write_slots_genesis_states:
                            self.write_slots_genesis_states.append(slot)

                    print(f'self.write_slots_genesis_states={self.write_slots_genesis_states}')

                self.state_storage[key] = state.accounts[address].storage.printable_storage
                self.state_write_slots[key]=get_writes_annotation_from_ws(state)
                if len(self.state_key_assigned_at_last)>0:
                    if key not in self.state_key_history.keys():
                        self.state_key_history[key]={len(ftn_seq)-1:self.state_key_assigned_at_last}
                    else:
                        if len(ftn_seq)-1 not in self.state_key_history[key].keys():
                            self.state_key_history[key][len(ftn_seq)-1]=self.state_key_assigned_at_last

        # print(f'\n-- state key history --')
        # for key,value in self.state_key_history.items() :
        #     print(f'\t{key}')
        #     print(f'\t{value}')


    def compute_weights_for_states_from_same_seq(self, state_keys:list)->list:
        """
        assume that the states given here are from the same function sequence
        ------------
        compute the weight for each new state
        for states from the same function sequence, only stats having different weights are kept.
        in other words, one of the states from the same function sequence having the same weight is considered (weight computation is important)
        """
        #count based on the key prefix
        count = {}
        for key in state_keys:
            key_prefix = get_key_1_prefix(key)
            if key_prefix not in count.keys():
                count[key_prefix] = [key]
            else:
                count[key_prefix] += [key]

        # compute priority values
        for key_prefix, keys in count.items():
            if len(keys) == 1:
                w = self.compute_weight(keys[0])
                if self.state_key_assigned_at_last in self.state_priority.keys():
                    part_weights = self.state_priority[self.state_key_assigned_at_last]
                    all_depths_weights = part_weights + [w]
                else:
                    all_depths_weights = [w]
                self.state_priority[keys[0]] = all_depths_weights
                self.queue.append(keys[0])
            else:
                # get state keys with different priority values that share the same function sequence (key prefix)
                key_weight_pairs = []
                for key in keys:
                    w = self.compute_weight(key)
                    if self.state_key_assigned_at_last in self.state_priority.keys():
                        all_depths_weights = self.state_priority[
                                      self.state_key_assigned_at_last] + [w]
                    else:
                        all_depths_weights = [w]
                    key_weight_pairs.append((key, all_depths_weights))

                # sort the based on weights in descending order
                key_weight_pairs.sort(key=lambda x: compute(x[1]), reverse=True)
                # only keep states that have different weight values
                cur_value = -1
                for key, weights in key_weight_pairs:
                    # only keep keys that have weights different than -1
                    if not cur_value == compute(weights):
                        self.state_priority[key] = weights
                        self.queue.append(key)
                        cur_value = compute(weights)  # update cur_value

        # after finishing computing weights for the newly generated state, reduce the weights for the state that is not fully considered.
        # this only happens on states at depth 1
        if self.state_key_assigned_at_last in self.save_half_considered_states.keys():
            self.state_priority[self.state_key_assigned_at_last]=[ele-1 for ele in self.state_priority[self.state_key_assigned_at_last]]

    def obtain_weight(self,state_key:str):
        def write_basic_features(slot,state_key:str)->list:
            p,n,c=False,False,False
            # check if a write is for a primitive type of state variable
            if not slot.symbolic:
                p=True
            # check if a concrete value is written
            if slot in self.state_storage[state_key].keys():
                write=self.state_storage[state_key][slot]
                if not write.symbolic:
                    c=True
            # check if this is a new write
            if is_a_new_write(slot,state_key):
                n=True
            print(f'p,c,n: {[p,c,n]}')
            return [p,c,n]

        def is_a_new_write(slot, state_key) -> list:
            """
            check whether slot is written in the previous depths
            """

            ftn_seq = get_ftn_seq_from_key_1(state_key)
            if len(ftn_seq)-1 in self.state_key_history[state_key].keys():
                pre_state_key=self.state_key_history[state_key][len(ftn_seq)-1]

                if is_slot_in_a_list(slot, self.state_storage[pre_state_key].keys()):
                    return False
                else:
                    return True
            else:
                if len(ftn_seq)==1:
                    if is_slot_in_a_list(slot, self.write_slots_genesis_states):
                        return False
                    else:
                        return True
                else:
                    print(f'Check what is the case')
                    return False


        print(f'\n---- {state_key} ----')

        ftn_seq = get_ftn_seq_from_key_1(state_key)
        writes_status=[]
        unique_writes=[]
        if len(ftn_seq) in self.state_write_slots[state_key].keys():
            write_slots = self.state_write_slots[state_key][len(ftn_seq)]
            for slot in write_slots:
                features=write_basic_features(slot,state_key)
                writes_status.append(features)

            # check if multiple writes are for one state variable or multiple ones
            if len(write_slots)>=2:
                unique_writes=[identify_slot_from_symbolic_slot_expression(s) for s in write_slots]

        if len(writes_status)==0:
            final_v= 0
        else:
            writes_weights=[turn_write_features_to_a_value(features) for features in writes_status]
            if len(unique_writes)<=1:
                final_v=max(writes_weights)
            else:
                final_v = max(writes_weights)+1

        print(f'weight: {final_v}: ({writes_status})')
        return final_v

    def compute_weight(self,key:str)->float:
        return self.obtain_weight(key)

    def pickup_a_state(self,dk_functions:list):
        """
        order states in self.queue by based on the weights computed from the raw weights
        return the first state in self.queue
        """

        temp = [(item, self.state_priority[item]) for item in self.queue]
        temp.sort(key=lambda x: compute(x[1]), reverse=True)
        temp=[(idx,item,weights) for idx,(item,weights) in enumerate(temp)]
        self.queue= [item for _, item, _ in temp]

        highest_weight=compute(temp[0][2])
        candidates=[(idx,item) for idx, item,weights in temp if compute(weights)==highest_weight]

        if len(candidates)==1:
            return self.queue.pop(0)
        else:
            win_idx = self.break_a_tie(candidates,dk_functions)
            return self.queue.pop(win_idx)

    def break_a_tie(self,index_state_key_pairs:list,dk_functions:list)->int:
        """
        depth: the depth that the state is generated
        soc: symbolic value overwrites a concrete value
        nopv: number of unique primitive type of state variables
        tnov: total number of unique state variables
        nodk: number of dk functions that can be reached
        return the index of state in the self.queue
        """
        def state_depth(key:str)->int:
            return len(get_ftn_seq_from_key_1(key))

        def is_primitive(state_key:str)->bool:
            ftn_seq = get_ftn_seq_from_key_1(state_key)
            if len(ftn_seq) in self.state_write_slots[state_key].keys():
                write_slots = self.state_write_slots[state_key][len(ftn_seq)]
                for slot in write_slots:
                    if not slot.symbolic:
                        return True
            return False

        def is_concrete(state_key:str)->bool:
            ftn_seq = get_ftn_seq_from_key_1(state_key)

            if len(ftn_seq) in self.state_write_slots[state_key].keys():
                w_slots = self.state_write_slots[state_key][len(ftn_seq)]
                for slot in w_slots:
                    write=self.state_storage[state_key][slot]
                    if not write.symbolic:
                        return True
            return False

        def share_same_seq_prefix(state_keys:list)->bool:
            ftn_seq_list=[get_ftn_seq_from_key_1(key)[0:-1] for key in state_keys]
            ftn_seq_prefix=ftn_seq_list[0]
            for seq in ftn_seq_list[1:]:
                for ftn in seq:
                    if ftn not in ftn_seq_prefix:
                        return False
            return True


        #------------------------------
        # break a tie based on the depth
        depth_candidates = [(idx, item, state_depth(item)) for idx, item in
                            index_state_key_pairs]
        depth_candidates.sort(key=lambda x: x[2],
                              reverse=False)  # sort based on depth
        smallest_depth = depth_candidates[0][2]
        depth_candidates = [(idx, item) for idx, item, d in depth_candidates if
                            d == smallest_depth]
        if len(depth_candidates) == 1:  # count how many states have the same depth that is small
            return depth_candidates[0][0]

        share_same_prefix=share_same_seq_prefix([item for _,item in depth_candidates])
        if share_same_prefix:
            # ------------------------------
            # break a tie based on whether a primitive type of state varialbe is written at the last depth
            last_depth_weight_1 = [(idx, item, is_primitive(item)) for idx, item
                                   in depth_candidates]
            last_depth_weight_1_candi = [(idx, item) for idx, item, is_primitive
                                         in last_depth_weight_1 if is_primitive]
            if len(last_depth_weight_1_candi) == 1:
                return last_depth_weight_1_candi[0][0]
            if len(last_depth_weight_1_candi) == 0:
                last_depth_weight_1_candi = [(idx, item) for idx, item, _ in
                                             last_depth_weight_1]

                # ------------------------------
            # break a tie based on whether a concrete value is assigned at the last depth
            last_depth_weight_2 = [(idx, item, is_concrete(item))
                                   for idx, item in last_depth_weight_1_candi]
            last_depth_weight_2_candi = [(idx, item) for
                                         idx, item, is_a_concrete
                                         in last_depth_weight_2 if
                                         is_a_concrete]
            if len(last_depth_weight_2_candi) == 1:
                return last_depth_weight_2_candi[0][0]
            if len(last_depth_weight_2_candi) == 0:
                last_depth_weight_2_candi = [(idx, item) for idx, item, _ in
                                             last_depth_weight_2]
            candidates = last_depth_weight_2_candi

        else:
            # ------------------------------
            # break a tie based on the weights at last depth
            last_depth_weight=[(idx,item,self.state_priority[item][-1]) for idx,item in depth_candidates]
            last_depth_weight.sort(key=lambda x:x[2],reverse=True)
            high_w=last_depth_weight[0][2]
            last_depth_weight_candi=[(idx,item) for idx,item,w in last_depth_weight if w==high_w]
            if len(last_depth_weight_candi)==1:
                return last_depth_weight_candi[0][0]

            # ------------------------------
            # break a tie based on nopv
            nopv_states=[(idx,item,self.count_written_primitive_type_sv(item)) for idx,item in last_depth_weight_candi]
            # print(f'nopv: {nopv_states}')
            nopv_states.sort(key=lambda x: x[2], reverse=True)
            high_nopv=nopv_states[0][2]
            nopv_states_candi=[(idx,item) for idx,item,nopv in nopv_states if nopv==high_nopv]
            if len(nopv_states_candi)==1:
                return nopv_states_candi[0][0]

            # ------------------------------
            # break a tie based on tnosv
            tnosv_states = [(idx, item, self.count_all_written_state_sv(item))
                           for idx, item in nopv_states_candi]
            tnosv_states.sort(key=lambda x: x[2], reverse=True)
            high_tnosv = tnosv_states[0][2]
            tnosv_states_candi = [(idx, item) for idx, item, nopv in tnosv_states if
                                 nopv == high_tnosv]
            if len(tnosv_states_candi) == 1:
                return tnosv_states_candi[0][0]

            candidates =tnosv_states_candi

        # ------------------------------
        # break a tie based on nodk
        targets = [dk for dk, _ in dk_functions]
        nodk_states=[(idx, item,
                      self.functionAssignment.get_targets_be_reached(
                          get_ftn_seq_from_key_1(item)[-1],
                          targets,
                          fdg.global_config.seq_len_limit - len(
                              get_ftn_seq_from_key_1(item))
                        )
                      )
                     for idx, item in candidates]


        nodk_states.sort(key=lambda x: x[2], reverse=True)
        max_num = nodk_states[0][2]
        nodk_states_candi = [(idx, item) for idx, item, num_t in
                             nodk_states if num_t == max_num]
        if len(nodk_states_candi) == 1:
            return nodk_states_candi[0][0]

        # ------------------------------
        # randomly select one
        selected = random_select_from_list([idx for idx, _ in nodk_states_candi], 1)
        print('need rules to break a tie. Now randomly select one')
        print(f'select: {self.queue[selected[0]]}')
        return selected[0]

    def a_symbolic_overrides_a_concrete(self, state_key: str) -> bool:
        def get_value_from_a_slot(slot, state_key: str):
            if state_key in self.state_storage.keys():
                if slot in self.state_storage[state_key].keys():
                    return self.state_storage[state_key][slot]
            return ""

        print(f'-- {state_key} --')
        ftn_seq = get_ftn_seq_from_key_1(state_key)
        if len(ftn_seq) in self.state_write_slots[state_key].keys():
            write_slots = self.state_write_slots[state_key][len(ftn_seq)]
            for slot in write_slots:
                if not slot.symbolic:  # consider primitive type of state variables
                    slot_value = get_value_from_a_slot(slot, state_key)
                    # a symbolic value is written to slot
                    if len(str(slot_value)) > 0 and slot_value.symbolic:
                        for depth in range(len(ftn_seq)):
                            if depth == 0:
                                if slot in self.write_slots_genesis_states:
                                    slot_v_genesis_state = \
                                    self.state_storage['constructor#0'][slot]
                                    if not slot_v_genesis_state.symbolic:
                                        if not str(slot_v_genesis_state) == '0':
                                            print(f'soc yes')
                                            return True
                            else:
                                if depth in self.state_write_slots[
                                    state_key].keys():
                                    w_slots = self.state_write_slots[state_key][
                                        depth]
                                    if slot in w_slots:
                                        state_key_at_depth = \
                                        self.state_key_history[state_key][depth]
                                        slot_value_at_depth = get_value_from_a_slot(
                                            slot, state_key_at_depth)
                                        if not slot_value_at_depth.symbolic:
                                            print(f'soc yes')
                                            return True
        print(f'soc no')
        return False

    def count_written_primitive_type_sv(self, state_key: str) -> int:
        """
        find all primitive state variables that are written by the state (writes including those in the previous steps)
        """

        unique_p_sv = []
        ftn_seq = get_ftn_seq_from_key_1(state_key)
        for depth in range(len(ftn_seq)):
            if depth == 0:
                for slot in self.write_slots_genesis_states:
                    if not slot.symbolic:
                        if slot not in unique_p_sv:
                            unique_p_sv.append(slot)
            else:
                if depth in self.state_write_slots[state_key].keys():
                    w_slots = self.state_write_slots[state_key][depth]
                    for slot in w_slots:
                        if not slot.symbolic:
                            if slot not in unique_p_sv:
                                unique_p_sv.append(slot)
        return len(unique_p_sv)

    def count_all_written_state_sv(self, state_key: str) -> int:
        """
        find all primitive state variables that are written by the state (writes including those in the previous steps)
        """
        total_unique_sv = []
        ftn_seq = get_ftn_seq_from_key_1(state_key)
        for depth in range(len(ftn_seq)):
            if depth == 0:
                slot_str_list = [identify_slot_from_symbolic_slot_expression(s)
                                 for s in self.write_slots_genesis_states]
                for slot_str in slot_str_list:
                    if slot_str not in total_unique_sv:
                        total_unique_sv.append(slot_str)
            else:
                if depth in self.state_write_slots[state_key].keys():
                    w_slots = self.state_write_slots[state_key][depth]
                    slot_str_list = [
                        identify_slot_from_symbolic_slot_expression(s) for s in
                        w_slots]
                    for slot_str in slot_str_list:
                        if slot_str not in total_unique_sv:
                            total_unique_sv.append(slot_str)
        return len(total_unique_sv)

    def xxx(self,state_key:str,dk_functions:list)->float:
        ...
