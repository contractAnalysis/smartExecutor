import re
from copy import copy

import fdg
from fdg.preprocessing.address_collection import collect_value_for_sender
from fdg.preprocessing.slot_location import hash_key_to_slot
from fdg.utils import str_without_space_line
from mythril.laser.smt import BitVec
from mythril.laser.smt.expression import simplify_yes
from z3 import BitVecRef, BitVecNumRef, Z3Exception

"""
extract the storage locations from Concat() expressions, condition expressions, and (not know yet)

observation: the expression can be extracted multiple times, so, saving the extracted results
On HoloToken.sol: before saving the results: 28 times
after saving the results: 6


"""

max_length=10000 # refers the length of the str version of a symbolic expression
expression_str_to_slot={} # used in the preprocessing

expression_str_to_slot_normal={} # used in the normal execution process
def map_concrete_hash_key_to_slot_normal(data:BitVec,concrete_hash:BitVec):
    """
    pplied in create_keccak(self, data: BitVec) n keccak_function_manager.py module
    """
    concrete_hash_str = str_without_space_line(concrete_hash)
    if concrete_hash_str not in expression_str_to_slot_normal.keys():
        expression_str_to_slot_normal[concrete_hash_str] = data


def get_slot_from_location_expression(concat_expr:BitVec)->str:
    """
    get the locations of storage from expressions:
        Concat(0,x,location)
        keccak256_512(Concat(0,x,location))
        need to think about the case of array

    also consider the case of concrete hash, the location info is collected in a place where it is created.
    used in preprocessing
    """

    if isinstance(concat_expr,BitVec) :
        if not concat_expr.symbolic:
            # in case of a concrete hash, find it corresponding slot from a map named hash_key_to_slot
            expr_str= str_without_space_line(concat_expr)

            # check if it is already considered once
            if expr_str in expression_str_to_slot.keys():
                return expression_str_to_slot[expr_str]

            # if not, then extract the slot
            if expr_str in hash_key_to_slot.keys():
                location=hash_key_to_slot[expr_str]
                slot= get_slot_from_location_expression(location)

            else:
                slot= expr_str
            # save the result
            if expr_str not in expression_str_to_slot.keys():
                expression_str_to_slot[expr_str] = slot
            return slot


    last_parameter=""
    try:
        # sim_data = simplify_yes(concat_expr)
        sim_data=concat_expr
        str_data = str_without_space_line(sim_data)

        # handle the case below:
        # 1+keccak256_512(Concat(If(1_calldatasize<=4...)
        # 2+keccak256_512(Concat(If(1_calldatasize<=4...)
        pattern = r"^(\d+\+)\w+"
        results=re.search(pattern, str_data)
        if results:
            # get the str that
            str_data=str_data.split(results.group(1))[-1]

        # check if it is already considered once
        if str_data in expression_str_to_slot.keys():
            last_parameter= expression_str_to_slot[str_data]
        else:
            if str_data.startswith('keccak256_512'):
                # Use regular expressions to find the last parameter within the keccak256_512 function
                last_parameter = re.search(r'keccak256_512\(.*?,(\d+)\)',
                                           str_data)
            else:
                # Use regular expressions to find the last parameter within the Concat function
                last_parameter = re.search(r'Concat\(.*?,(\d+)\)', str_data)

            if last_parameter is not None:
                last_parameter=last_parameter.group(1)
                # print(f'(new) exp:{str_data}')
                # print(f'(new) slot:{last_parameter}')

                # save the result
                expression_str_to_slot[str_data] = str(last_parameter)

    except Z3Exception as ze:
        print(f'Have Z3Exception: {concat_expr}')
    finally:
        return  last_parameter

def extract_locations_read_in_storage_in_a_condition(condition: BitVec)->list:
    """
        collect the storage locations read in a conditions:'If(If(255&UDiv(Store(Store(K(BitVec(256),0),4,0),0,1004753105490295263244812946565948198177742958590)[4],1)==0,1,0)==0,1,0)'
        collect the addresses that are compared with msg.sender
    """
    # get the str versions of condition and its simplified expression.

    condi_str = str_without_space_line(str(condition))

    simplified_condition = simplify_yes(copy(condition))
    simplified_condi_str = str_without_space_line(str(simplified_condition))


    # select which condition to consider
    # not simplified condition may contain ",...,...)[...],...))"
    # simplified condition may lose the storage read information

    if 'Store(K' in simplified_condi_str:
        temp_condi = simplified_condition

    elif 'Store(K' in condi_str:
        temp_condi = condition

    else:
        return []

    # collect the value that is compared with msg.sender
    if fdg.global_config.optimization == 1:
        collect_value_for_sender(simplified_condi_str)

    # collect the locations of the storage that are read.
    locations = []
    if isinstance(temp_condi, BitVec):
        def go_deep(item: BitVecRef):
            if isinstance(item, BitVecNumRef):
                return
            elif str(item.decl()) == 'Select':
                children = item.children()
                if str(children[0].decl()) == 'Store':
                    if children[1] not in locations:
                        # the second child is the position of the storage
                        # raw = z3.BitVecVal(value, size)
                        # return BitVec(raw, annotations)
                        locations.append(BitVec(children[1]))
                return
            else:
                for child in item.children():
                    go_deep(child)

        condi_raw = temp_condi.raw
        for item in condi_raw.children():
            go_deep(item)
    return locations


def identify_slot_from_symbolic_slot_expression(concat_expr: BitVec) -> str:
    """
    get the locations of storage from expressions:
        Concat(0,x,location)
        keccak256_512(Concat(0,x,location))
        need to think about the case of array

    also consider the case of concrete hash, the location info is collected in a place where it is created.
    """
    if isinstance(concat_expr,BitVec):
        if not concat_expr.symbolic:
            return str(concat_expr)
    last_parameter = ""
    try:
        str_data = str_without_space_line(concat_expr)

        # handle the case below:
        # 1+keccak256_512(Concat(If(1_calldatasize<=4...)
        # 2+keccak256_512(Concat(If(1_calldatasize<=4...)
        pattern = r"^(\d+\+)\w+"
        results = re.search(pattern, str_data)
        if results:
            # get the str that
            str_data = str_data.split(results.group(1))[-1]

        # check if it is already considered once
        if str_data in expression_str_to_slot_normal.keys():
            last_parameter = expression_str_to_slot_normal[str_data]
        else:
            if str_data.startswith('keccak256_512'):
                # Use regular expressions to find the last parameter within the keccak256_512 function
                last_parameter = re.search(r'keccak256_512\(.*?,(\d+)\)',
                                           str_data)
            else:
                # Use regular expressions to find the last parameter within the Concat function
                last_parameter = re.search(r'Concat\(.*?,(\d+)\)', str_data)

            if last_parameter is not None:
                last_parameter = last_parameter.group(1)
                # print(f'(new) exp:{str_data}')
                # print(f'(new) slot:{last_parameter}')
                # save the result
                expression_str_to_slot_normal[str_data] = str(last_parameter)

    except Z3Exception as ze:
        print(f'Have Z3Exception: {concat_expr}')
    finally:
        return last_parameter


def is_slot_in_a_list(slot, slot_list: list) -> bool:
    """
    pay special attention to slot that is symbolic. need to find the original slot, i.e., where the dynamic state variable is declared
    """
    if slot.symbolic:
        slot_str = identify_slot_from_symbolic_slot_expression(slot)

        if len(slot_str) == 0:
            print(f'slot_str:{slot_str}')
            print(
                f'Check why original slot can not be identified for {slot}.')
            return False
    else:
        slot_str = str(slot)

    slot_str_list = [identify_slot_from_symbolic_slot_expression(s) for s in slot_list]
    # print(f'slot: {slot_str} ==== slots: {slot_str_list}')
    if slot_str in slot_str_list:
        return True
    else:
        return False







