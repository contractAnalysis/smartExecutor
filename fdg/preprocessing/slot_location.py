
import fdg
from fdg.output_data import output_key_to_slot
from fdg.utils import str_without_space_line

from mythril.laser.smt import (
    BitVec,
    Function,
)



class Slot_Location():
    def __init__(self):
        self.key_to_slot_origin = {}
        self.hash_key_to_slot_origin = {}

        # map key name to the string version of the key
        self.str_key_to_slot_all = {}  # map all keys (str) to the slots

    def get_data(self):
        self.key_to_slot_origin=fdg.preprocessing.slot_location.key_to_slot
        self.hash_key_to_slot_origin = fdg.preprocessing.slot_location.hash_key_to_slot

        self._map_key_to_slot()

        output_key_to_slot(self.key_to_slot_origin, self.hash_key_to_slot_origin, 'key_to_slot.txt', 'map keys to slots')

    def _map_key_to_slot(self):
        """
        :return:
        """
        for str_key,str_value in self.key_to_slot_origin.items():
            if str_key not in self.str_key_to_slot_all.keys():
                self.str_key_to_slot_all[str_key] = [str_value]

        for str_key,str_value in self.hash_key_to_slot_origin.items():
            if str_key not in self.str_key_to_slot_all.keys():
                self.str_key_to_slot_all[str_key] = [str_value]

    def map_location_to_slot(self, location)->list:
        if not isinstance(location,str):
            str_loc=str_without_space_line(location)
        else:
            str_loc=location
        if str_loc in self.str_key_to_slot_all.keys():
            return self.str_key_to_slot_all[str_loc]
        else:
            return []



#----------------------------------------------
# key refers to the location in the storage, it is created through hash function
# the value of get_empty_keccak_hash
# 89477152217924674838424037953991966239322087453347756267410168184682657981552
global key_to_slot
key_to_slot={}

global hash_key_to_slot
hash_key_to_slot={}

def map_key_to_slot(data:BitVec, data_list:list):
    """
        applied in sha3_() of instructions.py to collect the slots that data belong to
        avoid applying symbolic() method, use str as the key
    """
    # print(f'\n............key.......................')
    # print(f'key:{str_without_space_line(data)}')
    str_data=str_without_space_line(data)
    if str_data not in key_to_slot.keys():
        slot=data_list[-1]
        slot_str=str_without_space_line(slot)
        if slot_str in key_to_slot.keys():
            key_to_slot[str_data] = key_to_slot[slot_str]
        else:
            key_to_slot[str_data] = slot_str


def map_hash_key_to_slot(func_input: BitVec, func: Function):
    """
    applied in _create_condition(self, func_input: BitVec) in keccak_function_manager.py module
    """
    # print(f'\n.......... hash key .........................')
    # print(f'key:{str_without_space_line(func(func_input))}')

    hash_key_str=str_without_space_line(func(func_input))
    if hash_key_str not in hash_key_to_slot.keys():
        func_input_str = str_without_space_line(func_input)
        if func_input_str in key_to_slot.keys():
            hash_key_to_slot[hash_key_str] = key_to_slot[func_input_str]
        else:
            hash_key_to_slot[hash_key_str] = func_input_str



def map_concrete_hash_key_to_slot(data:BitVec,concrete_hash:BitVec):
    """
    pplied in create_keccak(self, data: BitVec) n keccak_function_manager.py module
    """

    # print(f'\n............concrete key.......................')
    # print(f'key:{str_without_space_line(concrete_hash)}')
    # print(f'\tvalue:{str_without_space_line(data)}')

    concrete_hash_str = str_without_space_line(concrete_hash)
    if concrete_hash_str not in hash_key_to_slot.keys():
        data_str = str_without_space_line(data)
        if data_str in key_to_slot.keys():
            hash_key_to_slot[concrete_hash_str]=key_to_slot[data_str]
        else:
            hash_key_to_slot[concrete_hash_str] = data_str

