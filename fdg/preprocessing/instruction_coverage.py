import logging
from copy import copy

from fdg.utils import str_without_space_line
from mythril.laser.ethereum.state.global_state import GlobalState
from mythril.laser.smt.expression import simplify_yes

log = logging.getLogger(__name__)

class InstructionCoverage():
    def __init__(self,functions:list):
        self.coverage={}
        self.contract_coverage=0
        self.function_instruction_indices={ftn:[] for ftn in functions}
        self.function_instruction_complete_status={ftn:False for ftn in functions}
        self.function_special = []  # not completely going through
    def update_coverage(self,global_state:GlobalState,opcode:str):
        # Record coverage
        code = global_state.environment.code.bytecode
        if code not in self.coverage.keys():
            number_of_instructions = len(
                global_state.environment.code.instruction_list
            )
            self.coverage[code] = (
                number_of_instructions,
                [False] * number_of_instructions,
            )
        self.coverage[code][1][global_state.mstate.pc] = True


        # collection instructions for each function
        self.collect_function_instructions(global_state)

        # # compute coverage
        # self.compute_coverage()
        #
        # print(f'{global_state.environment.active_function_name}: {global_state.mstate.pc}: {global_state.instruction}')

        # if global_state.instruction['address']in [120,124,128]:
        #     print(f'xx')
        # function=global_state.environment.active_function_name
        # if function in ['use3(uint32)']:
        #     print(f'{function}: {global_state.mstate.pc}: {global_state.instruction}')
        #

        # self.print_state_info(global_state,opcode,None,'TransferERC20Token(address,uint256)')



    def collect_function_instructions(self,global_state:GlobalState):
        # collection instructions for each function
        function = global_state.environment.active_function_name
        instruction=global_state.instruction
        if function.__eq__('constructor'): return
        if function not in self.function_instruction_indices.keys():
            self.function_instruction_indices[function]=[]
        pc = global_state.mstate.pc
        if pc not in self.function_instruction_indices[function]:
            self.function_instruction_indices[function].append(pc)
        if str(instruction['opcode']) in ['STOP','RETURN']:
            self.function_instruction_complete_status[function]=True

    def call_at_end_of_preprocessing(self):
        # print(f'\nfunction instruction collection status:')
        # for ftn,v in self.function_instruction_complete_status.items():
        #     if not v:
        #         self.function_special.append(ftn)
        #     print(f'\t{ftn}:{v}')
        # print(f'the number of instructions of functions')
        # for k, v in self.function_instruction_indices.items():
        #     print(f'\t{k}:{len(v)}')

        return self.compute_coverage()


    def compute_coverage(self):
        for code, code_cov in self.coverage.items():
            self.contract_coverage = sum(code_cov[1]) / float(code_cov[0]) * 100
            print("preprocessing: Achieved {:.2f}% coverage.".format(self.contract_coverage))
            return self.contract_coverage
    def print_state_info(self,global_state:GlobalState,opcode:str,given_opcode:str=None,target_function:str=None):
        def print_based_on_opcode(opcode:str):
            # print(f'{function}: {global_state.mstate.pc}: {global_state.environment.code.instruction_list}')

            if opcode=='JUMPI':
                print(f'{function}: {global_state.mstate.pc}: {global_state.instruction}')
                condition = global_state.mstate.stack[-2]
                print(f'sim_condi:{str_without_space_line(simplify_yes(copy(condition)))}')
                print(f'  conditi:{str_without_space_line(condition)}')
                # condi = str(condition).translate({ord(term): None for term in string.whitespace})
                # print(f'condition:{condi}')
                # if 'Store' not in condi:
                #     return
                # p = NestedParser()
                # results = p.parse(condi)
                # if len(results) > 0:
                #     print(f'extracted info: {results}')
            else:
                print(f'{function}: {global_state.mstate.pc}: {global_state.instruction}')


        function = global_state.environment.active_function_name
        if target_function is not None:
            if not function.__eq__(target_function):
                return

            if given_opcode is not None:
                if not opcode.__eq__(given_opcode):
                    return

            print_based_on_opcode(opcode)
            return
        print_based_on_opcode(opcode)

