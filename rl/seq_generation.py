from flask import Flask, request, jsonify
import rl
from rl.config import model_path

from rl.generation.gen_utils import get_env, get_top_k_sequences, \
    retrieve_model, find_the_model_for_a_contract
from rl.generation.prediction import my_model_prediction


app = Flask(__name__)

class SeqGeneration:
    def __init__(self):
        pass
    def remove_contract_name_from_function_name(self, sequences:list,contract_name:str):
        temp_sequences= [ [ func.split(f'{contract_name}.')[-1] if f'{contract_name}.' in func else func for func in seq] for seq in sequences]
        return [[func.split(".")[-1] if "." in func else func for func in seq] for seq in temp_sequences]
    def generate_simple(self, data):

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
        results={}
        env=get_env(solidity_name,contract_name,solc_version=solc_version,start_functions=start_functions,target_functions=target_functions)
        if env is None:
            print(f'Fail to construct environment (possible reasons: the contract is an unseen contract, fail to compile the contract)')
            return {}
        # env.mode='test'
        if rl.config.rl_cur_parameters["dataset"]=='small_dataset':
            model_dir = f'{model_path}{rl.config.rl_cur_parameters["model_folder"]}/'
            model_file_prefix =rl.config.rl_cur_parameters["model_file_name_prefix"]
            print(f'use a general model')
        elif rl.config.rl_cur_parameters["dataset"]=='sGuard':
            model_dir =""
            model_file_prefix = ""
            model_dir,model_file_prefix=find_the_model_for_a_contract(solidity_name,contract_name,env,data["flag_whole"])
            if len(model_dir)==0:
                model_dir = f'{model_path}{rl.config.rl_cur_parameters["model_folder"]}/'
                model_file_prefix =rl.config.rl_cur_parameters["model_file_name_prefix"]
                print(f'use a general model')

        model=retrieve_model(model_dir, model_file_prefix, flag_maskable=rl.config.rl_cur_parameters["flag_maskable"] )
        # if env.env_name in ["ContractEnv_55", "ContractEnv_33"]:
        #     print(f'\n==== {env.solidity_name}:{env.contract_name} ====')
        #     for key, info in env.conEnvData_wsa["function_data"].items():
        #         print(f'{key}:{info["name"]}')

        for target in env.conEnvData_wsa["target_functions_in_integer"]:
            env.goal = target

            # print(f'target : {target} : {env.conEnvData_wsa["function_data"][str(target)]["name"]}')
            predict_results=my_model_prediction(model, env, rl.config.rl_cur_parameters["NUM_episode"],flag_maskable=rl.config.rl_cur_parameters["flag_maskable"])
            select_sequences=get_top_k_sequences(predict_results,top_k=top_k)
            clean_sequence=self.remove_contract_name_from_function_name(select_sequences,contract_name)
            results[env.conEnvData_wsa["function_data"][str(target)]["name"]]=clean_sequence
        return results

wrapper = SeqGeneration()


@app.route('/generate_simple', methods=['POST'])
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
    evaluate_compute_simple()

