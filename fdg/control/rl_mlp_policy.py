from copy import deepcopy

import requests

import fdg.global_config
import rl
from fdg.control.ftn_search_strategy import FunctionSearchStrategy
from fdg.control.function_assignment import FunctionAssignment
from fdg.fwrg_manager import FWRG_manager
from fdg.utils import get_ftn_seq_from_key_1
from rl.config import rl_cur_parameters, top_k

from rl.seq_generation import wrapper


class RL_MLP_Policy(FunctionSearchStrategy):
    def __init__(self):
        self.queue = []
        self.sequences = []
        super().__init__('rl_mlp_policy')


    def initialize(self, flag_one_start_function:bool, preprocess_timeout:bool, preprocess_coverage:float, all_functions:list, fwrg_manager:FWRG_manager,start_functions:list, target_functions:list, solidity_name:str, contract_name:str,solc_version:str=""):
        self.flag_one_start_function=flag_one_start_function
        self.preprocess_timeout = preprocess_timeout
        self.preprocess_coverage = preprocess_coverage

        self.all_functions=all_functions
        self.functionAssignment = FunctionAssignment(all_functions,
                                                     fwrg_manager)
        #
        self.start_functions=start_functions
        self.target_functions=target_functions
        self.target_functions_no_seq=[]
        self.solidity_name=solidity_name
        self.contract_name=contract_name
        self.solc_version=solc_version

        self.flag_rl_mlp_policy=True
        self.request_sequences() # obtain sequences



    def request_sequences_0(self):
        # Define the JSON data to send in the POST request
        data = {"solidity_name": f"{self.solidity_name}",
                "contract_name": f"{self.contract_name}",
                "top_k":f'{rl.config.top_k}',
                "flag_whole":False,
                "dataset":'small_dataset',
                }
        print(f'Request data:{data}')

        # Send a POST request to the server
        model_service_url = "http://127.0.0.1:5000/generate_simple"
        response = requests.post(model_service_url, json=data)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            result = response.json()
            print(f'Response data:{result["result"]}')

            for k, v in result['result'].items():
                print(f'{k}')
                for seq in v:
                    self.sequences.append(seq)
                    print(f'\t{seq}')
        else:
            print("Error:", response.status_code)
            self.flag_rl_mlp_policy=False

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
                    if target not in ['symbol()','name()','decimals()']:
                        self.target_functions_no_seq.append(target)
        else:
            print("Error:", "no sequences are generated")
            self.flag_rl_mlp_policy = False



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
        if len(states_dict)>0:
            for key, states in states_dict.items():

                if key not in self.world_states.keys():
                    self.world_states[key]=deepcopy(states)
                else:
                    self.world_states[key]+=deepcopy(states)
                self.queue.append(key)

        while True:
            # --------------
            # case 1
            # assign the only state
            if self.flag_one_start_function:
                self.flag_one_start_function = False  # only consider once
                state_key = self.queue.pop(0)
                assign_functions = self.functionAssignment.assign_all_functions()
                return {state_key: assign_functions}, True

            if len(self.queue)==0: return {},False
            state_key=self.queue.pop(0)
            seq=get_ftn_seq_from_key_1(state_key)
            functions=[]
            for seq_ in self.sequences:
                if len(seq)==len(seq_):continue
                if len(seq)<len(seq_):
                    flag_add=True
                    for i in range(len(seq)):
                        """
                        a speical case
                        0x7f0C14F2F72ca782Eea2835B9f63d3833B6669Ab.sol	0.4.24	UFragmentsPolicy
initialize(address,address,uint256),initialize(address) (se) vs initialize(address,UFragments,uint256) (generated)
                        """
                        if seq[i]!=seq_[i]:
                            pure_name=seq[i].split(f'(') if '(' in seq[i] else seq[i]
                            if seq[i][0:len(pure_name)]!=seq_[i][0:len(pure_name)]:
                                flag_add=False
                                break
                    if flag_add:
                        if seq_[len(seq)] not in functions:
                            functions.append(seq_[len(seq)])
            if len(functions)>0:
                dk_func=[ftn for ftn,_ in dk_functions]
                left_target=[ftn for ftn in self.target_functions_no_seq if ftn in dk_func]
                return {state_key:functions+left_target},True
            else:
                if rl.config.MIX in ['d']:
                    functions_1=self.random_policy(state_key,dk_functions)

                    dk_func = [ftn for ftn, _ in dk_functions]
                    left_target = [ftn for ftn in self.target_functions_no_seq
                                   if ftn in dk_func]

                    functions_1=list(set(functions_1+left_target))
                    functions_1 = [ftn for ftn in functions_1 if
                                 ftn not in ['symbol()', 'name()',
                                             'decimals()']]
                else:
                    dk_func = [ftn for ftn, _ in dk_functions]
                    functions_1 = [ftn for ftn in self.target_functions_no_seq
                                   if ftn in dk_func]
                if len(functions_1)>0:
                    return {state_key: functions_1}, True

    def random_policy(self,state_key:str,dk_functions:list):
        seq = get_ftn_seq_from_key_1(state_key)
        random_selected = self.random_select_functions()
        targets = [dk for dk, _ in dk_functions]
        if len(seq)==1:
            return list(set(random_selected+targets))
        elif len(seq)==2:
            return list(set(random_selected+targets))
        else:
            random_targets = self.random_select_targets(targets)
            return list(set(random_targets + random_selected))

    def random_select_functions(self):
        percent_of_functions=2
        if self.preprocess_timeout or fdg.global_config.preprocessing_exception:
            if self.preprocess_coverage<50:
                percent_of_functions= 7
            elif self.preprocess_coverage<80:
                percent_of_functions= 5
            elif self.preprocess_coverage<90:
                percent_of_functions= 3
            else:
                percent_of_functions= 2
        random_selected_functions = self.functionAssignment.select_functions_randomly(
            percent_of_functions)
        return random_selected_functions

    def random_select_targets(self,targets:list):
        percent_of_functions=2
        if self.preprocess_timeout or fdg.global_config.preprocessing_exception:
            if self.preprocess_coverage<50:
                percent_of_functions= 7
            elif self.preprocess_coverage<80:
                percent_of_functions= 5
            elif self.preprocess_coverage<90:
                percent_of_functions= 3
            else:
                percent_of_functions= 2
        random_selected_functions = self.functionAssignment.select_functions_randomly_1( targets,percent_of_functions)
        return random_selected_functions
