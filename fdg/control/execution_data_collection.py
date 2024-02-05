from copy import deepcopy

import fdg
from fdg.control.ftn_search_strategy import FunctionSearchStrategy
from fdg.control.function_assignment import FunctionAssignment
from fdg.expression_slot import identify_slot_from_symbolic_slot_expression
from fdg.output_data import print_data_for_mine_strategy
from fdg.utils import get_ftn_seq_from_key_1, get_key_1_prefix
from mythril.laser.plugin.plugins.dependency_pruner import \
    get_writes_annotation_from_ws
from fdg.fwrg_manager import FWRG_manager

class ExeDataCollection(FunctionSearchStrategy):
    def __init__(self):
        self.preprocess_timeout=False
        self.preprocess_coverage=0

        self.state_storage={}
        self.written_slots_in_depth_str={} # the writes from all depths in str version

        self.queue=[]
        self.state_key_assigned_at_last=""
        # self.parent_state_keys = {}

        super().__init__('exeDataCollection')


    def initialize(self,flag_one_state_depth1:bool,preprocess_timeout:bool, preprocess_coverage:float,all_functions:list,fwrg_manager:FWRG_manager):

        self.preprocess_timeout=preprocess_timeout
        self.preprocess_coverage=preprocess_coverage

        # self.functionAssignment=FunctionAssignment(all_functions,fwrg_manager)
        self.fwrg_manager=fwrg_manager
        self.all_functions=all_functions

        # print the read/write of the state variables of functions
        print('Function Reads: State variables read in conditions')
        for key,reads in self.fwrg_manager.fwrg.ftn_reads_in_condition.items():
            print(f'\t{key}:{reads}')
        print(f'Function Writes: State variables written')
        for key,writes in self.fwrg_manager.fwrg.ftn_writes.items():
            print(f'\t{key}:{writes}')




    def assign_states(self, dk_functions: list = None, states_dict: dict = {}, iteration:int=0) -> list:
        """

        :param dk_functions:
        :param fwrg:
        :param states_dict:
        :return:
        """
        print(f'============================')
        print(f'iteration:{iteration}')
        if iteration==3:
            print(f'targets:{[ftn for ftn,_ in dk_functions]}')
        # print(f'dk functions:{dk_functions}')

        if len(states_dict) > 0:
            # save the new states
            self.update_states(states_dict)

        # assign a state and the functions to be executed on it
        while True:
            if len(self.queue) == 0:
                return {}, None
            # print(f'queue')
            # for item in self.queue:
            #     print(f'\t{item}')
            state_key=self.queue.pop(-1)
            ftn_seq=get_ftn_seq_from_key_1(state_key)
            print(f'popped key:{state_key}:{ftn_seq}')
            if len(ftn_seq)>=4:continue
            flag_can_be_deleted = True
            assigned_children=['original_instruction_list']
            print(f'assigned functions:{assigned_children}')
            return {state_key: assigned_children}, flag_can_be_deleted



    def termination(self, states_num: int = 0, current_seq_length: int = 0, sequence_depth_limit: int = 0,
                    iteration: int = 0) -> bool:
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
                    # print(f'written_slots from annotation:{written_slots}')
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
                    print(f'{ftn_seq}:writes at the last depth:{writes_str}')


                else:
                    slots=state.accounts[address].storage.printable_storage.keys()

                    # save the slots in str version
                    slots_str=[identify_slot_from_symbolic_slot_expression(s) for s in slots]
                    if key not in self.written_slots_in_depth_str.keys():
                        self.written_slots_in_depth_str[key]={0:slots_str}
                    print(f'{ftn_seq}:writes at the last depth:{slots_str}')

                    self.state_storage[key] = state.accounts[address].storage.printable_storage


    def get_written_slots_in_depth_str(self, state_key:str):
        if state_key not in self.written_slots_in_depth_str.keys():
            return {}
        else:
            return self.written_slots_in_depth_str[state_key]

