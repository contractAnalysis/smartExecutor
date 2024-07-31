from copy import deepcopy

import fdg.global_config
from fdg.control.ftn_search_strategy import FunctionSearchStrategy
from fdg.fwrg_manager import FWRG_manager
from fdg.output_data import print_list, print_assigned_functions
from fdg.instruction_modification import InstructionModification
from fdg.preprocessing.preprocess import Preprocessing
from fdg.utils import get_key_1, get_ftn_seq_from_key_1
from mythril.laser.ethereum.state.world_state import WorldState
from mythril.laser.ethereum.svm import LaserEVM
from mythril.laser.plugin.plugins.dependency_pruner import get_ftn_seq_annotation_from_ws



class Guider():
    def __init__(self, ftn_search_strategy:FunctionSearchStrategy,functions:list):
        self.ftn_search_strategy=ftn_search_strategy
        self.instructionModification = InstructionModification(fdg.global_config.method_identifiers)
        self.all_functions=functions

        self.termination=False

        self.genesis_states=[]
        self.state_index=0 # used to form state keys


    def init(self, start_functions:list, depth_k_functions:list, preprocess:Preprocessing):
        fwrg_manager=FWRG_manager(start_functions, depth_k_functions, preprocess)
        if self.ftn_search_strategy.name in ['seq']:
            self.ftn_search_strategy.initialize(fwrg_manager.acyclicPaths.main_paths_sf, fwrg_manager.updateFWRG.main_paths_df, fwrg_manager)
        elif self.ftn_search_strategy.name in ['mine','bfs','dfs','rl_mlp_policy','mix','mix1']:
            flag_one_start_function=True if len(start_functions)==1 else False  #to-do: how to update flag_one_state_dpeht1
            if preprocess.coverage is None:
                preprocess.coverage=0
            if self.ftn_search_strategy.name in ['rl_mlp_policy','mix','mix1']:
                self.ftn_search_strategy.initialize(flag_one_start_function,preprocess.timeout,preprocess.coverage,preprocess.write_read_info.all_functions,fwrg_manager,start_functions,depth_k_functions,fdg.global_config.solidity_name,fdg.global_config.contract_name)
            else:
                self.ftn_search_strategy.initialize(flag_one_start_function,
                                                    preprocess.timeout,
                                                    preprocess.coverage,
                                                    preprocess.write_read_info.all_functions,
                                                    fwrg_manager)

    def organize_states(self, states:[WorldState]):
        all_states = {}
        for state in states:
            ftn_seq = get_ftn_seq_annotation_from_ws(state)

            if ftn_seq is None or len(ftn_seq) == 0:
                key = get_key_1(['constructor'], self.state_index)
            else:
                # do not save states that are generated at maximum depth
                if len(ftn_seq) >= fdg.global_config.seq_len_limit:
                    continue
                key = get_key_1(ftn_seq, self.state_index)

            # save state
            all_states[key] = [state]
            self.state_index += 1
        return all_states

    def start_iteration(self, laserEVM:LaserEVM=None, dk_functions:list=None, iteration:int=0):
        """
            prepare for states and functions to be executed on the states
        :param laserEVM:
        :param deep_function:
        :param iteration:
        :return:
        """
        #============================================
        if self.ftn_search_strategy.name in ['seq']:
            if iteration == 1:
                self.ftn_search_strategy.initialize()

                organize_states_dict={'constructor':laserEVM.open_states}
                states_functions,flag_world_state_del = self.ftn_search_strategy.assign_states(
                    dk_functions=None, fdfg=None, states_dict=organize_states_dict)
                print_assigned_functions(states_functions)
                self._prepare_states(laserEVM, organize_states_dict, states_functions,flag_world_state_del)

            else:
                organize_states_dict = self.organize_states(laserEVM.open_states)
                states_functions,flag_world_state_del = self.ftn_search_strategy.assign_states(
                    dk_functions=None, fdfg=None,
                    states_dict=organize_states_dict)
                organize_states_dict = {}
                if len(states_functions)>0:
                    for key, function in states_functions.items():
                        if len(function) > 0:
                            organize_states_dict[key] = deepcopy(self.ftn_search_strategy.world_states[key])
                    print_assigned_functions(states_functions)
                    self._prepare_states(laserEVM, organize_states_dict, states_functions,flag_world_state_del)
            return


        # ============================================
        if self.ftn_search_strategy.name in ['baseline']:
            if iteration==1:
                laserEVM.open_states = self.genesis_states
                sequences= [[ftn] for ftn in self.all_functions]
                print_list(sequences, f'current all sequence(s):')

            else:
                organize_states_dict = self.organize_states(laserEVM.open_states)


                states_functions,flag_world_state_del = self.ftn_search_strategy.assign_states(
                    dk_functions=None, states_dict=organize_states_dict)
                print_assigned_functions(states_functions)
                if self.ftn_search_strategy.name in ['baseline']:
                    organize_states_dict = {}
                    for key, function in states_functions.items():
                        if len(function) > 0:
                            organize_states_dict[key] = deepcopy(self.ftn_search_strategy.world_states[key])

                self._prepare_states(laserEVM, organize_states_dict, states_functions,False)
            return

        # =============== bfs,dfs,mine=============================
        # prepare for depth 1 execution for deep function collection
        if iteration==2 :
            laserEVM.open_states=self.genesis_states
            sequences=[[ftn] for ftn in self.all_functions]
            print_list(sequences, f'current all sequence(s):')
        else:
            # when iteration >2
            organize_states_dict=self.organize_states(laserEVM.open_states)
            states_functions,flag_world_state_del=self.ftn_search_strategy.assign_states(dk_functions=dk_functions, states_dict=organize_states_dict, iteration=iteration)

            if len(states_functions)==0:
                # no functions will be executed
                self.termination=True

            # get the states for the state keys in data states_functions returned from assign_states
            if self.ftn_search_strategy.name in ['dfs','mine','bfs','rl_mlp_policy','mix','mix1']:
                organize_states_dict = {}
                for key,function in states_functions.items():
                    if len(function)>0:
                        if key in self.ftn_search_strategy.world_states.keys():
                            organize_states_dict[key]=self.ftn_search_strategy.world_states[key]
                        else:
                            print(f'why {key} is not available?')

            print_assigned_functions(states_functions)
            self._prepare_states(laserEVM, organize_states_dict, states_functions,flag_world_state_del)


    def _prepare_states(self, laserEVM:LaserEVM, states_dict:dict, states_functions:dict,flag_wd_del:bool):
        cur_iteration_all_sequences = []
        # specify the functions to be executed on each open states(world states)
        if len(states_functions)==0:
            laserEVM.open_states=[]
            return

        modified_states = []
        for key, states in states_dict.items():
            ftn_seq = get_ftn_seq_from_key_1(key)
            next_functions = states_functions[key]

            if len(next_functions) > 0:
                # # save sequences to be executed
                # for child in next_functions:
                #     cur_iteration_all_sequences.append(ftn_seq + [child])

                # modify function dispatcher so that only specified functions are executed
                to_modify_states = deepcopy(states)
                self.instructionModification.modity_on_multiple_states(to_modify_states, next_functions)
                modified_states += to_modify_states


        # update the open states so that the states having no children nodes are removed
        laserEVM.open_states = modified_states

        if flag_wd_del:
            # delete states
            # print(f'\nbefore state delete:{self.ftn_search_strategy.world_states.keys()}')
            for key in states_dict.keys():
                print(f'delete: {key}')
                self.ftn_search_strategy.delete_state(key)
            # print(f'\n after state delete:{self.ftn_search_strategy.world_states.keys()}')

        # print_list(cur_iteration_all_sequences, f'current all sequence(s):')



    def end_iteration(self,laserEVM:LaserEVM,iteration:int):
        state_changing_seq = []
        len_seq=0
        for state in laserEVM.open_states:
            seq = get_ftn_seq_annotation_from_ws(state)
            if seq is None:continue
            len_seq=len(seq)
            if len_seq==0:continue
            if seq not in state_changing_seq:
                state_changing_seq.append(seq)
        print_list(state_changing_seq, f'current state changing sequence(s):')



        self.termination=self.ftn_search_strategy.termination(
            states_num=len(laserEVM.open_states),
            current_seq_length=len_seq,
            sequence_depth_limit=fdg.global_config.seq_len_limit,
            iteration=iteration)

    def get_start_sequence(self,laserEVM:LaserEVM):
        """
        get the sequences used to annotate the states (world states) at the end of Phase 1
        """
        state_chaning_seq = []
        for state in laserEVM.open_states:
            seq = get_ftn_seq_annotation_from_ws(state)
            if seq not in state_chaning_seq:
                state_chaning_seq.append(seq)
        return state_chaning_seq


    def should_terminate(self):
        return self.termination

    def save_genesis_states(self,states:list):
        self.genesis_states=deepcopy(states)
        if self.ftn_search_strategy.name in ['mine']:
            states_dict=self.organize_states(states)
            # if len(states_dict)>=2:
            #     print('Check when two or more genesis states are generated (guider.py)')
            self.ftn_search_strategy.update_states(states_dict)
            self.ftn_search_strategy.state_key_assigned_at_last =list(states_dict.keys())[0]



