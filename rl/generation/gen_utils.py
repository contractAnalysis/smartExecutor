from sb3_contrib import MaskablePPO
from stable_baselines3 import PPO
import random

import rl
from rl.contract_env_data.contract_info import sGuard_test_1, \
    sGuard_contract_info_into_groups, sGuard_train_1

from rl.env_data_preparation.contract_env_data_preparation import collect_env_data

from rl.envs.contract_env_discrete_action_space_03_3 import  ContractEnv_33
from rl.envs.contract_env_discrete_action_space_05_5 import ContractEnv_55

from rl.utils import  get_key_from_list, load_a_json_file, euclidean_distance

from rl.config import rl_cur_parameters,contract_json_file_path,model_path,model_groups



def get_env(solidity_name: str, contract_name: str, solc_version:str="0.4.25", start_functions:list=[],target_functions:list=[]):


    conDynamics, conEnvData_wsa = collect_env_data(solidity_name,contract_name,
                                                   solc_version=solc_version, start_functions=start_functions,target_functions=target_functions)
    if len(conEnvData_wsa)==0:
        return None

    ENV_NAME = rl.config.rl_cur_parameters["ENV_NAME"]
    flag_model = rl.config.rl_cur_parameters["flag_model"]
    goal_indicator = rl.config.rl_cur_parameters["goal_indicator"]
    NUM_actions = rl.config.rl_cur_parameters["NUM_actions"]
    NUM_state_var = rl.config.rl_cur_parameters["NUM_state_var"]
    mode = rl.config.rl_cur_parameters["mode"]


    if ENV_NAME in ["ContractEnv_33"]:
        env = ContractEnv_33(conDynamics, conEnvData_wsa, flag_model=flag_model,goal_indicator=goal_indicator,
                             mode=mode,action_size=NUM_actions,num_state_variable=NUM_state_var)
    elif ENV_NAME in ["ContractEnv_55"]:
        env = ContractEnv_55(conDynamics, conEnvData_wsa, flag_model=flag_model,
                             goal_indicator=goal_indicator,
                             mode=mode)
    env.contract_name = contract_name
    env.solidity_name = solidity_name
    return env

def retrieve_model(models_dir:str, model_file_prefix:str, flag_maskable:bool=True):

    flag_maskable = rl.config.rl_cur_parameters["flag_maskable"]
    if '.zip' in model_file_prefix:
        model_file_prefix=model_file_prefix.rstrip(".zip")
    if flag_maskable:
        model = MaskablePPO.load(f"{models_dir}{model_file_prefix}.zip")
    else:
        model = PPO.load(f"{models_dir}{model_file_prefix}.zip")
    return model


def find_the_model_for_a_contract(solidty_name:str, contract_name, env=None, flag_whole:bool=True):
    model_folder = rl.config.rl_cur_parameters["model_folder"]
    model_file_name_prefix = rl.config.rl_cur_parameters[
        "model_file_name_prefix"]
    if flag_whole:
        print(f'use a general model')
        return f'{model_path}{model_folder}/',model_file_name_prefix

    contract_data_for_env_construction_json_file_name = \
    rl.config.rl_cur_parameters[
        "contract_data_for_env_construction_json_file_name"]

    sGuard_contract_data = load_a_json_file(
        contract_json_file_path + contract_data_for_env_construction_json_file_name)

    cur_con_key=f'{solidty_name}{contract_name}'
    cur_state_variables=sGuard_contract_data[cur_con_key]['state_variables_selected'] if cur_con_key in sGuard_contract_data.keys() else []
    if len(cur_state_variables)>0:
        # either in the training or testing set
        cur_svar_key=get_key_from_list(cur_state_variables)
        if not cur_con_key in sGuard_train_1:
            for group_key, con_list in sGuard_contract_info_into_groups.items():
                for con_key in con_list:
                    con_env_data = sGuard_contract_data[
                        con_key] if con_key in sGuard_contract_data.keys() else {}
                    if len(con_env_data) > 0:
                        svar_key = get_key_from_list(
                            con_env_data['state_variables_selected'])
                        if cur_svar_key == svar_key:
                            model_dir = f'{model_path}{model_groups[group_key][0]}/'
                            model_file_prefix = model_groups[group_key][1]
                            print(f'use model from: {group_key} (testing)')
                            return model_dir,model_file_prefix
        else:
            # find the model for a contract from the training set
            for group_key, con_list in sGuard_contract_info_into_groups.items():
                if cur_con_key in con_list:
                    model_dir = f'{model_path}{model_groups[group_key][0]}/'
                    model_file_prefix = model_groups[group_key][1]
                    print(f'use model from: {group_key} (training)')
                    return model_dir,model_file_prefix

    else:
        # find the model for a contract not in the training or testing sets
        # case 1: not new but unseen contract, can be mapped to a group
        cur_state_variables=env.conEnvData_wsa['state_variables_selected']
        if len(cur_state_variables)==0: return "",""
        cur_svar_key=get_key_from_list(cur_state_variables)
        for group_key, con_list in sGuard_contract_info_into_groups.items():
            for con_key in con_list:
                con_env_data = sGuard_contract_data[
                    con_key] if con_key in sGuard_contract_data.keys() else {}
                if len(con_env_data) > 0:
                    svar_key = get_key_from_list(
                        con_env_data['state_variables_selected'])
                    if cur_svar_key == svar_key:
                        model_dir = f'{model_path}{model_groups[group_key][0]}/'
                        model_file_prefix = model_groups[group_key][1]
                        print(f'use model from: {group_key} (unseen,not new)')
                        return model_dir,model_file_prefix
        # case 2: new and similar contract, can be closely mapped to a group
        for group_key, con_list in sGuard_contract_info_into_groups.items():
            for con_key in con_list:
                con_env_data = sGuard_contract_data[
                    con_key] if con_key in sGuard_contract_data.keys() else {}
                if len(con_env_data) > 0:
                    svar = con_env_data['state_variables_selected']
                    distance=euclidean_distance(cur_state_variables, svar)
                    if distance<100:
                        model_dir = f'{model_path}{model_groups[group_key][0]}/'
                        model_file_prefix = model_groups[group_key][1]
                        print(f'use model from: {group_key} (unseen,new)')
                        return model_dir, model_file_prefix

    return "",""


def remove_repeated_sequences(sequences):
    seen = set()
    unique_sequences = []
    for seq in sequences:
        # Convert the sequence to a tuple to make it hashable
        seq_tuple = tuple(seq)
        if seq_tuple not in seen:
            seen.add(seq_tuple)
            unique_sequences.append(seq)
    return unique_sequences

def get_top_k_sequences(sequences:list, top_k:int=2):
    unique_sequences=remove_repeated_sequences(sequences)
    if len(unique_sequences)>top_k:
        return random.sample(unique_sequences,top_k)
    else:
        return unique_sequences
