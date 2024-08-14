import json
import os.path
from time import sleep

import fdg.global_config
import llm.llm_config
from llm.anthropic_utils import claude_create
from llm.llm_config import project_path, sleep_time, GPT4_model
from llm.openai_utils import gpt_request_chatComplection_new
from llm.utils import load_specific_prompt_data, present_list_as_str, \
    get_a_kv_pair_from_a_json, get_json_data_from_response_in_dict, \
    write_a_kv_pair_to_a_json_file, color_print, present_for_dict

prompt_path=f'{project_path}llm/prompts/'

if llm.llm_config.FLAG_exp:
    result_path="./responses/"
else:
    result_path=f'{project_path}llm/results/'



def message_preparation(state:str, contract_name:str, contract_code:str, start_functions:list, target_functions:list, msg_history:list=[], feedback:dict={},iteration:int=1,not_included_sequences:list=[]):
    # prepare prompt data
    if not llm.llm_config.FLAG_single_prompt:
        if iteration==1:
            seq_prompt= load_specific_prompt_data(prompt_path,"seq_prompts", 'get_sequence')
        elif iteration>1:
            seq_prompt = load_specific_prompt_data(prompt_path, "seq_prompts", 'get_sequence_1')
    else:
        seq_prompt = load_specific_prompt_data(prompt_path, "seq_prompts",'get_sequence_single')

    if state in ['sequence']:
        seq_data_items=seq_prompt['user']['data']
    else:
        pass

    all_data_items_values = {}
    all_data_items = list(set(seq_data_items))

    for item in all_data_items:
        value=''
        if item == 'contract_name':
            value = contract_name
        elif item == 'contract_code':
            value = contract_code
        elif item == 'start_functions':
            value = present_list_as_str(start_functions)
        elif item == 'target_functions':
            value = present_list_as_str(target_functions)
        elif item=='feedback':
            value=f'Feedback:{present_for_dict(feedback)}'
        elif item=="seq_length":
            value=fdg.global_config.seq_len_limit
        elif item=='not_included_sequences':
            value="" if len(not_included_sequences)==0 else f'Please avoid the sequences listed here as they are considered: {present_list_as_str(not_included_sequences)}'
        else:
            print(f'{item} is not provided. ')
        all_data_items_values[item]=value

    cur_msg=[]
    # include the past messages
    if state in ['sequence']:
        if not llm.llm_config.FLAG_single_prompt:
            if iteration>1:
                cur_msg=msg_history

    # prepare for the system message
    if state in ['sequence']:
        if len(cur_msg)==0:
            sys_msg = seq_prompt['system']['content']
            for item in seq_prompt['system']['data']:
                if f'##{item}##' in sys_msg:
                    sys_msg = sys_msg.replace(f'##{item}##',
                                              f'{all_data_items_values[item]}')
            cur_msg = [{"role": "system", "content": sys_msg}]


    # prepare for the user message
    if state in ['sequence']:
        #---------------------------
        user_msg = seq_prompt["user"]["content"]
        for item in seq_prompt["user"]["data"]:
            user_msg = user_msg.replace("##{}##".format(item),
                                        "{}".format(
                                            all_data_items_values[item]))
        cur_msg.append({"role": "user", "content": user_msg})

    else:
        print(f'no prompt message is prepared!')
        pass
    return cur_msg


def extract_response_with_gpt(engine:str,given_response:str):
    correct_response = load_specific_prompt_data(prompt_path,"seq_prompts",
                                              'extract_correct_response')
    # add system message
    sys_msg =  correct_response["system"]["content"]
    msg = [{"role": "system", "content": sys_msg}]

    # add user message
    user_msg =  correct_response["user"]['content']
    for data_item in correct_response['user']['data']:
        if data_item=='given_response':
            user_msg=user_msg.replace(f'##{data_item}##',given_response)
    msg.append({"role": "user", "content": user_msg})

    response0 = gpt_request_chatComplection_new(engine, msg)
    if "```json" in response0:
        response0=response0.strip("```json")
        response0=response0.strip("```")
        return json.loads(response0)
    else:
        if response0.startswith("{") and response0.endswith('}'):
            response0=json.loads(response0)
        return response0


def collect_sequences(data:dict,iteration:int=1):

    # get contract code for the prompt preparation
    contract_code=data['contract_code']
    contract_name=data['contract_name']
    solidity_name=data['solidity_name']
    target_functions=data['target_functions']
    start_functions=data['start_functions']
    msg_so_far=data['msg_so_far']
    feedback=data['feedback']
    gen_iteration=data['gen_iteration']
    not_included_sequences=data['not_included_sequences']

    # prepare for message
    msg=message_preparation('sequence',contract_name,contract_code,start_functions,target_functions,msg_history=msg_so_far,feedback=feedback,iteration=gen_iteration,not_included_sequences=not_included_sequences)

    # save the results
    if llm.llm_config.FLAG_exp:
        key = f'{solidity_name}_{contract_name}_sequence_iter_{iteration}'
        json_file_path = result_path + f'{solidity_name}_{contract_name}_seq_responses.json'
        json_file_path_raw = result_path + f'{solidity_name}_{contract_name}_seq_raw_responses.json'

        if not os.path.exists(json_file_path):
            # Create the file
            with open(json_file_path, 'w') as file:
                file.write('{}')
        if not os.path.exists(json_file_path_raw):
            # Create the file
            with open(json_file_path_raw, 'w') as file:
                file.write('{}')
        saved_value={}
    else:
        key = f'{solidity_name}_{contract_name}_sequence_iter_{iteration}'
        json_file_path = result_path + "seq_responses.json"
        json_file_path_raw = result_path + "seq_raw_responses.json"
        if not os.path.exists(json_file_path):
            # Create the file
            with open(json_file_path, 'w') as file:
                file.write('{}')
        if not os.path.exists(json_file_path_raw):
            # Create the file
            with open(json_file_path_raw, 'w') as file:
                file.write('{}')
        saved_value = get_a_kv_pair_from_a_json(json_file_path, key)


    if len(saved_value)==0:
        sleep(sleep_time)
        if llm.llm_config.Flag_gpt:
            response1 = gpt_request_chatComplection_new(GPT4_model, msg)
        else:
            response1 = claude_create(llm.llm_config.Claude_model, msg)
        write_a_kv_pair_to_a_json_file(json_file_path_raw,key,response1)
        seq_results = get_json_data_from_response_in_dict(response1)
        if len(seq_results)==0:
            seq_results=extract_response_with_gpt(GPT4_model,response1)
            if len(seq_results)==0:
                print(f"Fail to extract sequences from response {response1}")
        write_a_kv_pair_to_a_json_file(json_file_path, key, seq_results)
    else:
        seq_results=saved_value
        response1=get_a_kv_pair_from_a_json(json_file_path_raw,key)

    # color_print('Red', f'\n\n===={solidity_name}===={contract_name}===={iteration}=====')
    #
    # for k,v in seq_results.items():
    #     color_print('Blue', f'{k}:')
    #     color_print('Gray', f'\t{v}')
    # only keep the sequences returned instead of all the sequences.
    # msg.append(
    #     {"role": "assistant",
    #      "content": f'The sequences generated at iteration {iteration}:\n{seq_results}'})

    msg.append(
        {"role": "assistant",
         "content": f'{response1}'})
    return seq_results,msg

