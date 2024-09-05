import os
import sys


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_path=f'{get_project_root()}/'
sys.path.append(project_path)
# print(f'project path: {project_path}')

# project_path='C:\\Users\\18178\\PycharmProjects\\smartExecutor\\'
# project_path="./"
small_dataset_json_file="rl_small_dataset_contracts_data_for_env_construction_8_19_2024_8_in_integer.json"

output_path=project_path+"temp_results/"
contract_json_file_path=project_path+"rl/contract_env_data/"
model_path=project_path+"rl/models/"
contract_solidity_path=""
seq_len_limit=4

env_name='ContractEnv_55'
top_k=2
MIX="a"
NUM_episode=5

max_svar_value=5740
max_func_value_element= 70



# recent: after August 19th, 2024
# consider all Reads and Writes
rl_parameters={
    "sGuard": {
        "contract_data_for_env_construction_json_file_name": "rl_sGuard_contracts_data_for_env_construction_8_19_2024_16_in_integer.json",
        "contract_rw_data_json_file_name": 'rl_sGuard_contracts_data_for_env_construction_8_19_2024_16.json',
        "dataset": "sGuard",
        "NUM_state_var": 16,
        "NUM_actions": 51,
        "max_svar_value": 5740,
        "max_func_value_element": 70,
        "ENV_NAME": "ContractEnv_55",
        "NUM_episode": 5,
        "model_folder": 'ContractEnv_55_model7_sGuard_16_1724508857',
        "model_file_name_prefix": "414180000",
        "flag_model": 7,
        "goal_indicator": 2,
        "flag_maskable": False,
        "mode": 'predict',
        "flag_model_whole": True,
    },

    "small_dataset":{
        "contract_data_for_env_construction_json_file_name":"rl_small_dataset_contracts_data_for_env_construction_8_19_2024_8_in_integer.json",
        "contract_rw_data_json_file_name":'rl_small_dataset_contracts_data_for_env_construction_8_19_2024_8.json',
        "dataset":"small_dataset",
        "NUM_state_var":8,
        "NUM_actions":20,
        "max_svar_value":80,
        "max_func_value_element":30,
        "ENV_NAME":"ContractEnv_55",
        "NUM_episode":5,
        "model_folder":'ContractEnv_55_model7_small_dataset_8_1724161007',
        "model_file_name_prefix":"43100000",
        "flag_model":7,
        "goal_indicator":2,
        "flag_maskable":False,
        "mode":'predict',
        "flag_model_whole":True,
    },
    "HoloToken": {
        "contract_data_for_env_construction_json_file_name":"rl_small_dataset_contracts_data_for_env_construction_8_19_2024_8_in_integer.json",
        "contract_rw_data_json_file_name":'rl_small_dataset_contracts_data_for_env_construction_8_19_2024_8.json',
        "dataset": "small_dataset",
        "NUM_state_var": 8,
        "NUM_actions": 20,
        "max_svar_value": 80,
        "max_func_value_element": 30,
        "ENV_NAME": "ContractEnv_55",
        "NUM_episode": 5,
        "model_folder": 'ContractEnv_55_model7_small_dataset_8_20_1724125326_HoloToken',
        "model_file_name_prefix": "17380000",
        "flag_model": 7,
        "goal_indicator": 2,
        "flag_maskable": False,
        "mode": 'test',
        "flag_model_whole": True,
    }

}

# # old
# rl_parameters={
#     "sGuard": {
#         "contract_data_for_env_construction_json_file_name": "rl_sGuard_contracts_data_for_env_construction_5_15_2024_16_in_integer.json",
#         "contract_rw_data_json_file_name": 'rl_sGuard_contracts_data_for_env_construction_5_15_2024_16.json',
#         "dataset": "sGuard",
#         "NUM_state_var": 16,
#         "NUM_actions": 51,
#         "max_svar_value": 5740,
#         "max_func_value_element": 70,
#         "ENV_NAME": "ContractEnv_55",
#         "NUM_episode": 5,
#         "model_folder": 'ContractEnv_55_model7_sGuard_16_1723696146',
#         "model_file_name_prefix": "105650000",
#         "flag_model": 7,
#         "goal_indicator": 2,
#         "flag_maskable": False,
#         "mode": 'predict',
#         "flag_model_whole": True,
#     },
#
#     "small_dataset":{
#         "contract_data_for_env_construction_json_file_name":"rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8_in_integer.json",
#         "contract_rw_data_json_file_name":'rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8.json',
#         "dataset":"small_dataset",
#         "NUM_state_var":8,
#         "NUM_actions":20,
#         "max_svar_value":80,
#         "max_func_value_element":30,
#         "ENV_NAME":"ContractEnv_55",
#         "NUM_episode":5,
#         "model_folder":'ContractEnv_55_model7_small_dataset_8_1723673782',
#         "model_file_name_prefix":"10300000",
#         "flag_model":7,
#         "goal_indicator":2,
#         "flag_maskable":False,
#         "mode":'predict',
#         "flag_model_whole":True,
#     },
#     "HoloToken": {
#         "contract_data_for_env_construction_json_file_name": "rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8_in_integer.json",
#         "contract_rw_data_json_file_name": 'rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8.json',
#         "dataset": "small_dataset",
#         "NUM_state_var": 8,
#         "NUM_actions": 20,
#         "max_svar_value": 80,
#         "max_func_value_element": 30,
#         "ENV_NAME": "ContractEnv_55",
#         "NUM_episode": 5,
#         "model_folder": 'ContractEnv_55_model7_small_dataset_8_20_1723664007_HoloToken',
#         "model_file_name_prefix": "4500000",
#         "flag_model": 7,
#         "goal_indicator": 2,
#         "flag_maskable": False,
#         "mode": 'predict',
#         "flag_model_whole": True,
#     }
#
# }
#

rl_cur_parameters={
        "contract_data_for_env_construction_json_file_name":None,
        "contract_rw_data_json_file_name":None,
        "dataset":None,
        "NUM_state_var":None,
        "NUM_actions":None,
        "max_svar_value":None,
        "max_func_value_element":None,
        "ENV_NAME":None,
        "NUM_episode":None,
        "model_folder":None,
        "model_file_name_prefix":None,
        "flag_model":None,
        "goal_indicator":None,
        "flag_maskable":None,
        "mode":None,
        "flag_model_whole":None,
        "top_k":None,
    }

