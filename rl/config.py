import os
import sys


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_path=f'{get_project_root()}/'
sys.path.append(project_path)
# print(f'project path: {project_path}')

# project_path='C:\\Users\\18178\\PycharmProjects\\smartExecutor\\'
# project_path="./"
small_dataset_json_file="rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8.json"

output_path=project_path+"temp_results/"
contract_json_file_path=project_path+"rl/contract_env_data/"
model_path=project_path+"rl/models/"
contract_solidity_path=""
seq_len_limit=4

env_name='ContractEnv_33'
top_k=2
MIX="a"

model_groups={
    "group_1": ["ContractEnv_33_group_1_1718941700", "14430000"],
    "group_2": ["ContractEnv_33_group_2_1718941700", "14680000"],
    "group_3": ["ContractEnv_33_group_3_1718941700", "14700000"],
    "group_4": ["ContractEnv_33_group_4_1718941700", "14770000"],
    "group_5": ["ContractEnv_33_group_5_1718941700", "14680000"],
    "group_6": ["ContractEnv_33_group_6_1718941700", "14300000"],
    "group_7": ["ContractEnv_33_group_7_1718941700", "14480000"],
    "group_8": ["ContractEnv_33_group_8_1718941700", "14470000"],
    "group_9": ["ContractEnv_33_group_9_1718941700", "14770000"],
    "group_10": ["ContractEnv_33_group_10_1718941700", "14570000"],
    "group_11": ["ContractEnv_33_group_11_1718941700", "14690000"],
    "group_12": ["ContractEnv_33_group_12_1718941700", "14170000"],
    "group_13": ["ContractEnv_33_group_13_1718941700", "12890000"],
}

rl_parameters={
    "sGuard": {
        "contract_data_for_env_construction_json_file_name": "rl_sGuard_contracts_data_for_env_5_26_24_in_integer.json",
        "contract_rw_data_json_file_name": 'rl_sGuard_contracts_data_for_env_construction_5_26_24.json',
        "dataset": "sGuard",
        "NUM_state_var": 24,
        "NUM_actions": 51,
        "max_svar_value": 5740,
        "max_func_value_element": 70,
        "ENV_NAME": "ContractEnv_33",
        "NUM_episode": 5,
        "model_folder": 'ContractEnv_33_model6_sGuard_whole_1718462078',
        "model_file_name_prefix": "714650000",
        "flag_model": 6,
        "goal_indicator": 2,
        "flag_maskable": True,
        "mode": 'predict',
        "flag_model_whole": False,
    },

    "small_dataset":{
        "contract_data_for_env_construction_json_file_name":"rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8_in_integer.json",
        "contract_rw_data_json_file_name":'rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8.json',
        "dataset":"small_dataset",
        "NUM_state_var":8,
        "NUM_actions":20,
        "max_svar_value":80,
        "max_func_value_element":30,
        "ENV_NAME":"ContractEnv_33",
        "NUM_episode":5,
        "model_folder":'ContractEnv_33_model6_small_dataset_8_20_1720651760',
        "model_file_name_prefix":"3650000",
        "flag_model":6,
        "goal_indicator":2,
        "flag_maskable":True,
        "mode":'predict',
        "flag_model_whole":True,
    },
    "HoloToken": {
        "contract_data_for_env_construction_json_file_name": "rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8_in_integer.json",
        "contract_rw_data_json_file_name": 'rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8.json',
        "dataset": "small_dataset",
        "NUM_state_var": 8,
        "NUM_actions": 20,
        "max_svar_value": 80,
        "max_func_value_element": 30,
        "ENV_NAME": "ContractEnv_33",
        "NUM_episode": 5,
        "model_folder": 'ContractEnv_33_model6_small_dataset_8_20_1720645842_HoloToken',
        "model_file_name_prefix": "1670000",
        "flag_model": 6,
        "goal_indicator": 2,
        "flag_maskable": True,
        "mode": 'predict',
        "flag_model_whole": True,
    },

    "sGuard_env55":{
        "contract_data_for_env_construction_json_file_name": "rl_sGuard_contracts_data_for_env_5_26_24_in_integer.json",
        "contract_rw_data_json_file_name": 'rl_sGuard_contracts_data_for_env_construction_5_26_24.json',
        "dataset": "sGuard",
        "NUM_state_var": 24,
        "NUM_actions": 51,
        "max_svar_value": 5740,
        "max_func_value_element": 70,
        "ENV_NAME": "ContractEnv_55",
        "NUM_episode": 5,
        "model_folder": 'ContractEnv_55_model7_sGuard_whole',
        "model_file_name_prefix": "53800000",
        "flag_model": 7,
        "goal_indicator": 2,
        "flag_maskable": False,
        "mode": 'predict',
        "flag_model_whole": True,
    },
}

# rl_cur_parameters={
#         "contract_data_for_env_construction_json_file_name":"rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8_in_integer.json",
#         "contract_rw_data_json_file_name":'rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8.json',
#         "dataset":"small_dataset",
#         "NUM_state_var":8,
#         "NUM_actions":20,
#         "max_svar_value":80,
#         "max_func_value_element":30,
#         "ENV_NAME":"ContractEnv_33",
#         "NUM_episode":5,
#         "model_folder":'ContractEnv_33_model6_small_dataset_8_20_1720651760',
#         "model_file_name_prefix":"3650000",
#         "flag_model":6,
#         "goal_indicator":2,
#         "flag_maskable":True,
#         "mode":'predict',
#         "flag_model_whole":True,
#         "top_k":2,
#     }

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


# # ==========================================
# # July 2nd, 2024
# # for sGuard contracts
# # try a model trained with ContractEnv_33 on all the training contracts
#
# contract_data_for_env_construction_json_file_name= "rl_sGuard_contracts_data_for_env_5_26_24_in_integer.json"
# contract_rw_data_json_file_name= 'rl_sGuard_contracts_data_for_env_construction_5_26_24.json'
# dataset="sGuard"
# NUM_state_var=24
# NUM_actions=51
# max_svar_value =5740
# max_func_value_element = 70
# ENV_NAME="ContractEnv_33"
# NUM_episode=5#
# model_folder='ContractEnv_33_model6_sGuard_whole_1718462078'
# # model_file_name_prefix='505860000'
# model_file_name_prefix='714650000'
# flag_model=6
# goal_indicator=2
# flag_maskable=True
# mode='predict'
# flag_model_whole=False




# # ==========================================
# # July 5th, 2024
# # for small dataset
# contract_data_for_env_construction_json_file_name="rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8_in_integer.json"
# contract_rw_data_json_file_name= 'rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8.json'
# dataset="small_dataset"
# NUM_state_var=8
# NUM_actions=20
# max_svar_value = 80
# max_func_value_element = 30
# ENV_NAME="ContractEnv_33"
# NUM_episode=5
# model_folder='ContractEnv_33_model6_small_dataset_1720129090'
# model_file_name_prefix="24500000"
#
# model_folder="ContractEnv_33_model6_small_dataset_8_20_1720393951"
# model_file_name_prefix="8480000"
#
# #--------- July 10th ---
# model_folder="ContractEnv_33_model6_small_dataset_8_20_1720651760"
# model_file_name_prefix="3650000"
#
# flag_model=6
# goal_indicator=2
# flag_maskable=True
# mode='predict'
# flag_model_whole=True




# # ==========================================
# # July 7th, 2024
# # for a single contract HoloToken
# contract_data_for_env_construction_json_file_name="rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8_in_integer.json"
# contract_rw_data_json_file_name= 'rl_small_dataset_contracts_data_for_env_construction_7_4_2024_8.json'
# dataset="small_dataset"
# NUM_state_var=8
# NUM_actions=20
# max_svar_value = 80
# max_func_value_element = 30
# ENV_NAME="ContractEnv_33"
# NUM_episode=5
# model_folder='ContractEnv_33_model6_small_dataset_8_20_1720381850_HoloToken'
# model_file_name_prefix="4150000"
#
# # --------- July 10th ---
# model_folder="ContractEnv_33_model6_small_dataset_8_20_1720645842_HoloToken"
# model_file_name_prefix="1670000"
#
# flag_model=6
# goal_indicator=2
# flag_maskable=True
# mode='predict'
# flag_model_whole=False
