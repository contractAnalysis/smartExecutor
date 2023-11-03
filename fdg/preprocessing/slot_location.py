import re
from copy import copy

import fdg
from fdg.preprocessing.address_collection import collect_value_for_sender
from fdg.utils import str_without_space_line


from mythril.laser.smt import (
    BitVec,
)
from z3 import BitVecRef, BitVecNumRef, Z3Exception
from mythril.laser.smt.expression import simplify_yes
"""
extract the storage locations from Concat() expressions, condition expressions, and (not know yet)

observation: the expression can be extracted multiple times, so, saving the extracted results
On HoloToken.sol: before saving the results: 28 times
after saving the results: 6

"""

#----------------------------------------------
# key refers to the location in the storage, it is created through hash function
# the value of get_empty_keccak_hash
# 89477152217924674838424037953991966239322087453347756267410168184682657981552


# used to keep symbolic expressions and their mapped slots
# saved when identify slots from given expressions
expression_str_to_slot={}

max_length=10000 # refers the length of the str version of a symbolic expression


def map_concrete_hash_key_to_slot(expression:BitVec, data:BitVec):
    """
    pplied in create_keccak(self, data: BitVec) n keccak_function_manager.py module
    """
    sim_exp=simplify_yes(expression)
    if not sim_exp.symbolic:
        expr_str = str_without_space_line(expression)
        data_str = str_without_space_line(data)
        if expr_str not in expression_str_to_slot.keys():
            if data_str in expression_str_to_slot.keys():
                final_data_str =expression_str_to_slot[data_str]
                expression_str_to_slot[expr_str] = final_data_str
            else:
                expression_str_to_slot[expr_str] = data_str


def get_slot_from_location_expression(concat_expr:BitVec)->str:
    """

    get the locations of storage from expressions:
        Concat(0,x,location)
        keccak256_512(Concat(0,x,location))
        need to think about the case of array

    also consider the case of concrete hash, the location info is collected in a place where it is created.
    used in preprocessing
    """
    def map_expr_str_to_slot(expr_str:str)->str:
        matched_expr = find_matched_expr(expr_str,
                                         expression_str_to_slot.keys())
        if matched_expr is not None:
            temp = expression_str_to_slot[matched_expr]
            if temp in expression_str_to_slot.keys():
                return expression_str_to_slot[temp]
            else:
                return temp

        slot = expr_str
        # save the result
        if expr_str not in expression_str_to_slot.keys():
            expression_str_to_slot[expr_str] = slot
        return slot

    def find_matched_expr(expr:str, expr_list:list)->str:
        if len(expr)>=10:
            expr_prefix=expr[0:len(expr)-2]
            for e in expr_list:
                if str(e[0:len(e)-2]).__eq__(expr_prefix):
                    return e
            return None
        else:
            if expr in expr_list:
                return expr
            else:
                return None
    if isinstance(concat_expr,BitVec):
        if not concat_expr.symbolic:
            # in case of a concrete hash, find it corresponding slot from a map
            expr_str= str_without_space_line(concat_expr)
            # check if it is already considered once
            return map_expr_str_to_slot(expr_str)


    if isinstance(concat_expr, str):
        if concat_expr.isdigit():
            return map_expr_str_to_slot(concat_expr)

    str_data = str_without_space_line(concat_expr)
    # handle the case: 62514009886607029107290561805838585334079798074568712924583230797734656856475 +
    # Concat(If(1_calldatasize <= 4, 0, 1_calldata[4]),
    if str_data.count('+')==1:
        items=str_data.split('+')
        if items[0].isdigit() and len(items[0]) >= 10:
            return map_expr_str_to_slot(items[0])
        else:
            str_data = items[1]

    last_parameter = ""
    try:
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
            else:
                # print(f'Failed to identify a slot from {concat_expr}')
                last_parameter=""

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
    try:
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
    except:
        pass
    finally:
        return locations



