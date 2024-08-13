from copy import deepcopy, copy



import fdg.global_config
import rl
from fdg.control.ftn_search_strategy import FunctionSearchStrategy
from fdg.control.function_assignment import FunctionAssignment
from fdg.expression_slot import identify_slot_from_symbolic_slot_expression, \
    common_elements
from fdg.fwrg_manager import FWRG_manager
from fdg.output_data import my_print, print_data_for_mine_strategy
from fdg.utils import get_ftn_seq_from_key_1, random_select_from_list, \
    get_key_1_prefix, is_equal_list
from mythril.laser.plugin.plugins.dependency_pruner import \
    get_writes_annotation_from_ws
from rl.config import rl_cur_parameters
from rl.seq_generation import wrapper


class MIX1(FunctionSearchStrategy):
    def __init__(self):
        self.preprocess_timeout = False
        self.preprocess_coverage = 0

        self.state_storage = {}
        self.written_slots_in_depth_str = {}  # the writes from all depths in str version

        self.queue = []
        self.sequences = []

        self.state_key_assigned_at_last = ""
        self.flag_one_start_function = False
        self.executed_functions_on_states={}
        self.flag_rl=True
        self.queue_backup=[]

        super().__init__('mix1')


    def initialize(self, flag_one_start_function:bool, preprocess_timeout:bool, preprocess_coverage:float, all_functions:list, fwrg_manager:FWRG_manager,start_functions:list, target_functions:list, solidity_name:str, contract_name:str,solc_version:str=""):
        self.flag_one_start_function=flag_one_start_function
        self.preprocess_timeout = preprocess_timeout
        self.preprocess_coverage = preprocess_coverage


        self.start_functions=start_functions
        self.target_functions=target_functions
        self.target_functions_no_seq=[]
        self.solidity_name=solidity_name
        self.contract_name=contract_name
        self.solc_version=solc_version

        self.flag_rl_mlp_policy=True
        self.request_sequences() # obtain sequences

        self.all_functions = all_functions
        self.functionAssignment = FunctionAssignment(all_functions,
                                                     fwrg_manager,sequences=self.sequences)

        self.functionAssignment.targets_with_no_seq=self.target_functions_no_seq
        self.fwrg_manager=fwrg_manager


    def request_sequences(self):
        # Define the JSON data to send in the POST request
        data = {"solidity_name": f"{self.solidity_name}",
                "contract_name": f"{self.contract_name}",
                # "solc_version": "0.4.18",
                # "start_functions": [],
                # "target_functions": [],
                "top_k": f'{rl.config.top_k}',
                "flag_whole": rl.config.rl_cur_parameters["flag_model_whole"],
                "dataset": rl.config.rl_cur_parameters["dataset"],
                }
        # print(f'Request data:{data}')

        result = wrapper.generate_simple(data)
        if len(result)>0:
            for k, v in result.items():
                print(f'{k}')
                for seq in v:
                    self.sequences.append(seq)
                    print(f'\t{seq}')
            targets_with_seq=[ftn.split(f'.')[-1] if '.' in ftn else ftn for ftn in result.keys()]
            for target,_ in self.target_functions:
                if target not in targets_with_seq:
                    if target not in ['symbol()','name()','decimals()','version()']:
                        self.target_functions_no_seq.append(target)
            if len(self.sequences)==0:
                self.flag_rl=False

        else:
            print("Error:", "no sequences are generated")
            self.flag_rl_mlp_policy = False
            self.flag_rl=False




    def termination(self, states_num: int = 0, current_seq_length: int = 0, sequence_depth_limit: int = 0,
                    iteration: int = 0) -> bool:
        # need to test
        # if states_num == 0: return True
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
        if not self.preprocess_timeout or fdg.global_config.preprocessing_exception:
            if len(dk_functions) == 0: return {}, None

        if len(states_dict)>0:
            # save the new states
            self.update_states(states_dict)
            self.filter_states()

        # ---------------
        print_data_for_mine_strategy(self.queue)

        while True:
            if self.flag_rl:
                while True:
                    # pick up a state from the queue
                    state_key=""
                    if len(self.queue)>0:
                        state_key=self.queue.pop(0)
                    else:
                        self.flag_rl=False
                        # put all keys in the self.not_execute to self.queue
                        # if len(self.not_executes) > 0:
                        #     self.queue = list(set(self.not_executes.keys()))
                        if len(self.queue_backup) > 0:
                            self.queue = copy(self.queue_backup)
                            self.queue_backup=[]
                            break
                        else:
                            # no states to explore, end
                            return {}, False


                    # get the functions
                    functions=[]
                    ftn_seq = get_ftn_seq_from_key_1(state_key)
                    for seq_ in self.sequences:
                        if len(ftn_seq) >= len(seq_): continue
                        flag_add = True
                        for i in range(len(ftn_seq)):
                            """
                            a speical case
                            0x7f0C14F2F72ca782Eea2835B9f63d3833B6669Ab.sol	0.4.24	UFragmentsPolicy
    initialize(address,address,uint256),initialize(address) (se) vs initialize(address,UFragments,uint256) (generated)
                            """
                            if ftn_seq[i] not in [seq_[i]]:
                                pure_name = ftn_seq[i].split(f'(')[0] if '(' in ftn_seq[i] else ftn_seq[i]
                                if pure_name not in [seq_[i][0:len(pure_name)]]:
                                    flag_add = False
                                    break
                        if flag_add:
                            if seq_[len(ftn_seq)] not in functions:
                                functions.append(seq_[len(ftn_seq)])

                    self.executed_functions_on_states[state_key]=functions
                    if len(functions)>0:
                        self.state_key_assigned_at_last = state_key
                        return {state_key: functions}, False

            else:
                # --------------
                # case 1
                # assign the only state
                if self.flag_one_start_function:
                    self.flag_one_start_function = False  # only consider once
                    state_key = self.queue.pop(0)
                    assign_functions = self.functionAssignment.assign_all_functions()
                    self.state_key_assigned_at_last = state_key
                    return {state_key: assign_functions}, True

                # --------------
                # case 2
                # assign a state and the functions to be executed on it
                while True:
                    if len(self.queue) == 0:
                        return {}, False

                    not_to_execute = []

                    # pick up a state from the queue
                    targets = [dk for dk, _ in dk_functions]

                    state_key,functions=self.reintroduce_state_at_depth_1(targets)
                    if len(state_key)>0:
                        print(f'Reintroduce state {state_key} and assign functions: {functions}')
                        self.state_key_assigned_at_last = state_key
                        return {state_key: functions}, True

                    state_key = self.pickup_a_state(targets)  # order the states in self.queue and pick up the one has the highest weight

                    if state_key in self.executed_functions_on_states.keys():
                        not_to_execute=self.executed_functions_on_states[state_key]
                        # get back the states that should be generated after this state
                        if len(not_to_execute)>0:
                            state_key_seq=get_ftn_seq_from_key_1(state_key)
                            for ftn in not_to_execute:
                                target_seq=state_key_seq+[ftn]
                                for key in self.world_states.keys():
                                    key_seq=get_ftn_seq_from_key_1(key)
                                    if is_equal_list(target_seq,key_seq):
                                        if key not in self.queue:
                                            self.queue.append(key)
                                            break


                    flag_can_be_deleted = False if len(get_ftn_seq_from_key_1(state_key))==1 else True

                    percent_of_functions = 1
                    if self.preprocess_timeout or fdg.global_config.preprocessing_exception:
                        if self.preprocess_coverage < 50:
                            percent_of_functions = 7
                        elif self.preprocess_coverage < 80:
                            percent_of_functions = 5
                        elif self.preprocess_coverage < 90:
                            percent_of_functions = 3
                    children=[]
                    if self.preprocess_timeout or fdg.global_config.preprocessing_exception:
                        random_selected_functions = self.functionAssignment.select_functions_randomly(
                            percent_of_functions)
                        # assign functions
                        children = self.functionAssignment.assign_functions_timeout_mine(
                            state_key, dk_functions, random_selected_functions)
                    else:
                        children = self.functionAssignment.assign_functions(
                            state_key,
                            dk_functions)

                    children=[child for child in children if child not in not_to_execute]
                    if len(children)>0:
                        if state_key in self.executed_functions_on_states.keys():
                            self.executed_functions_on_states[state_key]+=children
                        else:
                            self.executed_functions_on_states[state_key] = children

                        self.state_key_assigned_at_last = state_key
                        return {state_key: children}, flag_can_be_deleted



    def update_states(self, states_dict:dict)->list:
        """
        save states
        """
        address = fdg.global_config.contract_address.value

        for key,states in states_dict.items():
            for state in states:
                ftn_seq=get_ftn_seq_from_key_1(key)
                if 'constructor' not in ftn_seq:
                    if len(ftn_seq)==1:
                        self.queue_backup.append(key)
                    self.world_states[key]=[deepcopy(state)]
                    self.queue.append(key)
                    self.state_storage[key] = state.accounts[
                        address].storage.printable_storage

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
                    self.delete_state(key)
                    continue
                else:
                    if key_prefix.endswith('fallback#fallback'):
                        self.delete_state(key)
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
                        else:
                            self.delete_state(key)

    def get_written_slots_in_depth_str(self, state_key:str):
        if state_key not in self.written_slots_in_depth_str.keys():
            return {}
        else:
            return self.written_slots_in_depth_str[state_key]

    def reintroduce_state_at_depth_1(self,targets:list):
        def has_depth_1_states_in_queue() -> bool:
            for key in self.queue:
                if len(get_ftn_seq_from_key_1(key)) == 1:
                    return True
            return False

        def reintroduce_a_state_at_depth_1(targets: list):
            for key in self.executed_functions_on_states.keys():
                ftn_seq = get_ftn_seq_from_key_1(key)
                if len(ftn_seq) == 1:
                    possible_functions = [t for t in targets if
                                          t not in self.executed_functions_on_states[key]]
                    if len(possible_functions) > 0:
                        self.executed_functions_on_states.pop(key)
                        return key, possible_functions
            return "",[]

        if not has_depth_1_states_in_queue():
            key,functions=reintroduce_a_state_at_depth_1(targets)
            return key,functions
        else:
            return "",[]

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
                    my_print(f'\tfor function {dk}:')
                    reads_str = [identify_slot_from_symbolic_slot_expression(s)
                                 for s in
                                 reads]
                    my_print(f'\t\tread slots:{reads_str}')
                    count_common = common_elements(reads_str,written_slot_by_state)
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
            my_print(f'\twrite slots:{written_slots_str}')

            written_slots_str_all=self.get_written_slots_in_depth_str(state_key)
            my_print(f'\twrite slots:{written_slots_str_all} (writes at each depth)')

            return written_slots_str



        if len(self.queue)==0:return None
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
                    my_print(f'\tfor function {dk}:')
                    reads_str = [identify_slot_from_symbolic_slot_expression(s)
                                 for s in
                                 reads]
                    my_print(f'\t\tread slots:{reads_str}')
                    count_common = common_elements(reads_str, recent_writes)
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

