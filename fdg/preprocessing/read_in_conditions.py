
from fdg.output_data import output_reads_in_conditions_1
from fdg.preprocessing.slot_location import max_length, \
    extract_locations_read_in_storage_in_a_condition, \
    get_slot_from_location_expression
from mythril.laser.ethereum.state.global_state import GlobalState
from mythril.laser.smt import BitVec


class ReadInCondition():
    def __init__(self,functions:list):
        self.all_functions=functions

        self.fun_address_conditions={ftn: {} for ftn in functions}
        self.read_slots_in_conditions = {}

        self.function_conditions={ftn:{} for ftn in functions}



    def collect_conditions(self, state: GlobalState):
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
            try:
                condition.__str__()[max_length]
            except IndexError:
                self.add_conditions(function, address, condition)



    def add_conditions(self,function:str, address:int,condition:BitVec,):
        if function=='constructor':return
        if address not in self.function_conditions[function].keys():
            self.function_conditions[function][address]=[condition]
        else:
            self.function_conditions[function][address]+=[condition]



    def extract_read_slots_in_conditions(self):
        for ftn, addr_conditions in self.function_conditions.items():
            self.read_slots_in_conditions[ftn] = []  # keep all slots read in conditions

            # collect all conditions
            all_conditions=[]
            for conditions in addr_conditions.values():
                for condi in conditions:
                    if condi not in all_conditions:
                        all_conditions.append(condi)

            # find the storage locations read in conditions
            all_locations=[]
            for condi in all_conditions:
                locations=extract_locations_read_in_storage_in_a_condition(condi)
                for loc in locations:
                    if loc not in all_locations:
                        all_locations.append(loc)

            # find all slots from locations
            all_slots=[]
            for loc in all_locations:
                slot=get_slot_from_location_expression(loc)
                if len(slot)>0:
                    if slot not in all_slots:
                        all_slots.append(slot)
            self.read_slots_in_conditions[ftn] = all_slots


    def print_read_slot_info(self):
        output_reads_in_conditions_1(self.read_slots_in_conditions,
                                     self.function_conditions,
                                           "reads_in_conditions.txt",
                                           "read information in conditions",
                                     )


