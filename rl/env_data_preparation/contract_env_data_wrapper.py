# Append the directory to your python path using sys
import sys
RL_dir='D:\\wei_space\\RL\\RL\\'  
if RL_dir not in sys.path:
  sys.path.append(RL_dir) 
  

  

from env_data_preparation.contract_env_data_collection import EnvDataCollection,EnvDataCollection02

from utils import sort_lists,equal_two_lists
from copy import (
    copy,
    deepcopy,
)

def order_a_list_of_vector(vector_list:list)->list:
    """
    example vector_list:
        list_of_lists_a = [
          ['a' , [3, 1, 4]],
          ['b' ,  [1, 5, 9]],
          ['c' ,  [2, 6, 5]],
          ['e' ,  [3, 5, 8]]
        ]
    """
    # Define a custom sorting key based on the sum of elements
    def custom_sort(sublist):
        # sort  based on the second element of the sublist
        v=''
        for e in sublist[1]:
            v+=f'{e}'
        return int(v)

    # Use the sorted function with the custom sorting key
    sorted_list_of_lists = sorted(vector_list, key=custom_sort)
    return  sorted_list_of_lists

class ContractEnvDataWrapper():
    """
    use simple integers as keys for functions
    add funcion vector presentation using the types of state variables
    
    """
    def __init__(self, envDataCollected: EnvDataCollection,
                 num_state_var: int = 8, num_func=10, num_reads: int = 3,
                 num_writes: int = 3):
        self.envDataCollected = envDataCollected
        self.num_state_var = num_state_var
        self.num_func = num_func
        self.num_reads = num_reads
        self.num_writes = num_writes

        self.state_info = {}
        self.function_data = {}  # the keys, names, and vectors of functions
        self.function_names=list(envDataCollected.function_reads_writes.keys())
        self.function_names.sort()  # keep the order among functions.
       
        self.func_name_to_key = {}
        self.targets = []  # the keys of the target functions
        self.start_functions=[]

        self.sequences = []  # sequences of functions in terms of function keys
        self.sequence_writes = {}  # the writes done by the last functions of function sequences
        
        self.constructor_info={}

    def prepare(self):
        self.set_initial_state_variable_info()
        self.prepare_function_data()
        self.prepare_function_sequence_data()
        self.update_targets()
        
    def set_initial_state_variable_info(self):
        # type info and write info of the constructor
        type_values = []
        for idx in range(self.num_state_var):
            if idx in self.envDataCollected.types_of_state_variables.keys():
                type_name = self.envDataCollected.types_of_state_variables[idx]
                type_value = \
                self.envDataCollected.mapping_types_of_state_variables_to_values[
                    type_name]
            else:
                type_value = 0
            type_values.append(type_value)

        
        # prepare paritial state information related to the state variables
        self.state_info['var_type'] = type_values

        # write info
        write_times = []
        if "constructor" in self.envDataCollected.function_sequence_writes.keys():
            writes = self.envDataCollected.function_sequence_writes[
                'constructor']
        else:
            writes = []
        for index in range(self.num_state_var):
            if index in writes:
                write_times.append(1)
            else:
                write_times.append(0)
        self.state_info['var_write_times'] = write_times

    def prepare_function_data(self):
        """
        vector: the reads and writes of the state varialbes in terms of (position+1)
        vector_type: the reads and writes of the state variables in terms of the types of the state variables.
        """
       
        function_data_temp=[]
        
        for func in self.function_names:
            r_w_info= self.envDataCollected.function_reads_writes[func]

            read_values = []
            if "reads" in r_w_info.keys():
                read_values = r_w_info["reads"]
                # 0 is preserved. so reads 1 means 1+1
                read_values = [r + 1 for r in read_values]
            write_values = []
            if "writes" in r_w_info.keys():
                write_values = r_w_info["writes"]
                # 0 is preserved. so write 1 means write 1+1
                write_values = [w + 1 for w in write_values]

            if len(read_values)==0 and len(write_values)==0:
              continue

            if len(read_values) > self.num_reads:
                read_values = read_values[0:self.num_reads]
            elif len(read_values) < self.num_reads:
                read_values += [0] * (self.num_reads - len(read_values))


            if len(write_values) > self.num_writes:
                write_values = write_values[0:self.num_writes]
            elif len(write_values) < self.num_writes:
                write_values += [0] * (self.num_writes - len(write_values))

            func_vector = read_values + write_values  
            
            # add vector_type
            read_types=[self.get_type_value(r-1) for r in read_values]
            write_types=[self.get_type_value(w-1) for w in write_values]
            func_vector_in_type= read_types+ write_types
            
            function_data_temp.append([func,func_vector,func_vector_in_type])
            
           
        
        ordered_function_data=order_a_list_of_vector(function_data_temp)
        
        func_key = 1  # 0 is preserved as it is used to denote that no function is selected
        for func, func_vector, func_vector_in_type in ordered_function_data:
            
            self.function_data[func_key] = {'name': func, 'vector': func_vector,'vector_in_type':func_vector_in_type}
            self.func_name_to_key[func] = func_key          
        
            func_key += 1
            
            
            
    def get_type_value(self, state_var_position:int)->int:
        if state_var_position in self.envDataCollected.types_of_state_variables.keys():
            var_type=self.envDataCollected.types_of_state_variables[state_var_position]
            if var_type in self.envDataCollected.mapping_types_of_state_variables_to_values.keys():
                type_value=self.envDataCollected.mapping_types_of_state_variables_to_values[var_type]
                return type_value
        return 0
            
            
           
    def prepare_function_sequence_data(self):
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

        for key, writes in self.envDataCollected.function_sequence_writes.items():
            if key == 'constructor': 
                writes=[w+1 for w in writes] # 0 is preserved
                if len(writes)>=3:
                    writes=writes[0:3]
                else:
                    writes += [0] * (3 - len(writes))
                write_types=[self.get_type_value(w-1) for w in writes]    
                self.constructor_info={'key':0,"name":'constructor','vector':[0,0,0,]+writes,'vector_in_type':[0,0,0]+write_types}
                
                continue
            
            func_seq = get_seq_from_key(key)
           
            func_seq_keys = [self.func_name_to_key[func]  for func in func_seq if func in self.func_name_to_key.keys()]
            new_key = get_key_from_seq(func_seq_keys)
            self.sequences.append(func_seq_keys)
            self.sequence_writes[new_key] = writes

    def update_targets(self):
        self.targets = [self.func_name_to_key[func] for func in
                        self.envDataCollected.targets]



# class ContractEnvDataWrapper_slot_remove():
#     """
#     use simple integers as keys for functions
#     state variables are mapped to the indices of an array concatenated from smaller arrays(each is for a type of state variables)
#     add funcion vector presentation using indices of the state variables
 
#    types: address,uint,int,... (require source code to obtain)
    
#     """
#     def __init__(self, envDataCollected: EnvDataCollection,
#                  num_state_var: int = 8, num_func=12, num_reads: int = 3,
#                  num_writes: int = 3):
#         self.envDataCollected = envDataCollected
    
#         self.num_state_var = num_state_var
#         self.num_func = num_func
#         self.num_reads = num_reads
#         self.num_writes = num_writes
        
#         self.state_variable_slots_to_indices={}
#         self.state_variable_types=[  "bool",
#           "int",
#           "uint",
#           "address",
#           'unknown',
#           'mapping',
#           'array',
#           "string_bytes",
#           "bytesx"

#            ]
#         self.state_variable_types_to_length={
#             "bool":3,
#             "int":2,
#             "uint":5,
#             "address":5,
#             "string_bytes":3,
#             "bytesx":3,
#             "mapping":5,
#             "array":2,
#             'unknown':2  #when multiple state variables are in a single storage slot
#             }
        
#         self.state_var_bin=[]
        

#         self.state_info = {}
#         self.function_data = {}  # the keys, names, and vectors of functions
#         self.function_names=list(envDataCollected.function_reads_writes.keys())
#         self.function_names.sort()  # keep the order among functions.
       
#         self.func_name_to_key = {}
#         self.targets = []  # the keys of the target functions
#         self.start_functions=[]
        
#         self.sequences = []  # sequences of functions in terms of function keys
#         self.sequence_writes = {}  # the writes done by the last functions of function sequences
#         self.sequences_action=[]
#         self.sequences_action_writes={}
#         self.constructor_info={}
#         self.selected_indices=[0]*self.num_state_var
        

        
#     def map_slots_to_indices(self, svar_weights:dict):        
#         state_var_identifier=[]
        
#         # go through the types to find the state variables for each type
#         # and map state variables to indices of an array made of concatenating empty arrays, whose length is the number of allowed instances of types
#         index=0
#         for var_type in self.state_variable_types:
           
#             len_for_type=self.state_variable_types_to_length[var_type]
#             targets_svar=[] # collect all the state variables of the type 'var_type'
#             for svar, type_ in self.envDataCollected.types_of_state_variables.items():               
             
#                 if type_ in [var_type]:
#                     targets_svar.append(svar)
#                 elif str(var_type).startswith(type_):
#                     targets_svar.append(svar)
#                 elif str(var_type).endswith(type_):
#                     targets_svar.append(svar)
                    
#             # order the state variables in the targets of a type
#             targets_and_weights=[[t,svar_weights[t] if t in svar_weights.keys() else 0 ] for t in targets_svar]
#             sorted_targets_and_weights = sorted(targets_and_weights, key=lambda x: x[1],reverse=True)
           
            
#             for idx in range(len_for_type):
                
#                 if idx <len(sorted_targets_and_weights):                    
#                     self.state_variable_slots_to_indices[sorted_targets_and_weights[idx][0]]=index
#                     state_var_identifier.append(1)
#                 else:
#                     state_var_identifier.append(0)
#                 index+=1
       
#         self.state_info['vector_in_bin']=state_var_identifier
#         print(f'state_var_identifier:\n\t{state_var_identifier}') 
#         print('self.state_variable_slots_to_indices:')
#         for k,v in self.state_variable_slots_to_indices.items():
#             print(f'\t{k}:{v}')
            
#     def get_functions_r_w_in_index_vector(self):
#         """
#         use the indices to represent functions
#         indices are mapped from slots of the state variables
        
#         The last element in the vector is reserved to distinguish functions that have the same vector
        
#         """
        
#         # get the indices that correspond to the slots of state variables
#         # use the last element to distinguish functions with the same elements
#         selected_indices=[-1]*(self.num_state_var-1)
#         mapped_indices=self.state_variable_slots_to_indices.values()
#         mapped_indices=sorted(list(mapped_indices),reverse=False)
#         for idx,index in enumerate(mapped_indices):
#             if idx>=len(selected_indices):
#                 break
#             selected_indices[idx]=index
#         self.selected_indices=selected_indices+[-1] 
        
#         print(f'self.selected_indices:{self.selected_indices}')
        
        
        
#         func_read_write_in_index={}
        
#         for func in self.function_names:
#             r_w_info= self.envDataCollected.function_reads_writes[func]

#             read_indices = []
#             if "reads" in r_w_info.keys():
#                 read_values = r_w_info["reads"]
#                 # 0 is preserved. so reads 1 means 1+1
#                 read_indices = [self.state_variable_slots_to_indices[r] for r in read_values]
#             write_indices = []
#             if "writes" in r_w_info.keys():
#                 write_values = r_w_info["writes"]
               
#                 # 0 is preserved. so write 1 means write 1+1
#                 # try :
#                 write_indices = [self.state_variable_slots_to_indices[w] for w in write_values if w in self.state_variable_slots_to_indices.keys()]
#                 # except KeyError:
#                 #     print(f'self.state_variable_slots_to_indices:{self.state_variable_slots_to_indices}')
#                 #     print(f'key error')
#             if len(read_indices)==0 and len(write_indices)==0:
#               continue
          
#             if len(read_indices) > self.num_reads:
#                 read_indices = read_indices[0:self.num_reads]
#             elif len(read_indices) < self.num_reads:
#                 # the values in selected indices include: 0,1,2..., and -1 which means the corresponding state variable does not exist
#                 # therefore use -2
#                 read_indices += [-2] * (self.num_reads - len(read_indices))


#             if len(write_indices) > self.num_writes:
#                 write_indices = write_indices[0:self.num_writes]
#             elif len(write_indices) < self.num_writes:
#                 write_indices += [-2] * (self.num_writes - len(write_indices))

#             # add the 7th element
#             read_vector_in_index=[1 if idx in read_indices else 0 for idx in selected_indices]+[0]
#             write_vecotr_in_index=[1 if idx in write_indices else 0 for idx in selected_indices]+[0]
            
            
#             func_read_write_in_index[func]={"reads":read_vector_in_index, 'writes':write_vecotr_in_index}           
                
#         return func_read_write_in_index
            



#     def prepare(self):
      
#         self.set_initial_state_variable_info()
#         self.prepare_function_data()
        
#         self.prepare_function_sequence_data()
#         self.update_targets()

        
#     def set_initial_state_variable_info(self):
#         # type info and write info of the constructor
#         type_values = []
#         for idx in range(self.num_state_var):
#             if idx in self.envDataCollected.types_of_state_variables.keys():
#                 type_name = self.envDataCollected.types_of_state_variables[idx]
#                 if type_name in  self.envDataCollected.mapping_types_of_state_variables_to_values.keys():
#                     type_value = \
#                     self.envDataCollected.mapping_types_of_state_variables_to_values[
#                         type_name]
#                 else:
#                     print(f'type {type_name} is not assigned a value (not considered).')
#             else:
#                 type_value = 0
#             type_values.append(type_value)

        
#         # prepare paritial state information related to the state variables
#         self.state_info['var_type'] = type_values

#         # write info
#         write_times = []
#         if "constructor" in self.envDataCollected.function_sequence_writes.keys():
#             writes = self.envDataCollected.function_sequence_writes[
#                 'constructor']
#         else:
#             writes = []
#         for index in range(self.num_state_var):
#             if index in writes:
#                 write_times.append(1)
#             else:
#                 write_times.append(0)
#         self.state_info['var_write_times'] = write_times
        
        

#     def prepare_function_data(self):
#         """
        
#         vector: the reads and writes of the state varialbes in terms of (position+1)
#         vector_type: the reads and writes of the state variables in terms of the types of the state variables.
#         """
#         def count_weight(read_write_list:list,data:dict):
#             for item in read_write_list:
#                 if item in data.keys():
#                     data[item]+=1
#                 else:
#                     data[item]=1
#         function_data_temp={}
#         svar_weights={}
        
#         for func in self.function_names:
#             r_w_info= self.envDataCollected.function_reads_writes[func]
         
            
#             read_values = []
#             if "reads" in r_w_info.keys():
#                 read_values = r_w_info["reads"]
#                 count_weight(read_values,svar_weights)
#                 # 0 is preserved. so reads 1 means 1+1
#                 read_values = [r + 1 for r in read_values]
                
                 
#             write_values = []
#             if "writes" in r_w_info.keys():
#                 write_values = r_w_info["writes"]
#                 count_weight(write_values,svar_weights)
#                 # 0 is preserved. so write 1 means write 1+1
#                 write_values = [w + 1 for w in write_values]
                

#             if len(read_values)==0 and len(write_values)==0:
#               continue

#             if len(read_values) > self.num_reads:
#                 read_values = read_values[0:self.num_reads]
#             elif len(read_values) < self.num_reads:
#                 read_values += [0] * (self.num_reads - len(read_values))


#             if len(write_values) > self.num_writes:
#                 write_values = write_values[0:self.num_writes]
#             elif len(write_values) < self.num_writes:
#                 write_values += [0] * (self.num_writes - len(write_values))

#             func_vector = read_values + write_values  
            
#             # add vector_type
#             read_types=[self.get_type_value(r-1) for r in read_values]
#             write_types=[self.get_type_value(w-1) for w in write_values]
#             func_vector_in_type= read_types+ write_types
            
#             function_data_temp[func]=[func,func_vector,func_vector_in_type]
            
#         print(f'svar_weights:')
#         for var, w in svar_weights.items():
#             print(f'\t{var}:{w}')
#         # map the slot positions of state variables to indices
#         self.map_slots_to_indices(svar_weights)  
        
        
#         func_read_write_in_index=self.get_functions_r_w_in_index_vector()
#         print(f'func_read_write_in_index:')
#         for func, value in func_read_write_in_index.items():
#             print(f'{func}')
#             print(f'\t{value["reads"]}')
#             print(f'\t{value["writes"]}')
            
#         # combine read vectors and write vectors        
#         func_rw_in_index={key:[e1*2+e2 for e1,e2 in zip(value['reads'],value['writes'])] for key,value in func_read_write_in_index.items()}
        
#         func_rw_data=[[key, value] for key,value in func_rw_in_index.items()]
#         sorted_func_rw_data=sort_lists(func_rw_data,index=1)
        
      
        
#         func_key=1
#         cur_vector=[]
#         same_vector_idx=0 # use to distinguish functions with the same vector
#         for name, comb_rw_vector_in_index in sorted_func_rw_data:
#             if name in function_data_temp.keys():
#                 func_data=function_data_temp[name]
#             else:
#                 func_data=['_',[0]*6,[0]*6]
#             if len(cur_vector)==0:
#                 cur_vector=comb_rw_vector_in_index
#             else:
#                 if equal_two_lists(cur_vector, comb_rw_vector_in_index):
#                     same_vector_idx+=1
#                     comb_rw_vector_in_index[-1]=same_vector_idx
#                 else:
#                     same_vector_idx=0
#                     cur_vector=comb_rw_vector_in_index
                
                 
#             r_w_data=self.envDataCollected.function_reads_writes[name]
#             self.function_data[func_key] = {'name': name, 
#                                             "reads":r_w_data["reads"] if "reads" in r_w_data.keys() else [],
#                                             "writes":r_w_data["writes"] if "writes" in r_w_data.keys() else [],
#                                             'vector': func_data[1],
#                                             'vector_in_type': func_data[2],
#                                             "vector_in_index_rw":comb_rw_vector_in_index,
#                                             'vector_in_index':func_read_write_in_index[name]['reads']+func_read_write_in_index[name]['writes'],
#                                             'action_integer_8':0
#                                             }
#             self.func_name_to_key[name] = func_key 
#             func_key+=1
           
#         print(f'func_read_write_in_index:')
#         for func, value in self.function_data.items():
#             print(f'{func}:{value["name"]}')
#             print(f'\t{value["vector_in_index_rw"]}')
    
#     def get_type_value(self, state_var_position:int)->int:
#         if state_var_position in self.envDataCollected.types_of_state_variables.keys():
#             var_type=self.envDataCollected.types_of_state_variables[state_var_position]
#             if var_type in self.envDataCollected.mapping_types_of_state_variables_to_values.keys():
#                 type_value=self.envDataCollected.mapping_types_of_state_variables_to_values[var_type]
#                 return type_value
#         return 0
            
            
           
#     def prepare_function_sequence_data(self):
#         """
#         note that the write slots(positions) are not increment by 1 when coming to the writes of the sequences
#         """
#         def get_seq_from_key(key: str) -> list:
#             if '#' not in key:
#                 return [key]
#             else:
#                 return key.split('#')

#         def get_key_from_seq(seq: list) -> str:
#             if len(seq) == 0: return ""
#             key = str(seq[0])
#             for ele in seq[1:]:
#                 key += f'#{ele}'
#             return key

#         for key, writes in self.envDataCollected.function_sequence_writes.items():
#             if key == 'constructor': 
                
#                 writes_slot=[w+1 for w in writes] # 0 is preserved
#                 if len(writes_slot)>=3:
#                     writes_slot=writes_slot[0:3]
#                 else:
#                     writes_slot += [0] * (3 - len(writes_slot))
#                 write_types=[self.get_type_value(w-1) for w in writes_slot]    
                
#                 write_indices=[self.state_variable_slots_to_indices[slot] for slot in writes]
#                 print(f'constructor write indices:{write_indices}')
#                 write_vecotr_in_index=[1 if idx in write_indices else 0 for idx in self.selected_indices]
#                 print(f'self.selected_indices:{self.selected_indices}')
#                 print(f'write_vecotr_in_index:{write_vecotr_in_index}')
#                 func_vector_in_index = [0]*self.num_state_var + write_vecotr_in_index
                
                
#                 self.constructor_info={'key':0,"name":'constructor','vector':[0]*self.num_reads+writes_slot,'vector_in_type':[0]*self.num_reads+write_types}
#                 self.constructor_info['vector_in_index']=func_vector_in_index
#                 self.constructor_info['vector_in_index_rw']=write_vecotr_in_index 
#                 continue
            
#             func_seq = get_seq_from_key(key)
           
#             func_seq_keys = [self.func_name_to_key[func]  for func in func_seq if func in self.func_name_to_key.keys()]
#             new_key = get_key_from_seq(func_seq_keys)
            
#             func_seq_actions=[0]*len(self.func_name_to_key.keys())
#             for idx,key in enumerate(func_seq_keys):
#                 assert key<=len(self.func_name_to_key.keys()) and key>=1
#                 func_seq_actions[key-1]=idx+1 # idx+1:denote action; key-1: the position of the function in the function array of regular functions
            
#             new_key_action=get_key_from_seq(func_seq_actions)  
            
#             self.sequences.append(func_seq_keys)
            
#             if func_seq_actions not in self.sequences_action:                
#                 self.sequences_action.append(func_seq_actions)
            
#             self.sequence_writes[new_key] = writes
#             self.sequences_action_writes[new_key_action]=writes
            


#     def update_targets(self):
#         for func in self.envDataCollected.targets:
#             if func in self.func_name_to_key.keys():
#                 self.targets.append(self.func_name_to_key[func])
#             else:
#                 print(f'target {func} do not have data thus will be ignored')
#         for func in self.envDataCollected.start_functions:
#             if func in self.func_name_to_key.keys():
#                 self.start_functions.append(self.func_name_to_key[func])
#         print(f'self.start_functions:{self.start_functions}')
        

class ContractEnvDataWrapper_slot_remove():
    """

    use simple integers as keys for functions
    state variables are mapped to the indices of an array concatenated from smaller arrays(each is for a type of state variables)
    add funcion vector presentation using indices of the state variables
    
    In this case, the types: static, dynamic (does not require source code to obtain)
    
    """
    def __init__(self, envDataCollected: EnvDataCollection,
                 num_state_var: int = 8, num_func=12, num_reads: int = 3,
                 num_writes: int = 3):
        self.envDataCollected = envDataCollected
    
        self.num_state_var = num_state_var
        self.num_func = num_func
        self.num_reads = num_reads
        self.num_writes = num_writes
        
        self.state_variable_slots_to_indices={}
        
        self.state_variable_ds=['static',"dynamic"]
        self.state_varriable_ds_to_types={
            "dynamic":['mapping','array'],
            "static":["bool", "int","uint","address", 'unknown',"string_bytes","bytesx"]    
                }

        self.state_variable_ds_to_length={
            "dynamic":3,
            "static":5,
            }
        
        self.state_var_bin=[]
        

        self.state_info = {}
        self.function_data = {}  # the keys, names, and vectors of functions
        self.function_names=list(envDataCollected.function_reads_writes.keys())
        self.function_names.sort()  # keep the order among functions.
       
        self.func_name_to_key = {}
        self.targets = []  # the keys of the target functions
        self.start_functions=[]
        
        self.sequences = []  # sequences of functions in terms of function keys
        self.sequence_writes = {}  # the writes done by the last functions of function sequences
        self.sequences_action=[]
        self.sequences_action_writes={}
        self.constructor_info={}
        self.selected_indices=[0]*self.num_state_var
        

        
    def map_slots_to_indices(self, svar_weights:dict):        
        state_var_identifier=[]
        
        # go through the types to find the state variables for each type
        # and map state variables to indices of an array made of concatenating empty arrays, whose length is the number of allowed instances of types
        index=0
        for var_ds in self.state_variable_ds:
           
            len_for_ds=self.state_variable_ds_to_length[var_ds]
            targets_svar=[] # collect all the state variables of the type 'var_type'
            for svar, type_ in self.envDataCollected.types_of_state_variables.items():               
                if type_ in self.state_varriable_ds_to_types[var_ds]:
                    targets_svar.append(svar) 
                
                    
            # order the state variables according to the order they are defined
            targets_and_weights=[[t,svar_weights[t] if t in svar_weights.keys() else 0 ] for t in targets_svar]
            sorted_targets_and_weights = sorted(targets_and_weights, key=lambda x: x[0],reverse=False)
           
            
            for idx in range(len_for_ds):
                
                if idx <len(sorted_targets_and_weights):                    
                    self.state_variable_slots_to_indices[sorted_targets_and_weights[idx][0]]=index
                    state_var_identifier.append(1)
                else:
                    state_var_identifier.append(0)
                index+=1
       
        self.state_info['vector_in_bin']=state_var_identifier
        print(f'state_var_identifier:\n\t{state_var_identifier}') 
        print('self.state_variable_slots_to_indices:')
        for k,v in self.state_variable_slots_to_indices.items():
            print(f'\t{k}:{v}')
            
    def get_functions_r_w_in_index_vector(self):
        """
        use the indices to represent functions
        indices are mapped from slots of the state variables
        
        
        
        """
        
        # get the indices that correspond to the slots of state variables
        # use the last element to distinguish functions with the same elements
        selected_indices=[-1]*self.num_state_var
        mapped_indices=self.state_variable_slots_to_indices.values()
        mapped_indices=sorted(list(mapped_indices),reverse=False)
        for idx,index in enumerate(mapped_indices):
            if idx>=len(selected_indices):
                break
            selected_indices[idx]=index
        self.selected_indices=selected_indices
        
        print(f'self.selected_indices:{self.selected_indices}')
        
        
        
        func_read_write_in_index={}
        
        for func in self.function_names:
            r_w_info= self.envDataCollected.function_reads_writes[func]

            read_indices = []
            if "reads" in r_w_info.keys():
                read_values = r_w_info["reads"]
                # 0 is preserved. so reads 1 means 1+1
                read_indices = [self.state_variable_slots_to_indices[r] for r in read_values if r in self.state_variable_slots_to_indices.keys()]
            write_indices = []
            if "writes" in r_w_info.keys():
                write_values = r_w_info["writes"]
               
                # 0 is preserved. so write 1 means write 1+1
                # try :
                write_indices = [self.state_variable_slots_to_indices[w] for w in write_values if w in self.state_variable_slots_to_indices.keys()]
                # except KeyError:
                #     print(f'self.state_variable_slots_to_indices:{self.state_variable_slots_to_indices}')
                #     print(f'key error')
            if len(read_indices)==0 and len(write_indices)==0:
              continue
          
            if len(read_indices) > self.num_reads:
                read_indices = read_indices[0:self.num_reads]
            elif len(read_indices) < self.num_reads:
                # the values in selected indices include: 0,1,2..., and -1 which means the corresponding state variable does not exist
                # therefore use -2
                read_indices += [-2] * (self.num_reads - len(read_indices))


            if len(write_indices) > self.num_writes:
                write_indices = write_indices[0:self.num_writes]
            elif len(write_indices) < self.num_writes:
                write_indices += [-2] * (self.num_writes - len(write_indices))

            # add the 7th element
            read_vector_in_index=[1 if idx in read_indices else 0 for idx in selected_indices]
            write_vecotr_in_index=[1 if idx in write_indices else 0 for idx in selected_indices]
            
            
            func_read_write_in_index[func]={"reads":read_vector_in_index, 'writes':write_vecotr_in_index}           
                
        return func_read_write_in_index
            

            
    def get_functions_r_w_in_index(self):
        """
        use the indices to represent the state variables read/written by each function
        
        """

        
        func_read_write_in_index={}
        
        for func in self.function_names:
            r_w_info= self.envDataCollected.function_reads_writes[func]

            read_indices = []
            if "reads" in r_w_info.keys():
                read_values = r_w_info["reads"]
                # 0 is preserved. so reads 1 means 1+1
                read_indices = [self.state_variable_slots_to_indices[r]+1 for r in read_values if r in self.state_variable_slots_to_indices.keys() ]
            write_indices = []
            if "writes" in r_w_info.keys():
                write_values = r_w_info["writes"]
               
                # 0 is preserved. so write 1 means write 1+1
                # try :
                write_indices = [self.state_variable_slots_to_indices[w]+1 for w in write_values if w in self.state_variable_slots_to_indices.keys()]
                # except KeyError:
                #     print(f'self.state_variable_slots_to_indices:{self.state_variable_slots_to_indices}')
                #     print(f'key error')
            if len(read_indices)==0 and len(write_indices)==0:
              continue
          
            if len(read_indices) > self.num_reads:
                read_indices = read_indices[0:self.num_reads]
            elif len(read_indices) < self.num_reads:
                
                read_indices += [0] * (self.num_reads - len(read_indices))


            if len(write_indices) > self.num_writes:
                write_indices = write_indices[0:self.num_writes]
            elif len(write_indices) < self.num_writes:
                write_indices += [0] * (self.num_writes - len(write_indices))

  
            
            func_read_write_in_index[func]={"reads":read_indices, 'writes':write_indices}           
                
        return func_read_write_in_index
            



    def prepare(self):
      
        self.set_initial_state_variable_info()
        self.prepare_function_data()
        
        self.prepare_function_sequence_data()
        self.update_targets()

        
    def set_initial_state_variable_info(self):
        # type info and write info of the constructor
        type_values = []
        for idx in range(self.num_state_var):
            if idx in self.envDataCollected.types_of_state_variables.keys():
                type_name = self.envDataCollected.types_of_state_variables[idx]
                if type_name in  self.envDataCollected.mapping_types_of_state_variables_to_values.keys():
                    type_value = \
                    self.envDataCollected.mapping_types_of_state_variables_to_values[
                        type_name]
                else:
                    print(f'type {type_name} is not assigned a value (not considered).')
            else:
                type_value = 0
            type_values.append(type_value)

        
        # prepare paritial state information related to the state variables
        self.state_info['var_type'] = type_values

        # write info
        write_times = []
        if "constructor" in self.envDataCollected.function_sequence_writes.keys():
            writes = self.envDataCollected.function_sequence_writes[
                'constructor']
        else:
            writes = []
        for index in range(self.num_state_var):
            if index in writes:
                write_times.append(1)
            else:
                write_times.append(0)
        self.state_info['var_write_times'] = write_times
        
        

    def prepare_function_data(self):
        """
        
        vector: the reads and writes of the state varialbes in terms of (position+1)
        vector_type: the reads and writes of the state variables in terms of the types of the state variables.
        """
        def count_weight(read_write_list:list,data:dict):
            for item in read_write_list:
                if item in data.keys():
                    data[item]+=1
                else:
                    data[item]=1
        function_data_temp={}
        svar_weights={}
        
        for func in self.function_names:
            r_w_info= self.envDataCollected.function_reads_writes[func]
         
            
            read_values = []
            if "reads" in r_w_info.keys():
                read_values = r_w_info["reads"]
                count_weight(read_values,svar_weights)
                # 0 is preserved. so reads 1 means 1+1
                read_values = [r + 1 for r in read_values]
                
                 
            write_values = []
            if "writes" in r_w_info.keys():
                write_values = r_w_info["writes"]
                count_weight(write_values,svar_weights)
                # 0 is preserved. so write 1 means write 1+1
                write_values = [w + 1 for w in write_values]
                

            if len(read_values)==0 and len(write_values)==0:
              continue

            if len(read_values) > self.num_reads:
                read_values = read_values[0:self.num_reads]
            elif len(read_values) < self.num_reads:
                read_values += [0] * (self.num_reads - len(read_values))


            if len(write_values) > self.num_writes:
                write_values = write_values[0:self.num_writes]
            elif len(write_values) < self.num_writes:
                write_values += [0] * (self.num_writes - len(write_values))

            func_vector = read_values + write_values  
            
            # add vector_type
            read_types=[self.get_type_value(r-1) for r in read_values]
            write_types=[self.get_type_value(w-1) for w in write_values]
            func_vector_in_type= read_types+ write_types
            
            function_data_temp[func]=[func,func_vector,func_vector_in_type]
            
        print(f'svar_weights:')
        for var, w in svar_weights.items():
            print(f'\t{var}:{w}')
        # map the slot positions of state variables to indices
        self.map_slots_to_indices(svar_weights)  
        
        
        func_read_write_in_index_vector=self.get_functions_r_w_in_index_vector()

            
        # combine read vectors and write vectors        
        func_rw_in_index={key:[e1*2+e2 for e1,e2 in zip(value['reads'],value['writes'])] for key,value in func_read_write_in_index_vector.items()}
        
        func_rw_data=[[key, value] for key,value in func_rw_in_index.items()]
        sorted_func_rw_data=sort_lists(func_rw_data,index=1)
        
        # 
        func_r_and_w_in_index=self.get_functions_r_w_in_index()
      
        
        func_key=1
        cur_vector=[]
        same_vector_idx=0 # use to distinguish functions with the same vector
        for name, comb_rw_vector_in_index in sorted_func_rw_data:
            comb_rw_in_idx_new=copy(comb_rw_vector_in_index)
            if name in function_data_temp.keys():
                func_data=function_data_temp[name]
            else:
                func_data=['_',[0]*(self.num_reads+self.num_writes),[0]*(self.num_reads+self.num_writes)]
            if len(cur_vector)==0:
                cur_vector=comb_rw_vector_in_index
                concate_rw_vector_in_idx=func_r_and_w_in_index[name]['reads']+func_r_and_w_in_index[name]['writes']+[same_vector_idx]
                comb_rw_in_idx_new+=[same_vector_idx]
            else:
                if equal_two_lists(cur_vector, comb_rw_vector_in_index):
                    same_vector_idx+=1                    
                    concate_rw_vector_in_idx=func_r_and_w_in_index[name]['reads']+func_r_and_w_in_index[name]['writes']+[same_vector_idx]
                    comb_rw_in_idx_new+=[same_vector_idx]
                else:
                    same_vector_idx=0
                    cur_vector=comb_rw_vector_in_index                   
                    concate_rw_vector_in_idx=func_r_and_w_in_index[name]['reads']+func_r_and_w_in_index[name]['writes']+[same_vector_idx]
                    comb_rw_in_idx_new+=[same_vector_idx]
                
                 
            r_w_data=self.envDataCollected.function_reads_writes[name]
            self.function_data[func_key] = {'name': name, 
                                            "reads":r_w_data["reads"] if "reads" in r_w_data.keys() else [],
                                            "writes":r_w_data["writes"] if "writes" in r_w_data.keys() else [],
                                            'vector': func_data[1],
                                            'vector_in_type': func_data[2],
                                            "vector_in_index_rw":comb_rw_in_idx_new, #old: comb_rw_vector_in_index,
                                            'vector_in_index':func_read_write_in_index_vector[name]['reads']+func_read_write_in_index_vector[name]['writes'],
                                            'vector_in_index_rafterw':concate_rw_vector_in_idx
                                            
                                            }
            self.func_name_to_key[name] = func_key 
            func_key+=1
           
        print(f'func_read_write_in_index:')
        for func, value in self.function_data.items():
            print(f'{func}:{value["name"]}')
            print(f'\t{value["vector_in_index_rw"]}')
            print(f'\t{value["vector_in_index_rafterw"]}')
            

    
    def get_type_value(self, state_var_position:int)->int:
        if state_var_position in self.envDataCollected.types_of_state_variables.keys():
            var_type=self.envDataCollected.types_of_state_variables[state_var_position]
            if var_type in self.envDataCollected.mapping_types_of_state_variables_to_values.keys():
                type_value=self.envDataCollected.mapping_types_of_state_variables_to_values[var_type]
                return type_value
        return 0
            
            
           
    def prepare_function_sequence_data(self):
        """
        note that the write slots(positions) are not increment by 1 when coming to the writes of the sequences
        """
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

        for key, writes in self.envDataCollected.function_sequence_writes.items():
            if key == 'constructor': 
                print(f"writes:{writes}")
                
                writes_slot=[w+1 for w in writes] # 0 is preserved
                if len(writes_slot)>=self.num_writes:
                    writes_slot=writes_slot[0:3]
                else:
                    writes_slot += [0] * (self.num_writes - len(writes_slot))
                
                write_types=[self.get_type_value(w-1) for w in writes_slot]    
                
                write_idx=[self.state_variable_slots_to_indices[w-1]+1 if w-1 in self.state_variable_slots_to_indices.keys() else 0 for w in writes_slot]
               
                
                
                write_indices=[self.state_variable_slots_to_indices[slot] for slot in writes if slot in self.state_variable_slots_to_indices.keys()]                
                print(f'constructor write indices:{write_indices}')
                
                
                write_vecotr_in_index=[1 if idx in write_indices else 0 for idx in self.selected_indices]
               
               
                func_vector_in_index = [0]*self.num_state_var + write_vecotr_in_index
                
                
                self.constructor_info={'key':0,"name":'constructor','vector':[0]*self.num_reads+writes_slot,'vector_in_type':[0]*self.num_reads+write_types}
                self.constructor_info['vector_in_index']=func_vector_in_index
                self.constructor_info['vector_in_index_rw']=write_vecotr_in_index 
                self.constructor_info['vector_in_index_rafterw']=[0]*self.num_reads+ write_idx+[0]
                print(f'vector_in_index_rafterw of constructor:{self.constructor_info["vector_in_index_rafterw"]}')
                continue
            
            func_seq = get_seq_from_key(key)
           
            func_seq_keys = [self.func_name_to_key[func]  for func in func_seq if func in self.func_name_to_key.keys()]
            new_key = get_key_from_seq(func_seq_keys)
            
            func_seq_actions=[0]*len(self.func_name_to_key.keys())
            for idx,key in enumerate(func_seq_keys):
                assert key<=len(self.func_name_to_key.keys()) and key>=1
                func_seq_actions[key-1]=idx+1 # idx+1:denote action; key-1: the position of the function in the function array of regular functions
            
            new_key_action=get_key_from_seq(func_seq_actions)  
            
            self.sequences.append(func_seq_keys)
            
            if func_seq_actions not in self.sequences_action:                
                self.sequences_action.append(func_seq_actions)
            
            self.sequence_writes[new_key] = writes
            self.sequences_action_writes[new_key_action]=writes
            


    def update_targets(self):
        for func in self.envDataCollected.targets:
            if func in self.func_name_to_key.keys():
                self.targets.append(self.func_name_to_key[func])
            else:
                print(f'target {func} do not have data thus will be ignored')
        for func in self.envDataCollected.start_functions:
            if func in self.func_name_to_key.keys():
                self.start_functions.append(self.func_name_to_key[func])
        print(f'self.start_functions:{self.start_functions}')
        

class ContractEnvDataWrapper_wsa():
    """

    use simple integers as keys for functions
    state variables are mapped to integers (like how to tokenize in AI)

    Assume that the source code is available
    the reads and writes are also based on the source code, which is different from the previous cases (pure bytecodes or partly bytecode (3/13/2024))
    
    """
    def __init__(self, envDataCollected: EnvDataCollection02,
                 num_state_var: int = 8, num_reads: int = 3,
                 num_writes: int = 3):
        
        self.envDataCollected = envDataCollected
    
        self.num_state_var = num_state_var

        self.num_reads = num_reads
        self.num_writes = num_writes  
        

        
        self.state_variables_in_integer= sorted(self.envDataCollected.state_variables_in_integer)
        self.selected_svar=[]
        
        self.state_info = {}
        self.function_data = {}  # the keys, names, and vectors of functions
        
        self.considered_functions=[] # functions in sequences and target functions (some target functions can not appear in sequences)
       
        self.func_name_to_key = {}
        self.targets = []  # the keys of the target functions
        self.start_functions=[]
        
        self.sequences = []  # sequences of functions in terms of function keys
        self.sequence_writes = {}  # the writes done by the last functions of function sequences

        self.constructor_info={}

        



    def prepare(self):      

        self.prepare_function_data()
        
        self.prepare_function_sequence_data()
        
        self.update_targets()


            
    def get_functions_r_w_in_index(self):
        """
        use the indices to represent the state variables read/written by each function
        
        """
        
     
        if len(self.state_variables_in_integer)>self.num_state_var:
            self.selected_svar=self.state_variables_in_integer[0:self.num_state_var]
        else:
            self.selected_svar=self.state_variables_in_integer+[0]*(self.num_state_var-len(self.state_variables_in_integer))
        
        # print(f'state variables:{self.envDataCollected.state_variables}')
        # print(f'state variables:{self.envDataCollected.state_variables_in_integer}')
        # print(f'selected_state_variables:{self.selected_svar}')
        func_read_write_in_index={}
        
        for func in self.envDataCollected.function_reads_writes_in_integer.keys():
            r_w_info= self.envDataCollected.function_reads_writes_in_integer[func]

            read_int = []
            if "reads" in r_w_info.keys():
                read_int = r_w_info["reads"]
               
            write_int = []
            if "writes" in r_w_info.keys():
                write_int = r_w_info["writes"]               
               
            if len(read_int)==0 and len(write_int)==0:
              continue
          
            if len(read_int) > self.num_reads:
                read_int = read_int[0:self.num_reads]
            elif len(read_int) < self.num_reads:                
                read_int += [-1] * (self.num_reads - len(read_int))


            if len(write_int) > self.num_writes:
                write_int = write_int[0:self.num_writes]
            elif len(write_int) < self.num_writes:
                write_int += [-1] * (self.num_writes - len(write_int))

  
            read_indices=[ 1 if svar in read_int else 0 for svar in self.selected_svar]
            write_indices=[ 1 if svar in write_int else 0 for svar in self.selected_svar]
            func_read_write_in_index[func]={"reads":read_indices, 'writes':write_indices}           
                
        return func_read_write_in_index
            

        

    def prepare_function_data(self):
        """
        
        vector: the reads and writes of the state varialbes in terms of (position+1)
        vector_type: the reads and writes of the state variables in terms of the types of the state variables.
        """
                    
        
        
        func_read_write_in_index_vector=self.get_functions_r_w_in_index()
            
        # combine read vectors and write vectors        
        func_rw_in_index={key:[e1*2+e2 for e1,e2 in zip(value['reads'],value['writes'])] for key,value in func_read_write_in_index_vector.items()}
        
        func_rw_data=[[key, value] for key,value in func_rw_in_index.items()]
        sorted_func_rw_data=sort_lists(func_rw_data,index=1)
        
      
        
        func_key=1
        cur_vector=[]
        same_vector_idx=0 # use to distinguish functions with the same vector
        for name, comb_rw_vector_in_index in sorted_func_rw_data:
            comb_rw_in_idx_new=deepcopy(comb_rw_vector_in_index)
            
            if len(cur_vector)==0:
                cur_vector=comb_rw_vector_in_index                
                comb_rw_in_idx_new+=[same_vector_idx]
            else:
                if equal_two_lists(cur_vector, comb_rw_vector_in_index):
                    same_vector_idx+=1                    
                   
                    comb_rw_in_idx_new+=[same_vector_idx]
                else:
                    same_vector_idx=0
                    cur_vector=comb_rw_vector_in_index                   
                   
                    comb_rw_in_idx_new+=[same_vector_idx]
                
            reads=self.envDataCollected.function_reads_writes_in_integer[name]['reads']
            writes=self.envDataCollected.function_reads_writes_in_integer[name]['writes']

            # from comb_rw_in_idx_new to get reads and writes and the last element used to distinguish functions with the same presentation
            reads_=[]
            writes_=[]
            for idx, item in enumerate(comb_rw_in_idx_new[0:8]):
                if item==1:
                    writes_.append(self.selected_svar[idx])
                elif item==2:
                    reads_.append(self.selected_svar[idx])
                elif item==3:
                    writes_.append(self.selected_svar[idx])
                    reads_.append(self.selected_svar[idx])
            reads_=reads_[0:3] if len(reads_)>=3 else reads_+[0]*(3-len(reads_))
            writes_=writes_[0:3] if len(writes_)>=3 else writes_+[0]*(3-len(writes_))

            func_rw_in_concate=reads_+writes_+[comb_rw_in_idx_new[-1]]
            
            if '(' in name:
                pure_name=name.split('(')[0]
            else:
                pure_name=name
            if '.' in pure_name:
                pure_name=pure_name.split('.')[-1]
           
            if name=='constructor':
                
               self.function_data[0] = {'name': name, 
                                               "pure_name":pure_name, 
                                               "reads":reads,
                                               "writes":writes,
                                               "vector_in_index_rw":comb_rw_in_idx_new, #old: comb_rw_vector_in_index,
                                               "vector_rw_in_concate":func_rw_in_concate
                                               }
               self.func_name_to_key[pure_name] = 0
            else:
            
                self.function_data[func_key] = {'name': name, 
                                                "pure_name":pure_name, 
                                                "reads":reads,
                                                "writes":writes,
                                                "vector_in_index_rw":comb_rw_in_idx_new, #old: comb_rw_vector_in_index,
                                                "vector_rw_in_concate": func_rw_in_concate
                                                }
                self.func_name_to_key[pure_name] = func_key 
                func_key+=1
                
                
        if 0 not in self.function_data.keys():
            self.function_data[0] = {'name': "constructor()", 
                                            "pure_name":"constructor", 
                                            "reads":[],
                                            "writes":[],
                                            "vector_in_index_rw":[0]*9, #old: comb_rw_vector_in_index,
                                            "vector_rw_in_concate":[0]*7
                                            }
            self.func_name_to_key[pure_name] = 0
    
        print(f'func_read_write_in_index:')
        for func, value in self.function_data.items():
            print(f'{func}:{value["name"]}')
            print(f'\t{value["vector_in_index_rw"]}')
          
            


            
           
    def prepare_function_sequence_data(self):
        """
        note that the write slots(positions) are not increment by 1 when coming to the writes of the sequences
        """
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

        for key, writes in self.envDataCollected.function_sequence_writes.items():
            if key == 'constructor':                
                continue
            
            func_seq = get_seq_from_key(key)
           
            func_seq_keys = [self.func_name_to_key[func]  for func in func_seq if func in self.func_name_to_key.keys()]
            new_key = get_key_from_seq(func_seq_keys)
            
            self.sequences.append(func_seq_keys)
            
            self.sequence_writes[new_key] = writes
 
            


    def update_targets(self):
        for func in self.envDataCollected.targets:
            if func in self.func_name_to_key.keys():
                self.targets.append(self.func_name_to_key[func])
            else:
                print(f'target {func} do not have data thus will be ignored')
        for func in self.envDataCollected.start_functions:
            if func in self.func_name_to_key.keys():
                self.start_functions.append(self.func_name_to_key[func])
        print(f'self.start_functions:{self.start_functions}')
        

class CollectContractEnvData_wsa():
    """
    use the static analysis data to collect the required data

     
    """
    def __init__(self, envDataCollected: EnvDataCollection02,
                 num_state_var: int = 8, num_reads: int = 3,
                 num_writes: int = 3):
        
        self.envDataCollected = envDataCollected    
        self.num_state_var = num_state_var
        self.num_reads = num_reads
        self.num_writes = num_writes          

        
        self.state_variables_in_integer= sorted(self.envDataCollected.state_variables_in_integer)
        self.selected_svar=[]
        

        self.function_data = {}  # the keys, names, and vectors of functions
        self.function_value=[]
        self.function_value_n0=[]


           
    def get_functions_r_w_in_index(self):
        """
        use the indices to represent the state variables read/written by each function
        
        """
        
     
        if len(self.state_variables_in_integer)>self.num_state_var:
            self.selected_svar=self.state_variables_in_integer[0:self.num_state_var]
        else:
            self.selected_svar=self.state_variables_in_integer+[0]*(self.num_state_var-len(self.state_variables_in_integer))

        func_read_write_in_index={}
        
        for func in self.envDataCollected.function_reads_writes_in_integer.keys():
            r_w_info= self.envDataCollected.function_reads_writes_in_integer[func]

            read_int = []
            if "reads" in r_w_info.keys():
                read_int =deepcopy(r_w_info["reads"])
               
            write_int = []
            if "writes" in r_w_info.keys():
                write_int =deepcopy( r_w_info["writes"]  )             
               
            if len(read_int)==0 and len(write_int)==0:
              continue
          
            if len(read_int) > self.num_reads:
                read_int=sorted(read_int,reverse=False)
                read_int = read_int[0:self.num_reads]
            elif len(read_int) < self.num_reads:                
                read_int += [-1] * (self.num_reads - len(read_int))


            if len(write_int) > self.num_writes:
                write_int=sorted(write_int,reverse=False)
                write_int = write_int[0:self.num_writes]
            elif len(write_int) < self.num_writes:
                write_int += [-1] * (self.num_writes - len(write_int))

  
            read_indices=[ 1 if svar in read_int else 0 for svar in self.selected_svar]
            write_indices=[ 1 if svar in write_int else 0 for svar in self.selected_svar]
            func_read_write_in_index[func]={"reads":read_indices, 'writes':write_indices}           
            
            
            # if func in ['BHT.contTransfer(address,uint256)','BHE.contTransfer(address,uint256)']:
            #     print(f'---------------')
            #     print(f'self.selected_svar:{self.selected_svar}')
            #     print(f'read_int:{read_int}')
            #     print(f'read_indices:{read_indices}')                
            #     print(f'write_indices:{write_indices}')
            
        return func_read_write_in_index
            

  
    
    def collect_function_data(self):
        func_read_write_in_index_vector=self.get_functions_r_w_in_index()
            
        # combine read vectors and write vectors        
        func_rw_in_index={key:[e1*2+e2 for e1,e2 in zip(value['reads'],value['writes'])] for key,value in func_read_write_in_index_vector.items()}
        
        self.function_value=[0]*self.num_state_var
        for k,value in func_rw_in_index.items():
            # print(f'\t{value}:{k}')
            self.function_value=[e1+e2 for e1,e2 in zip(self.function_value,value)]  
        
        
        # print(f'self.function_value:{self.function_value}')
       
        self.function_value_n0=[0]*self.num_state_var
        for k,value in func_rw_in_index.items():
            if k not in ['constructor','constructor()']:
                # print(f'\t{value}:{k}')
                self.function_value_n0=[e1+e2 for e1,e2 in zip(self.function_value_n0,value)]  
        
        # print(f'self.function_value_n0:{self.function_value_n0}')
        # func_rw_data=[[key, value] for key,value in func_rw_in_index.items()]
        # sorted_func_rw_data=sort_lists(func_rw_data,index=1)
        

        for name, comb_rw_vector_in_index in func_rw_in_index.items():           
            
                
            reads=self.envDataCollected.function_reads_writes_in_integer[name]['reads']
            writes=self.envDataCollected.function_reads_writes_in_integer[name]['writes']
            
            reads=sorted(reads,reverse=False)
            writes=sorted(writes,reverse=False)
            # from comb_rw_in_idx_new to get reads and writes and the last element used to distinguish functions with the same presentation

                    
            reads_=reads[0:3] if len(reads)>=3 else reads+[0]*(3-len(reads))
            writes_=writes[0:3] if len(writes)>=3 else writes+[0]*(3-len(writes))

            func_rw_in_concate=reads_+writes_
            
            if '(' in name:
                pure_name=name.split('(')[0]
            else:
                pure_name=name
            if '.' in pure_name:
                pure_name=pure_name.split('.')[-1]
           
            if name=='constructor':
                
               self.function_data[name] = {'name': name, 
                                               "pure_name":pure_name, 
                                               "reads":reads,
                                               "writes":writes,
                                               "vector_in_index_rw":comb_rw_vector_in_index, #old: comb_rw_vector_in_index,
                                               "vector_rw_in_concate":func_rw_in_concate
                                               }
               
            else:
            
                self.function_data[name] = {'name': name, 
                                                "pure_name":pure_name, 
                                                "reads":reads,
                                                "writes":writes,
                                                "vector_in_index_rw":comb_rw_vector_in_index, 
                                                "vector_rw_in_concate": func_rw_in_concate
                                                }
           
                
                
        if 'constructor' not in self.function_data.keys():
            self.function_data['constructor'] = {'name': "constructor()", 
                                            "pure_name":"constructor", 
                                            "reads":[],
                                            "writes":[],
                                            "vector_in_index_rw":[0]*self.num_state_var, 
                                            "vector_rw_in_concate":[0]*(self.num_reads+self.num_writes)
                                            }
            
    
         
        

    def obtain_contract_data(self):
        self.collect_function_data()
        data={
            "state_variable": self.envDataCollected.state_variables,         
            "state_variables_in_integer":self.state_variables_in_integer,
            "state_variables_selected":self.selected_svar, # select 8 state variables
            "function_value":self.function_value,
            "function_value_n0":self.function_value_n0,
            "function_data":self.function_data,
            "function_sequences":self.envDataCollected.function_sequence_writes,
            "functions_in_sequences":self.envDataCollected.functions_in_sequences,
            "target_functions":self.envDataCollected.targets,
            "start_functions":self.envDataCollected.start_functions
            }
            
        return data
           



        
