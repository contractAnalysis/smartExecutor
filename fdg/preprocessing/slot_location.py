

from fdg.utils import str_without_space_line

from mythril.laser.smt import (
    BitVec,
)




#----------------------------------------------
# key refers to the location in the storage, it is created through hash function
# the value of get_empty_keccak_hash
# 89477152217924674838424037953991966239322087453347756267410168184682657981552


global hash_key_to_slot
hash_key_to_slot={}


def map_concrete_hash_key_to_slot(data:BitVec,concrete_hash:BitVec):
    """
    pplied in create_keccak(self, data: BitVec) n keccak_function_manager.py module
    """
    concrete_hash_str = str_without_space_line(concrete_hash)
    if concrete_hash_str not in hash_key_to_slot.keys():
        hash_key_to_slot[concrete_hash_str] = data


