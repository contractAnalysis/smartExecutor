import fdg.global_config
from fdg.utils import str_without_space_line

flag_basic=True
flag_detail=False
flag_exp=False





def print_list(sequences,description:str=''):
    if not flag_basic:return
    if flag_exp:return
    print(f'\n====== {description} ======')
    if len(sequences)==0:
        print(f'\t[]')
    else:
        for seq in sequences:
            print(f'\t{seq}')
def print_dict(data,description:str=''):
    if not flag_basic:return
    if flag_exp:return
    print(f'\n====== {description} ======')
    if len(data)==0:
        print("\t{}")
    else:
        for k,v in data.items():
            print(f'\t{k}')
            if isinstance(v,list):
                for item in v:
                    print(f'\t{item}')
            else:print(f'\t{v}')

def print_function_assignmnets(data:dict):

    if not flag_basic:return
    if flag_exp: return
    print(f'\n====== function assignment times ======')
    for k,v in data.items():
        print(f'{k}:{v}')


#========================
# in ftn_search_strategy.py
#------------------------
def print_data_for_mine_strategy(cur_queue, d1, d2, d3, state_write_slots:dict, state_priority:dict, state_storage:dict, ):

    if not flag_basic:return
    if flag_exp: return
    print(f'\n==============================')
    print(f'd1__queue:')
    for item in d1:
        print(f'\t{item}')
    print(f'd2__queue:')
    for item in d2:
        print(f'\t{item}')
    print(f'd3__queue:')
    for item in d3:
        print(f'\t{item}')
    print(f'cur_queue:')
    for item in cur_queue:
        print(f'\t{item}')


    # print(f'\n==== write slots of states ==== ')
    # for k, v in state_write_slots.items():
    #     if isinstance(v,dict):
    #         print(f'{k}')
    #         for k1,v1 in v.items():
    #             print(f'\tdepth:{k1}')
    #             for item in v1:
    #                 print(f'\t\t{str_without_space_line(item)}')

    print(f'\n======  priority of states ======')
    for k, v in state_priority.items():
        print(f'{k}:{v}')

    # print(f'\n==== storage ====')
    # for k,v in self.state_storage.items():
    #     if isinstance(v,dict):
    #         print(f'{k}')
    #         for k1,v1 in v.items():
    #             print(f'\t{str_without_space_line(k1)}:\n\t\t{str_without_space_line(v1)}')

def print_data_for_dfs_strategy(stack:list):

    if not flag_basic:return
    if flag_exp: return
    print(f'\n==============================')
    print(f'stack:')
    for item in stack:
        print(f'\t{item}')

def print_data_for_bfs_strategy(queue:list):

    if not flag_basic:return
    if flag_exp: return
    print(f'\n==============================')
    print(f'queue:')
    for item in queue:
        print(f'\t{item}')

#========================
# in guider.py
#------------------------
def print_assigned_functions(state_and_assigned_funtions:dict):

    if not flag_basic:return
    if flag_exp: return
    print(f'\n====== state and assigned functions ======')
    for key,value in state_and_assigned_funtions.items():
        print(f'state key: {key}')
        print(f'functions: {value}')


#========================
# in function_coverage.py
#------------------------
def print_coverage(contrart_cov:float,functions_cov:dict,description:str):

    if not flag_basic:return
    # print(f'\n====== {description} ======')
    print("contract coverage: {:.2f}%".format(contrart_cov))
    if flag_exp: return
    if len(functions_cov)==0:
        print('function coverage: None')
    else:
        print('function coverage:')
        for ftn, cov in functions_cov.items():
            print("\t{:.2f}%: {}".format(cov, ftn))

#========================
# in slot_location.py
#------------------------
def output_key_to_slot(key_to_slot:dict, hash_key_to_slot:dict, file_name:str, description:str):

    if not flag_detail:return
    with open(fdg.global_config.output_path+file_name,'w') as fw:
        fw.write(f'\n==============={description}======================\n')

        for key,value in key_to_slot.items():
            fw.write(f'\n-----------------------\n')
            fw.write(f'key: {key}\n')
            fw.write(f'value: {value}\n')
        fw.write(f'\n=====================================\n')
        fw.write(f'\nmap hash keys to slots\n')
        for key, value in hash_key_to_slot.items():
            fw.write(f'\n-----------------------\n')
            fw.write(f'key: {key}\n')
            fw.write(f'value: {value}\n')
    fw.close()

#========================
# in write_read_info.py
#------------------------
def output_write_read_data(read_slots:dict,write_slots:dict,read_slot_order:dict,reads_addr_location:dict,writes_addr_location:dict, file_name:str,description:str):

    if not flag_detail:return

    with open(fdg.global_config.output_path+file_name,'w') as fw:
        fw.write(f'\n====== {description} ======\n')
        fw.write(f'\n-------------------------\n')
        fw.write('function reads\n')
        for ftn, slots in read_slots.items():
            fw.write(f'{ftn}:{slots}\n')

        fw.write(f'\n-------------------------\n')
        fw.write('function writes\n')
        for ftn, slots in write_slots.items():
            fw.write(f'{ftn}:{slots}\n')

        fw.write(f'\n-------------------------\n')
        fw.write('function reads in order\n')
        for ftn, slots in read_slot_order.items():
            fw.write(f'{ftn}:{slots}\n')

        fw.write(f'\n-------------------------\n')
        fw.write('function write addresses and locations\n')
        for ftn, writes in writes_addr_location.items():
            fw.write(f'\tfunction {ftn}:\n')
            for addr,locations in writes.items():
                fw.write(f'\taddress {addr}:{locations}\n')

        fw.write(f'\n-------------------------\n')
        fw.write('function read addresses and locations\n')
        for ftn, reads in reads_addr_location.items():
            fw.write(f'\tfunction {ftn}:\n')
            for addr,locations in reads.items():
                fw.write(f'\taddress {addr}:{locations}\n')

        fw.close()


#========================
# in read_in_conditions.py
#------------------------
def output_reads_in_conditions(reads_in_conditions:dict,read_slots_in_conditions:dict,read_addr_slots_in_conditions:dict,file_name:str,description:str):

    if not flag_detail:return

    with open(fdg.global_config.output_path + file_name , 'w') as fw:
        fw.write(f'\n====== reads in conditions in functions ======\n')
        for ftn,read_info in reads_in_conditions.items():
            fw.write(f'\n-----{ftn}--------\n')
            fw.write(f'\tread slots: {read_info}\n')


        fw.write(f'\n====== read slots in conditions in functions ======\n')
        for ftn,read_info in read_slots_in_conditions.items():
            fw.write(f'\n-----{ftn}--------\n')
            fw.write(f'\tread slots: {read_info}\n')

        fw.write(f'\n====== read slots with address conditions in functions ======\n')
        for ftn, read_info in read_addr_slots_in_conditions.items():
            for addr, info in read_info.items():
                fw.write(f'\n-----{ftn}--------\n')
                fw.write(f'\taddress {addr}: slots {info}\n')

    fw.close()

def output_reads_in_conditions_1(reads_in_conditions:dict,read_slots_in_conditions:dict,read_addr_slots_in_conditions:dict,function_conditions:dict,file_name:str,description:str):

    if not flag_detail:return

    with open(fdg.global_config.output_path + file_name , 'w') as fw:
        fw.write(f'\n====== reads in conditions in functions ======\n')


        for ftn,read_info in reads_in_conditions.items():
            fw.write(f'\n-----{ftn}--------\n')
            fw.write(f'\tread slots: {read_info}\n')

        fw.write(f'\n====== read slots with address conditions in functions ======\n')
        for ftn, read_info in read_addr_slots_in_conditions.items():
            for addr, info in read_info.items():
                fw.write(f'\n-----{ftn}--------\n')
                fw.write(f'\taddress {addr}: slots {info}\n')

        fw.write(f'\n====== read slots in conditions in functions ======\n')
        for ftn,read_info in read_slots_in_conditions.items():
            fw.write(f'\n-----{ftn}--------\n')
            fw.write(f'\tread slots: {read_info}\n')



        fw.write(f'\n====== conditions for each function ======\n')
        for ftn, conditions in function_conditions.items():
            fw.write(f'\n-----{ftn}--------\n')
            for addr, cond_list in conditions.items():
                fw.write(f'\n-----{addr}--------\n')
                for cond in cond_list:
                    fw.write(f'\t{cond}\n')
    fw.close()



#========================
# in fwrg_manager.py
#------------------------
def output_fwrg_data(graph:dict,file_name:str,description:str):

    if not flag_detail:return
    with open(fdg.global_config.output_path + file_name, 'w') as fw:
        fw.write(f'\n====== {description} ======\n')
        for ftn, data in graph.items():
            fw.write(f'\n{ftn}:\n')
            fw.write(f'\t{data}\n')



