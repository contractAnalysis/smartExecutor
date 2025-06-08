import os.path
from copy import deepcopy, copy

import fdg
import llm
from fdg.control.ftn_search_strategy import FunctionSearchStrategy
from fdg.control.function_assignment import FunctionAssignment
from fdg.control.llm_related import get_feedback, get_candidate_sequences, \
    prune_candidate_sequences, initial_check_generated_sequences, \
    check_generated_candidate_sequences, prune_candidate_sequences_basic, \
    prune_candidate_sequences_advance, shorten_candidate_sequences, \
    print_sequences_in_dict, shorten_candidate_sequences_LP, \
    prune_candidate_sequences_PS, obtain_most_N_candi_sequences
from fdg.control.weight_computation import compute, \
    turn_write_features_to_a_value
from fdg.expression_slot import is_slot_in_a_list, \
    identify_slot_from_symbolic_slot_expression, common_elements

from fdg.fwrg_manager import FWRG_manager
from fdg.output_data import print_data_for_mine_strategy_1, \
    print_data_for_mine_strategy, my_print
from fdg.utils import get_ftn_seq_from_key_1, get_key_1_prefix, \
    random_select_from_list
from llm.llm_config import SEQ_iteration
from llm.obtain_sequence import collect_sequences, collect_candidate_sequences, \
    chop_candidate_sequences
from llm.utils import present_list_as_str, color_print
from mythril.laser.plugin.plugins.dependency_pruner import \
    get_writes_annotation_from_ws



class LLM(FunctionSearchStrategy):
    def __init__(self):
        self.preprocess_timeout=False
        self.preprocess_coverage=0

        self.state_storage={}
        self.written_slots_in_depth_str={} # the writes from all depths in str version

        self.queue=[]


        self.solidity_name=""
        self.contract_name=""
        self.contract_code=""
        self.start_functions = []
        self.target_functions = []
        self.all_functions = []
        self.all_sequences_dict = {}
        self.all_sequences=[]

        self.cur_targets=[] # the targets for which sequences are generated for them in the current generation iteration
        self.cur_sequences_to_be_exe_dict={} # the generated sequences for the current generation iteration
        self.cur_all_sequences=[]
        self.cur_iteration=0 # indicate the iteration for the generation process
        self.cur_seq_status={}  # save the status for target functions in the current generation iteration
        self.cur_actual_executed_seq=[]  # save the actual executed sequences in the current generation iteration

        self.feedback_all={} # save execution feedback according to targets

        self.valid_sequences_dict = {}  # save all valid sequences as additional context

        self.bad_sequences_w_reason=[] # save all invalid sequences as additional context
        self.all_sequences=[]


        self.msg_so_far=[]
        self.candidate_sequences={}
        self.state_key_assigned_at_last=""
        self.flag_one_start_function=False
        super().__init__('llm')


    def initialize(self, flag_one_start_function:bool, preprocess_timeout:bool, preprocess_coverage:float, all_functions:list, fwrg_manager:FWRG_manager,start_functions:list=[],target_functions:list=[]):
        self.flag_one_start_function=flag_one_start_function
        self.preprocess_timeout=preprocess_timeout
        self.preprocess_coverage=preprocess_coverage

        self.solidity_name = fdg.global_config.solidity_name
        self.contract_name = fdg.global_config.contract_name
        self.contract_code = llm.llm_config.contract_code

        self.start_functions =[ftn.split(f'(')[0] if "(" in ftn else ftn for ftn in start_functions]
        self.target_functions =[ftn.split(f'(')[0] if "(" in ftn else ftn for ftn in target_functions]
        self.target_functions = [ftn for ftn in self.target_functions if
                            ftn not in ['symbol', 'name', 'version', 'owner']]

        self.all_functions=all_functions
        self.all_functions_pure_name=[item.split(f'(')[0] if '(' in item else item for item in all_functions]
        self.cur_targets=self.target_functions

        self.functionAssignment=FunctionAssignment(self.all_functions,fwrg_manager)
        self.fwrg_manager=fwrg_manager

        self.gen_sequences()  # obtain sequences




        self.candidate_sequences={}
        self.left_target_code_coverage={}

    def save_valid_sequences(self, valid_sequence):
        if self.cur_iteration not in self.valid_sequences_dict.keys():
            self.valid_sequences_dict[self.cur_iteration]=[]
        if valid_sequence not in self.valid_sequences_dict[self.cur_iteration]:
            self.valid_sequences_dict[self.cur_iteration].append(valid_sequence)

        if valid_sequence not in self.cur_actual_executed_seq:
            self.cur_actual_executed_seq.append(valid_sequence)

    def gen_sequences(self,feedback:dict={},msg_so_far:list=[],):
        """
            The iteration process to generate sequences.
        """
        # iteration update and check
        self.cur_iteration+=1
        if self.cur_iteration>SEQ_iteration:
            self.cur_sequences_to_be_exe_dict={}
            self.cur_all_sequences={}
            return

        # prepare for data used to prompt construction
        data={}
        sequences={}

        # ----------------------------
        # data preparation for prompt construction
        if llm.llm_config.LLM_Mode in ['sel']:
            if self.cur_iteration==1:
                # get candidate sequences
                # collect candidate sequences based on the graph
                # get the graph
                graph = {k.split(f'(')[0] if '(' in k else k: [
                    item.split(f'(')[0] if '(' in item else item for item in v]
                    for
                    k, v
                    in
                    self.fwrg_manager.updateFWRG.fwrg_targets_augmented.items()}

                self.candidate_sequences = get_candidate_sequences(
                    graph, self.start_functions, self.cur_targets)

                # ---------------
                # candidate sequence pruning
                valid_sequences = [item for sublist in
                                   self.valid_sequences_dict.values() for item
                                   in
                                   sublist]
                others = [[item] for item in
                          self.start_functions]  # valid sequences of length 1
                valid_sequences = valid_sequences + others

                # basic pruning
                self.candidate_sequences = prune_candidate_sequences_basic(
                    self.cur_iteration,
                    self.cur_targets,
                    self.cur_sequences_to_be_exe_dict,
                    self.cur_all_sequences,
                    self.cur_actual_executed_seq,
                    self.candidate_sequences)

                # @self.candidate_sequences_cur
                self.candidate_sequences, candidate_sequences_dict = prune_candidate_sequences_advance(
                    self.cur_targets,
                    valid_sequences,
                    self.candidate_sequences)

                self.candidate_sequences = obtain_most_N_candi_sequences(
                    candidate_sequences_dict,
                    self.cur_sequences_to_be_exe_dict,
                    llm.llm_config.NUM_max_candidate_sequences)

                # @self.candidate_sequences_cur
                print_sequences_in_dict(self.candidate_sequences)

                # ---------------
                # prepare for data for sequence generation
                # check: when there is one candidate sequence for a target
                target_candidate_sequences_dict_for_prompt = {}
                targets_with_1_candidate_sequence = {}

                for target in self.cur_targets:
                    # @self.candidate_sequences_cur
                    if target not in self.candidate_sequences.keys():
                        target_candidate_sequences_dict_for_prompt[target] = []
                        continue
                    else:
                        # @self.candidate_sequences_cur
                        paths = self.candidate_sequences[target]
                        if len(paths) == 1:
                            targets_with_1_candidate_sequence[target] = paths
                        else:
                            target_candidate_sequences_dict_for_prompt[
                                target] = paths

                # check if there are some targets that have only one candidate sequence so that LLM is not required to make selection
                targets_w1_candi_seq = list(
                    targets_with_1_candidate_sequence.keys())

                # Define the JSON data to send in the POST request
                data = {"solidity_name": f"{self.solidity_name}",
                        "contract_name": f"{self.contract_name}",
                        "start_functions": self.start_functions,
                        "target_functions": self.cur_targets,
                        "contract_code": self.contract_code,
                        "feedback": {t: v for t, v in feedback.items() if
                                     t in self.cur_targets},

                        "valid_sequences": self.valid_sequences_dict,
                        "bad_sequences_w_reason": self.bad_sequences_w_reason,
                        "iteration": self.cur_iteration,
                        "candidate_sequences": self.candidate_sequences,
                        "msg_so_far": msg_so_far
                        }

                if len(target_candidate_sequences_dict_for_prompt) == 0 and len(
                    targets_w1_candi_seq) > 0:
                    color_print('Red',
                                f"No need to generate sequences as there is only one candidate sequence for each target({os.path.basename(__file__)}).")
                    sequences = targets_with_1_candidate_sequence
                else:
                    sequences = {}
            else:
                # i.e., self.cur_iteration>2
                # Define the JSON data to send in the POST request
                data = {"solidity_name": f"{self.solidity_name}",
                        "contract_name": f"{self.contract_name}",
                        "start_functions": self.start_functions,
                        "target_functions": self.cur_targets,
                        "contract_code": self.contract_code,
                        "feedback": {t: v for t, v in feedback.items() if
                                     t in self.cur_targets},
                        "valid_sequences": self.valid_sequences_dict,
                        "bad_sequences_w_reason": self.bad_sequences_w_reason,
                        "iteration": self.cur_iteration,
                        "candidate_sequences": self.candidate_sequences,
                        "msg_so_far": msg_so_far
                        }




        elif self.cur_iteration==1 or llm.llm_config.LLM_Mode in ['gen']:
            # Define the JSON data to send in the POST request
            data = {"solidity_name": f"{self.solidity_name}",
                    "contract_name": f"{self.contract_name}",
                    "start_functions": self.start_functions,
                    "target_functions": self.cur_targets,
                    "contract_code": self.contract_code,
                    "feedback": {t: v for t, v in feedback.items() if
                                 t in self.cur_targets},
                    "valid_sequences": self.valid_sequences_dict,
                    "bad_sequences_w_reason": self.bad_sequences_w_reason,
                    "iteration": self.cur_iteration,
                    "candidate_sequences": {},
                    'targets_w1_candidate_sequence': {},
                    "msg_so_far": msg_so_far
                    }

        elif self.cur_iteration>=2 and llm.llm_config.LLM_Mode not in ['gen']:
            if self.cur_iteration==2:
                #---------------
                # candidate sequence collection
                if llm.llm_config.LLM_Mode in ['gen_sel']:
                    # collect candidate sequences based on the graph
                    # get the graph
                    graph = {k.split(f'(')[0] if '(' in k else k: [
                        item.split(f'(')[0] if '(' in item else item for item in v]
                        for
                        k, v
                        in
                        self.fwrg_manager.updateFWRG.fwrg_targets_augmented.items()}

                    self.candidate_sequences = get_candidate_sequences(
                        graph, self.start_functions, self.cur_targets)




                elif llm.llm_config.LLM_Mode in ['gen_sel_llm']:
                    # get candidate sequences from an LLM model
                    # make sure msg_so_far is an empty list
                    data = {"solidity_name": f"{self.solidity_name}",
                            "contract_name": f"{self.contract_name}",
                            "start_functions": self.start_functions,
                            "target_functions": self.cur_targets,
                            "contract_code": self.contract_code,
                            "feedback": {t: v for t, v in feedback.items() if
                                         t in self.cur_targets},
                            "num_sequences": llm.llm_config.NUM_max_candidate_sequences,
                            "valid_sequences": self.valid_sequences_dict,
                            "bad_sequences_w_reason": self.bad_sequences_w_reason,
                            "iteration": self.cur_iteration,
                            "msg_so_far": [],
                            "candidate_sequences": {}
                            }
                    self.candidate_sequences= collect_candidate_sequences(
                        data)

                    # initial check the candidate sequences
                    # check_generated_candidate_sequences
                    self.candidate_sequences= check_generated_candidate_sequences(
                        self.candidate_sequences, self.start_functions, self.cur_targets,
                        self.all_functions_pure_name)




                # ---------------
                # candidate sequence pruning
                valid_sequences = [item for sublist in
                                self.valid_sequences_dict.values() for item in
                                sublist]
                others = [[item] for item in
                                   self.start_functions]  # valid sequences of length 1
                valid_sequences = valid_sequences + others

                # basic pruning
                self.candidate_sequences = prune_candidate_sequences_basic(
                    self.cur_iteration,
                    self.cur_targets,
                    self.cur_sequences_to_be_exe_dict,
                    self.cur_all_sequences,
                    self.cur_actual_executed_seq,
                    self.candidate_sequences)

                #@self.candidate_sequences_cur
                self.candidate_sequences,candidate_sequences_dict = prune_candidate_sequences_advance(
                    self.cur_targets,
                    valid_sequences,
                    self.candidate_sequences)


                self.candidate_sequences=obtain_most_N_candi_sequences(candidate_sequences_dict,
                                                                       self.cur_sequences_to_be_exe_dict, llm.llm_config.NUM_max_candidate_sequences)



                # @self.candidate_sequences_cur
                print_sequences_in_dict(self.candidate_sequences)

                # ---------------
                # prepare for data for sequence generation
                # check: when there is one candidate sequence for a target
                target_candidate_sequences_dict_for_prompt = {}
                targets_with_1_candidate_sequence = {}

                for target in self.cur_targets:
                    # @self.candidate_sequences_cur
                    if target not in self.candidate_sequences.keys():
                        target_candidate_sequences_dict_for_prompt[target] = []
                        continue
                    else:
                        # @self.candidate_sequences_cur
                        paths = self.candidate_sequences[target]
                        if len(paths) == 1:
                            targets_with_1_candidate_sequence[target] = paths
                        else:
                            target_candidate_sequences_dict_for_prompt[
                                target] = paths


                # check if there are some targets that have only one candidate sequence so that LLM is not required to make selection
                targets_w1_candi_seq = list(
                    targets_with_1_candidate_sequence.keys())

                # Define the JSON data to send in the POST request
                data = {"solidity_name": f"{self.solidity_name}",
                        "contract_name": f"{self.contract_name}",
                        "start_functions": self.start_functions,
                        "target_functions": self.cur_targets,
                        "contract_code": self.contract_code,
                        "feedback": {t: v for t, v in feedback.items() if
                                     t in self.cur_targets},

                        "valid_sequences": self.valid_sequences_dict,
                        "bad_sequences_w_reason": self.bad_sequences_w_reason,
                        "iteration": self.cur_iteration,
                        "candidate_sequences": target_candidate_sequences_dict_for_prompt,
                        'targets_w1_candidate_sequence': targets_w1_candi_seq,
                        "msg_so_far": msg_so_far
                        }

                if len(target_candidate_sequences_dict_for_prompt) == 0 and len(targets_w1_candi_seq)>0:
                    color_print('Red',
                                f"No need to generate sequences as there is only one candidate sequence for each target({os.path.basename(__file__)}).")
                    sequences = targets_with_1_candidate_sequence
                else:
                    sequences={}
            else:
                # i.e., self.cur_iteration>2
                # Define the JSON data to send in the POST request
                data = {"solidity_name": f"{self.solidity_name}",
                        "contract_name": f"{self.contract_name}",
                        "start_functions": self.start_functions,
                        "target_functions": self.cur_targets,
                        "contract_code": self.contract_code,
                        "feedback": {t: v for t, v in feedback.items() if
                                     t in self.cur_targets},
                        "valid_sequences": self.valid_sequences_dict,
                        "bad_sequences_w_reason": self.bad_sequences_w_reason,
                        "iteration": self.cur_iteration,
                        "candidate_sequences": {},
                        'targets_w1_candidate_sequence': {},
                        "msg_so_far": msg_so_far
                        }



        #----------------------------
        # sequence generation
        if len(sequences)==0:
            sequences,self.msg_so_far=collect_sequences(data,iteration=self.cur_iteration)

            if len(sequences)==0:
                color_print("Red",f'No sequence is generated ({os.path.basename(__file__)}).')
                return

            # ----------------------------
            # sequence initial checking or preliminary checking
            self.cur_sequences_to_be_exe_dict = {}
            self.cur_all_sequences=[]
            self.cur_seq_status={}

            sequences_status_dict,sequences_w1_status_dict=initial_check_generated_sequences(sequences,self.start_functions,self.cur_targets,self.all_functions_pure_name)

            sequences_to_consider={}
            if len(sequences_status_dict.keys())>0:
                sequences_to_consider={k:v["sequence"] for k,v in sequences_status_dict.items() if v['consider']}

            for k,v in sequences_w1_status_dict.items():
                if k not in sequences_to_consider.keys():
                    if v['consider']:
                        sequences_to_consider[k]=v["sequence"]


            self.cur_sequences_to_be_exe_dict=sequences_to_consider


            self.cur_all_sequences=[value["sequence"] for value in sequences_status_dict.values() ]
            # these are the sequences manually fixed from the generated sequences
            self.cur_all_sequences+=[value["sequence"] for value in sequences_w1_status_dict.values() ]


            # add bad_sequences

            for value in sequences_status_dict.values():
                if value['sequence'] not in self.all_sequences and not value['consider']:
                    # only consider the statuses on sequences not on target or length.
                    if "[" in value['status'] and "]" in value['status']:
                        self.bad_sequences_w_reason.append(value['status'])


            # keep the status of the sequences, which can be updated based on the execution of a subset of sequences.
            self.cur_seq_status={k:v["status"] for k,v in sequences_status_dict.items() }

            # add all current sequences to all the sequences of the whole process
            for seq in self.cur_all_sequences:
                if seq not in self.all_sequences:
                    self.all_sequences.append(seq)


            # add sequences for targets with 1 candidate sequence (no need to query an LLM)
            if llm.llm_config.LLM_Mode not in ['gen','sel'] and self.cur_iteration==2:
                for key, paths in targets_with_1_candidate_sequence.items():
                    if len(paths)==1:
                        if paths[0] not in self.all_sequences:
                            self.cur_all_sequences.append(paths[0])
                            self.cur_sequences_to_be_exe_dict[key] = paths[0]
                            self.all_sequences.append(paths[0])


        if self.cur_iteration>=2:
            # find start states for the sequences
            self.find_start_states()


    def find_start_states(self):

        def be_a_prefix(seq1:list,seq2:list)->bool:
            if len(seq1)>=len(seq2):return False
            for i,e1 in enumerate(seq1):
                if e1 not in [seq2[i]]:
                    return False
            return True
        state_keys=list(set(self.world_states.keys()))
        state_keys_seq=[(key,get_ftn_seq_from_key_1(key)) for key in state_keys]
        state_keys_seq.sort(key=lambda x:len(x[1]), reverse=True)
        for seq in self.cur_sequences_to_be_exe_dict.values():
            max_prefix_len=0
            for key,ftn_seq in state_keys_seq:
                ftn_seq_temp=[ftn.split(f'(')[0] if '(' in ftn else ftn for ftn in ftn_seq]
                if be_a_prefix(ftn_seq_temp,seq):
                    if max_prefix_len==0:
                        max_prefix_len=len(ftn_seq_temp)
                        if key not in self.queue:
                            color_print('Red',
                                        f'Find the state {key} for sequence {seq}')
                            self.queue.append(key)
                        continue
                    else:
                        if max_prefix_len>0:
                            if key not in self.queue:
                                if len(ftn_seq_temp)==max_prefix_len:
                                    color_print('Red',
                                                f'Find the state {key} for sequence {seq}')
                                    self.queue.append(key)




    def identify_functions(self,state_key:str):
        """
        from a list of sequences, find the next functions for a state.
        a next function is the function immediately following the state sequence in the sequence prefixed by the state sequence.
        """
        def find_next_function(seq1:list,seq2:list):
            if len(seq1)>=len(seq2):return ""
            for i, e1 in enumerate(seq1):
                if e1 not in [seq2[i]]:
                    return ""
            return seq2[len(seq1)]
        functions=[]
        ftn_seq=get_ftn_seq_from_key_1(state_key)
        ftn_seq_temp = [ftn.split(f'(')[0] if '(' in ftn else ftn for ftn in
                        ftn_seq]
        for seq in self.cur_sequences_to_be_exe_dict.values():
            next_func=find_next_function(ftn_seq_temp,seq)
            if len(next_func)>0:
                functions.append(next_func)
        return list(set(functions))



    def assign_states(self, dk_functions: list = None, states_dict: dict = {}, iteration:int=0) -> list:
        """

        :param dk_functions:
        :param fwrg:
        :param states_dict:
        :return:
        """

        if len(dk_functions) == 0: return {}, None
        if len(states_dict) > 0:
            # save the new states
            self.update_states(states_dict)
            self.filter_states()

        # ---------------
        print_data_for_mine_strategy(self.queue)

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
                left_target_cov={ftn.split(f'(')[0] if '(' in ftn else ftn:cov for ftn,cov in dk_functions}
                left_target_cov={ftn:value for ftn,value in left_target_cov.items() if ftn not in ['symbol','name','version','owner'] }

                self.cur_targets = [ftn.split(f'(')[0] if '(' in ftn else ftn
                                    for ftn, _ in dk_functions]
                self.cur_targets = [ftn for ftn in self.cur_targets if
                                    ftn not in ['symbol', 'name', 'version',
                                                'owner']]

                if self.cur_iteration >= llm.llm_config.SEQ_iteration:
                    return {}, None

                if self.cur_iteration==1:
                    for k, cov in left_target_cov.items():
                        self.left_target_code_coverage[k]=[cov]
                elif self.cur_iteration>=2:
                    for k,v in left_target_cov.items():
                        self.left_target_code_coverage[k].append(v)

                cur_feedback=get_feedback(self.cur_targets, self.cur_sequences_to_be_exe_dict, self.cur_actual_executed_seq, left_target_cov,target_code_coverage=self.left_target_code_coverage, other_cur_feedback=self.cur_seq_status)
                for t,status in cur_feedback.items():
                    if t in self.feedback_all.keys():
                        self.feedback_all[t].append(status)
                    else:
                        self.feedback_all[t]=[status]

                self.gen_sequences(feedback=self.feedback_all,msg_so_far=self.msg_so_far)
                self.cur_actual_executed_seq = []


            # double check
            if len(self.queue)==0:
                continue

            flag_can_be_deleted = False

            # # pick up a state from the queue
            # targets = [dk for dk, _ in dk_functions]
            # state_key = self.pickup_a_state(
            #     targets)  # order the states in self.queue and pick up the one has the highest weight

            state_key=self.queue.pop(0)

            next_functions=self.identify_functions(state_key)
            if len(next_functions)>0:
                self.state_key_assigned_at_last = state_key
                return {state_key: next_functions}, flag_can_be_deleted


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
                # if key_prefix.startswith('fallback') and key_prefix.endswith('fallback'):
                #     continue
                # else:
                #     if key_prefix.endswith('fallback#fallback'):
                #         continue

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
                    if idx<=1:
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



