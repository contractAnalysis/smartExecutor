# -*- coding: utf-8 -*-
"""
prepare for the data needed to create environments

@author: SERC
"""
import ast
import random
from copy import deepcopy

import rl
from rl.env_data_preparation.contract_dynamics import ContractDynamics
from rl.config import contract_solidity_path,rl_cur_parameters, contract_json_file_path

from rl.generation.contract_data_slither import get_rw_data_from_slither

from rl.utils import load_a_json_file, get_seq_from_key

import os


class EnvDataCollection02():
    """
    prepare for the data needed to create environments
        static analysis data
        arg1 (a list of files): file containing the data resulted from the symbolic execution


    """

    def __init__(self, solidity_file_name: str, contract_name: str,
                 files_of_se_data: list=[]):

        self.solidity_file_name = solidity_file_name
        self.contract_name = contract_name

        self.file_paths_for_se_data = files_of_se_data

        self.targets = []
        self.start_functions = []
        self.functions_in_sequences = []  # get the function appearing in sequences
        self.function_sequence_writes = {}

        self.state_variables = []
        self.state_variables_in_integer = []

        self.function_reads_writes = {}
        self.function_sequence_writes = {}
        self.function_reads_writes_in_integer = {}

    def init(self):
        self.get_execution_data(self.file_paths_for_se_data)

        self.get_functions_in_sequences()

    def get_execution_data(self, file_paths: [str]):
        def get_key_from_list(data_list: list) -> str:
            if len(data_list) == 0:
                return ''
            else:
                key = data_list[0]
                for item in data_list[1:]:
                    key += "#" + item
                return key

        for file_path in file_paths:
            flag_reads = False
            flag_writes = False
            flag_start_function = False
            with open(file_path) as file:
                for line in file:
                    line = line.strip()
                    if len(line) == 0: continue
                    # print(f'{line}')
                    if ":writes at the last depth:" in line:
                        items = line.split(":")
                        seq = ast.literal_eval(items[0])

                        seq_ = [func.split(f'(')[0] if '(' in func else func for
                                func in seq]

                        writes = ast.literal_eval(items[-1])
                        seq_key = get_key_from_list(seq_)

                        writes_int = [int(ele) for ele in writes if
                                      len(ele) > 0]
                        if seq_key not in self.function_sequence_writes.keys():
                            self.function_sequence_writes[seq_key] = writes_int
                        else:
                            for w in writes_int:
                                if w not in self.function_sequence_writes[
                                    seq_key]:
                                    self.function_sequence_writes[
                                        seq_key].append(w)
                        if flag_start_function:
                            if seq_[0] not in self.start_functions:
                                self.start_functions.append(seq_[0])

                        continue
                    else:
                        if "targets:[" in line:
                            targets = ast.literal_eval(
                                line.split('targets:')[-1])
                            for t in targets:
                                t_ = t.split(f'(')[0] if '(' in t else t
                                if t_ not in self.targets:
                                    self.targets.append(t_)
                            continue

                        elif "Function Reads: State variables read in conditions" in line:
                            flag_reads = True
                            flag_writes = False
                            continue
                        elif "Function Writes: State variables written" in line:
                            flag_reads = False
                            flag_writes = True
                            continue
                        elif "iteration:3" in line:
                            flag_reads = flag_writes = False
                            flag_start_function = True
                            continue
                        elif "iteration:4" in line:

                            flag_start_function = False
                            continue
                    if "=====================" in line: continue
                    # get the state variables read in conditions
                    if flag_reads:
                        items = line.split(':')
                        try:
                            reads = ast.literal_eval(items[-1])
                            reads = [int(read) for read in reads]
                            if items[0] not in self.function_reads_writes.keys():
                                self.function_reads_writes[items[0]] = {
                                    'reads': reads}
                            else:
                                for read in reads:
                                    if read not in \
                                            self.function_reads_writes[items[0]][
                                                'reads']:
                                        self.function_reads_writes[items[0]][
                                            'reads'].append(read)
                        except:
                            pass
                    # get the state variables written
                    if flag_writes:
                        items = line.split(':')
                        try:
                            writes = ast.literal_eval(items[-1])
                            writes = [int(write) for write in writes]
                            if items[0] not in self.function_reads_writes.keys():
                                self.function_reads_writes[items[0]] = {
                                    'writes': writes}
                            else:
                                if 'writes' not in self.function_reads_writes[
                                    items[0]].keys():
                                    self.function_reads_writes[items[0]][
                                        'writes'] = writes
                                else:
                                    for write in writes:
                                        if write not in \
                                                self.function_reads_writes[
                                                    items[0]][
                                                    'writes']:
                                            self.function_reads_writes[items[0]][
                                                'writes'].append(write)
                        except:
                            pass



    def get_functions_in_sequences(self):
        def get_seq_from_key(key: str):
            if '#' in key:
                return key.split("#")
            else:
                return [key]

        for key in self.function_sequence_writes.keys():
            key_seq = get_seq_from_key(key)
            for func in key_seq:
                if func not in self.functions_in_sequences:
                    self.functions_in_sequences.append(func)

    def receive_data_from_static_analysis(self, static_analysis_data: dict):
        key = f'{self.solidity_file_name}{self.contract_name}'

        # if key in ['0x000000000019fff0e5b945e90ee1e606aa22c6c2.solDaiBackstopSyndicateV2']:
        #    print(f'xs')
        if "found_contract_data_in_int" in static_analysis_data.keys():
            # for sGuard dataset
            if key not in static_analysis_data["found_contract_data_in_int"].keys():
                print(f'{key} does not has static analysis data.')
            else:
                contract_data=static_analysis_data['found_contract_data_in_int'][key]
                self.state_variables = list(contract_data['svar_to_int'].keys())
                self.state_variables_in_integer = list(contract_data['int_to_svar'].keys())
                self.state_variables_in_integer=[int(svar) if isinstance(svar,str) else svar for svar in self.state_variables_in_integer]
                self.function_reads_writes = contract_data["function_data"]
                self.function_reads_writes_in_integer = contract_data["function_data_in_int"]
                # print(f'\n function reads and writes from static analysis')
                # for k, v in self.function_reads_writes.items():
                #     print(f'{k}:{v}')
                # print(f'\n function reads and writes(integers) from static analysis')
                # for k, v in self.function_reads_writes_in_integer.items():
                #     print(f'{k}:{v}')
        else:
            if 'contract_function_r_w_in_int' in static_analysis_data.keys():
                # for my dataset (a small dataset)
                self.state_variables = static_analysis_data['contract_svar'][key]
                self.state_variables_in_integer = static_analysis_data['contract_svar_in_int'][key]
                self.state_variables_in_integer = [
                    int(svar) if isinstance(svar, str) else svar for svar in
                    self.state_variables_in_integer]
                self.function_reads_writes = static_analysis_data["contract_function_r_w"][key]
                self.function_reads_writes_in_integer =  static_analysis_data["contract_function_r_w_in_int"][key]
            else:
                # for individual contract
                self.state_variables = static_analysis_data["state_variables"]
                self.state_variables_in_integer =static_analysis_data["state_variables_in_integer"]
                self.state_variables_in_integer = [
                    int(svar) if isinstance(svar, str) else svar for svar in
                    self.state_variables_in_integer]
                self.state_variables_in_integer=list(set(self.state_variables_in_integer))
                self.function_reads_writes = static_analysis_data["function_data"]
                self.function_reads_writes_in_integer =static_analysis_data["function_data_in_integer"]



class CollectContractEnvData_wsa():
    """
    use the static analysis data to collect the required data


    """

    def __init__(self, envDataCollected: EnvDataCollection02,
                 num_state_var: int = 24, num_reads: int = 3,
                 num_writes: int = 3):

        self.envDataCollected = envDataCollected
        self.num_state_var = num_state_var
        self.num_reads = num_reads
        self.num_writes = num_writes

        self.state_variables_in_integer = sorted(
            self.envDataCollected.state_variables_in_integer)
        self.selected_svar = []

        self.function_data = {}  # the keys, names, and vectors of functions
        self.function_value = []
        self.function_value_n0 = []

    def get_functions_r_w_in_index(self):
        """
        use the indices to represent the state variables read/written by each function

        """

        if len(self.state_variables_in_integer) > self.num_state_var:
            self.selected_svar = self.state_variables_in_integer[
                                 0:self.num_state_var]
        else:
            self.selected_svar = self.state_variables_in_integer + [0] * (
                        self.num_state_var - len(
                    self.state_variables_in_integer))

        func_read_write_in_index = {}

        for func in self.envDataCollected.function_reads_writes_in_integer.keys():
            r_w_info = self.envDataCollected.function_reads_writes_in_integer[
                func]

            read_int = []
            if "reads" in r_w_info.keys():
                read_int = deepcopy(r_w_info["reads"])

            write_int = []
            if "writes" in r_w_info.keys():
                write_int = deepcopy(r_w_info["writes"])

            if len(read_int) == 0 and len(write_int) == 0:
                continue

            if len(read_int) > self.num_reads:
                read_int = sorted(read_int, reverse=False)
                read_int = read_int[0:self.num_reads]
            elif len(read_int) < self.num_reads:
                read_int += [-1] * (self.num_reads - len(read_int))

            if len(write_int) > self.num_writes:
                write_int = sorted(write_int, reverse=False)
                write_int = write_int[0:self.num_writes]
            elif len(write_int) < self.num_writes:
                write_int += [-1] * (self.num_writes - len(write_int))

            read_indices = [1 if svar in read_int else 0 for svar in
                            self.selected_svar]
            write_indices = [1 if svar in write_int else 0 for svar in
                             self.selected_svar]
            func_read_write_in_index[func] = {"reads": read_indices,
                                              'writes': write_indices}

            # if func in ['BHT.contTransfer(address,uint256)','BHE.contTransfer(address,uint256)']:
            #     print(f'---------------')
            #     print(f'self.selected_svar:{self.selected_svar}')
            #     print(f'read_int:{read_int}')
            #     print(f'read_indices:{read_indices}')
            #     print(f'write_indices:{write_indices}')

        return func_read_write_in_index

    def collect_function_data(self):
        func_read_write_in_index_vector = self.get_functions_r_w_in_index()

        # combine read vectors and write vectors
        func_rw_in_index = {key: [e1 * 2 + e2 for e1, e2 in
                                  zip(value['reads'], value['writes'])] for
                            key, value in
                            func_read_write_in_index_vector.items()}

        self.function_value = [0] * self.num_state_var
        for k, value in func_rw_in_index.items():

            self.function_value = [e1 + e2 for e1, e2 in
                                   zip(self.function_value, value)]



        self.function_value_n0 = [0] * self.num_state_var
        for k, value in func_rw_in_index.items():
            if k not in ['constructor', 'constructor()']:

                self.function_value_n0 = [e1 + e2 for e1, e2 in
                                          zip(self.function_value_n0, value)]

                # print(f'self.function_value_n0:{self.function_value_n0}')
        # func_rw_data=[[key, value] for key,value in func_rw_in_index.items()]
        # sorted_func_rw_data=sort_lists(func_rw_data,index=1)

        for name, comb_rw_vector_in_index in func_rw_in_index.items():

            reads = \
            self.envDataCollected.function_reads_writes_in_integer[name][
                'reads']
            writes = \
            self.envDataCollected.function_reads_writes_in_integer[name][
                'writes']

            reads = sorted(reads, reverse=False)
            writes = sorted(writes, reverse=False)
            # from comb_rw_in_idx_new to get reads and writes and the last element used to distinguish functions with the same presentation

            reads_ = reads[0:3] if len(reads) >= 3 else reads + [0] * (
                        3 - len(reads))
            writes_ = writes[0:3] if len(writes) >= 3 else writes + [0] * (
                        3 - len(writes))

            func_rw_in_concate = reads_ + writes_

            if '(' in name:
                pure_name = name.split('(')[0]
            else:
                pure_name = name
            if '.' in pure_name:
                pure_name = pure_name.split('.')[-1]

            if name == 'constructor':

                self.function_data[name] = {'name': name,
                                            "pure_name": pure_name,
                                            "reads": reads,
                                            "writes": writes,
                                            "vector_in_index_rw": comb_rw_vector_in_index,
                                            # old: comb_rw_vector_in_index,
                                            "vector_rw_in_concate": func_rw_in_concate
                                            }

            else:

                self.function_data[name] = {'name': name,
                                            "pure_name": pure_name,
                                            "reads": reads,
                                            "writes": writes,
                                            "vector_in_index_rw": comb_rw_vector_in_index,
                                            "vector_rw_in_concate": func_rw_in_concate
                                            }

        if 'constructor' not in self.function_data.keys():
            self.function_data['constructor'] = {'name': "constructor()",
                                                 "pure_name": "constructor",
                                                 "reads": [],
                                                 "writes": [],
                                                 "vector_in_index_rw": [
                                                                           0] * self.num_state_var,
                                                 "vector_rw_in_concate": [0] * (
                                                             self.num_reads + self.num_writes)
                                                 }

    def obtain_contract_data(self):
        self.collect_function_data()
        data = {
            "state_variable": self.envDataCollected.state_variables,
            "state_variables_in_integer": self.state_variables_in_integer,
            "state_variables_selected": self.selected_svar,
            # select 8 state variables
            "function_value": self.function_value,
            "function_value_n0": self.function_value_n0,
            "function_data": self.function_data,
            "function_sequences": self.envDataCollected.function_sequence_writes,
            "functions_in_sequences": self.envDataCollected.functions_in_sequences,
            "target_functions": self.envDataCollected.targets,
            "start_functions": self.envDataCollected.start_functions
        }

        return data


def list_files(directory,extenion:str=".txt"):
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(extenion):
                files.append(os.path.join(root, filename))
    return files

def get_key_from_list(data:list)->str:
    if len(data)==0: return ""
    if len(data)==1: return f'{data[0]}'
    key=f'{data[0]}'
    for item in data[1:]:
        key+=f'#{item}'
    return key


def parepare_rw_data_and_or_sequences(solidity_name:str,contract_name:str,solc_version:str, start_functions:list=[],target_functions:list=[]):

    # collect valid sequences ()
    env_data = EnvDataCollection02(solidity_name, contract_name,[])
    env_data.init()
    env_data.start_functions=start_functions
    env_data.targets=target_functions

    # collect rw data (require the mapping from svar names to integers)
    contracts_static_data = load_a_json_file(f'{contract_json_file_path}{rl.config.rl_cur_parameters["contract_rw_data_json_file_name"]}')
    svar_to_int=contracts_static_data['svar_to_int']
    svar_by_type=contracts_static_data['svar_by_type']

    svar_names, svar_constants,svar_type,function_r_w=get_rw_data_from_slither(contract_solidity_path,solidity_name,contract_name,solc_version=solc_version)

    if len(svar_names)==0 and len(function_r_w)==0:return {}
    #================================
    # map state variables to integers
    my_svar_to_int = {}
    one_key=list(svar_to_int.keys())[0]
    if ',' not in one_key:
        for svar in svar_names:
            if svar in svar_to_int.keys():
                my_svar_to_int[svar]=svar_to_int[svar]
            else:
                tp=svar_type[svar]
                if tp not in svar_by_type.keys():
                    # temporarily focus on the case of my dataset
                    # possible multiple state variables are treated as the same
                    for item in ['byte','uint','int']:
                        if item in tp:
                            tp=item
                    if tp==svar_type[svar]:
                        # treat like a contract type
                        tp='Roles.Role'
                if tp in svar_by_type.keys():
                    svar_names_of_tp = svar_by_type[tp]
                    select_a_svar = random.choice(svar_names_of_tp)
                    my_svar_to_int[svar] = svar_to_int[select_a_svar]
                else:
                    # ignore this state variable as its type is not considered
                    pass
    else:
        for svar in svar_names:
            tp=svar_type[svar]
            s_key=f'{svar},{tp}'
            if s_key in svar_to_int:
                my_svar_to_int[svar]=svar_to_int[s_key]
            else:
                svar_names_of_tp=svar_by_type[tp]
                select_a_svar = random.choice(svar_names_of_tp)
                my_svar_to_int[svar] = svar_to_int[f'{select_a_svar},{tp}']


    function_rw_in_int={}
    for func, rw_info in function_r_w.items():
        # pure_name= func if "(" not in func else func.split(f'(')[0]
        rw_info_in_int={k:list(set([my_svar_to_int[v] for v in svar_list if v in my_svar_to_int.keys() ])) for k,svar_list in rw_info.items()}
        function_rw_in_int[func]=rw_info_in_int

    my_static_data={
        "state_variables":svar_names,
        "state_variables_in_integer":list(my_svar_to_int.values()),
        "function_data":function_r_w,
        "function_data_in_integer":function_rw_in_int
    }

    env_data.receive_data_from_static_analysis(my_static_data)
    conEnvData = CollectContractEnvData_wsa(env_data,num_state_var=rl.config.rl_cur_parameters["NUM_state_var"])
    data = conEnvData.obtain_contract_data()
    return data


def contract_data_mapping_function_to_integer(contracts_data:dict,target_contract_data:dict):
    # ================================
    # map functions to integers based on existing data
    contract_function_to_int_by_svar = contracts_data[
        'contract_function_to_int_by_svar']
    contract_by_svar=contracts_data['contract_by_svar']

    function_to_int={}
    int_to_function={}
    int_key= 0

    svar_key=get_key_from_list(target_contract_data['state_variables_selected'])
    if svar_key in contract_by_svar.keys():
        if svar_key in contract_function_to_int_by_svar.keys():
            function_to_int=contract_function_to_int_by_svar[svar_key]['function_to_int']
            int_to_function = contract_function_to_int_by_svar[svar_key]['int_to_function']
            int_key=max(list(int_to_function.keys()))

    for name, func_data in target_contract_data["function_data"].items():
        if func_data["pure_name"] in ['constructor']: continue
        func_key = f'{func_data["pure_name"]},{get_key_from_list(func_data["vector_rw_in_concate"])}'
        if func_key not in function_to_int.keys():
            int_key += 1
            function_to_int[func_key] = int_key
            int_to_function[int_key] = func_key


    svar_selected = target_contract_data['state_variables_selected']
    key_svar = get_key_from_list(svar_selected)
    function_to_int_data = {
            'function_to_int': function_to_int,
            'int_to_function': int_to_function}

    func_pure_name_to_int = {}
    int_to_func_pure_name = {}
    function_data_with_int_key = {}
    for func_name, func_data in target_contract_data['function_data'].items():
        if func_data["pure_name"] in ['constructor']: continue
        func_key = f'{func_data["pure_name"]},{get_key_from_list(func_data["vector_rw_in_concate"])}'
        int_key = int(function_to_int_data['function_to_int'][func_key])
        func_data['int_key'] = int_key
        func_data['func_key'] = func_key
        func_pure_name_to_int[func_data["pure_name"]] = int_key
        int_to_func_pure_name[int_key] = func_data["pure_name"]
        function_data_with_int_key[str(int_key)] = func_data

    # get function sequences in integer
    sequences_in_int = []
    sequence_writes = {}
    for key, writes in target_contract_data['function_sequences'].items():
        if key == 'constructor':
            continue

        func_seq = get_seq_from_key(key)

        func_seq_int = [func_pure_name_to_int[func] for func in func_seq if
                        func in func_pure_name_to_int.keys()]

        sequences_in_int.append(func_seq_int)
        new_key = get_key_from_list(func_seq_int)
        sequence_writes[new_key] = writes

    targets = []
    starts = []
    for func in target_contract_data['target_functions']:
        func=func if '(' not in func else func.split('(')[0]
        if func in func_pure_name_to_int.keys():
            targets.append(func_pure_name_to_int[func])
        else:
            print(f'target {func} do not have data thus will be ignored')



    for func in target_contract_data['start_functions']:
        func = func if '(' not in func else func.split('(')[0]
        if func in func_pure_name_to_int.keys():
            starts.append(func_pure_name_to_int[func])

    func_in_seq_in_integer = []
    for func in target_contract_data["functions_in_sequences"]:
        if func in func_pure_name_to_int.keys():
            func_in_seq_in_integer.append(func_pure_name_to_int[func])

    target_contract_data_final = {
        "state_variable": target_contract_data["state_variable"],
        "state_variables_in_integer": target_contract_data["state_variables_in_integer"],
        "state_variables_selected": target_contract_data["state_variables_selected"],
        # select 8 state variables
        "function_value": target_contract_data["function_value"],
        "function_value_n0": target_contract_data["function_value_n0"],
        "function_data": function_data_with_int_key,
        "func_pure_name_to_int": func_pure_name_to_int,
        "int_to_func_pure_name": int_to_func_pure_name,
        "function_sequences": target_contract_data["function_sequences"],
        "function_sequences_in_integer": sequences_in_int,
        "sequence_writes": sequence_writes,
        # the writes from symbolic execution not static analysis（careful)
        "functions_in_sequences": target_contract_data["functions_in_sequences"],
        "functions_in_sequences_in_integer": func_in_seq_in_integer,
        "target_functions": target_contract_data["target_functions"],
        "start_functions": target_contract_data["start_functions"],
        "target_functions_in_integer": targets,
        "start_functions_in_integer": starts
    }
    return target_contract_data_final


def collect_env_data(solidity_name:str,contract_name:str, solc_version:str="0.4.25", start_functions:list=[],target_functions:list=[]):
    contracts_data = load_a_json_file(
        f'{contract_json_file_path}{rl.config.rl_cur_parameters["contract_data_for_env_construction_json_file_name"]}')

    contract_key = f'{solidity_name}{contract_name}'
    if contract_key in contracts_data.keys():
        # contracts in training or testing (have both static rw data and valid sequences collected)
        data = contracts_data[contract_key]
    else:
        # contracts not in either training or testing sets (have static rw data)
        rw_data_and_seq = parepare_rw_data_and_or_sequences(solidity_name, contract_name,
                                  solc_version=solc_version,
                                  target_functions=target_functions,
                                  start_functions=start_functions)
        if len(rw_data_and_seq)==0:
            data={}
        else:
            data=contract_data_mapping_function_to_integer(contracts_data,rw_data_and_seq)
    if len(data)>0:
        # remove repeated sequences
        sequences=data["function_sequences_in_integer"]
        left_s=[]
        for s in sequences:
            if s not in left_s:
                left_s.append(s)
        # note that the sequences given to   ContractDynamics must be sorted based on the length of the sequences in ascending order
        left_s.sort(key=len,reverse=False)

        conDynamics=ContractDynamics(left_s,data["sequence_writes"],goals=data["target_functions_in_integer"])
        return conDynamics, data
    else:
        return None,{}



