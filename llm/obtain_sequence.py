import json
import os.path
import time
from json import JSONDecodeError
from time import sleep

import fdg.global_config
import llm.llm_config

from llm.llm_config import project_path, sleep_time
from llm.openai_utils import gpt_request, llama_request, deepseek_request, \
    starcoder_request, mistral_request, qwen_request, palmyra_request, \
    gemma_request
from llm.utils import load_specific_prompt_data, present_list_as_str, \
    get_a_kv_pair_from_a_json, get_json_data_from_response_in_dict, \
    write_a_kv_pair_to_a_json_file, color_print, present_for_dict


prompt_path=f'{project_path}llm/prompts/'
def get_path_to_save_result():
    if llm.llm_config.FLAG_exp:
        result_path="./responses/"
    else:
        result_path=f'{project_path}llm/results/'
    return result_path

def data_processing(data:dict)->dict:
    if llm.llm_config.FLAG_conversation:
        data['prompt_style']="con"
        data['prompt_file']='prompts_con'

        if "valid_sequences" in data.keys():
            if int(data['iteration'])-1 in data['valid_sequences'].keys():
                # provide the valid sequences of the last iteration
                data['valid_sequences']=data['valid_sequences'][int(data['iteration'])-1]
            else:
                data['valid_sequences'] = []
        # use the feedback of the sequences of the targets from the last iteration
        data['feedback']={t: status[-1] if len(status)>0 else "not available." for t,status in data['feedback'].items() if t in data['target_functions']}

    else:
        data['prompt_style'] = "ind"
        data['prompt_file'] = 'prompts_ind'

    if llm.llm_config.LLM_Mode in ['sel']:
        ...
    elif llm.llm_config.LLM_Mode not in ['gen'] and data['iteration']>=2:
        if len(data['msg_so_far'])>0:
            # remove the target that has only one candidate sequence (no need to generate a sequence)
            data['target_functions']=list(data['candidate_sequences'].keys())


    if llm.llm_config.LLM_model in ['gpt']:
        model=llm.llm_config.gpt_model
    elif llm.llm_config.LLM_model in ['deepseek']:
        model=llm.llm_config.deepseek_model
    elif llm.llm_config.LLM_model in ['llama']:
        model=llm.llm_config.llama_model
    elif llm.llm_config.LLM_model in ['starcoder']:
        model=llm.llm_config.starcoder_model
    elif llm.llm_config.LLM_model in ['mistral']:
        model=llm.llm_config.mistral_model
    elif llm.llm_config.LLM_model in ['qwen']:
        model=llm.llm_config.qwen_model
    elif llm.llm_config.LLM_model in ['palmyra']:
        model=llm.llm_config.palmyra_model
    elif llm.llm_config.LLM_model in ['gemma']:
        model=llm.llm_config.gemma_model
    else:
        model=llm.llm_config.llama_model

    data['llm_model']=model
    data['llm_model_sim'] = llm.llm_config.LLM_model
    data['llm_mode']=llm.llm_config.LLM_Mode
    data['llm_temperature']=llm.llm_config.temperature
    data['num_max_candi']=llm.llm_config.NUM_max_candidate_sequences
    return data

def message_preparation(state:str, prompt_file_name:str,data:dict={}):
    # prepare prompt data
    if data['llm_mode'] in ['sel']:
        seq_prompt = load_specific_prompt_data(prompt_path, prompt_file_name,
                                               'get_sequence_sel')
    elif data['iteration']==1:
        seq_prompt = load_specific_prompt_data(prompt_path,
                                                   prompt_file_name,
                                                   'get_sequence')

    elif data['iteration']>=2:
        if data['llm_mode'] in ['gen']:
            seq_prompt = load_specific_prompt_data(prompt_path, prompt_file_name, 'get_sequence_gen')
        elif data['llm_mode'] in ['gen_sel']:
            if len(data['msg_so_far']) == 0:
                # deal with large number of candidate sequences
                if len(data['target_functions'])==1:
                    seq_prompt = load_specific_prompt_data(prompt_path,
                                                           prompt_file_name,
                                                           'chop_candidate_sequences1')
                else:
                    seq_prompt = load_specific_prompt_data(prompt_path,
                                                           prompt_file_name,
                                                           'chop_candidate_sequences')
            else:
                seq_prompt = load_specific_prompt_data(prompt_path, prompt_file_name,
                                                   'get_sequence_gen_sel')

        elif data['llm_mode'] in ['gen_sel_llm']:
            if len(data['msg_so_far'])==0:
                # for candidate sequence generation
                seq_prompt= load_specific_prompt_data(prompt_path, prompt_file_name,
                                                   'get_candidate_sequences_llm')
            else:
                seq_prompt = load_specific_prompt_data(prompt_path,
                                                       prompt_file_name,
                                                       'get_sequence_gen_sel')
        else:
            seq_prompt = load_specific_prompt_data(prompt_path, prompt_file_name,
                                               'get_sequence_gen_sel')


    if state in ['sequence']:
        if data['llm_mode'] in ['sel'] and data['iteration']>1:
            seq_data_items = seq_prompt['user']['data1']
        else:
            seq_data_items=seq_prompt['user']['data']
    else:
        pass

    all_data_items_values = {}
    all_data_items = list(set(seq_data_items))

    for item in all_data_items:
        value=''
        if item == 'contract_name':
            value = data["contract_name"]
        elif item == 'contract_code':
            value = data["contract_code"]
        elif item == 'start_functions':
            value = present_list_as_str(data["start_functions"])
        elif item == 'target_functions':
            value = present_list_as_str(data["target_functions"])
        elif item=='feedback':
            value=f'{present_for_dict(data["feedback"])}'
        elif item=="seq_length":
            value=fdg.global_config.seq_len_limit  # the length of a function sequence presented as a list without the constructor().
        elif item=='valid_sequences':
            if len(data["valid_sequences"])==0:
                value="No valid sequences"
            else:
                value= present_list_as_str(data["valid_sequences"]) # type: list
        elif item == 'bad_sequences':
            value=present_list_as_str(data['bad_sequences_w_reason'])
        elif item=='num_sequences':
            value= data["num_sequences"]
        elif item=='iteration':
            value=data["iteration"]
        elif item=='one_iteration_before':
            value=str(int(data["iteration"])-1)

        elif item=='candidate_sequences':
            value=present_for_dict(data["candidate_sequences"])

        elif item=='huge_num_sequences':
            value=present_for_dict(data["huge_num_sequences"])
        else:
            print(f'{item} is not provided. ')
        all_data_items_values[item]=value



    cur_msg=[]
    # include the past messages
    if state in ['sequence']:
        if not llm.llm_config.FLAG_single_prompt:
            if data['iteration']>1:
                cur_msg=data["msg_so_far"]

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
        if data['llm_mode'] in ['sel']:
            if data['iteration']==1:
                user_msg=seq_prompt['user']['content']
            else:
                user_msg=seq_prompt['user']['content1']

        elif data['iteration']>2 and data['llm_mode'] not in ['gen']:
            user_msg = seq_prompt["user"]["content1"]
        else:
            user_msg = seq_prompt["user"]["content"]

        if data['llm_mode'] in ['sel']:
            if data['iteration']==1:
                data_items=seq_prompt["user"]["data"]
            else:
                data_items = seq_prompt["user"]["data1"]
        else:
            data_items= seq_prompt["user"]["data"]
        for item in data_items:
            user_msg = user_msg.replace("##{}##".format(item),
                                        "{}".format(
                                            all_data_items_values[item]))
        cur_msg.append({"role": "user", "content": user_msg})

    else:
        print(f'no prompt message is prepared!')
        pass
    return cur_msg


def request_llm(llm_model_sim, llm_model_whole, msg, temperature=0):
    # request an LLM to get sequences
    if llm_model_sim in ['gpt']:
        response1,token_counts = gpt_request(llm_model_whole, msg, temperature=temperature)
    elif llm_model_sim in ['deepseek']:
        response1, token_counts = llama_request(llm_model_whole, msg, temperature=temperature)
    elif llm_model_sim in ['llama']:
        response1, token_counts = deepseek_request(llm_model_whole, msg, temperature=temperature)
    elif llm_model_sim in ['starcoder']:
        response1, token_counts = starcoder_request(llm_model_whole, msg, temperature=temperature)
    elif llm_model_sim in ['mistral']:
        response1, token_counts = mistral_request(llm_model_whole, msg,temperature=temperature)
    elif llm_model_sim in ['qwen']:
        response1, token_counts = qwen_request(llm_model_whole, msg,
                                                  temperature=temperature)
    elif llm_model_sim in ['palmyra']:
        response1, token_counts = palmyra_request(llm_model_whole, msg,
                                               temperature=temperature)
    elif llm_model_sim in ['gemma']:
        response1, token_counts = gemma_request(llm_model_whole, msg,
                                               temperature=temperature)
    else:
        response1, token_counts = llama_request(llm_model_whole, msg, temperature=temperature)
    return response1, token_counts

def extract_response_with_llm(llm_model_sim:str, llm_model_whole:str, given_response:str):
    correct_response = load_specific_prompt_data(prompt_path,"prompts_con",
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

    # request an LLM to get sequences
    seq_results={}
    response0, token_counts = request_llm(llm_model_sim, llm_model_whole,msg)
    try:
        seq_results = get_json_data_from_response_in_dict(response0)

    except Exception:
        color_print("Red",f'JSONDecodeError: Expecting value: line 1 column 1 (char 0) in (extract_response_with_llm)')

    return seq_results



def collect_sequences(data:dict,iteration:int=1):

    data=data_processing(data)
    prompt_file_name=data['prompt_file']
    prompt_style=data['prompt_style']

    # prepare for message
    msg=message_preparation('sequence',prompt_file_name,data=data)

    # save the results
    if llm.llm_config.FLAG_exp:
        key = f'{data["solidity_name"]}_{data["contract_name"]}_sequence_iter_{data["iteration"]}'
        result_path=get_path_to_save_result()
        file_name_prefix = result_path + f'{data["solidity_name"]}_{data["contract_name"]}_{data["llm_model_sim"]}_{data["llm_mode"]}_{data["llm_temperature"]}_{llm.llm_config.SEQ_iteration}_{data["num_max_candi"]}_{llm.llm_config.candi_percentage}_{llm.llm_config.times}'

        json_file_path = file_name_prefix+'_seq_responses.json'
        json_file_path_raw = file_name_prefix+'_seq_raw_responses.json'

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
        key = f'{data["solidity_name"]}_{data["contract_name"]}_sequence_iter_{data["iteration"]}'
        result_path = get_path_to_save_result()
        file_name_prefix = result_path + f'{data["solidity_name"]}_{data["contract_name"]}_{data["llm_model_sim"]}_{data["llm_mode"]}_{data["llm_temperature"]}_{llm.llm_config.SEQ_iteration}_{data["num_max_candi"]}_{llm.llm_config.candi_percentage}_{llm.llm_config.times}'

        json_file_path = file_name_prefix+f'_seq_responses.json'
        json_file_path_raw =file_name_prefix+f'_seq_raw_responses.json'

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
        sleep(sleep_time) # used to control the request rate

        start_time=time.time()
        # request an LLM to get sequences
        response1, token_counts = request_llm(data['llm_model_sim'], data['llm_model'],
                                              msg,temperature=data['llm_temperature'])
        # to measure the time required to get sequences
        end_time = time.time()
        llm.llm_config.time_records.append(end_time - start_time)
        llm.llm_config.input_tokens.append(token_counts[0])
        llm.llm_config.output_tokens.append(token_counts[1])

        # extract and save response
        if len(msg)==2:
            write_a_kv_pair_to_a_json_file(json_file_path_raw, f'{key}_system',msg[0])
        write_a_kv_pair_to_a_json_file(json_file_path_raw, f'{key}_prompt',msg[-1])

        response1_={"role": "assistant","content": f'{response1}'}
        write_a_kv_pair_to_a_json_file(json_file_path_raw,f'{key}_response',response1_)

        seq_results = get_json_data_from_response_in_dict(response1)

        loop=0
        while isinstance(seq_results,str) or len(seq_results)==0:
            loop+=1
            if loop>=3:
                color_print("Red", f"Fail to extract sequences from response {response1}({os.path.basename(__file__)})")
                break
            seq_results=extract_response_with_llm("gpt", "gpt-4o-2024-05-13", response1)


        write_a_kv_pair_to_a_json_file(json_file_path, key, seq_results)

    else:
        seq_results=saved_value
        response1=get_a_kv_pair_from_a_json(json_file_path_raw,f'{key}_response')

    color_print('Red', f'\n\n===== Generated sequences ===={data["solidity_name"]}===={data["contract_name"]}===={data["iteration"]}===={os.path.basename(__file__)}')
    if isinstance(seq_results,dict):
        for k,v in seq_results.items():
            if k not in data['target_functions']:continue
            color_print('Blue', f'{k}:')
            color_print('Gray', f'\t{v}')
    else:
        color_print('Red',"Fail to generate or extract sequences.")

    msg.append(
        {"role": "assistant",
         "content": f'{response1}'})
    return seq_results,msg

def collect_candidate_sequences(data:dict):
    data = data_processing(data)
    prompt_file_name = data['prompt_file']
    prompt_style = data['prompt_style']

    # prepare for message
    msg = message_preparation('sequence', prompt_file_name, data=data)

    # save the results
    if llm.llm_config.FLAG_exp:
        key = f'{data["solidity_name"]}_{data["contract_name"]}_candidate_sequences'
        result_path = get_path_to_save_result()
        file_name_prefix = result_path + f'{data["solidity_name"]}_{data["contract_name"]}_{data["llm_model_sim"]}_{data["llm_mode"]}_{data["llm_temperature"]}_{llm.llm_config.SEQ_iteration}_{data["num_max_candi"]}_{llm.llm_config.candi_percentage}_{llm.llm_config.times}'

        json_file_path = file_name_prefix + '_seq_responses.json'
        json_file_path_raw = file_name_prefix + '_seq_raw_responses.json'

        if not os.path.exists(json_file_path):
            # Create the file
            with open(json_file_path, 'w') as file:
                file.write('{}')
        if not os.path.exists(json_file_path_raw):
            # Create the file
            with open(json_file_path_raw, 'w') as file:
                file.write('{}')
        saved_value = {}
    else:
        key = f'{data["solidity_name"]}_{data["contract_name"]}_candidate_sequences'
        result_path = get_path_to_save_result()
        file_name_prefix = result_path + f'{data["solidity_name"]}_{data["contract_name"]}_{data["llm_model_sim"]}_{data["llm_mode"]}_{data["llm_temperature"]}_{llm.llm_config.SEQ_iteration}_{data["num_max_candi"]}_{llm.llm_config.candi_percentage}_{llm.llm_config.times}'

        json_file_path = file_name_prefix + f'_seq_responses.json'
        json_file_path_raw = file_name_prefix + f'_seq_raw_responses.json'

        if not os.path.exists(json_file_path):
            # Create the file
            with open(json_file_path, 'w') as file:
                file.write('{}')
        if not os.path.exists(json_file_path_raw):
            # Create the file
            with open(json_file_path_raw, 'w') as file:
                file.write('{}')
        saved_value = get_a_kv_pair_from_a_json(json_file_path, key)

    if len(saved_value) == 0:
        sleep(sleep_time)  # used to control the request rate

        start_time = time.time()
        # request an LLM to get sequences
        response1, token_counts = request_llm(data['llm_model_sim'],
                                              data['llm_model'],
                                              msg, temperature=data[
                'llm_temperature'])

        # to measure the time required to get sequences
        end_time = time.time()
        llm.llm_config.time_records.append(end_time - start_time)
        llm.llm_config.input_tokens.append(token_counts[0])
        llm.llm_config.output_tokens.append(token_counts[1])


        write_a_kv_pair_to_a_json_file(json_file_path_raw, f'{key}_prompt',
                                       msg)

        response1_ = {"role": "assistant", "content": f'{response1}'}
        write_a_kv_pair_to_a_json_file(json_file_path_raw, f'{key}_response',
                                       response1_)

        seq_results = get_json_data_from_response_in_dict(response1)
        loop = 0
        while isinstance(seq_results, str) or len(seq_results) == 0:
            loop += 1
            if loop >= 3:
                color_print("Red",
                            f"Fail to extract sequences from response {response1}({os.path.basename(__file__)})")
                break
            seq_results = extract_response_with_llm("gpt", "gpt-4o-2024-05-13", response1)
        write_a_kv_pair_to_a_json_file(json_file_path, key, seq_results)

    else:
        seq_results = saved_value

    color_print('Red',
                f'\n\n===== Generated candidate sequences ===={data["solidity_name"]}===={data["contract_name"]}===={data["iteration"]}===={os.path.basename(__file__)}')
    if isinstance(seq_results,dict):
        for k, v in seq_results.items():
            color_print('Blue', f'{k}:')
            if isinstance(v, list):
                for s in v:
                    color_print('Gray', f'\t{s}')
            else:
                color_print("Blue","not a list,why?")
                color_print('Gray', f'\t{v}')
    else:
        color_print('Red', f'Fail to extract the sequences from the response.')

    return seq_results

def chop_candidate_sequences(data:dict):
    data = data_processing(data)
    prompt_file_name = data['prompt_file']
    prompt_style = data['prompt_style']

    # prepare for message
    msg = message_preparation('sequence', prompt_file_name, data=data)

    # save the results
    if llm.llm_config.FLAG_exp:
        key = f'{data["solidity_name"]}_{data["contract_name"]}_chop_candidate_sequences'
        result_path = get_path_to_save_result()
        file_name_prefix = result_path + f'{data["solidity_name"]}_{data["contract_name"]}_{data["llm_model_sim"]}_{data["llm_mode"]}_{data["llm_temperature"]}_{llm.llm_config.SEQ_iteration}_{data["num_max_candi"]}_{llm.llm_config.candi_percentage}_{llm.llm_config.times}'

        json_file_path = file_name_prefix + '_seq_responses.json'
        json_file_path_raw = file_name_prefix + '_seq_raw_responses.json'

        if not os.path.exists(json_file_path):
            # Create the file
            with open(json_file_path, 'w') as file:
                file.write('{}')
        if not os.path.exists(json_file_path_raw):
            # Create the file
            with open(json_file_path_raw, 'w') as file:
                file.write('{}')
        saved_value = {}
    else:
        key = f'{data["solidity_name"]}_{data["contract_name"]}_chop_candidate_sequences'
        result_path = get_path_to_save_result()
        file_name_prefix = result_path + f'{data["solidity_name"]}_{data["contract_name"]}_{data["llm_model_sim"]}_{data["llm_mode"]}_{prompt_style}_{data["llm_temperature"]}_{data["num_max_candi"]}_{llm.llm_config.times}'

        json_file_path = file_name_prefix + f'_seq_responses.json'
        json_file_path_raw = file_name_prefix + f'_seq_raw_responses.json'

        if not os.path.exists(json_file_path):
            # Create the file
            with open(json_file_path, 'w') as file:
                file.write('{}')
        if not os.path.exists(json_file_path_raw):
            # Create the file
            with open(json_file_path_raw, 'w') as file:
                file.write('{}')
        saved_value = get_a_kv_pair_from_a_json(json_file_path, key)

    if len(saved_value) == 0:
        sleep(sleep_time)  # used to control the request rate

        start_time = time.time()
        # request an LLM to get sequences
        response1, token_counts = request_llm(data['llm_model_sim'],
                                              data['llm_model'],
                                              msg, temperature=data[
                'llm_temperature'])

        # to measure the time required to get sequences
        end_time = time.time()
        llm.llm_config.time_records.append(end_time - start_time)
        llm.llm_config.input_tokens.append(token_counts[0])
        llm.llm_config.output_tokens.append(token_counts[1])


        write_a_kv_pair_to_a_json_file(json_file_path_raw, f'{key}_prompt',
                                       msg)

        response1_ = {"role": "assistant", "content": f'{response1}'}
        write_a_kv_pair_to_a_json_file(json_file_path_raw, f'{key}_response',
                                       response1_)

        seq_results = get_json_data_from_response_in_dict(response1)
        loop = 0
        while isinstance(seq_results, str) or len(seq_results) == 0:
            loop += 1
            if loop >= 3:
                color_print("Red",
                            f"Fail to extract sequences from response {response1}({os.path.basename(__file__)})")
                break
            seq_results = extract_response_with_llm("gpt", "gpt-4o-2024-05-13", response1)
        write_a_kv_pair_to_a_json_file(json_file_path, key, seq_results)

    else:
        seq_results = saved_value

    color_print('Red',
                f'\n\n===== Chop candidate sequences ===={data["solidity_name"]}===={data["contract_name"]}===={data["iteration"]}===={os.path.basename(__file__)}')
    if isinstance(seq_results,dict):
        for k, v in seq_results.items():
            color_print('Blue', f'{k}:')
            if isinstance(v, list):
                for s in v:
                    color_print('Gray', f'\t{s}')
            else:
                color_print("Blue","not a list,why?")
                color_print('Gray', f'\t{v}')
    else:
        color_print('Red', f'Fail to extract the sequences from the response.')

    return seq_results

