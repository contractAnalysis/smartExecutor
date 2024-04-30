import re

from fdg.output_data import my_print
from fdg.utils import str_without_space_line
from mythril.laser.smt import BitVec
from z3 import  Z3Exception

"""
extract the storage locations from Concat() expressions, condition expressions, and (not know yet)

observation: the expression can be extracted multiple times, so, saving the extracted results
On HoloToken.sol: before saving the results: 28 times
after saving the results: 6


"""


max_length=10000
expression_str_to_slot_normal={} # used in the normal execution process

def map_concrete_hash_key_to_slot_normal(expression:BitVec, data:BitVec):
    """
    pplied in create_keccak(self, data: BitVec) n keccak_function_manager.py module
    """
    if not expression.symbolic:
        expr_str = str_without_space_line(expression)
        data_str=str_without_space_line(data)
        if expr_str not in expression_str_to_slot_normal.keys():
            if data_str in expression_str_to_slot_normal.keys():
                final_data_str=expression_str_to_slot_normal[data_str]
                expression_str_to_slot_normal[expr_str] = final_data_str
                # print(f'map: {expr_str}')
                # print(f'to: {final_data_str}')
            else:
                expression_str_to_slot_normal[expr_str] = data_str
                # print(f'map: {expr_str}')
                # print(f'to: {data_str}')


def identify_slot_from_symbolic_slot_expression(concat_expr: BitVec) -> str:
    """
    get the locations of storage from expressions:
        Concat(0,x,location)
        keccak256_512(Concat(0,x,location))
        need to think about the case of array

    also consider the case of concrete hash, the location info is collected in a place where it is created.
    """

    def map_expr_str_to_slot(expr_str:str)->str:
        matched_expr = find_matched_expr(expr_str,
                                         expression_str_to_slot_normal.keys())
        if matched_expr is not None:
            temp = expression_str_to_slot_normal[matched_expr]
            if temp in expression_str_to_slot_normal.keys():
                return expression_str_to_slot_normal[temp]
            else:
                return temp

        slot = expr_str
        # save the result
        if expr_str not in expression_str_to_slot_normal.keys():
            expression_str_to_slot_normal[expr_str] = slot
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
            expr_str = str_without_space_line(concat_expr)
            # check if it is already considered once
            return map_expr_str_to_slot(expr_str)

    if isinstance(concat_expr, str):
        if concat_expr.isdigit():
            return map_expr_str_to_slot(concat_expr)

    str_data = str_without_space_line(concat_expr)
    if len(str_data)>=max_length:
        # print(f'reach max length')
        return ""

    # handle the case: 62514009886607029107290561805838585334079798074568712924583230797734656856475 +
    # Concat(If(1_calldatasize <= 4, 0, 1_calldata[4]),
    if str_data.count('+')==1:
        items=str_data.split('+')
        if items[0].isdigit() and len(items[0])>=10:
            return map_expr_str_to_slot(items[0])
        else:
            str_data=items[1]


    last_parameter = ""
    try:

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
            else:
                # print(f'Failed to identify a slot from {concat_expr}')
                last_parameter=""

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
            my_print(f'slot_str:{slot_str}')
            my_print(
                f'Check why original slot can not be identified for {slot}.')
            return False
    else:
        slot_str = str(slot)

    slot_str_list = [identify_slot_from_symbolic_slot_expression(s) for s in slot_list]

    my_print(f'is slot {slot_str} in slots {slot_str_list}?')
    if slot_str in slot_str_list:
        my_print(f'\t yes')
        return True
    else:
        my_print(f'\t no')
        return False


def common_elements(lst_1_str:list,lst_2_str:list)->list:

    common_ele=[]
    for ele in lst_1_str:
        if ele in lst_2_str:
            common_ele.append(ele)
    return common_ele





