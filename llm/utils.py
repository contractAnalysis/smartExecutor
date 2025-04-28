import json
import os
import re
from json import JSONDecodeError

import llm.llm_config


def read_a_file(file_path):
    return open(file_path, 'r', encoding="utf-8").read()

def remove_comments(input_str):
    # # Remove single-line comments (// ...)
    # input_str = re.sub(r'\/\/.*', '', input_str)

    # Remove multi-line comments (/* ... */)
    input_str = re.sub(r'\/\*.*?\*\/', '', input_str, flags=re.DOTALL)

    # Remove unnecessary space lines
    input_str = re.sub(r'\n\s*\n', '\n', input_str, flags=re.MULTILINE)

    return input_str


def remove_import_statements(file_content:str)->str:
    # Define the regular expression pattern to match import statements
    import_pattern = r'^\s*import\s+[^\n\r;]+[;\n\r]'
    # Remove import statements from the Solidity code
    cleaned_code = re.sub(import_pattern, '', file_content, flags=re.MULTILINE)

    return cleaned_code


def get_related_source_code(contract_name:str, solidity_file:str, solc_result,file_content:str=""):
    """

    """
    if "sources" in solc_result.keys():
        if solidity_file in solc_result['sources'].keys():
            ast=""
            if 'ast' in solc_result['sources'][solidity_file].keys():
                ast=solc_result['sources'][solidity_file]['ast']
            elif "legacyAST" in solc_result['sources'][solidity_file].keys():
                ast = solc_result['sources'][solidity_file]['legacyAST']
            else:
                return
            pragma_id=0
            pragma_src=""
            if len(ast) > 0:
                contract_srcmap = {}
                target_linearized_base_contracts = []
                contract_id_to_name = {}
                for node in ast['nodes']:
                    if 'name' not in node.keys():
                        if node['nodeType'] in ['PragmaDirective']:
                            pragma_id=node['id']
                            pragma_src = node['src']
                        continue
                    contract_id_to_name[node['id']] = node["name"]
                    contract_srcmap[node["name"]] = node['src']
                    if node["name"] in [contract_name]:
                        target_linearized_base_contracts = node[
                            "linearizedBaseContracts"]

                if file_content is None:
                    file_content = read_a_file(solidity_file)
                pragma_src = pragma_src.split(f':')
                src_map = [int(e) for e in pragma_src[0:2]]
                related_code =f'{file_content[src_map[0]:src_map[0] + src_map[1]]}\n'
                for id in target_linearized_base_contracts:
                    src_map = contract_srcmap[contract_id_to_name[id]].split(f':')
                    src_map = [int(e) for e in src_map[0:2]]
                    related_code += f'{file_content[src_map[0]:src_map[0] + src_map[1]]}\n'

                # llm.llm_config.contract_code= remove_comments(related_code)
                llm.llm_config.contract_code = related_code

def load_specific_prompt_data(prompt_path:str,prompt_file_name:str,prompt_key:str)->dict:
    path=prompt_path+"{}.json".format(prompt_file_name)
    data=load_a_json_file(path)
    if prompt_key in data.keys():
        return data[prompt_key]
    return {}

def load_a_json_file(file_path:str):
    data = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as file:
                data = json.load(file)

        except json.JSONDecodeError as e:
            print(f"Error loading JSON from {file_path}: {e}")
        finally:
            return data

    else:
        print(f"File does not exist: {file_path}")
        return data

def present_list_as_str(lst:list)->str:
    if isinstance(lst,list):
        if len(lst)==0:return ''
        elif len(lst)==1: return str(lst[0])
        elif len(lst)==2:return f'{lst[0]} and {lst[1]}'
        else:
            v=str(lst[0])
            for e in lst[1:-1]:
                v+=f', {e}'
            v+=f', and {lst[-1]}'
            return v
    else:
        color_print("Red",f'Warning: {lst} should be a list. (in function:present_list_as_str) ({os.path.basename(__file__)})')
        return lst
def get_a_kv_pair_from_a_json(json_file_path_name:str,key:str):
    # Open the existing JSON file for reading
    if os.path.exists(json_file_path_name):
        with open(json_file_path_name, 'r') as file:
            data = json.load(file)
            if key in data.keys():
                return data[key]
            else:
                return ""
    else:
        print(f"File does not exist: {json_file_path_name}")
        return ""
def get_json_data_from_response_in_dict(response: str,function_name:str=""):
    """

    :param response:
    :param function_name: used to check if the extracted data is what is needed
    :return:
    """
    data = {}
    response=response.strip()
    try:
        if "```json" in response:
            if response.startswith("```json") and response.endswith("```"):
                data=response.strip("```json").strip("```")
                return json.loads(data)
            else:
                response_seg = response.split("```")
                for seg in response_seg:
                    if seg.startswith('json'):
                        if "{" in seg:
                            if "}" in seg:
                                first_idx = seg.index('{')
                                last_idx = seg.rindex('}')
                                raw_data = seg[first_idx:last_idx + 1]

                                data = json.loads(raw_data)
                                if len(function_name) == 0:
                                    return data
                                else:
                                    if function_name in data.keys():
                                        return data
                                    else:
                                        data = {}
                                        return data


        elif "```" in response:
            if response.startswith("```") and response.endswith("```"):
                data = response.strip("```").strip("```")
                return json.loads(data)
            else:
                response_seg = response.split("```")
                for seg in response_seg:
                    if "{" in seg:
                        if "}" in seg:
                            first_idx = seg.index('{')
                            last_idx = seg.rindex('}')
                            raw_data = seg[first_idx:last_idx + 1]

                            data = json.loads(raw_data)
                            if len(function_name) == 0:
                                return data
                            else:
                                if function_name in data.keys():
                                    return data
                                else:
                                    data = {}
                                    return data

        else:
            if response.startswith("{") and response.endswith("}"):
                data = response.strip("```json").strip("```")
                return json.loads(data)
            else:
                return data
    except JSONDecodeError:
        color_print("Red",f'JSONDecodeError {os.path.basename(__file__)}')
    return data

def write_a_kv_pair_to_a_json_file(json_file_path_name:str,key:str,value:str):
    # Open the existing JSON file for reading
    with open(json_file_path_name, 'r') as file:
        data = json.load(file)

    # Modify the data as needed
    data[key] = value

    # Write the modified data back to the same JSON file
    with open(json_file_path_name, 'w') as file:
        json.dump(data, file,
                  indent=4)  # Optionally, use 'indent' to format the JSON for readability

def color_print(color_name:str,print_content:str):
    if color_name not in ['Magenta',"Green","Red","Blue",'Gray']:
        color_v="Red"
    else:color_v=color_name
    content= "{}{}{}".format(
        llm.llm_config.color_prefix[color_v],
        print_content,
        llm.llm_config.color_prefix["Gray"],
    )
    print(content)


def present_for_dict(feedback:dict, keys:list=[])->str:
    if len(feedback)==0:return ""
    content=""
    for func,status in feedback.items():
        content+=f'{func}:{status}\n'
    return content
