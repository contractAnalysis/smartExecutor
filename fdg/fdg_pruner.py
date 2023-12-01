
# support FDG-guided execution and sequence execution
from fdg.control.mine import Mine, Mine1
from fdg.preprocessing.address_collection import collect_addresses_in_constructor

from fdg.control.ftn_search_strategy import BFS, RandomBaseline, DFS, Seq
from fdg.control.guider import Guider

from fdg.function_coverage import FunctionCoverage

from fdg.preprocessing.preprocess import Preprocessing
from fdg.constraint_check import state_constraints_hash_check

from mythril.laser.ethereum.state.world_state import WorldState
from mythril.laser.ethereum.svm import LaserEVM
from mythril.laser.plugin.interface import LaserPlugin
from mythril.laser.plugin.builder import PluginBuilder
from mythril.laser.plugin.plugins.coverage import InstructionCoveragePlugin
from mythril.laser.ethereum.state.global_state import GlobalState
from mythril.laser.ethereum.transaction.transaction_models import (
    ContractCreationTransaction,
)

import logging
import fdg.global_config
from mythril.laser.plugin.plugins.dependency_pruner import get_dependency_annotation


log = logging.getLogger(__name__)




class FDG_prunerBuilder(PluginBuilder):
    name = "fdg-pruner"
    def __call__(self, *args, **kwargs):
        return FDG_pruner(**kwargs)



class FDG_pruner(LaserPlugin):
    """ """
    def __init__(self,instructionCoveragePlugin:InstructionCoveragePlugin):
        """Creates FDG pruner"""
        self._reset()
        self.functionCoverage=FunctionCoverage(instructionCoveragePlugin )

    def _reset(self):
        self._iteration_ = 0

        self.state_hash_check=None
        self.preprocess=None
        self.condi_cov=None


        if fdg.global_config.random_baseline>0:
            self.search_stragety = RandomBaseline(fdg.global_config.random_baseline,
                                                  fdg.global_config.method_identifiers)
        elif fdg.global_config.function_search_strategy=='dfs':
            self.search_stragety=DFS()
        elif fdg.global_config.function_search_strategy=='mine':
            self.search_stragety=Mine()
        elif fdg.global_config.function_search_strategy=='mine1':
            self.search_stragety=Mine1()
        elif fdg.global_config.function_search_strategy=='seq':
            self.search_stragety=Seq()
        else:
            self.search_stragety = Mine()

        self.guider=Guider(self.search_stragety,list(fdg.global_config.method_identifiers.keys()))

        self.depth_k=[]
        self.flag_code_cov=True
        self.flag_num_condition=False

    def initialize(self, symbolic_vm: LaserEVM) -> None:
        """Initializes the FDG_pruner
        :param symbolic_vm
        """
        self._reset()

        @symbolic_vm.laser_hook("start_sym_exec")
        def start_sym_exec_hook():

            # for saving the generated states and executed sequences
            self.state_hash_check=state_constraints_hash_check()


        @symbolic_vm.laser_hook("stop_sym_exec")
        def stop_sym_exec_hook():
            if fdg.global_config.random_baseline>0:return
            # if not fdg.global_config.flag_preprocess_timeout:
            #     if not fdg.global_config.preprocessing_exception:
            #         if self.preprocess is not None and self.functionCoverage is not None:
            #             if self.preprocess.coverage == self.functionCoverage.coverage:
            #                 print(f'Reach the maximum coverage.')
            #
            # if fdg.global_config.print_function_coverage==1:
            #    deep_functions_1st_time=self.functionCoverage.get_deep_functions_1st_time()
            #    if len(deep_functions_1st_time) > 0:
            #         self.get_depth_k_functions()
            #         deep_function_in_the_end =self.depth_k
            #         print(
            #             f'depth-k functions: {len(deep_functions_1st_time) - len(deep_function_in_the_end)} out of {len(deep_functions_1st_time)} reaches the threshold {fdg.global_config.function_coverage_threshold}%')
            #
            #         print(f'all depth-k function(s): {deep_functions_1st_time}')
            #         print(f'left depth-k function(s): {deep_function_in_the_end}')



        @symbolic_vm.laser_hook("start_sym_trans_laserEVM")
        def start_sym_trans_hook_laserEVM(laserEVM: LaserEVM):
            """
            ...
            add states to laserEVM.open_states so that they can be used
            as base states in the next iteration of symbolic transaction
            :param laserEVM: instance of LaserEVM
            :return:
            """
            self._iteration_ += 1
            fdg.global_config.tx_len=1
            log.info(f'\n===================================')
            log.info(f'start_iteration: self._iteration_={self._iteration_}')

            if self._iteration_==1:
                laserEVM.open_states = [
                    state for state in laserEVM.open_states if state.constraints.is_possible
                ]
                if len(laserEVM.open_states) == 0:
                    fdg.global_config.transaction_count = self._iteration_
                    print('no state is generated')
                    return

                print(f'number of genesis states: {len(laserEVM.open_states)}')

                # it means no contract is deployed as no valid contracts are given
                if isinstance(fdg.global_config.contract_address,str): return

                self.guider.instructionModification.feed_instructions(
                    laserEVM.open_states[0], fdg.global_config.contract_address)

                self.guider.save_genesis_states(laserEVM.open_states)
                self.get_runtime_bytecode(laserEVM.open_states[0],fdg.global_config.contract_address)


            if fdg.global_config.random_baseline>0 :
                self.guider.start_iteration(
                    laserEVM=laserEVM, deep_functions=None, iteration=self._iteration_)

                return

            if self._iteration_==1:
                # do preprocessing
                self.preprocess = Preprocessing(fdg.global_config.method_identifiers,
                                                laserEVM.open_states[0],
                                                fdg.global_config.contract_address)

                self.preprocess.main_preprocessing_start(self._iteration_, laserEVM)
                return

            else:

                if self._iteration_==2:
                    # prepare for the execution in depth 1
                    self.guider.start_iteration(laserEVM=laserEVM,iteration=self._iteration_)
                    # self.condi_cov=ConditionCoverage(self.preprocess)
                else:
                    self.get_depth_k_functions()
                    self.guider.start_iteration(laserEVM, self.depth_k, self._iteration_)
                    flag_terminate=self.guider.should_terminate()
                    if flag_terminate:
                        fdg.global_config.transaction_count=self._iteration_
                        laserEVM.open_states=[]


        @symbolic_vm.laser_hook("stop_sym_trans_laserEVM")
        def stop_sym_trans_hook_laserEVM(laserEVM: LaserEVM):
            """
            - save states
            - some saved states are used as initial states in sequence execution

            :param laserEVM:
            :return:
            """
            log.info(f'\n----------------------------------------')
            log.info(f'end: self._iteration_={self._iteration_}')

            if fdg.global_config.random_baseline>0 :
                # prune unfeasible states
                old_states_count = len(laserEVM.open_states)
                laserEVM.open_states = [
                    state for state in laserEVM.open_states if state.constraints.is_possible
                ]
                prune_count = old_states_count - len(laserEVM.open_states)
                if prune_count: log.info("Pruned {} unreachable states".format(prune_count))

                # compute coverage
                self.functionCoverage.compute_contract_coverage(fdg.global_config.target_runtime_bytecode)
                self.functionCoverage.print_coverage()


                # check at the end of iteration
                self.guider.end_iteration(laserEVM,self._iteration_)
                flag_terminate=self.guider.should_terminate()
                if flag_terminate:
                    fdg.global_config.transaction_count=self._iteration_

                if self._iteration_==1 and len(laserEVM.open_states) == 1:
                    # in case that there are one state
                    self.search_stragety.initialize(True)

                # termination based on the coverage of the contract
                if self.functionCoverage.coverage >= fdg.global_config.function_coverage_threshold:
                    if not self.search_stragety.flag_one_state_at_depth1:
                        fdg.global_config.transaction_count = self._iteration_

                return


            #++++++++++++++++++++++++++++++++++++++++++++++++++
            if self.preprocess is None: return

            # collect results at the end of preprocessing
            if self._iteration_==1:
                self.preprocess.main_preprocessing_end(self._iteration_)
                self.functionCoverage.feed_function_indices(
                    self.preprocess.instruction_cov.function_instruction_indices)
                self.functionCoverage.set_runtime_bytecode(fdg.global_config.target_runtime_bytecode)
                return


            #----------------------------------------
            # end of normal symbolic execution
            # prune unfeasible states
            old_states_count = len(laserEVM.open_states)
            laserEVM.open_states = [
                state for state in laserEVM.open_states if state.constraints.is_possible
            ]
            prune_count = old_states_count - len(laserEVM.open_states)
            if prune_count: log.info("Pruned {} unreachable states".format(prune_count))


            # compute coverage
            self.functionCoverage.compute_coverage()
            self.functionCoverage.print_coverage()

            if self._iteration_==2:
                if len(laserEVM.open_states) == 0:
                    print('No states are generated at depth 1.')
                # initialize fdfg manager
                self.guider.end_iteration(laserEVM,self._iteration_)
                sequences=self.guider.get_start_sequence(laserEVM)
                flag_termination=self.guider.should_terminate()
                if flag_termination:
                    fdg.global_config.transaction_count=self._iteration_
                    return
                if self.search_stragety.name in ['bfs','dfs','mine','mine1']:
                    self.get_depth_k_functions()
                    start_functions = [seq[-1] for seq in sequences if len(seq)>0 ]
                    start_functions = list(set(start_functions))
                    self.guider.init(start_functions,self.depth_k,self.preprocess)


            else:

                self.guider.end_iteration(laserEVM,self._iteration_)

            flag_termination=self.guider.should_terminate()
            if flag_termination:
                fdg.global_config.transaction_count = self._iteration_


            # # termination based on deep functions(not appropriate when timeout can happen in preprocessing as the instructions of functions can not be correctly obtained)
            # self.get_depth_k_functions()            #
            # if len(self.depth_k) ==0:
            #     fdg.global_config.transaction_count = self._iteration_

            # termination based on the coverage of the contract
            if self.functionCoverage.coverage>=fdg.global_config.function_coverage_threshold:
                if self.search_stragety.name in ['mine', 'mine1']:
                    if self.functionCoverage.coverage>=fdg.global_config.function_coverage_threshold+1:
                        if not self.search_stragety.flag_one_state_at_depth1:
                            # make sure that when there is only one state generated at depth1,
                            # the execution does not terminate
                            fdg.global_config.transaction_count = self._iteration_
                else:
                    if not self.search_stragety.flag_one_state_at_depth1:
                        # make sure that when there is only one state generated at depth1,
                        # the execution does not terminate
                        fdg.global_config.transaction_count = self._iteration_

        # record the instructions visited
        @symbolic_vm.laser_hook("preprocessing_execute_state")
        def execute_state_hook(global_state: GlobalState,opcode:str):
            self.preprocess.instruction_cov.update_coverage(global_state,opcode)

        @symbolic_vm.preprocessing_pre_hook("SLOAD")
        def sload_hook(state: GlobalState):
            """
               collect the locations in storage that are read
            :param state:
            :return:
            """
            self.preprocess.write_read_info.update_sload(state)


        @symbolic_vm.preprocessing_pre_hook("SSTORE")
        def sstore_hook(state: GlobalState):
            """
             collect the locations in storage that are written
            :param state:
            :return:
            """
            self.preprocess.write_read_info.update_sstore(state)

        @symbolic_vm.preprocessing_pre_hook("JUMPI")
        def jumpi_hook(state: GlobalState):
            """
             collect the locations in storage that are written
            :param state:
            :return:
            """
            self.preprocess.read_in_conditions.collect_conditions(state)


        @symbolic_vm.pre_hook("SSTORE")
        def sstore_hook_constructor(state: GlobalState):
            """
            collect concrete addresses in constructor if there are
            :param state:
            :return:
            """
            if self._iteration_ == 0:
                # collect addresses
                location = state.mstate.stack[-1]
                value = state.mstate.stack[-2]
                if not value.symbolic:
                    collect_addresses_in_constructor(str(location), str(value))



        @symbolic_vm.laser_hook("pre_execute_state")
        def pre_execute_state_hook(global_state:GlobalState):
            self.state_hash_check.record_pre_hash(global_state)

        @symbolic_vm.laser_hook("post_execute_state")
        def post_execute_state_hook(opcode,new_states:[GlobalState]):
            self.state_hash_check.record_post_hash(opcode,new_states)


        @symbolic_vm.pre_hook("STOP")
        def stop_hook(state: GlobalState):
            # _transaction_end(state)
            pass

        @symbolic_vm.pre_hook("RETURN")
        def return_hook(state: GlobalState):
            # _transaction_end(state)
            pass

        def _transaction_end(state: GlobalState) -> None:
            """update the function sequence resulting this state

            :param state:
            """

            pass


        @symbolic_vm.laser_hook("add_world_state")
        def world_state_filter_hook(state: GlobalState):
            if isinstance(state.current_transaction, ContractCreationTransaction):
                # Reset iteration variable
                self._iteration_ = 0
                return


    def get_depth_k_functions(self):
        # ---------------------------------------------
        self.depth_k=self.functionCoverage.compute_deep_functions()

    def get_runtime_bytecode(self,state:WorldState,contract_address):
        fdg.global_config.target_runtime_bytecode=state.accounts[contract_address.value].code.bytecode



