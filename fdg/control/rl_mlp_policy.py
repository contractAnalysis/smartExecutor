from copy import deepcopy

import requests

import fdg.global_config
from fdg.control.ftn_search_strategy import FunctionSearchStrategy
from fdg.control.function_assignment import FunctionAssignment
from fdg.fwrg_manager import FWRG_manager
from fdg.utils import get_ftn_seq_from_key_1
from rl.config import dataset, flag_model_whole, top_k
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
        self.solidity_name=solidity_name
        self.contract_name=contract_name
        self.solc_version=solc_version

        self.flag_rl_mlp_policy=True
        self.request_sequences() # obtain sequences



    def request_sequences_0(self):
        # Define the JSON data to send in the POST request
        data = {"solidity_name": f"{self.solidity_name}",
                "contract_name": f"{self.contract_name}",
                "top_k":f'{fdg.global_config.top_k}',
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
                "top_k": f'{top_k}',
                "flag_whole": flag_model_whole,
                "dataset": dataset,
                }
        # print(f'Request data:{data}')

        result = wrapper.generate_simple(data)
        if len(result)>0:
            for k, v in result.items():
                print(f'{k}')
                for seq in v:
                    self.sequences.append(seq)
                    print(f'\t{seq}')

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

