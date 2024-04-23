from copy import copy

import fdg.global_config
from fdg.output_data import print_coverage
from mythril.laser.plugin.plugins.coverage import InstructionCoveragePlugin
import numpy as np

class FunctionCoverage():
    def __init__(self,coveragePlugin:InstructionCoveragePlugin):
        self.coverage_plugin=coveragePlugin # the plugin that record the instructions visited.
        self.function_instruction_indices= {} # key: function pure name(only pure name is available from SolidityContract), value: the indices of instructions belonging to the function
        self.contract_bytecode='' # the bytecode of the contract that is used to retrieve the instruction coverage status from the coverage plugin

        self.function_coverage={}
        self.coverage=0
        self.deep_functions=[]
        self.deep_functions_1st_time = []  # record how many deep functions are there

    def feed_function_intruction_indices(self, function_instruction_indices:dict):
        self.function_instruction_indices=function_instruction_indices
        # initialize coverage for each function except constructor
        for ftn, ftn_instr_list in self.function_instruction_indices.items():
            # if ftn=='constructor' or ftn=='fallback':continue
            if ftn == 'constructor': continue
            if len(ftn_instr_list)==0:continue
            self.function_coverage[ftn] = 0 / len(ftn_instr_list)

    def set_runtime_bytecode(self,runtime_bytecode:str):
        self.contract_bytecode=runtime_bytecode

    def print_coverage(self):
        print_coverage(self.coverage,self.function_coverage,'coverage')

    def get_deep_functions_1st_time(self):
        return [ftn for ftn,_ in self.deep_functions_1st_time]

    def compute_contract_coverage(self,runtime_bytecode:str):
        if runtime_bytecode in self.coverage_plugin.coverage.keys():
            # get the instruction list belonging to the contract
            code_cov = self.coverage_plugin.coverage[runtime_bytecode ]
            self.coverage = sum(code_cov[1]) / float(code_cov[0]) * 100


    def compute_coverage(self):
        if self.contract_bytecode in self.coverage_plugin.coverage.keys():
            code_cov = self.coverage_plugin.coverage[self.contract_bytecode]
            self.coverage = sum(code_cov[1]) / float(code_cov[0]) * 100 # get contract coverage

            # compute coverage for each function
            instructions_cover_record = code_cov[1]
            if len(instructions_cover_record) > 0:
                instr_array = np.array(instructions_cover_record)
                for ftn,cov in self.function_coverage.items():
                    if cov==100:continue
                    ftn_instruction_indices=self.function_instruction_indices[ftn]
                    try:
                        status = instr_array[ftn_instruction_indices]
                        cov_instr = sum(status)
                        cov = cov_instr / float(len(status)) * 100
                        self.function_coverage[ftn]=cov
                    except IndexError:
                        print(f'The instructions of {ftn} are not all in the target contract.')
                        continue

    def get_contract_coverage(self):
        return self.coverage


    def get_coverage_for_a_function(self,ftn_name:str):
        if ftn_name in self.function_coverage.keys():
            return self.function_coverage[ftn_name]
        else: return -1


    def compute_deep_functions(self):
        """
        get a deep functions based the code coverage of each functions

        :return:
        """
        deep_ftn_coverage=[]
        for ftn_name, coverage in self.function_coverage.items():
            if coverage==0:
                print(f'{ftn_name}:{coverage} is not considered')
                continue
            if coverage<fdg.global_config.function_coverage_threshold:
                deep_ftn_coverage.append((ftn_name,coverage))

        self.deep_functions=deep_ftn_coverage
        if len(self.deep_functions_1st_time)==0:
            self.deep_functions_1st_time=self.deep_functions
        # order functions based on coverage
        self.deep_functions.sort(key=lambda x:x[1])
        return self.deep_functions

    def get_deep_functions(self)->list:
        """
        :return: a list of numbers indicating deep functions
        """
        return self.deep_functions



    def print_not_covered_instructions(self,ftn_name:str,instruction_list:list):
        if self.contract_bytecode in self.coverage_plugin.coverage.keys():
            code_cov = self.coverage_plugin.coverage[self.contract_bytecode]
             # compute coverage for each function
            instructions_cover_record = code_cov[1]
            if len(instructions_cover_record) > 0:
                instr_array = np.array(instructions_cover_record)
                if ftn_name in self.function_instruction_indices.keys():
                    ftn_instr_indices=self.function_instruction_indices[ftn_name]
                    print(f'== all instructions for {ftn_name}')
                    for instr_idx in ftn_instr_indices:
                        print(f'  {instruction_list[instr_idx]}')

                    print(f'== uncoverd instructions for {ftn_name}')
                    for instr_idx in ftn_instr_indices:
                        if not instr_array[instr_idx]:
                            print(f'  {instruction_list[instr_idx]}')



if __name__=='__main__':
    a=np.array(list(range(10)))
    print(a)
    print(a[[2,3,4]])
