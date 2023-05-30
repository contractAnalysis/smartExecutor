import time
from copy import copy

from z3 import BitVecRef, BitVecNumRef

import fdg
from fdg.preprocessing.address_collection import collect_value_for_sender
from fdg.output_data import output_reads_in_conditions_1

from fdg.preprocessing.slot_location import Slot_Location

from fdg.utils import str_without_space_line
from mythril.laser.ethereum.state.global_state import GlobalState
from mythril.laser.smt import BitVec
from mythril.laser.smt.expression import simplify_yes


class ReadInCondition():
    def __init__(self,functions:list):
        self.all_functions=functions
        self.fun_read_in_conditions={ftn: {} for ftn in functions}
        self.function_conditions={ftn:{} for ftn in functions}

        self.read_slots_in_conditions={}
        self.read_addr_slots_in_conditions={}


    def extract_from_condition_x(self, state: GlobalState):
        """
        extract the location(slot) of the storage read in conditions
        :param state:
        :return:
        """
        function = state.environment.active_function_name
        address = state.instruction['address']
        # obtain the index to storage if there is
        if function not in ['fallback']:
            # it takes a lot of time to get the condition from the stack and convert it to str in version v0.23.22

            print('\n-------')
            seconds_start = time.time()
            condition = state.mstate.stack[-2]
            # print(f'condition:{condition}')
            seconds_end = time.time()
            print(f'takes time:{seconds_end - seconds_start}')

            seconds_start = time.time()
            condi_str = str_without_space_line(str(condition))
            seconds_end = time.time()
            print(f'takes time:{seconds_end - seconds_start}')
            print('-------\n')

            simplify_condi = simplify_yes(copy(condition))
            simplify_condi_str = str_without_space_line(simplify_condi)

            if fdg.global_config.optimization == 1:
                collect_value_for_sender(simplify_condi_str)  # collect the value that is compared with msg.sender

            self.add_conditions(function, address, condi_str)

            temp_condi = ''
            if 'Store(K' in condi_str:
                temp_condi = condition
            elif 'Store(K' in simplify_condi_str:
                temp_condi = simplify_condi

            if isinstance(temp_condi, BitVec):
                locations = []
                def go_deep(item: BitVecRef):
                    if isinstance(item, BitVecNumRef):
                        return
                    elif str(item.decl()) == 'Select':
                        children = item.children()
                        if str(children[0].decl()) == 'Store':
                            if children[1] not in locations:
                                locations.append(children[1]) # the second child is the position of the storage
                        return
                    else:
                        for child in item.children():
                            go_deep(child)

                condi_raw = temp_condi.raw
                for item in condi_raw.children():
                    go_deep(item)
                self.add_read_in_condition(function, address, locations)

    def extract_from_condition(self, state: GlobalState):
        """
        extract the location(slot) of the storage read in conditions
        :param state:
        :return:
        """
        function = state.environment.active_function_name
        address = state.instruction['address']
        # obtain the index to storage if there is
        if function not in ['fallback']:
            condition = state.mstate.stack[-2]

            condi_str = str_without_space_line(str(condition))

            simplify_condi = simplify_yes(copy(condition))
            simplify_condi_str = str_without_space_line(simplify_condi)

            if fdg.global_config.optimization == 1:
                collect_value_for_sender(simplify_condi_str)  # collect the value that is compared with msg.sender

            self.add_conditions(function, address, condi_str)

            temp_condi = ''
            if 'Store(K' in condi_str:
                temp_condi = condition
            elif 'Store(K' in simplify_condi_str:
                temp_condi = simplify_condi

            if isinstance(temp_condi, BitVec):
                locations = []
                def go_deep(item: BitVecRef):
                    if isinstance(item, BitVecNumRef):
                        return
                    elif str(item.decl()) == 'Select':
                        children = item.children()
                        if str(children[0].decl()) == 'Store':
                            if children[1] not in locations:
                                locations.append(children[1]) # the second child is the position of the storage
                        return
                    else:
                        for child in item.children():
                            go_deep(child)

                condi_raw = temp_condi.raw
                for item in condi_raw.children():
                    go_deep(item)
                self.add_read_in_condition(function, address, locations)

    def add_conditions(self,function:str, address:int,condition:BitVec):
        if function=='constructor':return
        if address not in self.function_conditions[function].keys():
            self.function_conditions[function][address]=[condition]
        else:
            self.function_conditions[function][address]+=[condition]

    def add_read_in_condition(self, function:str, address:int, locations:list):
        if function == 'constructor': return
        if len(locations)==0:return
        try:
            if address not in self.fun_read_in_conditions[function].keys():
                self.fun_read_in_conditions[function][address]=locations
            else:
                for loc in locations:
                    if loc not in self.fun_read_in_conditions[function][address]:
                        self.fun_read_in_conditions[function][address]+=[loc]
        except:
            print(f'Exception at adding locations {locations} to address {address} for function {function}')

    def get_read_slots(self,slot_location:Slot_Location):
        # print(f'\n====== read_in_conditions.py =====')
        for ftn, read_info in self.fun_read_in_conditions.items():
            self.read_slots_in_conditions[ftn]=[] # keep all slots read in conditions
            self.read_addr_slots_in_conditions[ftn]={} # organize slots based on bytecode addresses
            ftn_slots=[]
            for addr,loc_list in read_info.items():
                addr_slots=[]
                for loc in loc_list:
                    try:
                        loc_str=str_without_space_line(loc)
                        mapped_slots = slot_location.map_location_to_slot(loc)
                        if len(mapped_slots)==0:
                            mapped_slots=[loc_str]

                        for item in mapped_slots:
                            if item  not in ftn_slots:
                                ftn_slots.append(item )
                            if item  not in addr_slots:
                                addr_slots.append(item )
                    except:
                        print(f'{loc} is not mapped to a slot (read_in_conditions.py).')
                self.read_addr_slots_in_conditions[ftn][addr]=addr_slots
            self.read_slots_in_conditions[ftn]=ftn_slots






    def print_read_slot_info(self):
        output_reads_in_conditions_1(self.fun_read_in_conditions,
                                           self.read_slots_in_conditions,
                                           self.read_addr_slots_in_conditions,
                                            self.function_conditions,
                                           "reads_in_conditions.txt",
                                           "read information in conditions",
                                           )


