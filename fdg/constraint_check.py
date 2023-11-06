import fdg.global_config
from fdg.constraint_check_time import constraint_check_time_flags
from mythril.laser.ethereum.state.global_state import GlobalState


class state_constraints_hash_check():
    def __init__(self):
        self.pre_constraints_lenth=0
        self.post_constraints_lenth = []


    @constraint_check_time_flags
    def record_pre_hash(self, state:GlobalState):
        self.pre_constraints_lenth =len(state.world_state.constraints)


    @constraint_check_time_flags
    def record_post_hash(self, opcode, new_states:[GlobalState]):

        if not str(opcode).__eq__('JUMPI'):
            if str(opcode) in ['REVERT', 'EMPTY']:
                fdg.global_config.flag_query_solver = [False] * len(new_states)
            else:
                self.post_constraints_lenth = [len(state.world_state.constraints) for state in new_states]
                fdg.global_config.flag_query_solver = self.need_to_check()
        else:
            fdg.global_config.flag_query_solver=[]
        # print(f'{opcode}: query_check_flag(s): {fdg.FDG_global.flag_query_solver}')
        # pass


    def need_to_check(self) -> list:
        return [False if length==self.pre_constraints_lenth else True for length in self.post_constraints_lenth]

