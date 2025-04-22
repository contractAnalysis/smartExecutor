import os.path
from copy import copy

from llm.utils import color_print
from tests.llm.test_data_HoloToken import graph, \
    current_sequences_in_interations

"""
test:
    candidate sequence generation
    feedback collection
    candidate sequence pruning

for easy testing, I just copy the major functions here and slightly modify(no logic changing) so that they can be executed independently

functions related to candidate sequences generation and refining
    get_candidate_sequences() # called once in llm.py     
    prune_candidate_sequences() # called iteratively in llm.py    
    find_start_states()
    get_feedback()

"""

SEQ_4_Consideration=5

SEQ_iteration=3
NUM_max_candidate_sequences=10
NUM_min_candidate_sequences=5

def get_candidate_sequences(graph, start_functions, cur_targets):
    def find_all_paths(graph, start, target='d', max_length=4, path=None):
        if path is None:
            path = []

        path.append(start)
        if start == target and len(path) <= max_length:
            return [path]

        if start not in graph or len(path) > max_length:
            return []

        all_paths = []
        if start in graph:
            for neighbor in graph[start]:
                if neighbor not in path:  # Avoid cycles
                    new_paths = find_all_paths(graph, neighbor, target,
                                               max_length,
                                               path[:])
                    all_paths.extend(new_paths)
        return all_paths


    # print the received graph built from data dependency
    color_print('Red', f'\n\n====graph===={os.path.basename(__file__)}')
    for k, v in graph.items():
        color_print('Blue', f'"{k}":{v}')

    all_target_paths_dict = {}
    for target in cur_targets:
        target_paths = []
        for start_node in start_functions:
            paths = find_all_paths(graph, start_node, target=target)
            for p in paths:
                if p not in target_paths and len(p) > 1:
                    target_paths.append(p)
        all_target_paths_dict[target] = target_paths

    # print the paths grouped by targets
    color_print('Red',
                f'\n\n==== paths grouped by targets===={os.path.basename(__file__)}')
    for tar, paths in all_target_paths_dict.items():
        color_print('Blue', f'"{tar}":')
        for pa in paths:
            color_print('Gray', f'{pa},')

    return all_target_paths_dict


def prune_candidate_sequences(cur_iteration,cur_targets, cur_sequences_dict, cur_actual_executed_seq,candidate_sequences):
    """
    prune candidate sequences for current targets
    """

    def should_include(seq, seq_list):
        def is_prefix(seq1, seq2):
            # Check if seq1 is longer than seq2
            if len(seq1) > len(seq2):
                return False

            # Compare each element of seq1 with the corresponding element of seq2
            for i in range(len(seq1)):
                if seq1[i] not in [seq2[i]]:
                    return False
            # If we've made it through the loop, seq1 is a prefix of seq2
            return True

        for path in seq_list:
            if is_prefix(path, seq):
                color_print('Blue', f'{seq} should be included. It has a prefix {path}')
                return True
        color_print('Red', f'{seq} should not be included')
        return False

    def is_contained(seq, seq_list):
        def is_equal(seq1, seq2):
            if len(seq1) != len(seq2):
                return False

            for i in range(len(seq1)):
                if seq1[i] not in [seq2[i]]:
                    return False
            return True

        for path in seq_list:
            if is_equal(seq, path):
                return True
        return False

    all_cur_sequences = list(cur_sequences_dict.values())

    color_print('Red',
                f'\n==== all current sequences ==== {cur_iteration} ===={os.path.basename(__file__)}')
    for pa in all_cur_sequences:
        color_print('Gray', f'{pa}')

    color_print('Red',
                f'\n==== all currently executed sequences ==== {cur_iteration} ===={os.path.basename(__file__)}')
    for pa in cur_actual_executed_seq:
        color_print('Gray', f'{pa}')

    if cur_iteration == 2:

        for target in cur_targets:
            if target not in candidate_sequences.keys(): continue

            candi_seq = candidate_sequences[target]
            color_print('Red',
                        f'\n==== candidate sequences for {target}===={os.path.basename(__file__)}')
            for pa in candi_seq:
                color_print('Gray', f'{pa}')

            # remove the sequences that are executed
            temp_candi=[]
            for seq in candi_seq:
                if is_contained(seq, all_cur_sequences):
                    color_print('Red', f'{seq} is contained in current sequences and thus should be removed')
                else:
                    temp_candi.append(seq)

            refined_paths = []
            flag_stop=False
            for i in range(3, 0, -1):
                for seq in candi_seq:

                    # keep the sequences that have the prefix appearing in the sequences executed successfully

                    if should_include(seq, [path[0:i] for path in
                                            cur_actual_executed_seq if
                                            len(path) >= i]):
                        refined_paths.append(seq)
                        if len(refined_paths)>=NUM_max_candidate_sequences:
                            flag_stop=True
                            break
                if flag_stop:
                    break

            candidate_sequences[target] = refined_paths
            color_print('Gray',
                        f'\n{len(refined_paths)}/{len(candi_seq)} are kept ({len(refined_paths) / len(candi_seq)})')


    elif cur_iteration > 2:

        for target in cur_targets:
            refined_paths = []
            if target not in candidate_sequences.keys(): continue
            candi_seq = candidate_sequences[target]
            color_print('Red',
                        f'\n==== candidate sequences for {target}===={os.path.basename(__file__)}')
            for pa in candi_seq:
                color_print('Blue', f'{pa}')

            for seq in candi_seq:
                # remove the sequences that are executed
                if is_contained(seq, all_cur_sequences):
                    color_print('Blue',
                                f'{seq} is contained in current sequences and thus should be removed')
                    continue
                refined_paths.append(seq)
            candidate_sequences[target] = refined_paths


def get_feedback(cur_targets,cur_sequences_dict,cur_actual_executed_seq,left_targets_and_coverage:dict):
    def be_a_prefix_1(seq1:list,seq2:list):
        if len(seq1)>len(seq2):return False
        for i,e1 in enumerate(seq1):
            if e1 not in [seq2[i]]:
                return False
        return True

    cur_seq_status={}
    for target in cur_targets:
        if target in cur_sequences_dict.keys():
            gen_seq=cur_sequences_dict[target]
            flag_valid=False
            # has a valid sequence but low code coverage
            for actual_seq in cur_actual_executed_seq:
                if be_a_prefix_1(gen_seq, actual_seq):
                    flag_valid = True
                    if target in left_targets_and_coverage.keys():
                        cur_seq_status[target]=f"{gen_seq} is a valid sequence, but function {target} has the low code coverage {left_targets_and_coverage[target]} and thus another different sequence is required."
                    else:
                        cur_seq_status[
                            target] = f"{gen_seq} is a valid sequence."
                    break

            # does not have a valid sequence
            if not flag_valid:
                # identify the function, at which the execution fails
                actual_seq=[seq for seq in cur_actual_executed_seq if len(seq)>0]
                for idx,func in enumerate(gen_seq):
                    if func in [seq[idx] for seq in actual_seq ]:
                        # remove unmatched sequences and continue
                        actual_seq=[seq for seq in actual_seq if seq[idx] in [func] and idx+1<len(seq)]
                    else:
                        break

                if idx <len(gen_seq):
                    if idx==0:idx=1 # never stops at depth 1
                    cur_seq_status[
                        target] = f"{gen_seq} is invalid. The execution stops at function {gen_seq[idx]}."

    return cur_seq_status


if __name__ == "__main__":

    start_functions = ['transferOwnership', 'setMinter', 'decreaseApproval',
                       'increaseApproval', 'setDestroyer']

    # ========= iteration 1 ========================
    cur_iteration = 1
    cur_targets = ['transferFrom', 'mint', 'burn', 'transfer', 'approve',
    'finishMinting', 'decreaseApproval']
    left_targets_and_coverage = {
    'transfer': 32.68608414239482,
    'burn': 51.072961373390555
    }

    # test feedback collection
    feedback = get_feedback(
        cur_targets,
        current_sequences_in_interations[f'all_iteration_{cur_iteration}'],
    current_sequences_in_interations[f'exe_iteration_{cur_iteration}'],
    left_targets_and_coverage
    )

    color_print('Red',
    f'\n==== feedback ==== {cur_iteration} ===={os.path.basename(__file__)}')
    for target, status in feedback.items():
        color_print('Blue', f'{target}')
        color_print('Gray', f'{status}')



    #========= iteration 2 ========================
    cur_iteration=2
    cur_targets=['transfer', 'burn']

    candidate_sequences=get_candidate_sequences(graph,start_functions,cur_targets)

    prune_candidate_sequences(cur_iteration,cur_targets,
                              current_sequences_in_interations[f'all_iteration_{cur_iteration-1}'],
                              current_sequences_in_interations[f'exe_iteration_{cur_iteration-1}'],
                              candidate_sequences,

                              )

    # print the received graph built from data dependency
    color_print('Red',
                f'\n\n==== candidate sequences after pruning ===== {cur_iteration} ===={os.path.basename(__file__)}')
    for k, v in candidate_sequences.items():
        color_print('Blue', f'"{k}":')
        for p in v:
            color_print('Gray', f'{p}')

    for i in range(3,1,-1):
        print(f'{i}')
