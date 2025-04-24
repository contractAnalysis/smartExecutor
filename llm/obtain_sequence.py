import json
import os.path
import time
from time import sleep

import fdg.global_config
import llm.llm_config
from llm.anthropic_utils import claude_create
from llm.llm_config import project_path, sleep_time, LLM_model
from llm.openai_utils import gpt_request, llama_request, deepseek_request
from llm.utils import load_specific_prompt_data, present_list_as_str, \
    get_a_kv_pair_from_a_json, get_json_data_from_response_in_dict, \
    write_a_kv_pair_to_a_json_file, color_print, present_for_dict

prompt_path=f'{project_path}llm/prompts/'

if llm.llm_config.FLAG_exp:
    result_path="./responses/"
else:
    result_path=f'{project_path}llm/results/'

def data_processing(data:dict)->dict:
    if llm.llm_config.FLAG_conversation:
        data['prompt_style']="con"
        data['prompt_file']='prompts_con'

        if "valid_sequences" in data.keys():
            if int(data['iteration'])-1 in data['valid_sequences'].keys():
                # provide the valid sequences of the last iteration
                data['valid_sequences']=data['valid_sequences'][int(data['iteration'])-1]
        # use the feedback of the sequences of the targets from the last iteration
        data['feedback']={t: status[-1] if len(status)>0 else "not available." for t,status in data['feedback'].items() if t in data['target_functions']}

    else:
        data['prompt_style'] = "ind"
        data['prompt_file'] = 'prompts_ind'

    if llm.llm_config.LLM_Mode not in ['gen'] and data['iteration']>=2:
        # remove the target that has only one candidate sequence (no need to generate a sequence)
        data['target_functions']=list(data['candidate_sequences'].keys())

    if llm.llm_config.LLM_model in ['gpt']:
        model=llm.llm_config.gpt_model
    elif llm.llm_config.LLM_model in ['deepseek']:
        model=llm.llm_config.deepseek_model
    elif llm.llm_config.LLM_model in ['llama']:
        model=llm.llm_config.llama_model
    else:
        model=llm.llm_config.llama_model

    data['llm_model']=model
    data['llm_model_sim'] = llm.llm_config.LLM_model

    data['llm_mode']=llm.llm_config.LLM_Mode
    data['llm_temperature']=llm.llm_config.temperature
    return data

def message_preparation(state:str, prompt_file_name:str,data:dict={}):
    # prepare prompt data
    if data['iteration']==1:
        seq_prompt= load_specific_prompt_data(prompt_path,prompt_file_name, 'get_sequence')
    elif data['iteration']>=2:
        if data['llm_mode'] in ['gen']:
            seq_prompt = load_specific_prompt_data(prompt_path, prompt_file_name, 'get_sequence_gen')

        elif data['llm_mode'] in ['gen_sel']:
            seq_prompt = load_specific_prompt_data(prompt_path, prompt_file_name,
                                                   'get_sequence_gen_sel_tradition')
        else:
            seq_prompt = load_specific_prompt_data(prompt_path, prompt_file_name,
                                               'get_sequence_gen_sel_llm')


    if state in ['sequence']:
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
            value= present_list_as_str(data["valid_sequences"]) # type: list

        elif item=='iteration':
            value=data["iteration"]
        elif item=='one_iteration_before':
            value=str(int(data["iteration"])-1)

        elif item=='candidate_sequences':
            value=present_for_dict(data["candidate_sequences"])
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

    response0 = gpt_request(engine, msg)
    if "```json" in response0:
        response0=response0.strip("```json")
        response0=response0.strip("```")
        return json.loads(response0)
    else:
        if response0.startswith("{") and response0.endswith('}'):
            response0=json.loads(response0)
        return response0


def collect_sequences(data:dict,iteration:int=1):

    data=data_processing(data)
    prompt_file_name=data['prompt_file']
    prompt_style=data['prompt_style']

    # prepare for message
    msg=message_preparation('sequence',prompt_file_name,data=data)

    # save the results
    if llm.llm_config.FLAG_exp:
        key = f'{data["solidity_name"]}_{data["contract_name"]}_sequence_iter_{data["iteration"]}'
        file_name_prefix=result_path + f'{data["solidity_name"]}_{data["contract_name"]}_{data["llm_model_sim"]}_{data["llm_mode"]}_{prompt_style}_{data["llm_temperature"]}'
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
        file_name_prefix = result_path + f'{data["solidity_name"]}_{data["contract_name"]}_{data["llm_model_sim"]}_{data["llm_mode"]}_{prompt_style}_{data["llm_temperature"]}'

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
        if data['llm_model'] in ['gpt']:
            response1 = gpt_request(data['llm_model'], msg,temperature=data['llm_temperature'])
        elif data['llm_model'] in ['deepseek']:
            response1,token_counts = llama_request(data['llm_model'], msg,temperature=data['llm_temperature'])
        elif data['llm_model'] in ['llama']:
            response1,token_counts = deepseek_request(data['llm_model'], msg,temperature=data['llm_temperature'])
        elif data['llm_model'] in ['starcoder']:
            ...
        else:
            response1,token_counts = llama_request(data['llm_model'], msg,temperature=data['llm_temperature'])

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
        if len(seq_results)==0:
            seq_results=extract_response_with_gpt(LLM_model, response1)
            if len(seq_results)==0:
                print(f"Fail to extract sequences from response {response1}")
        write_a_kv_pair_to_a_json_file(json_file_path, key, seq_results)

    else:
        seq_results=saved_value
        response1=get_a_kv_pair_from_a_json(json_file_path_raw,f'{key}_response')

    color_print('Red', f'\n\n==== Generated sequences ===={data["solidity_name"]}===={data["contract_name"]}===={data["iteration"]}===={os.path.basename(__file__)}')

    for k,v in seq_results.items():
        color_print('Blue', f'{k}:')
        color_print('Gray', f'\t{v}')

    msg.append(
        {"role": "assistant",
         "content": f'{response1}'})
    return seq_results,msg

