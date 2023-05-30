import math

import fdg.global_config
from fdg.fwrg_manager import FWRG_manager
from fdg.output_data import print_function_assignmnets
from fdg.utils import get_ftn_seq_from_key_1, random_indices

class FunctionAssignment():
    def __init__(self,all_functions:list,fwrg_manager:FWRG_manager,select_percent:int=0):

        self.all_functions = all_functions
        self.fwrg_manager = fwrg_manager

        self.assignment_times={}
        for ftn in self.all_functions:
            self.assignment_times[ftn]=0
        if 'fallback' not in self.assignment_times.keys():
            self.assignment_times['fallback']=0
        self.times_limit=fdg.global_config.execution_times_limit

        self.random_select_percent=select_percent # for the case of baseline


    def assign_functions_for_baseline(self)->list:
        # # find the functions whose
        # to_consider_functions=[]
        # for ftn, times in self.assignment_times.items():
        #     if ftn=='fallback':continue
        #     if times<self.times_limit:
        #         to_consider_functions.append(ftn)
        #
        # if len(to_consider_functions)==0:
        #     return []

        to_consider_functions=self.all_functions
        select_num=math.ceil((self.random_select_percent/10)*len(to_consider_functions))

        select_indices=random_indices(0,len(to_consider_functions)-1,select_num)
        selected_functions=[ftn for idx,ftn in enumerate(to_consider_functions) if idx in select_indices]

        # self.record_assignment(selected_functions)
        return selected_functions

    def assign_all_functions(self):
        if len(self.all_functions)==0:
            print(f'keep the original instruction list in function_assignment.py')

            return ['original_instruction_list']
        self.record_assignment(self.all_functions)
        return self.all_functions

    def record_assignment(self,assigned_functions:list):
        for ftn in assigned_functions:
            if ftn in self.assignment_times.keys():
                self.assignment_times[ftn]+=1

    def fallback_case(self, ftn_seq:list):
        if ftn_seq[-1] in ['fallback','Fallback']:
            if len(self.all_functions)==0:
                print(f'keep the original instruction list in function_assignment.py')
                return ['original_instruction_list']
        return []

    def assign_functions(self,state_key:str,dk_functions:list,to_execute_functions:list=[],not_to_execute:list=[]):
        print_function_assignmnets(self.assignment_times)

        if len(to_execute_functions)==0:
            ftn_seq = get_ftn_seq_from_key_1(state_key)
            fallback_case=self.fallback_case(ftn_seq)
            if len(fallback_case)>0:
                return fallback_case

            children =self.fwrg_manager.get_children_fwrg_T_A(ftn_seq[-1])
            if len(ftn_seq)==1:
                # handle the missed sequence: [A,A], function A writes and reads the same state variable
                children_o = self.fwrg_manager.get_children_fwrg(ftn_seq[-1])
                children+=children_o
                children=list(set(children))

            # consider all the children
            if fdg.global_config.flag_consider_all_reads==1:
                children_o=self.fwrg_manager.get_children_all_reads(ftn_seq[-1])
                children+=children_o
                children=list(set(children))

            children=[child for child in children if child not in not_to_execute]

            assigned_functions=self.check_children(ftn_seq, children, dk_functions)

            # the not-to-be-execucted functions may be added in check_children
            assigned_functions=[child for child in assigned_functions if child not in not_to_execute]
            self.record_assignment(assigned_functions)
            return assigned_functions
        else:
            self.record_assignment(to_execute_functions)
            return to_execute_functions

    def assign_functions_timeout(self, state_key: str, percent_of_functions:int=1):
        print_function_assignmnets(self.assignment_times)

        ftn_seq = get_ftn_seq_from_key_1(state_key)
        fallback_case = self.fallback_case(ftn_seq)
        if len(fallback_case) > 0:
            return fallback_case

        selected_functions=self.check_children_timeout(state_key,percent_of_functions)
        if len(selected_functions)>0:
            self.record_assignment(selected_functions)
        else:
            print(f'no functions are assigned as they reach the times limit.')
        return selected_functions



    def check_children(self, executed_ftn_seq: list, children_of_ftn: list, dk_functions: list) -> list:
        # keep depth-k functions, the times of execution is within the limit
        # or the times limit reaches but the coverage is lower than 80
        dk_left=[]
        for ftn, cov in dk_functions:
            # if ftn=='fallback':continue
            if len(executed_ftn_seq) >= 2:
                if ftn in executed_ftn_seq:
                    continue
            if self.assignment_times[ftn]<self.times_limit:
                dk_left.append(ftn)
                continue
            if self.assignment_times[ftn]>=2*self.times_limit:
                continue
            if cov<50:
                dk_left.append(ftn)


        if len(children_of_ftn) == 0:
            # print('\nchildrn is None')
            # consider depth-k functions whose coverage is below 80%
            assign_children = [ftn for ftn in dk_left]
            if len(executed_ftn_seq) >= 2:
                assign_children = [ftn for ftn in assign_children if ftn not in executed_ftn_seq]

            return assign_children

        else:
            if len(executed_ftn_seq) >= 2:
                children_of_ftn = [ftn for ftn in children_of_ftn if ftn not in executed_ftn_seq]

            children_left=[]
            for ftn in children_of_ftn:
                if ftn in dk_left:
                    children_left.append(ftn)
                    continue

                depth = self.fwrg_manager.acyclicPaths.path_len_limit - len(executed_ftn_seq) - 1

                if depth == 1:
                    # check if one of children can be a deep function
                    for child in self.fwrg_manager.get_children_fwrg_T_A(ftn):
                        if child in dk_left:
                            children_left.append(ftn)
                            break
                if depth == 2:
                    # check if its children or grandchildren can be a deep function
                    for child in self.fwrg_manager.get_children_fwrg_T_A(ftn):
                        if child in dk_left:
                            children_left.append(ftn)
                            continue
                        for g_child in self.fwrg_manager.get_children_fwrg_T_A(child):
                            if g_child in dk_left:
                                children_left.append(ftn)
                                break

            #remove repeated children
            children_left = list(set(children_left))


            # when there are few children, add some depth-k functions
            if len(children_left) < 3:
                for ftn in dk_left:
                    if ftn not in children_left:
                        children_left.append(ftn)
                        # print(f'\n{ftn} is assigned (not based on graph)')
                    if len(children_left) >= 3:
                        break

            return children_left

    def check_children_timeout(self, state_key:str, percent_of_functions:int) -> list:

        to_be_considered_functions = [ftn for ftn, times in self.assignment_times.items() if
                                      times < self.times_limit]

        ftn_seq = get_ftn_seq_from_key_1(state_key)
        # do not consider the functions that appear in the sequence
        if len(ftn_seq) >= 2:
            to_be_considered_functions = [ftn for ftn in to_be_considered_functions if ftn not in ftn_seq]

        children_1 = self.fwrg_manager.get_children_fwrg_T_A(ftn_seq[-1])
        # due to preprocessing timeout,read/write info is partly obtained. so, consider all reads

        # consider all the children
        if fdg.global_config.flag_consider_all_reads == 1:
            children_0 = self.fwrg_manager.get_children_all_reads(ftn_seq[-1])
        else:
            children_0 = self.fwrg_manager.get_children_fwrg(ftn_seq[-1])

        children=list(set(children_0+children_1))
        children=[child for child in children if child in to_be_considered_functions]
        selected_functions = to_be_considered_functions
        if percent_of_functions < 10:
            if len(to_be_considered_functions) >3:
                select_number = math.ceil((percent_of_functions / 10) * len(to_be_considered_functions))
                select_indices = random_indices(0, len(to_be_considered_functions) - 1, select_number)
                selected_functions = [ftn for idx, ftn in enumerate(to_be_considered_functions) if
                                      idx in select_indices]


        return list(set(selected_functions+children))


