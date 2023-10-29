from copy import deepcopy

import fdg
from fdg.control.ftn_search_strategy import FunctionSearchStrategy
from fdg.control.function_assignment import FunctionAssignment
from fdg.control.weight_computation import compute, \
    turn_write_features_to_a_value, compute_mine
from fdg.expression_utils import is_slot_in_a_list,identify_slot_from_symbolic_slot_expression

from fdg.fwrg_manager import FWRG_manager
from fdg.output_data import print_data_for_mine_strategy_1, \
    print_data_for_mine_strategy
from fdg.utils import get_ftn_seq_from_key_1, get_key_1_prefix, \
    random_select_from_list
from mythril.laser.plugin.plugins.dependency_pruner import \
    get_writes_annotation_from_ws


class Mine(FunctionSearchStrategy):
    def __init__(self):
        self.proprocess_timeout=False
        self.preprocess_coverage=0

        self.state_storage={}
        self.write_slots_genesis_states=[]
        self.state_write_slots={}
        self.state_priority={}

        self.queue=[]
        self.state_key_assigned_at_last=""
        self.save_half_considered_states={} # the states that are assigned but not fully considered. (some children are not considered yet)

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
                        # # reduce 1 from the weight of this state
                        # self.state_priority[state_key] = [weight - 2 for weight
                        #                                   in
                        #                                   self.state_priority[
                        #                                       state_key]]
                        self.queue.append(
                            state_key)  # add the state back to self.queue
                        flag_can_be_deleted = False

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
                    weights = part_weights + [w]
                else:
                    weights = [w]
                self.state_priority[keys[0]] = weights
                self.queue.append(keys[0])
            else:
                # get state keys with different priority values that share the same function sequence (key prefix)
                key_weight_pairs = []
                for key in keys:
                    w = self.compute_weight(key)
                    if self.state_key_assigned_at_last in self.state_priority.keys():
                        weights = self.state_priority[
                                      self.state_key_assigned_at_last] + [w]
                    else:
                        weights = [w]
                    key_weight_pairs.append((key, weights))

                # sort the based on weights in descending order
                key_weight_pairs.sort(key=lambda x: compute_mine(x[1]), reverse=True)
                # only keep states that have different weight values
                cur_value = -1
                for key, weights in key_weight_pairs:
                    # only keep keys that have weights different than -1
                    if not cur_value == compute_mine(weights):
                        self.state_priority[key] = weights
                        self.queue.append(key)
                        cur_value = compute_mine(weights)  # update cur_value

        # after finishing computing weights for the newly generated state, reduce the weights for the state that is not fully considered.
        if self.state_key_assigned_at_last in self.save_half_considered_states.keys():
            self.state_priority[self.state_key_assigned_at_last]=[ele-1 for ele in self.state_priority[self.state_key_assigned_at_last]]

    def get_weight(self, key:str)->float:

        def weight_new_or_old_writes(data:list)->int:
            """
            determine the weight based on the data list that records whether a slot is written or not.
            len(data): the number of times that a slot may be written ( the last depth)
            data[0]=True: at depth 0, a slot is not written; otherwise, it is written.
            """
            if len(data)==1:
                if data[0]:return 2
            elif len(data)==2:
                if data.count(True)==2:
                    return 2
                elif data.count(True)==1:
                    return 1
            elif len(data)>=3:
                if data.count(True)>=3:
                    return 2
                elif data.count(True)==2:
                    return 1
            return 0


        def slot_weight(slot,state_key):
            flag_primitive=True
            v = 0
            if slot.symbolic:
                flag_primitive=False
                v += 1
            else:
                v += 2
            if slot in self.state_storage[state_key].keys():
                write = self.state_storage[state_key][slot]
                if write.symbolic:
                    v += 1
                else:
                    if not str(write.value) == '0':
                        v += 3
            return v,flag_primitive

        def check_with_previous_depths(slot,state_key,ftn_seq:list)->list:
            """
            check whether slot is written in the previous depths
            """
            not_written_before = []
            for depth in range(0,len(ftn_seq)):
                if depth==0:
                    if is_slot_in_a_list(slot, self.write_slots_genesis_states):
                        not_written_before.append(False)
                    else:
                        not_written_before.append(True)
                else:
                    if depth in self.state_write_slots[state_key].keys():
                        w_slots = self.state_write_slots[state_key][depth]
                        if is_slot_in_a_list(slot,w_slots):
                            not_written_before.append(False)
                        else:
                            not_written_before.append(True)

            return not_written_before

        def weight_from_multiple_writes(values:list):
            if len(values) == 0:
                return 0
            else:
                final_v = max(values)
                if len(values) >= 2:
                    final_v += 1

                if len(ftn_seq) == 3:
                    if not flag_simple_sv:
                        final_v = final_v - 2
                elif len(ftn_seq) == 2:
                    if not flag_simple_sv:
                        final_v = max(values) - 1
            return final_v

        values=[]
        ftn_seq = get_ftn_seq_from_key_1(key)
        flag_simple_sv=False
        if len(ftn_seq) in self.state_write_slots[key].keys():
            write_slots = self.state_write_slots[key][len(ftn_seq)]
            for slot in write_slots:
                v,is_primitive=slot_weight(slot,key)
                check_written_before=check_with_previous_depths(slot,key,ftn_seq)
                v+=weight_new_or_old_writes(check_written_before)
                values.append(v)
        return weight_from_multiple_writes(values)


    def compute_weight(self,key:str)->float:
        return self.get_weight(key)

    def pickup_a_state(self,dk_functions:list):
        """
        order states in self.queue
        return the first state in self.queue
        """


        temp = [(item, self.state_priority[item]) for item in self.queue]
        temp.sort(key=lambda x: compute_mine(x[1]), reverse=True)
        temp=[(idx,item,weights) for idx,(item,weights) in enumerate(temp)] # check if it is correct
        self.queue= [item for _, item, _ in temp]

        highest_weight=compute_mine(temp[0][2])
        candidates=[(idx,item) for idx, item,weights in temp if compute_mine(weights)==highest_weight]

        if len(candidates)==1:
            return self.queue.pop(0)
        else:
            win_idx=self.break_a_tie(candidates,dk_functions)
            return self.queue.pop(win_idx)

    # def break_a_tie(self,idx_state_key_pairs:list, dk_functions:list)->int:
    #     def state_depth(key:str)->int:
    #         return len(get_ftn_seq_from_key_1(key))
    #
    #     # compare the depth
    #     depth_candidates = [(idx, item, state_depth(item)) for idx, item in
    #                         idx_state_key_pairs]
    #     depth_candidates.sort(key=lambda x: x[2], reverse=False)  # sort based on depth
    #     smallest_depth = depth_candidates[0][2]
    #     depth_candidates = [(idx, item) for idx, item, d in depth_candidates if
    #                         d == smallest_depth]
    #     if len(depth_candidates) == 1:  # count how many states have the same depth that is small
    #         return depth_candidates[0][0]
    #
    #
    #     # consider the weight of the last depth
    #     last_weight_candidates = [(idx, item, self.state_priority[item][-1]) for idx, item in
    #         depth_candidates]
    #     last_weight_candidates.sort(key=lambda x: x[2], reverse=True)
    #     h_w = last_weight_candidates[0][2]
    #     last_weight_candidates = [(idx, item) for idx, item, last_w in
    #                               last_weight_candidates if
    #                               last_w == h_w]
    #     if len(last_weight_candidates) == 1:
    #         return last_weight_candidates[0][0]
    #
    #
    #     # compare the number of targets that can reach
    #     targets = [dk for dk, _ in dk_functions]
    #     target_candidates = [(idx, item,
    #                           self.functionAssignment.get_num_targets_be_reached(
    #                               get_ftn_seq_from_key_1(item)[-1],
    #                               targets,
    #                               fdg.global_config.seq_len_limit - len(
    #                                   get_ftn_seq_from_key_1(item))
    #                           ))
    #                          for idx, item in last_weight_candidates]
    #
    #     target_candidates.sort(key=lambda x: x[2], reverse=True)
    #     max_num = target_candidates[0][2]
    #     target_candidates = [(idx, item) for idx, item, num_t in
    #                          target_candidates if num_t == max_num]
    #     if len(target_candidates) == 1:
    #         return target_candidates[0][0]
    #
    #     print('need to rules to break a tie. Now randomly select one')
    #     selected = random_select_from_list(
    #         [idx for idx, _ in target_candidates], 1)
    #     return selected[0]

    def break_a_tie(self, index_state_key_pairs: list,
                    dk_functions: list) -> int:
        """
        depth: the depth that the state is generated
        soc: symbolic value overwrites a concrete value
        nopv: number of unique primitive type of state variables
        tnov: total number of unique state variables
        nodk: number of dk functions that can be reached
        return the index of state in the self.queue
        """

        def state_depth(key: str) -> int:
            return len(get_ftn_seq_from_key_1(key))

        def is_primitive(state_key: str) -> bool:
            ftn_seq = get_ftn_seq_from_key_1(state_key)
            if len(ftn_seq) in self.state_write_slots[state_key].keys():
                write_slots = self.state_write_slots[state_key][len(ftn_seq)]
                for slot in write_slots:
                    if not slot.symbolic:
                        return True
            return False

        def is_concrete(state_key: str) -> bool:
            ftn_seq = get_ftn_seq_from_key_1(state_key)

            if len(ftn_seq) in self.state_write_slots[state_key].keys():
                w_slots = self.state_write_slots[state_key][len(ftn_seq)]
                for slot in w_slots:
                    write = self.state_storage[state_key][slot]
                    if not write.symbolic:
                        return True
            return False

        def share_same_seq_prefix(state_keys: list) -> bool:
            ftn_seq_list = [get_ftn_seq_from_key_1(key)[0:-1] for key in
                            state_keys]
            ftn_seq_prefix = ftn_seq_list[0]
            for seq in ftn_seq_list[1:]:
                for ftn in seq:
                    if ftn not in ftn_seq_prefix:
                        return False
            return True

        # ------------------------------
        # break a tie based on the depth
        depth_candidates = [(idx, item, state_depth(item)) for idx, item in
                            index_state_key_pairs]
        depth_candidates.sort(key=lambda x: x[2],
                              reverse=False)  # sort based on depth
        smallest_depth = depth_candidates[0][2]
        depth_candidates = [(idx, item) for idx, item, d in depth_candidates if
                            d == smallest_depth]
        if len(
            depth_candidates) == 1:  # count how many states have the same depth that is small
            return depth_candidates[0][0]

        share_same_prefix = share_same_seq_prefix(
            [item for _, item in depth_candidates])
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
            last_depth_weight = [(idx, item, self.state_priority[item][-1]) for
                                 idx, item in depth_candidates]
            last_depth_weight.sort(key=lambda x: x[2], reverse=True)
            high_w = last_depth_weight[0][2]
            last_depth_weight_candi = [(idx, item) for idx, item, w in
                                       last_depth_weight if w == high_w]
            if len(last_depth_weight_candi) == 1:
                return last_depth_weight_candi[0][0]

            # ------------------------------
            # break a tie based on nopv
            nopv_states = [
                (idx, item, self.count_written_primitive_type_sv(item)) for
                idx, item in last_depth_weight_candi]
            # print(f'nopv: {nopv_states}')
            nopv_states.sort(key=lambda x: x[2], reverse=True)
            high_nopv = nopv_states[0][2]
            nopv_states_candi = [(idx, item) for idx, item, nopv in nopv_states
                                 if nopv == high_nopv]
            if len(nopv_states_candi) == 1:
                return nopv_states_candi[0][0]

            # ------------------------------
            # break a tie based on tnosv
            tnosv_states = [(idx, item, self.count_all_written_state_sv(item))
                            for idx, item in nopv_states_candi]
            tnosv_states.sort(key=lambda x: x[2], reverse=True)
            high_tnosv = tnosv_states[0][2]
            tnosv_states_candi = [(idx, item) for idx, item, nopv in
                                  tnosv_states if
                                  nopv == high_tnosv]
            if len(tnosv_states_candi) == 1:
                return tnosv_states_candi[0][0]

            candidates = tnosv_states_candi

        # ------------------------------
        # break a tie based on nodk
        targets = [dk for dk, _ in dk_functions]
        nodk_states = [(idx, item,
                        self.functionAssignment.get_num_targets_be_reached(
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
        selected = random_select_from_list(
            [idx for idx, _ in nodk_states_candi], 1)
        print('need rules to break a tie. Now randomly select one')
        print(f'select: {self.queue[selected[0]]}')
        return selected[0]


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

class Mine1(FunctionSearchStrategy):
    def __init__(self):
        self.proprocess_timeout=False
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
        print_data_for_mine_strategy(self.queue, self.state_write_slots,
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
                        # # reduce 1 from the weight of this state
                        # self.state_priority[state_key] = [weight - 2 for weight
                        #                                   in
                        #                                   self.state_priority[
                        #                                       state_key]]
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
            return [p,c,n]

        def is_a_new_write(slot, state_key) -> list:
            """
            check whether slot is written in the previous depths
            """

            ftn_seq = get_ftn_seq_from_key_1(state_key)
            for depth in range(0, len(ftn_seq)):
                if depth == 0:
                    # print(f'-- depth:{depth} ---')
                    if is_slot_in_a_list(slot, self.write_slots_genesis_states):
                        return False
                else:
                    if depth in self.state_write_slots[state_key].keys():
                        # print(f'-- depth:{depth} ---')
                        w_slots = self.state_write_slots[state_key][depth]
                        if is_slot_in_a_list(slot, w_slots):
                            return False
            return True

        # print(f'\n---- {state_key} ----')

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
            if len(writes_weights)>=2:
                if len(unique_writes)==1:
                    final_v=max(writes_weights)
                else:
                    final_v=max(writes_weights)+len(unique_writes)-1
            else:
                final_v=writes_weights[0]

        # print(f'weight: {final_v}: ({writes_status})')
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
                      self.functionAssignment.get_num_targets_be_reached(
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
