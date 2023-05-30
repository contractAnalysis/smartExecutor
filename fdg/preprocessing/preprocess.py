import time

import fdg.global_config

from fdg.preprocessing.instruction_coverage import InstructionCoverage

from fdg.preprocessing.read_in_conditions import ReadInCondition
from fdg.preprocessing.slot_location import Slot_Location
from fdg.preprocessing.write_read_info import Function_Write_Read_Info
from mythril.laser.ethereum.strategy.basic import DepthFirstSearchStrategy, BreadthFirstSearchStrategy
from mythril.laser.ethereum.strategy.extensions.bounded_loops import BoundedLoopsStrategy


import logging

from mythril.laser.ethereum.transaction.symbolic import execute_message_call_preprocessing

log = logging.getLogger(__name__)

class Preprocessing():
    def __init__(self,method_identifiers:dict,state,contract_address):
        self.function_to_signature=method_identifiers

        self.read_in_conditions=ReadInCondition(list(method_identifiers.keys()))
        # print_dict(method_identifiers,"function and signature")

        self.write_read_info=Function_Write_Read_Info(list(method_identifiers.keys()))

        self.instruction_cov=InstructionCoverage(list(method_identifiers.keys()))
        self.slot_location = Slot_Location()

        self.timeout=False
        self.coverage=0

    def main_preprocessing_start(self,iteration:int,laserEVM):
        fdg.global_config.tx_len = 1  # temporarily used as a flag
        log.info(f'start_iteration preprocessing.')

        laserEVM.open_states = laserEVM.open_states[0:1]

        # laserEVM.strategy=DepthFirstSearchStrategy(laserEVM.work_list,laserEVM.max_depth)
        laserEVM.strategy = BreadthFirstSearchStrategy(laserEVM.work_list, laserEVM.max_depth)

        laserEVM.extend_strategy(BoundedLoopsStrategy, loop_bound=2)
        return


    def main_preprocessing_end(self, iteration:int):
        self.slot_location.get_data()

        self.timeout = fdg.global_config.flag_preprocess_timeout
        self.coverage=self.instruction_cov.call_at_end_of_preprocessing()

        # seconds_start = time.time()

        self.write_read_info.map_locations_to_slots(self.slot_location)
        self.write_read_info.print_write_read_info()  #output

        # seconds_end = time.time()
        # print(f'self.write_read_info.map_locations_to_slots:{seconds_end - seconds_start}')

        # seconds_start = time.time()
        self.read_in_conditions.get_read_slots(self.slot_location)
        self.read_in_conditions.print_read_slot_info()
        # seconds_end = time.time()
        # print(f'self.read_in_conditions.get_read_slots:{seconds_end - seconds_start}')


        log.info(f'end preprocessing.')
        return




def execute_preprocessing(address, laserEVM):
    from time import time
    begin = time()
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
    end = time()
    print(f"preprocessing time(s): {end - begin}")

