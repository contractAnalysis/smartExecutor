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

    def can_reach_targets(self,ftn:str,targets:list,max_depth:int)->bool:
        """
        check there is a path from ftn to one of the targets
        the max length of such a path should be no larger than max_depth
        """
        if ftn in targets:return True

        depth=0
        functions=[ftn]
        while depth<max_depth:
            depth+=1
            all_children=[]
            for func in functions:
                children=self.fwrg_manager.get_children_fwrg_T_A(func)
                if len([child for child in children if child in targets])>0:
                    return True
                all_children+=children
            # prepare for the next depth
            functions=list(set(all_children))

        # if not end after while statement, return False
        return False

    def get_targets_be_reached(self, ftn:str, targets:list, max_depth:int)->int:
        targets_be_reached=[]
        if ftn in targets:
            targets_be_reached.append(ftn)

        functions=[ftn]
        depth=0
        while depth<max_depth:
            depth+=1
            all_children=[]
            for func in functions:
                children=self.fwrg_manager.get_children_fwrg_T_A(func)
                for child in children:
                    if child in targets and child not in targets_be_reached:
                        targets_be_reached.append(child)
                all_children+=children

            functions=list(set(all_children))
        return targets_be_reached


    def assign_functions_for_baseline(self)->list:

        to_consider_functions=self.all_functions
        select_num=math.ceil((self.random_select_percent/10)*len(to_consider_functions))

        select_indices=random_indices(0,len(to_consider_functions)-1,select_num)
        selected_functions=[ftn for idx,ftn in enumerate(to_consider_functions) if idx in select_indices]

        # self.record_assignment(selected_functions)
        return selected_functions

    def assign_all_functions(self):
        if len(self.all_functions)==0:
            # print(f'keep the original instruction list in function_assignment.py')

            return ['original_instruction_list']
        self.record_assignment(self.all_functions)
        return self.all_functions

    def select_functions_randomly(self,percentage:int)->list:
        to_consider_functions = self.all_functions
        select_num = math.ceil(
            (percentage/ 10) * len(to_consider_functions))

        select_indices = random_indices(0, len(to_consider_functions) - 1,
                                        select_num)
        selected_functions = [ftn for idx, ftn in
                              enumerate(to_consider_functions) if
                              idx in select_indices]

        return selected_functions

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

        if len(to_execute_functions)>0:
            self.record_assignment(to_execute_functions)
            return to_execute_functions
        else:
            ftn_seq = get_ftn_seq_from_key_1(state_key)

            fallback_case = self.fallback_case(ftn_seq)
            if len(fallback_case) > 0:
                return fallback_case

            # identify the dk functions for a particular state
            dk_left = []
            for ftn, cov in dk_functions:
                # if ftn=='fallback':continue
                if self.assignment_times[ftn] < self.times_limit:
                    dk_left.append(ftn)
                    continue
                if self.assignment_times[ftn] >= 2 * self.times_limit:
                    continue
                if cov < 70:
                    dk_left.append(ftn)

            # get children from the augmented graph
            children = self.fwrg_manager.get_children_fwrg_T_A(ftn_seq[-1])

            # another case to get children: when the flag is set that all reads in a function are considered
            if fdg.global_config.flag_consider_all_reads == 1:
                children_o = self.fwrg_manager.get_children_all_reads(
                    ftn_seq[-1])
                children += children_o
                children = list(set(children))

            # remove children that should not be executed (i.e. already considered)
            children = [child for child in children if
                        child not in not_to_execute]

            # consider children that are target or can reach a target
            children = [child for child in children if
                        self.can_reach_targets(child,
                                               dk_left,
                                               fdg.global_config.seq_len_limit - len(ftn_seq)-1
                                               )
                        ]


            #----------------
            # to-do list
            # if no child or few children are found, is it possible to assign dk functions?


            #----------------
            # consider a function that no function can reach it in the graph (because the reads in conditions are not captured)
            considered=self.consider_dk_functions_not_reachable()
            for ftn in considered:
                if ftn not in children:
                    children.append(ftn)

            # permit self dependency once
            if len(ftn_seq) >= 2:
                children = [child for child in children if
                            child not in ftn_seq[0:-1]]

            self.record_assignment(children)
            return children

    def consider_dk_functions_not_reachable(self)->list:
        """
        unreachable: the reads in a condition are not recognized, or no reads in a condition.
        handle: consider all the reads in a function

        symbol(),name(),version() are functions that are not reachable.
        """
        if len(self.fwrg_manager.updateFWRG.dk_not_reachable)==0:
            return []
        # consider it until the execution times reach the limits (on the first several states)
        considers=[]
        for ftn in self.fwrg_manager.updateFWRG.dk_not_reachable:
            # if ftn in ['symbol()','name()','version()']:continue
            if self.assignment_times[ftn] < self.times_limit:
                considers.append(ftn)

        return considers

    def when_no_children_assigned(self,dk_functions:list):
        pass



    def assign_functions_timeout(self, state_key: str,dk_functions:list, percent_of_functions:int=1):
        print_function_assignmnets(self.assignment_times)

        ftn_seq = get_ftn_seq_from_key_1(state_key)
        fallback_case = self.fallback_case(ftn_seq)
        if len(fallback_case) > 0:
            return fallback_case

        # identify the functions to be considered
        to_be_considered_functions = []
        for ftn, cov in dk_functions:
            # if ftn=='fallback':continue
            if self.assignment_times[ftn] < self.times_limit:
                to_be_considered_functions.append(ftn)
                continue
            if self.assignment_times[ftn] >= 2 * self.times_limit:
                continue
            if cov < 70:
                to_be_considered_functions.append(ftn)

        # get children when all reads are considered due to preprocessing timeout,read/write info is partly obtained. so, consider all reads
        children = self.fwrg_manager.get_children_all_reads(ftn_seq[-1])

        # consider children that are target or can reach a target
        children = [child for child in children if
                    self.can_reach_targets(child,
                                           to_be_considered_functions,
                                           fdg.global_config.seq_len_limit - len(
                                               ftn_seq) - 1
                                           )
                    ]

        # permit self dependency once
        if len(ftn_seq) >= 2:
            children = [child for child in children if
                        child not in ftn_seq[0:-1]]

        # select functions from to be considered functions
        selected_functions = to_be_considered_functions
        if percent_of_functions < 10:
            if len(to_be_considered_functions) > 3:
                select_number = math.ceil(
                    (percent_of_functions / 10) * len(
                        to_be_considered_functions))
                select_indices = random_indices(0,
                                                len(to_be_considered_functions) - 1,
                                                select_number)
                selected_functions = [ftn for idx, ftn in enumerate(
                    to_be_considered_functions) if
                                      idx in select_indices]

        assigned_functions= list(set(selected_functions + children))

        if len(assigned_functions)>0:
            self.record_assignment(assigned_functions)

        return assigned_functions

    def assign_functions_timeout_mine(self, state_key: str,dk_functions:list,randomly_selected_functions:list):
        print_function_assignmnets(self.assignment_times)

        ftn_seq = get_ftn_seq_from_key_1(state_key)
        fallback_case = self.fallback_case(ftn_seq)
        if len(fallback_case) > 0:
            return fallback_case

        # identify the functions to be considered
        to_be_considered_functions = []
        for ftn, cov in dk_functions:
            # if ftn=='fallback':continue
            if self.assignment_times[ftn] < self.times_limit:
                to_be_considered_functions.append(ftn)
                continue
            if self.assignment_times[ftn] >= 2 * self.times_limit:
                continue
            if cov < 70:
                to_be_considered_functions.append(ftn)

        # get children when all reads are considered due to preprocessing timeout,read/write info is partly obtained. so, consider all reads
        children = self.fwrg_manager.get_children_all_reads(ftn_seq[-1])

        # consider children that are target or can reach a target
        children = [child for child in children if
                    self.can_reach_targets(child,
                                           to_be_considered_functions,
                                           fdg.global_config.seq_len_limit - len(
                                               ftn_seq) - 1
                                           )
                    ]

        # permit self dependency once
        if len(ftn_seq) >= 2:
            children = [child for child in children if
                        child not in ftn_seq[0:-1]]

        # select functions from to be considered functions

        assigned_functions= list(set(randomly_selected_functions + children))

        if len(assigned_functions)>0:
            self.record_assignment(assigned_functions)

        return assigned_functions

