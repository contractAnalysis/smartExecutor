import time

from flask import Flask, request, jsonify
import rl
from rl.config import model_path

from rl.generation.gen_utils import get_env, get_top_k_sequences, \
    retrieve_model, refine_sequences
from rl.generation.prediction import my_model_prediction







class SeqGeneration:
    def __init__(self):
        pass
    def remove_contract_name_from_function_name(self, sequences:list,contract_name:str):
        temp_sequences= [ [ func.split(f'{contract_name}.')[-1] if f'{contract_name}.' in func else func for func in seq] for seq in sequences]
        return [[func.split(".")[-1] if "." in func else func for func in seq] for seq in temp_sequences]

    def generate_simple(self, data):
        seconds_start = time.time()
        solidity_name=data['solidity_name']
        contract_name=data['contract_name']

        if 'solc_version' in data.keys():
            solc_version=data['solc_version']
        else:
            solc_version='0.4.25'
        if 'target_functions' in data.keys():
            target_functions = data['target_functions']
        else:
            target_functions=[]
        if 'start_functions' in data.keys():
            start_functions = data['start_functions']
        else:
            start_functions = []

        top_k=data['top_k']
        if isinstance(top_k,str):
            top_k=int(top_k)

        env=get_env(solidity_name,contract_name,solc_version=solc_version,start_functions=start_functions,target_functions=target_functions)
        if env is None:
            print(f'Fail to construct environment (possible reasons: the contract is an unseen contract, fail to compile the contract)')
            return {}

        model_paths = []
        if rl.config.rl_cur_parameters["dataset"]== 'small_dataset':
            model_dir = f'{model_path}{rl.config.rl_cur_parameters["model_folder"]}/'
            model_file_prefix = rl.config.rl_cur_parameters["model_file_name_prefix"]
            model_paths.append(f"{model_dir}{model_file_prefix}.zip")
        elif rl.config.rl_cur_parameters["dataset"] == 'sGuard':
            model_dir = f'{model_path}{rl.config.rl_cur_parameters["model_folder"]}/'
            model_file_prefix = rl.config.rl_cur_parameters["model_file_name_prefix"]
            model_paths.append(f"{model_dir}{model_file_prefix}.zip")

        results={}
        for target in env.conEnvData_wsa["target_functions_in_integer"]:
            env.goal = target
            goal_name=env.conEnvData_wsa["function_data"][str(target)]["name"]
            results[goal_name]=[]

        for m_path in model_paths:
            model=retrieve_model(m_path)
            for target in env.conEnvData_wsa["target_functions_in_integer"]:
                env.goal = target
                goal_name = env.conEnvData_wsa["function_data"][str(target)][
                    "name"]
                # print(f'target : {target} : {goal_name}')
                predict_results=my_model_prediction(model, env,rl.config.NUM_episode,flag_maskable=rl.config.rl_cur_parameters["flag_maskable"])
                clean_sequence=self.remove_contract_name_from_function_name(predict_results,contract_name)
                results[goal_name] += clean_sequence

        for k in results.keys():
            results[k]=refine_sequences(get_top_k_sequences(results[k],top_k=top_k), k)
        seconds_end = time.time()
        print(f'#@generation_time')
        print(f'generation time(s):{seconds_end - seconds_start}')
        return results

wrapper = SeqGeneration()



def generate_simple():
    # Get data from the request
    data = request.json

    # Perform computation using the wrapper
    result = wrapper.generate_simple(data)

    # Return the result
    return jsonify({'result': result})

def evaluate_compute_simple():

    #=======================
    # for small dataset
    data = {"solidity_name": "HoloToken.sol",
            "contract_name": "HoloToken",
            "solc_version":"0.4.18",
            "start_functions":['setDestroyer', 'setMinter', 'transferOwnership', 'decreaseApproval', 'increaseApproval'],
            "target_functions":['transferFrom', 'mint', 'burn', 'transfer', 'approve', 'finishMinting', 'decreaseApproval'],
            'top_k':2,
            "flag_whole":False}

    # data = {"solidity_name": "HoloToken_test_01.sol",
    #         "contract_name": "HoloToken_test_01",
    #         "solc_version": "0.4.18",
    #         "start_functions": [],
    #         "target_functions": [],
    #         'top_k': 2,
    #         "flag_whole": False}

    # =======================
    # for sGuard dataset

    # data = {"solidity_name": "0x2600004fd1585f7270756ddc88ad9cfa10dd0428.sol",
    #         "contract_name": "GemJoin5",
    #         "solc_version":"0.5.12",
    #         "start_functions":['deny(address)','rely(address)','cage()','exit(address,uint256)','join(address,uint256)'],
    #         "target_functions":['exit(address,uint256)','join(address,uint256)'],
    #         'top_k':2,
    #         "flag_whole":True}



    # data = {"solidity_name": "0x2a7e7718b755f9868e6b64dd18c6886707dd9c10.sol",
    #         "contract_name": "DharmaAccountRecoveryManagerV2Staging",
    #         "solc_version":" ",
    #         "start_functions":[],
    #         "target_functions":[],
    #         'top_k':2,
    #         "flag_whole":False}


    # data = {"solidity_name": "0x08411AfEb66c909F57d84FdcC5dD6DF5AB7062BC.sol",
    #         "contract_name": "BTCFeed",
    #         "solc_version":" ",
    #         "start_functions":[],
    #         "target_functions":[],
    #         'top_k':2,
    #         "flag_whole":True}


    # data = {"solidity_name": "0x7a58da7c0568557ec65cd53c0dbe5b134a022a14.sol",
    #         "contract_name": "ZEBELLION",
    #         "solc_version":" ",
    #         "start_functions":[],
    #         "target_functions":[],
    #         'top_k':2,
    #         "flag_whole":True}
    result = wrapper.generate_simple(data)
    for k,v in result.items():
        print(f'{k}')
        for item in v:
            print(f'\t{item}')

if __name__ == '__main__':
    # app.run(debug=True)
    rl.config.rl_cur_parameters=rl.config.rl_parameters['HoloToken']
    evaluate_compute_simple()



