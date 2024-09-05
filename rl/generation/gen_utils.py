from sb3_contrib import MaskablePPO
from stable_baselines3 import PPO


import rl
from rl.env_data_preparation.contract_env_data_preparation import collect_env_data
from rl.envs.contract_env_discrete_action_space_05_5 import ContractEnv_55

from rl.utils import get_key_from_list, get_seq_from_key





def get_env(solidity_name: str, contract_name: str, solc_version:str="0.4.25", start_functions:list=[],target_functions:list=[]):


    conDynamics, conEnvData_wsa = collect_env_data(solidity_name,contract_name,
                                                   solc_version=solc_version, start_functions=start_functions,target_functions=target_functions)
    if len(conEnvData_wsa)==0:
        return None

    ENV_NAME = rl.config.rl_cur_parameters["ENV_NAME"]
    flag_model = rl.config.rl_cur_parameters["flag_model"]
    goal_indicator = rl.config.rl_cur_parameters["goal_indicator"]

    NUM_state_var = rl.config.rl_cur_parameters["NUM_state_var"]
    mode = rl.config.rl_cur_parameters["mode"]
    max_svar_value = rl.config.rl_cur_parameters["max_svar_value"]
    max_func_value_element = rl.config.rl_cur_parameters["max_func_value_element"]


    if ENV_NAME in ["ContractEnv_55"]:
        env = ContractEnv_55(conDynamics, conEnvData_wsa, flag_model=flag_model,
                             goal_indicator=goal_indicator,num_state_svar=NUM_state_var,
                             mode=mode,max_svar_value=max_svar_value,max_func_value_element=max_func_value_element)
    else:
        return None
    env.contract_name = contract_name
    env.solidity_name = solidity_name
    return env

def retrieve_model(model_path:str):

    flag_maskable = rl.config.rl_cur_parameters["flag_maskable"]
    if flag_maskable:
        model = MaskablePPO.load(model_path)
    else:
        model = PPO.load(model_path)
    return model


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
    seq_counts=[[get_key_from_list(seq),sequences.count(seq)] for seq in unique_sequences]
    seq_counts.sort(key=lambda x:x[1], reverse=True)
    unique_sequences.sort(key=len,reverse=False)
    if len(seq_counts)>top_k:
        if top_k>=2:
            if len(get_seq_from_key(seq_counts[0][0]))==4 and len(get_seq_from_key(seq_counts[1][0]))==4:
                for key, _ in seq_counts[top_k:]:
                    if len(get_seq_from_key(key))==2:
                        return [get_seq_from_key(key) for key, _ in seq_counts[0:top_k-1]]+[get_seq_from_key(key)]
            # check if [a,a] exits
            special_seq=[]
            for key,_ in seq_counts:
                seq=get_seq_from_key(key)
                if len(seq)==2:
                    if len(list(set(seq)))==1:
                        special_seq.append(seq)
            if len(special_seq)>=top_k:
                return special_seq[0:top_k]
            else:
                if len(special_seq)==1:
                    return special_seq+[get_seq_from_key(key) for key, _ in seq_counts[0:top_k-1]]
                else:
                    return [get_seq_from_key(key) for key,_ in seq_counts[0:top_k]]

        return [get_seq_from_key(key) for key,_ in seq_counts[0:top_k]]
    else:
        return [get_seq_from_key(key) for key,_ in seq_counts]




def refine_sequences(sequences:list,target:str)->list:
    target_name = target.split(f'.')[-1] if '.' in target else target
    kept=[]
    for seq in sequences:
        # if len(seq) - len(set(seq)) >=2 or (len(seq) - len(set(seq))==1 and len(seq)==4):
        if len(seq) - len(set(seq)) >= 2:
            seq_=[]
            for ftn in seq[0:-1]:
                if ftn not in seq_:
                    seq_.append(ftn)
            seq_.append(seq[-1])
            if seq_ not in kept:
                kept.append(seq_)

        else:
            if len(seq)==1:
                if seq+[target_name] not in kept:
                    kept.append(seq+[target_name])
            else:
                if seq not in kept:
                    kept.append(seq)

    kept=[seq+[target_name] if seq[-1] not in [target_name] else seq for seq in kept]
    return kept


