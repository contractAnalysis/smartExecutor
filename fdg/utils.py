
import itertools as it
import string
import time
import numpy as np
# from ethereum import utils

# solve case 6: msg.sender must be a particular value
# type 1: msg.sender==a particular value
from z3 import BitVecNumRef

import fdg.global_config
from mythril.laser.smt import BitVec


def str_without_space_line(data:str)->str:
    if isinstance(data,BitVec):
        data=str(data.raw)
    else:
        data=str(data)

    return data.translate({ord(term): None for term in string.whitespace})

def random_indices(start:int,end:int,size_select:int)->list:
    select=np.random.choice(range(start,end+1,1),size=size_select,replace=False)
    return select

def random_select_from_list(given_data:list,size_select:int)->list:
    select=np.random.choice(range(len(given_data)),size=size_select,replace=False)
    return [given_data[idx] for idx in select]

def random_select(sequences: list, num_selected: int):
    if len(sequences)>num_selected:
        select = np.random.choice(range(len(sequences)), size=num_selected, replace=False)
        return [sequences[idx] for idx in select]
    else: return sequences


def get_combination(list_for_comb,comb_length:int):
    """
    :param list_for_comb: [[1,4], [2,6],[5]]
    :param comb_length: 2 (two elements in a combination)
    :return: [(1, 2), (1, 6), (4, 2), (4, 6), (1, 5), (4, 5), (2, 5), (6, 5)]
    """
    com_re = []
    # do combination with length
    num_groups = len(list_for_comb)
    if num_groups<comb_length:return []

    # get group combinations
    com_groups = it.combinations(list_for_comb, comb_length)

    for groups in com_groups:
        com_re +=it.product(*list(groups))

    return com_re

def get_combination_for_a_list(list_for_comb,comb_length:int):
    re=[]
    if comb_length==1:
        re=[[item] for item in list_for_comb]
        return re
    for item in it.combinations(list_for_comb, comb_length):
        re.append(list(item))
    return re


def get_binary(length:int,number:int):
    bin_list=[]
    bin_str=bin(number)

    bin_list=[int(bin_str[i]) for i in range(2,len(bin_str))]
    if length>len(bin_list):
        extra=[0 for i in range(length -len(bin_list))]
        bin_list=extra+bin_list
    return bin_list



def hash_for_list(constraints:list) -> str:
    """
    Return function names corresponding signature hash
    :param func: function name
    :return: Its hash signature
    """

    # start=time.time()
    # combined=''
    # for item in constraints:
    #     if str(item) not in ['True','False']:
    #         # print(f'constraint item is considered: {str(item)}')
    #         combined+=str(item)
    #     else:
    #         # print(f'constriant item not considered:{str(item)}')
    #         ...
    # end=time.time()
    # fdg.global_config.time_temp+=end-start
    # #return combined
    # return utils.sha3(combined).hex()
    ...

def hash_for_constraint_list(constraints:list) -> list:
    # start=time.time()
    # hash_results=[utils.sha3(str(con)) for con in constraints if str(con) not in ['True','False']]
    # end=time.time()
    # fdg.global_config.time_temp+=end-start
    # return hash_results
    ...

def print_sequences(sequences,description:str=''):
    print(f'\n{description}')
    if len(sequences)==0:
        print(f'\t[]')
    else:
        for seq in sequences:
            print(f'\t{seq}')
def get_key(ftn_seq:list)->str:
    if len(ftn_seq)==1:
        return ftn_seq[0]
    if len(ftn_seq)==0:
        return ''
    key=ftn_seq[0]
    for i in range(1,len(ftn_seq)):
        key+="#"+ftn_seq[i]
    return key
def get_ftn_seq_from_key(key:str)->list:
    if '#' in key:
        return key.split('#')
    else:
        return [key]

def get_key_1(ftn_seq:list,index:int)->str:
    if len(ftn_seq)==1:
        return ftn_seq[0]+"#"+str(index)
    if len(ftn_seq)==0:
        return ''
    key=ftn_seq[0]
    for i in range(1,len(ftn_seq)):
        key+="#"+ftn_seq[i]
    return key+"#"+str(index)

def get_key_1_prefix(key:str)->str:
    idx=key.rindex("#")
    return key[0:idx]


def get_ftn_seq_from_key_1(key:str)->list:
    if '#' in key:
        return key.split('#')[0:-1]
    else:
        return [key]



def is_equal_list(seq1:list,seq2:list)->bool:
    """
    a special case
    ['initialize(address,address,uint256)', 'setCpiOracle(IOracle)']
    ['initialize(address)', 'setCpiOracle(address)']
    """
    if len(seq1)>len(seq2):return False
    if len(seq1)<len(seq2): return False
    for i in range(len(seq1)):
        if seq1[i] not in [seq2[i]]:
            pure_name=seq1[i].split(f'(')[0] if '(' in seq1[i] else seq1[i]
            if pure_name not in [seq2[i][0:len(pure_name)]]:
                return False
    return True

