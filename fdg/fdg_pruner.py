
# support FDG-guided execution and sequence execution
from fdg.control.mine import Mine
from fdg.control.mix import MIX
from fdg.control.mix1 import MIX1
from fdg.control.rl_mlp_policy import RL_MLP_Policy
from fdg.preprocessing.address_collection import collect_addresses_in_constructor

from fdg.control.ftn_search_strategy import BFS, RandomBaseline, DFS, Seq
from fdg.control.guider import Guider

from fdg.function_coverage import FunctionCoverage

from fdg.preprocessing.preprocess import Preprocessing


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
        self.functionCoverage=FunctionCoverage(instructionCoveragePlugin)

    def _reset(self):
        self._iteration_ = 0

        self.state_hash_check=None
        self.preprocess=None
        self.condi_cov=None


        if fdg.global_config.random_baseline>0:
            self.search_stragety = RandomBaseline(fdg.global_config.random_baseline,
                                                  fdg.global_config.method_identifiers)
        elif fdg.global_config.function_search_strategy=='rl_mlp_policy':
            self.search_stragety=RL_MLP_Policy()
        elif fdg.global_config.function_search_strategy=='dfs':
            self.search_stragety=DFS()
        elif fdg.global_config.function_search_strategy=='mine':
            self.search_stragety=Mine()
        elif fdg.global_config.function_search_strategy=='seq':
            self.search_stragety=Seq()
        elif fdg.global_config.function_search_strategy=='mix':
            self.search_stragety=MIX()
        elif fdg.global_config.function_search_strategy=='mix1':
            self.search_stragety=MIX1()
        else:
            self.search_stragety = BFS()

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

            # # for saving the generated states and executed sequences
            # self.state_hash_check=state_constraints_hash_check()
            pass


        @symbolic_vm.laser_hook("stop_sym_exec")
        def stop_sym_exec_hook():
            if fdg.global_config.random_baseline>0:return



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

                self.guider.save_genesis_states(laserEVM.open_states) # to-do: think about removing it
                self.get_runtime_bytecode(laserEVM.open_states[0],fdg.global_config.contract_address)

            if fdg.global_config.random_baseline > 0:
                self.guider.start_iteration(
                    laserEVM=laserEVM, dk_functions=None,
                    iteration=self._iteration_)
                return

            if self.search_stragety.name in ['seq']:
                self.guider.start_iteration(
                    laserEVM=laserEVM, dk_functions=None,
                    iteration=self._iteration_)
                return

            if self._iteration_==1:
                # create a Preprocessing instance
                self.preprocess = Preprocessing(fdg.global_config.method_identifiers,
                                                laserEVM.open_states[0],
                                                fdg.global_config.contract_address)

                # do preprocessing
                self.preprocess.main_preprocessing_start(self._iteration_, laserEVM)
                return

            else:
                #===========================================
                if self.search_stragety.name in ['rl_mlp_policy','mix','mix1']:
                    if self._iteration_ == 2:
                        # execute all possible functions to find start functions and target functions
                        pass
                    else:
                        self.get_depth_k_functions()
                        self.guider.start_iteration(laserEVM, self.depth_k,
                                                    self._iteration_)
                        flag_terminate = self.guider.should_terminate()
                        if flag_terminate:
                            fdg.global_config.transaction_count = self._iteration_
                            laserEVM.open_states = []
                    return

                # =============================================
                if self._iteration_<=fdg.global_config.p1_dl+1:
                    # Phase 1
                    ...
                else:
                    # Phase 2
                    self.get_depth_k_functions()
                    self.guider.start_iteration(laserEVM, self.depth_k,
                                                self._iteration_)
                    flag_terminate = self.guider.should_terminate()
                    if flag_terminate:
                        fdg.global_config.transaction_count = self._iteration_
                        laserEVM.open_states = []

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
            # ++++++++++++++++++++++++++++++++++++++++++++++++++
            if fdg.global_config.random_baseline > 0:
                # prune unfeasible states
                old_states_count = len(laserEVM.open_states)
                laserEVM.open_states = [
                    state for state in laserEVM.open_states if
                    state.constraints.is_possible
                ]
                prune_count = old_states_count - len(laserEVM.open_states)
                if prune_count: log.info(
                    "Pruned {} unreachable states".format(prune_count))

                # compute coverage
                self.functionCoverage.compute_contract_coverage(
                    fdg.global_config.target_runtime_bytecode)
                # self.functionCoverage.print_coverage()

                # check at the end of iteration
                self.guider.end_iteration(laserEVM, self._iteration_)
                flag_terminate = self.guider.should_terminate()
                if flag_terminate:
                    fdg.global_config.transaction_count = self._iteration_

                if self._iteration_ == 1 and len(laserEVM.open_states) == 1:
                    # in case that there are one state
                    self.search_stragety.initialize(True)

                # termination based on the coverage of the contract
                if self.functionCoverage.coverage >= fdg.global_config.function_coverage_threshold:
                    if not self.search_stragety.flag_one_start_function:
                        fdg.global_config.transaction_count = self._iteration_

                return
            # ++++++++++++++++++++++++++++++++++++++++++++++++++
            if self.search_stragety.name in ['seq']:
                # prune unfeasible states
                old_states_count = len(laserEVM.open_states)
                laserEVM.open_states = [
                    state for state in laserEVM.open_states if
                    state.constraints.is_possible
                ]
                prune_count = old_states_count - len(laserEVM.open_states)
                if prune_count: log.info(
                    "Pruned {} unreachable states".format(prune_count))

                # compute coverage
                self.functionCoverage.compute_contract_coverage(
                    fdg.global_config.target_runtime_bytecode)
                # self.functionCoverage.print_coverage()

                # check at the end of iteration
                self.guider.end_iteration(laserEVM, self._iteration_)
                flag_terminate = self.guider.should_terminate()
                if flag_terminate:
                    fdg.global_config.transaction_count = self._iteration_



            #++++++++++++++++++++++++++++++++++++++++++++++++++
            if self.preprocess is None: return

            # collect results at the end of preprocessing
            if self._iteration_==1:
                self.preprocess.main_preprocessing_end(self._iteration_)
                self.functionCoverage.feed_function_intruction_indices(
                    self.preprocess.instruction_cov.function_instruction_indices)
                self.functionCoverage.set_runtime_bytecode(fdg.global_config.target_runtime_bytecode)
                return


            #----------------------------------------
            # at the end of each iteration in the normal symbolic execution
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

            if self._iteration_ == 2:
                # at iteration 2 (i.e., at the end of depth 1)
                if len(laserEVM.open_states) == 0:
                    print('No states are generated at depth 1.')
                    # terminate
                    fdg.global_config.transaction_count = self._iteration_
                    return


            # ++++++++++++++++++++++++++++++++++++++++++++++++++
            if self.search_stragety.name in ['rl_mlp_policy','mix','mix1']:
                if self._iteration_ == 2:
                    self.guider.end_iteration(laserEVM, self._iteration_)
                    # initialize guider
                    self.get_depth_k_functions()
                    sequences = self.guider.get_start_sequence(laserEVM)
                    start_functions = [seq[-1] for seq in sequences if
                                       len(seq) > 0]
                    start_functions = list(set(start_functions))
                    self.guider.init(start_functions, self.depth_k,
                                     self.preprocess)
                else:
                    self.guider.end_iteration(laserEVM, self._iteration_)

                flag_termination = self.guider.should_terminate()
                if flag_termination:
                    fdg.global_config.transaction_count = self._iteration_

                # termination based on the coverage of the contract
                if self.functionCoverage.coverage >= fdg.global_config.function_coverage_threshold:

                    if self.functionCoverage.coverage >= fdg.global_config.function_coverage_threshold + 1:
                        if not self.search_stragety.flag_one_start_function:
                            # make sure that when there is only one state generated at depth1,
                            # the execution does not terminate
                            fdg.global_config.transaction_count = self._iteration_
                return

            # ++++++++++++++++++++++++++++++++++++++++++++++++++
            if self._iteration_<=fdg.global_config.p1_dl:
                # the basic symbolic execution
                ...

            elif self._iteration_==fdg.global_config.p1_dl+1:
                # call init() of self.guider so that it can prepare to guide
                self.guider.end_iteration(laserEVM,self._iteration_)
                sequences=self.guider.get_start_sequence(laserEVM)

                flag_termination=self.guider.should_terminate()
                if flag_termination:
                    fdg.global_config.transaction_count=self._iteration_
                    return
                if self.search_stragety.name in ['bfs','dfs','mine']:
                    self.get_depth_k_functions()
                    start_functions = [seq[-1] for seq in sequences if len(seq)>0 ]
                    start_functions = list(set(start_functions))
                    self.guider.init(start_functions,self.depth_k,self.preprocess)
            else:
                # belong to Phase 2
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
                if self.search_stragety.name in ['mine']:
                    if self.functionCoverage.coverage>=fdg.global_config.function_coverage_threshold+1:
                        if not self.search_stragety.flag_one_start_function:
                            # make sure that when there is only one state generated at depth1,
                            # the execution does not terminate
                            fdg.global_config.transaction_count = self._iteration_
                else:
                    if not self.search_stragety.flag_one_start_function:
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



