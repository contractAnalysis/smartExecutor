# -*- coding: utf-8 -*-
"""
Created on Fri Feb 23 16:43:25 2024

@author: SERC
"""
import gymnasium
import numpy as np
import random

import os
import json
random.seed(10)
def get_key_from_list(lst:list)->str:
    if len(lst)==0:return ""
    if len(lst)==1:
        return f'{lst[0]}'
    key=f'{lst[0]}'
    for item in lst[1:]:
        key+=f'#{item}'
    return key

def get_seq_from_key(key: str) -> list:
    if '#' not in key:
        return [key]
    else:
        return key.split('#')

def get_key_from_seq(seq: list) -> str:
    if len(seq) == 0: return ""
    key = str(seq[0])
    for ele in seq[1:]:
        key += f'#{ele}'
    return key

def jump_json_object_to_json(data,file_path:str,indent=4):
    with open(file_path,'w',encoding='utf-8') as f:
        json.dump(data,f,indent=indent)
        
def load_a_json_file(file_path:str):
    data={}
    if os.path.exists(file_path):
        try:
            with open(file_path,'r') as file:
                data=json.load(file)
        except json.JSONDecodeError as e:
            print(f'Error loading JSON from {file_path}:{e}')
        finally:
            return data
    else:
        print(f'File does not exist:{file_path}')
        return data

def scale_value_continous(value:int, min_val:int, max_val:int)->float:
    
    if min_val == max_val:        
        return 0.0  # or any other default value you choose
    else:
        return (value - min_val) / (max_val - min_val)
   
def xxx(goal_reaching_status:dict):
    goal_weight_status={}
    goal_reaching_times=[(key,times) for key,times in goal_reaching_status.items()]
    
    grt_d=sort_lists(goal_reaching_times,reverse=True) 
   
        
    for idx in range(len(grt_d)):                
        goal=grt_d[idx][0] 
        weight=(idx+1)
        goal_weight_status[goal]=weight
    return goal_weight_status

def equal_two_lists(lst1:list,lst2:list)->bool:
    if len(lst1)!=len(lst2):return False
    for e1,e2 in zip(lst1,lst2):
        if e1!=e2:
            return False
    return True


def euclidean_distance(arr1, arr2):
    return np.linalg.norm(np.array(arr1) - np.array(arr2))

def goal_rewarding(action,goal,cur_sequence:list,goal_indicator:int=0,goals:list=[],flag_test:bool=False,mode:str='train'):
    reward=0
    terminate = False
    cur_length=len(cur_sequence)
    
    if cur_length==1:
        reward+=0.2
    else:
        if goal_indicator==0:
            # valid transition
            if cur_sequence[-1]==goal:
                # reach the goal
                terminate = True
                if cur_length == 2:
                    reward =7                     
                elif cur_length == 3:
                    reward = 6
                elif cur_length == 4:
                    reward = 5
                if mode=='train' and terminate:
                    print(f'goal {goal} is reached; func seq:{cur_sequence}; reward: {reward}')

            else:
                reward=0.2
        elif goal_indicator==1:                        
            
            if cur_sequence[-1]==goal:
                if cur_sequence.count(goal)==1:
                    # reach the goal
                    
                  
                    if cur_length == 2:
                        reward +=6
                    elif cur_length == 3:
                        reward += 5.5 
                    elif cur_length == 4:
                        reward += 5                                    
                        
                    # if mode=='train' and terminate:
                    #     print(f'goal {self.goal} is reached; action sequence:{self.previous_actions}; reward: {reward}')

            if reward==0:                
                if action in goals:
                    reward+=0.5
                else:
                    reward=+0.2
        elif goal_indicator==2:
            if cur_sequence[-1]==goal:
                # reach the goal
                terminate = True
                if cur_length == 2:
                    reward =6                     
                elif cur_length == 3:
                    reward = 5.5
                elif cur_length == 4:
                    reward = 5
                if mode=='train' and terminate:
                    print(f'goal {goal} is reached; func seq:{cur_sequence}; reward: {reward}')

            else:
                reward=0.2
                
    return reward,terminate
 


# my_list = ['a', 'b', 'c', 'd', 'e']
# weights = [10, 5, 1, 1, 20]

def weighted_random_selection(lst, weights):
    total_weight = sum(weights)
    pick = random.uniform(0, total_weight) 
    current = 0
    for i, w in enumerate(weights):
        current += w
        if current > pick:
            return lst[i]
    
def weighted_choice(elements, weights):
    total_weight = sum(weights)
    rand_value = random.uniform(0, total_weight)
    cumulative_weight = 0

    for element, weight in zip(elements, weights):
        cumulative_weight += weight
        if rand_value <= cumulative_weight:
            return element
    
def random_selection(lst):
    random_value = random.choice(lst)
    return random_value
    
def sort_lists(my_lists:list, index:int=-1, reverse:bool=True)->list:

    
    # Define a function to convert a list of digits to an integer
    def list_to_int(lst):
        
        if index>=0 and index <len(lst):
            #   my_lists = [
            #     ['a', [3, 8, 5]],
            #     ['b', [1, 5, 2]],
            #     ['c', [7, 2, 9]],
            #     ['d', [4, 1, 6]]
            # ]
            return int(''.join(map(str, lst[index])))
        else:
            #   my_lists = [
            #     [3, 8, 5],
            #     [1, 5, 2],
            #     [7, 2, 9],
            #     [4, 1, 6]
            # ]
            return int(''.join(map(str, lst)))
            
    # Sort the list of lists based on the value they can form in descending order
    sorted_list_by_value = sorted(my_lists, key=list_to_int, reverse=reverse)
    
    return sorted_list_by_value

def is_equal(ls1:list,ls2:list)->bool:
    if len(ls1)==len(ls2):
        for e1, e2 in zip(ls1,ls2):
            if not e1==e2:
                return False
        return True
    else:
        return False
    
def load_a_json_file(file_path:str):
    data = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as file:
                data = json.load(file)

        except json.JSONDecodeError as e:
            print(f"Error loading JSON from {file_path}: {e}")
        finally:
            return data

    else:
        print(f"File does not exist: {file_path}")
        return data
