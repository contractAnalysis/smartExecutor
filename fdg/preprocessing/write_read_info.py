

from fdg.output_data import output_write_read_data
from fdg.preprocessing.slot_location import max_length, \
    get_slot_from_location_expression

from mythril.laser.ethereum.state.global_state import GlobalState


class Function_Write_Read_Info():
    def __init__(self,all_functions:list):
        self.all_functions=all_functions

        self.write_slots={}
        self.read_slots={}

        self.reads_addr_location={} # collected from SLOAD
        self.writes_addr_location={} # collected from SSTORE


    def print_write_read_info(self):
        output_write_read_data(self.read_slots,
                               self.write_slots,
                               { },
                               self.reads_addr_location,
                               self.writes_addr_location,
                               'ftn_write_read_info.txt',
                               'writes and reads in functions'
                               )



    def update_sload(self, state:GlobalState):
        """
        read locations from address
        note: from an address (instruction) different state variables can be read at differnt loops
        :param state:
        :return:
        """
        function = state.environment.active_function_name
        address = state.instruction['address']
        location = state.mstate.stack[-1]
        try:
            location.__str__()[max_length]
        except IndexError:

            if function not in self.reads_addr_location.keys():
                self.reads_addr_location[function] = {}
            if address not in self.reads_addr_location[function].keys():
                # only record one location
                self.reads_addr_location[function][address] = [location]
            else:
                if location not in self.reads_addr_location[function][address]:
                    self.reads_addr_location[function][address] += [location]


    def update_sstore(self, state:GlobalState):
        """
        get write location
        note: from an address (instruction), different state variables can be written in different loops.

        :param state:
        :return:
        """
        function = state.environment.active_function_name
        address = state.instruction['address']
        location = state.mstate.stack[-1]
        try:
            location.__str__()[max_length]
        except IndexError:

            if function not in self.writes_addr_location.keys():
                self.writes_addr_location[function]={}

            if address not in self.writes_addr_location[function].keys():
                # at each address, only record one location, the other locations are related to the first one
                self.writes_addr_location[function][address]=[location]
            else:
                if location not in self.writes_addr_location[function][address]:
                    self.writes_addr_location[function][address] += [location]

    def refine_read_write_slots(self):
        for ftn_name,writes in self.writes_addr_location.items():
            my_slots=[]
            locations_all=[]
            for addr,locations in writes.items():
                for loc in locations:
                    if loc not in locations_all:
                        locations_all.append(loc)

            for loc in locations_all:
                re_slot=get_slot_from_location_expression(loc)
                if len(re_slot)>0:
                    if re_slot not in my_slots:
                        my_slots.append(re_slot)
            self.write_slots[ftn_name]=my_slots

        for ftn_name,reads in self.reads_addr_location.items():
            my_slots=[]
            locations_all = []
            for addr, locations in reads.items():
                for loc in locations:
                    if loc not in locations_all:
                        locations_all.append(loc)

            for loc in locations_all:
                re_slot=get_slot_from_location_expression(loc)
                # if re_slot is not None:
                if len(re_slot) > 0:
                    if re_slot not in my_slots:
                        my_slots.append(re_slot)

            self.read_slots[ftn_name]=my_slots


