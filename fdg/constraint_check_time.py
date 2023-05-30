from time import time
from mythril.support.support_utils import Singleton
from typing import Callable

def constraint_check_time_flags(func: Callable):
    """Measures statistics for annotated smt query check function"""
    cons_chk_flags = StateConstraintCheckIndicator()

    def function_wrapper(*args, **kwargs):
        # if not cons_chk_flags.enabled:
        #     return func(*args, **kwargs)
        begin = time()

        result = func(*args, **kwargs)

        end = time()
        cons_chk_flags.accumated_time += end - begin
        # print(f'constraint checking accumulated time:{cons_chk_flags.accumated_time}')

        return result

    return function_wrapper


class StateConstraintCheckIndicator(object, metaclass=Singleton):
    def __init__(self):
        self.accumated_time = 0
        self.enabled = False


    def __repr__(self):
        return "checking time: {}".format(
            self.accumated_time
        )

