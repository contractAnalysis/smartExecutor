import time
from copy import deepcopy, copy

import fdg.global_config
from fdg.output_data import output_key_to_slot

from fdg.preprocessing.instruction_coverage import InstructionCoverage

from fdg.preprocessing.read_in_conditions import ReadInCondition
from fdg.preprocessing.slot_location import expression_str_to_slot

from fdg.preprocessing.write_read_info import Function_Write_Read_Info
from mythril.laser.ethereum.function_managers.keccak_function_manager import keccak_function_manager
from mythril.laser.ethereum.strategy.basic import DepthFirstSearchStrategy, BreadthFirstSearchStrategy
from mythril.laser.ethereum.strategy.extensions.bounded_loops import BoundedLoopsStrategy


import logging

from mythril.laser.ethereum.transaction.symbolic import execute_message_call_preprocessing

log = logging.getLogger(__name__)
"""
For each function:
    need to collect conditions
    instruction indices
    read/write slots

expression to slot map (can not simplify expression, because the slot information can be lost if the expression can simplified to a concrete value.

concrete addresses used in the contract, which may be used to check against msg.sender which is implemented an array of three concrete addresses by default

"""
class Preprocessing():
    def __init__(self,method_identifiers:dict,state,contract_address):
        self.function_to_signature=method_identifiers

        self.read_in_conditions=ReadInCondition(list(method_identifiers.keys()))
        # print_dict(method_identifiers,"function and signature")

        self.write_read_info=Function_Write_Read_Info(list(method_identifiers.keys()))

        self.instruction_cov=InstructionCoverage(list(method_identifiers.keys()))


        self.timeout=False
        self.coverage=0

        self.save_keccak_function_manager=None

    def main_preprocessing_start(self,iteration:int,laserEVM):
        fdg.global_config.tx_len = 1  # temporarily used as a flag
        log.info(f'start_iteration preprocessing.')

        # save keccak_function_manager
        self.save_keccak_function_manager=deepcopy(keccak_function_manager)

        laserEVM.open_states = laserEVM.open_states[0:1]

        # laserEVM.strategy=DepthFirstSearchStrategy(laserEVM.work_list,laserEVM.max_depth)
        laserEVM.strategy = BreadthFirstSearchStrategy(laserEVM.work_list, laserEVM.max_depth)

        laserEVM.extend_strategy(BoundedLoopsStrategy, loop_bound=2)
        return


    def main_preprocessing_end(self, iteration:int):
        # set back the save data
        keccak_function_manager.set_data(self.save_keccak_function_manager)

        self.timeout = fdg.global_config.flag_preprocess_timeout
        self.coverage=self.instruction_cov.call_at_end_of_preprocessing()

        seconds_start = time.time()

        output_key_to_slot(expression_str_to_slot,'key_to_slot.txt','hash values to the corresponding slots')

        self.write_read_info.refine_read_write_slots()
        self.write_read_info.print_write_read_info()  #output

        seconds_end = time.time()
        # print(f'self.write_read_info time(s):{seconds_end - seconds_start}')

        seconds_start = time.time()

        self.read_in_conditions.extract_read_slots_in_conditions()
        self.read_in_conditions.print_read_slot_info()

        seconds_end = time.time()
        # print(f'self.read_in_conditions time(s):{seconds_end - seconds_start}')

        # print(f'\n==== expression_str_to_slot ====')
        # for key,value in expression_str_to_slot.items():
        #     print(f'\texpression: {key}')
        #     print(f'\tslot: {value}')

        log.info(f'end preprocessing.')
        return




def execute_preprocessing(address, laserEVM):

    begin = time.time()
    print("Starting preprocessing.")
    fdg.global_config.flag_preprocessing = True

    # doing preprocesing on a copy of laserEVM.
    # the problem of doing preprocessing on the original laserEVM is that
    # it is hard to set the current state of laserEVM to the previous laserEVM state (generated after contract creation transaction)


    for hook in laserEVM._start_sym_trans_hooks_laserEVM:
        hook(laserEVM)

    execute_message_call_preprocessing(laserEVM, address)

    for hook in laserEVM._stop_sym_trans_hooks_laserEVM:
        hook(laserEVM)

    fdg.global_config.flag_preprocessing = False

    print("Ending preprocessing.")#
    end = time.time()
    print(f"preprocessing time(s): {end - begin}")

