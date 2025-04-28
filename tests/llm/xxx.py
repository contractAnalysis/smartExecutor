import os.path
from copy import copy

import llm
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
NUM_max_candidate_sequences=15
NUM_min_candidate_sequences=5

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


def find_invalid_sequences(sequences_bf_exe, sequences_af_exe) -> list:
    invalid = []
    for seq_bf in sequences_bf_exe:
        # identify the function, at which the execution fails
        actual_seq = [seq for seq in sequences_af_exe if len(seq) > 0]
        flag_invalid=False
        for idx, func in enumerate(seq_bf):
            if func in [seq[idx] for seq in actual_seq]:
                # remove unmatched sequences and continue
                actual_seq = [seq for seq in actual_seq if
                              seq[idx] in [func] and idx + 1 < len(seq)]
            else:
                flag_invalid=True
                break

        if flag_invalid:
            if idx == 0: idx = 1  # never stops at depth 1
            invalid.append(seq_bf[0:idx + 1])

    return invalid


def prune_candidate_sequences(cur_iteration, cur_targets,
                              cur_sequences_to_be_exe_dict, cur_all_sequences,
                              cur_actual_executed_seq, candidate_sequences
                             ):
    """
    prune candidate sequences for current targets

    remove executed sequences


    """

    def should_include(seq, seq_list):

        for path in seq_list:
            if is_prefix(path, seq):
                color_print('Blue',
                            f'{seq} should be included. It has a prefix {path}')
                return True
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

    cur_sequences_to_be_exe = list(cur_sequences_to_be_exe_dict.values())
    pruned_candi_sequences = {}

    color_print('Red',
                f'\n==== current all sequences ==== {cur_iteration} ===={os.path.basename(__file__)}')
    for pa in cur_all_sequences:
        color_print('Gray', f'{pa}')

    color_print('Red',
                f'\n==== all currently executed sequences ==== {cur_iteration} ===={os.path.basename(__file__)}')
    for pa in cur_actual_executed_seq:
        color_print('Gray', f'{pa}')

    for target in cur_targets:
        if target not in candidate_sequences.keys(): continue

        candi_seq = candidate_sequences[target]
        color_print('Red',
                    f'\n==== candidate sequences for {target}===={os.path.basename(__file__)}')
        for pa in candi_seq:
            color_print('Gray', f'{pa}')

        # remove the sequences that are generated
        temp_candi = []
        for seq in candi_seq:
            if is_contained(seq, cur_all_sequences):
                color_print('Red',
                            f'{seq} is contained in current sequences and thus should be removed')
            else:
                temp_candi.append(seq)

        # remove the sequences that has an invalid prefix
        invalid_seq = find_invalid_sequences(cur_sequences_to_be_exe,
                                             cur_actual_executed_seq)
        temp_candi_2 = []
        for seq in temp_candi:
            flag_remove = False
            for x_seq in invalid_seq:
                if is_prefix(x_seq, seq):
                    flag_remove = True
                    color_print('Red',
                                f'{seq} should be removed as it contains an invalid sequence {x_seq}.')
                    break
            if not flag_remove:
                temp_candi_2.append(seq)

        # keep the sequences that have the prefix appearing in the sequences executed successfully
        refined_paths = []

        flag_stop = False
        for i in range(3, 0, -1):
            for seq in temp_candi_2:
                if seq in refined_paths:continue
                if should_include(seq, [path[0:i] for path in
                                        cur_actual_executed_seq if
                                        len(path) >= i]):
                    refined_paths.append(seq)
                    if len(refined_paths) >= NUM_max_candidate_sequences:
                        flag_stop = True
                        break
            if flag_stop:
                break

        pruned_candi_sequences[target] = refined_paths
        color_print('Gray',
                    f'\n{len(refined_paths)}/{len(candi_seq)} are kept ({len(refined_paths) / len(candi_seq)})')

    return pruned_candi_sequences


def get_feedback(cur_targets, cur_sequences_to_be_exe_dict, cur_actual_executed_seq, left_targets_and_coverage:dict, other_cur_feedback:dict={}):
    """
        feedback: valid sequence, or invalid (pointing the position the execution stop)
        via: comparing with the sequences before and after sequence execution.
        other_cur_feedback: feedback for some invalid sequences without execution to validate (e.g., the first function is not a start function).

        only provide feedback for targets that more sequences are required.
    """
    color_print('Red', f'cur_targets:{ cur_targets}')
    color_print('Red', f'self,left_targets_and_coverage:')
    for k, v in left_targets_and_coverage.items():
        color_print("Blue", f'{k}:{v}')

    def be_a_prefix_1(seq1:list,seq2:list):
        if len(seq1)>len(seq2):return False
        for i,e1 in enumerate(seq1):
            if e1 not in [seq2[i]]:
                return False
        return True

    cur_seq_status={}
    for target in cur_targets:
        if target not in cur_sequences_to_be_exe_dict.keys():
            if target in other_cur_feedback.keys():
                cur_seq_status[target]=other_cur_feedback[target]
            else:
                # the status is unknown
                if not llm.llm_config.FLAG_exp:
                    print(f'No feedback is found for target {target} in file {os.path.basename(__file__)}')
        else:
            #
            gen_seq=cur_sequences_to_be_exe_dict[target]
            flag_valid=False
            # has a valid sequence but low code coverage
            for actual_seq in cur_actual_executed_seq:
                if be_a_prefix_1(gen_seq, actual_seq):
                    flag_valid = True
                    if target in left_targets_and_coverage.keys():
                        cur_seq_status[target]=f"{gen_seq} is a valid sequence, but function {target} has the low code coverage {left_targets_and_coverage[target]} and thus another different sequence is required."
                    else:
                        cur_seq_status[
                            target] = f"{gen_seq} is a valid sequence. The coverage of {target} reaches a threshold. "
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


    color_print('Red',
    f'\n==== feedback on targets ======={os.path.basename(__file__)}')
    for target, status in cur_seq_status.items():
        color_print('Blue', f'{target}')
        color_print('Gray', f'{status}')
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

    prune_candi_sequences=prune_candidate_sequences(cur_iteration,cur_targets,
                              current_sequences_in_interations[f'all_iteration_{cur_iteration-1}'],current_sequences_in_interations[f'all_iteration_{cur_iteration-1}'],
                              current_sequences_in_interations[f'exe_iteration_{cur_iteration-1}'],
                              candidate_sequences,

                              )

    # print the received graph built from data dependency
    color_print('Red',
                f'\n\n==== candidate sequences after pruning ===== {cur_iteration} ===={os.path.basename(__file__)}')
    for k, v in prune_candi_sequences.items():
        color_print('Blue', f'"{k}":')
        for p in v:
            color_print('Gray', f'{p}')

    for i in range(3,1,-1):
        print(f'{i}')


