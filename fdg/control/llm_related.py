import os
from math import floor

import numpy as np

import fdg.global_config
import llm.llm_config

from llm.llm_config import NUM_max_candidate_sequences
from llm.utils import color_print


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

def get_feedback(cur_targets, cur_sequences_to_be_exe_dict, cur_actual_executed_seq, left_targets_and_coverage:dict,target_code_coverage:dict={}, other_cur_feedback:dict={}):
    """
        feedback: valid sequence, or invalid (pointing the position the execution stop)
        via: comparing with the sequences before and after sequence execution.
        other_cur_feedback: feedback for some invalid sequences without execution to validate (e.g., the first function is not a start function).

        only provide feedback for targets that more sequences are required.
    """
    color_print('Red', f'====== Collect feedback =========={os.path.basename(__file__)}')
    color_print('Red', f'target(s):{ cur_targets}')
    color_print('Red', f'target: code coverage:')
    for k, v in left_targets_and_coverage.items():
        color_print("Gray", f'\t{k}:{v}')



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
                    color_print("Red",f'{target}:No sequence is found. (from file {os.path.basename(__file__)})')
                cur_seq_status[target] = f'No sequence is found.'
        else:
            #
            gen_seq=cur_sequences_to_be_exe_dict[target]
            flag_valid=False
            # has a valid sequence but low code coverage
            for actual_seq in cur_actual_executed_seq:
                if be_a_prefix_1(gen_seq, actual_seq):
                    flag_valid = True
                    if target in left_targets_and_coverage.keys():
                        code_cov=[]
                        if target in target_code_coverage.keys():
                            code_cov=target_code_coverage[target]
                        if len(code_cov)==0:
                            cur_seq_status[target]=f"{gen_seq} is a valid sequence, but function {target} has the code coverage {left_targets_and_coverage[target]} below the threshold {fdg.global_config.function_coverage_threshold} and thus another different sequence is required for {target}."
                        else:
                            if round(left_targets_and_coverage[target])==round(code_cov[-1]):
                                cur_seq_status[
                                    target] = f"{gen_seq} is a valid sequence. However,function {target} still has the code coverage {left_targets_and_coverage[target]} below the threshold {fdg.global_config.function_coverage_threshold}. The code coverage does not change after the execution of this sequence. Hence, please try to understand the contract code and find a proper sequence for {target}."
                            elif round(left_targets_and_coverage[target])-round(code_cov[-1])<5:
                                cur_seq_status[
                                    target] = f"{gen_seq} is a valid sequence. However,function {target} still has the code coverage {left_targets_and_coverage[target]} below the threshold {fdg.global_config.function_coverage_threshold}. The code coverage increase is not significant after the execution of this sequence. Please try your best to find a proper sequence for {target}."
                            else:
                                cur_seq_status[
                                    target] = f"{gen_seq} is a valid sequence. However, the code coverage  {left_targets_and_coverage[target]} of function {target} remains below the threshold {fdg.global_config.function_coverage_threshold}. The code coverage increases a lot. Please keep up to find a sequence for this target function."

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

                    dif_cur_cov_threshold=round(fdg.global_config.function_coverage_threshold)-round(left_targets_and_coverage[target])

                    if dif_cur_cov_threshold>20:
                        cur_seq_status[
                            target] = f"{gen_seq} is invalid. The execution stops at function {gen_seq[idx]}. The code coverage of this function so far is {left_targets_and_coverage[target]}, far below the threshold. Please check the whole smart contract code to find a proper sequence for {target}."
                    else:
                        cur_seq_status[
                            target] = f"{gen_seq} is invalid. The execution stops at function {gen_seq[idx]}. The code coverage of this function so far is {left_targets_and_coverage[target]}. The code coverage can be further improved. Please find a proper sequence to increase code coverage for {target}."


    for target, status in cur_seq_status.items():
        color_print('Blue', f'{target}')
        color_print('Gray', f'{status}')

    return cur_seq_status


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

    # # print the paths grouped by targets
    # color_print('Red',
    #             f'\n\n==== paths grouped by targets===={os.path.basename(__file__)}')
    # for tar, paths in all_target_paths_dict.items():
    #     color_print('Blue', f'"{tar}":')
    #     for pa in paths:
    #         color_print('Gray', f'{pa},')

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

def random_select_from_list(given_data:list,size_select:int)->list:
    if len(given_data)>size_select:
        select=np.random.choice(range(len(given_data)),size=size_select,replace=False)
        return [given_data[idx] for idx in select]
    else:
        return given_data

def prune_candidate_sequences(cur_iteration, cur_targets,
                              cur_sequences_to_be_exe_dict, cur_all_sequences,
                              cur_actual_executed_seq, valid_sequences,candidate_sequences, num_limit:bool=True
                             ):
    """
    prune candidate sequences for current targets

    remove:
        sequences in cur_all_sequences
        sequences containing a prefix that is invalid  (invalid sequences found via: all current sequences and all currently executd sequences
    keep:
        sequences containing a prefix that is valid until the number of the kept sequences reaches a threshold.


    """

    def should_include(seq, seq_list):
        if len(seq_list)==0:return False
        for path in seq_list:
            if is_prefix(path, seq):
                color_print('Blue',
                            f'{seq} should be included. It has a prefix {path}')
                return True
        return False

    def contain_other_targets(seq_sufix,targets):
        """
        check if there are other targets following the valid prefix of a sequence.
        """
        for func in seq_sufix[0:-1]:
            if func in targets:
                return True
        return False

    def distance_to_longest_valid_prefix(valid_sequences,seq):
        seq_len=[len(s) for s in valid_sequences]
        max_len=max(seq_len)
        for i in range(max_len,0,-1):
            valid_seq=[p for p in valid_sequences if len(p)==i]
            for s in valid_seq:
                if is_prefix(s, seq):
                    distance=len(seq)-len(s)
                    # color_print("Blue",f'\t\tDistance:{len(seq)-len(s)}; valid prefix: {s}')
                    return distance,s        #
        # color_print("Blue",f'\t\tDistance:{len(seq)-1}; (longest valid prefix is 1)')
        return 0,[]
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

    color_print("Red",
                f"==== Prune generated candidate sequences (remove executed or invalid sequences) ==== {os.path.basename(__file__)}")
    if len(candidate_sequences.keys())==0:
        color_print("Red","No candidate sequences.")
        return {}

    cur_sequences_to_be_exe = list(cur_sequences_to_be_exe_dict.values())
    pruned_candi_sequences = {}
    pruned_candi_sequences_dict={}



    color_print('Red',
                f'\n==== current all sequences ==== {cur_iteration-1} ===={os.path.basename(__file__)}')
    for pa in cur_all_sequences:
        color_print('Gray', f'{pa}')

    color_print('Red',
                f'\n==== all currently executed sequences ==== {cur_iteration-1} ===={os.path.basename(__file__)}')
    for pa in cur_actual_executed_seq:
        color_print('Gray', f'{pa}')


    for target in cur_targets:
        if target not in candidate_sequences.keys(): continue
        candi_seq = candidate_sequences[target]
        if len(candi_seq)==0:continue
        color_print('Red',
                    f'\n==== candidate sequences for {target}===={os.path.basename(__file__)}')
        for pa in candi_seq:
            color_print('Gray', f'{pa}')


        temp_candi_0=candi_seq

        # remove the sequences that are considered
        temp_candi_1 = []
        for seq in temp_candi_0:
            if is_contained(seq, cur_all_sequences):
                color_print('Red',
                            f'{seq} is contained in current sequences and thus should be removed')
            else:
                temp_candi_1.append(seq)

        # remove the sequences that has an invalid prefix
        invalid_seq = find_invalid_sequences(cur_sequences_to_be_exe,
                                             cur_actual_executed_seq)
        temp_candi_2 = []
        for seq in temp_candi_1:
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

        refine_paths_dict={}
        for seq in temp_candi_2:
            distance,prefix=distance_to_longest_valid_prefix(valid_sequences,seq)
            if distance>0:
                if not contain_other_targets(seq[len(prefix):len(seq)],
                                             candidate_sequences.keys()):
                    refined_paths.append(seq)
                    if distance in refine_paths_dict.keys():
                        refine_paths_dict[distance]+=[seq]
                    else:
                        refine_paths_dict[distance]=[seq]

        pruned_candi_sequences[target] = refined_paths
        if num_limit:
            if 1 in refine_paths_dict.keys():
                return_seq = refine_paths_dict[1]
            else:
                return_seq = []
            for d in range(2, 5, 1):
                if len(return_seq) < llm.llm_config.NUM_max_candidate_sequences:
                    if d in refine_paths_dict.keys():
                        d_seq = refine_paths_dict[d]
                    else:
                        d_seq = []
                    if len(d_seq) < llm.llm_config.NUM_max_candidate_sequences - len(return_seq):
                        return_seq += d_seq
                    else:
                        d_seq_3 = [p for p in d_seq if len(p) == 3]
                        if len(d_seq_3) <= llm.llm_config.NUM_max_candidate_sequences - len(
                            return_seq):
                            return_seq += d_seq_3
                            d_seq_left = [p for p in d_seq if len(p) > 3]
                            sel_seq = random_select_from_list(d_seq_left,
                                                              llm.llm_config.NUM_max_candidate_sequences - len(
                                                                  return_seq))
                        else:
                            sel_seq = random_select_from_list(d_seq_3,
                                                              llm.llm_config.NUM_max_candidate_sequences - len(
                                                                  return_seq))

                        return_seq += sel_seq
                        break

            pruned_candi_sequences_dict[target] = return_seq
        if target not in pruned_candi_sequences_dict.keys():
            pruned_candi_sequences_dict[target]=[s for seq in refine_paths_dict.values() for s in seq]


        color_print('Gray', f'\n{len(pruned_candi_sequences_dict[target])}/{len(candi_seq)} are kept ({len(pruned_candi_sequences_dict[target]) / len(candi_seq)})')





    if len(pruned_candi_sequences_dict.keys()) > 0:
        for k, seq_list in pruned_candi_sequences_dict.items():
            color_print('Blue', f'{k}:')
            if len(seq_list) == 0:
                color_print("Gray", "\t[]")
            else:
                for path in seq_list:
                    color_print("Gray", f'\t{path}')
    else:
        color_print('Red', f'all sequences are pruned:')

    return pruned_candi_sequences_dict


def print_sequences_in_dict(sequences_dict:dict):
    if len(sequences_dict.keys()) > 0:
        for k, seq_list in sequences_dict.items():
            color_print('Blue', f'{k}:')
            if len(seq_list) == 0:
                color_print("Gray", "\t[]")
            else:
                for path in seq_list:
                    color_print("Gray", f'\t{path}')
    else:
        color_print('Red', f'No sequences:')


def prune_candidate_sequences_basic(cur_iteration, cur_targets,
                              cur_sequences_to_be_exe_dict, cur_all_sequences,
                              cur_actual_executed_seq,candidate_sequences):
    """
    basic pruning
    remove:
        sequences in cur_all_sequences
        sequences containing a prefix that is invalid  (invalid sequences found via: all current sequences and all currently executd sequences
    keep:
        sequences containing a prefix that is valid until the number of the kept sequences reaches a threshold.
    """


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

    color_print("Red",
                f"===== Basic pruning the generated candidate sequences (remove executed or invalid sequences) ==== {os.path.basename(__file__)}")
    if len(candidate_sequences.keys())==0:
        color_print("Red","No candidate sequences.")
        return {}

    cur_sequences_to_be_exe = list(cur_sequences_to_be_exe_dict.values())

    pruned_candi_sequences_dict={}

    color_print('Red',
                f'\n==== current all sequences ==== {cur_iteration-1} ===={os.path.basename(__file__)}')
    for pa in cur_all_sequences:
        color_print('Gray', f'{pa}')

    color_print('Red',
                f'\n==== all currently executed sequences ==== {cur_iteration-1} ===={os.path.basename(__file__)}')
    for pa in cur_actual_executed_seq:
        color_print('Gray', f'{pa}')


    for target in cur_targets:
        if target not in candidate_sequences.keys(): continue
        candi_seq = candidate_sequences[target]
        if len(candi_seq)==0:continue


        temp_candi_0=candi_seq
        # remove the sequences that are considered
        temp_candi_1 = []
        for seq in temp_candi_0:
            if is_contained(seq, cur_all_sequences):
                color_print('Red',
                            f'{seq} is contained in current sequences and thus should be removed')
            else:
                temp_candi_1.append(seq)

        # remove the sequences that has an invalid prefix
        invalid_seq = find_invalid_sequences(cur_sequences_to_be_exe,
                                             cur_actual_executed_seq)
        temp_candi_2 = []
        for seq in temp_candi_1:
            flag_remove = False
            for x_seq in invalid_seq:
                if is_prefix(x_seq, seq):
                    flag_remove = True
                    color_print('Red',
                                f'{seq} should be removed as it contains an invalid sequence {x_seq}.')
                    break
            if not flag_remove:
                temp_candi_2.append(seq)


        pruned_candi_sequences_dict[target]=temp_candi_2

        color_print('Gray', f'{target}:{len(pruned_candi_sequences_dict[target])}/{len(candi_seq)} are kept ({len(pruned_candi_sequences_dict[target]) / len(candi_seq)})')

    return pruned_candi_sequences_dict

def prune_candidate_sequences_advance(cur_targets,
                               valid_sequences,candidate_sequences
                             ):
    """
    prune candidate sequences for current targets

    """

    def contain_other_targets(seq_sufix,targets):
        """
        check if there are other targets following the valid prefix of a sequence.
        """
        for func in seq_sufix[0:-1]:
            if func in targets:
                return True
        return False

    def distance_to_longest_valid_prefix(valid_sequences,seq):
        seq_len=[len(s) for s in valid_sequences]
        max_len=max(seq_len)
        for i in range(max_len,0,-1):
            valid_seq=[p for p in valid_sequences if len(p)==i]
            for s in valid_seq:
                if is_prefix(s, seq):
                    distance=len(seq)-len(s)
                    # color_print("Blue",f'\t\tDistance:{len(seq)-len(s)}; valid prefix: {s}')
                    return distance,s        #
        # color_print("Blue",f'\t\tDistance:{len(seq)-1}; (longest valid prefix is 1)')
        return 0,[]


    color_print("Red", f"===== advanced pruning ==== {os.path.basename(__file__)}")
    if len(candidate_sequences.keys())==0:
        color_print("Red","No candidate sequences.")
        return {},{}


    pruned_candi_sequences = {}
    pruned_candi_sequences_dict={}

    for target in cur_targets:
        if target not in candidate_sequences.keys(): continue
        candi_seq = candidate_sequences[target]
        if len(candi_seq)==0:continue
        # color_print('Red',
        #             f'\n==== candidate sequences for {target}===={os.path.basename(__file__)}')
        # for pa in candi_seq:
        #     color_print('Gray', f'{pa}')

        refined_paths=[]
        refine_paths_dict={}
        for seq in candi_seq:
            # use the number of sequence to determine the rigorousness of pruning
            if len(candi_seq)>=100:
                flag=True
            else:
                flag=False
            distance,prefix=distance_to_longest_valid_prefix(valid_sequences,seq)
            if distance>0:
                if not flag:
                    seq_seg_to_check=seq[len(prefix):len(seq)]
                else:
                    seq_seg_to_check = seq[1:len(seq)]

                if not contain_other_targets(seq_seg_to_check,
                                             candidate_sequences.keys()):
                    refined_paths.append(seq)
                    if distance in refine_paths_dict.keys():
                        refine_paths_dict[distance]+=[seq]
                    else:
                        refine_paths_dict[distance]=[seq]

        pruned_candi_sequences[target] = refined_paths
        pruned_candi_sequences_dict[target]=refine_paths_dict


        color_print('Gray', f'{target}:{len(refined_paths)}/{len(candi_seq)} are kept ({len(refined_paths) / len(candi_seq)})')

    return pruned_candi_sequences,pruned_candi_sequences_dict

def prune_candidate_sequences_PS(candidate_sequences_dict,generated_sequences_dict,num_candi):
    """
    keep sequences based on the past generated sequences
    take advantage of the sequences generated. there should be some reasons or logic.
    """
    def contain_a_subet(sequence,subset_list):
        for subset in subset_list:
            if set(subset).issubset(set(sequence)):
                return True
        return False

    def contain_a_subet0(sequence,subset):
        if set(subset).issubset(set(sequence)):
            return True
        return False

    def need_to_prune(sequences_dict, num_candi):
        sequences=[s for seq_list in sequences_dict.values() for s in seq_list]
        if len(sequences)<num_candi:
            return False
        else:
            return True

    results={}
    for target, candi_dict in candidate_sequences_dict.items():
        if not need_to_prune(candi_dict,num_candi):
            results[target] = candi_dict
            continue

        d_seq={}
        if target in generated_sequences_dict.keys():
            seq_generated = generated_sequences_dict[target]
            seq_generated=[ seq_generated[0:i] for i in range(1,len(seq_generated),1)]
        else:
            seq_generated = []
        if len(seq_generated)>0:
            for d,seq_list in candi_dict.items():
                seq_left = []
                for s in seq_list:
                    if contain_a_subet(s,seq_generated):
                        seq_left.append(s)
                d_seq[d]=seq_left
        else:
            d_seq=candi_dict

        results[target]=d_seq
    return results



def shorten_candidate_sequences(candidate_sequences_dict,num_candi):
    """
    prioritize sequences with short distances from valid prefix to the target.
    """
    results={}
    for target, candi_dict in candidate_sequences_dict.items():
        keys =list(candi_dict.keys())
        keys.sort(reverse=False)
        if len(keys)==0:continue

        return_seq=[]
        for d in keys:
            if d in candi_dict.keys():
                d_seq = candi_dict[d]
            else:
                d_seq = []
            if len(d_seq) <= num_candi- len(return_seq):
                return_seq += d_seq
            else:
                sel_seq = random_select_from_list(d_seq, num_candi - len(
                                                      return_seq))

                return_seq += sel_seq
                break

        results[target]=return_seq
    return results


def shorten_candidate_sequences_LP(candidate_sequences_dict,num_candi,not_consider_sequences_dict:dict={}):
    """
    prioritize sequences with longer valid prefixes and shorter distances
    """

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

    # reorganize based the valid prefix length and distance
    reorgainze_seq={}
    for target, candi_dict in candidate_sequences_dict.items():
        d_seq={}
        for d,seq_list in candi_dict.items():
            for seq in seq_list:
                prefix_len=len(seq)-d
                if f'{prefix_len}:{d}' not in d_seq.keys():
                    d_seq[f'{prefix_len}:{d}']=[seq]
                else:
                    d_seq[f'{prefix_len}:{d}']+=[seq]
        reorgainze_seq[target]=d_seq

    results = {}
    for target, candi_dict in reorgainze_seq.items():
        # keys =list(candi_dict.keys())
        # keys.sort(reverse=True)
        # if len(keys)==0:continue

        return_seq =[]
        # assume that the longest length is 4
        # keys=["3:1","2:1","2:2","1:1","1:2","1:3"]
        keys = ["3:1", "2:1", "2:2","1:1"]
        for d in keys:
            d_seq = []
            if d in candi_dict.keys():
                d_seq = candi_dict[d]

            d_rm=[]
            if target in not_consider_sequences_dict.keys():
                d_rm=not_consider_sequences_dict[target]
            d_seq=[s for s in d_seq if not is_contained(s,d_rm)]

            if len(d_seq) <= num_candi - len(return_seq):
                return_seq += d_seq
            else:
                sel_seq = random_select_from_list(d_seq,
                                                      num_candi - len(
                                                          return_seq))
                return_seq += sel_seq
                break

        if len(return_seq)<num_candi:
            keys = [ "1:2", "1:3"]
            for d in keys:
                d_seq = []
                if d in candi_dict.keys():
                    d_seq = candi_dict[d]

                d_rm = []
                if target in not_consider_sequences_dict.keys():
                    d_rm = not_consider_sequences_dict[target]
                d_seq = [s for s in d_seq if not is_contained(s, d_rm)]

                if len(d_seq) <= num_candi - len(return_seq):
                    return_seq += d_seq
                else:
                    sel_seq = random_select_from_list(d_seq,
                                                      num_candi - len(
                                                          return_seq))

                    return_seq += sel_seq
                    break
        results[target] = return_seq


    return results

def obtain_most_N_candi_sequences(candidate_sequences_dict, generated_sequences_dict, num_candi):
    result_seq_dict = {}
    if llm.llm_config.candi_percentage<0:
        # randomly select num_candi sequences
        print(f'randomly select {num_candi} candidate sequences')
        for target, candi_dict in candidate_sequences_dict.items():
            d_seq = []
            for seq_list in candi_dict.values():
                d_seq+=seq_list

            result_seq_dict[target] = random_select_from_list(d_seq,num_candi)
        return result_seq_dict
    else:
        consider_num = floor(num_candi * llm.llm_config.candi_percentage)
        pruned_seq_dict=prune_candidate_sequences_PS(candidate_sequences_dict,generated_sequences_dict, consider_num)

        result_seq_dict1=shorten_candidate_sequences_LP(pruned_seq_dict,consider_num)
        result_seq_dict2= shorten_candidate_sequences_LP(candidate_sequences_dict,num_candi-consider_num,not_consider_sequences_dict=result_seq_dict1)

        for t,v in result_seq_dict1.items():
            if t in result_seq_dict2.keys():
                v1=result_seq_dict2[t]
                result_seq_dict[t]=v+v1
            else:
                result_seq_dict[t]=v
        return result_seq_dict



def initial_check_generated_sequences(sequences, start_functions,targets, all_functions_pure_name,length_limit=fdg.global_config.seq_len_limit):


    sequences_status={}
    sequences_of_length1={}

    for key, seq in sequences.items():

        target = key.split(f'(')[0] if "(" in key else key

        #-----------------
        # check if the target is indeed the target we focus on
        if target not in targets:
            sequences_status[target]={k:v for k,v in zip(["consider","status","sequence"],[False,f"{target} is not a target.",seq])}
            continue

        if len(seq) == 0:
            sequences_status[target] = {k: v for k, v in
                                    zip(["consider", "status", "sequence"],
                                        [False, f"The length of the sequence is 0.",
                                         seq])}
            continue

        # clear the sequence by only keeping the pure function names
        seq_temp = [ftn.split(f'(')[0] if "(" in ftn else ftn for ftn in seq]

        # ------------------
        # check if contain not-defined functions
        flag_consider = True
        for func in seq_temp:
            if func not in all_functions_pure_name+['fallback']:
                flag_consider = False
                status=f"{seq_temp} is a really bad sequence as it contains an element {func}, which is not a function. This is a serious problem. Please only consider the functions defined in the source code."
                sequences_status[target] = {k: v for k, v in
                                            zip(["consider", "status",
                                                 "sequence"],
                                                [False,
                                                 status,
                                                 seq_temp])
                                            }

                break
        if not flag_consider:
            continue

        # #------------------
        # # if containing no-state-changing functions
        # # to-do-list: check if containing no-state-changing functions (need to distinguish state-changing functions
        # for item in seq_temp:
        #     if item not in self.functionAssignment.all_functions:
        #         ...

        # ------------------------
        # check the first function
        if seq_temp[0] not in start_functions:
            if len(seq_temp)==1:
                status = f"{seq_temp} is a bad sequence as the first function {seq_temp[0]} is not a start function and the length of it is 1 while the required length should be larger than 1. Please be aware of the length limit."
                sequences_status[target] = {k: v for k, v in
                                            zip(["consider", "status",
                                                 "sequence"],
                                                [False,
                                                 status,
                                                 seq_temp])
                                            }

            else:
                status = f"{seq_temp} is a bad sequence as the first function {seq_temp[0]} is not a start function."
                sequences_status[target] = {k: v for k, v in
                                            zip(["consider", "status",
                                                 "sequence"],
                                                [False,
                                                 status,
                                                 seq_temp])
                                            }


            continue

        # ------------------------
        # check the sequence length
        if len(seq_temp) > length_limit:
            status = f"{seq_temp} is a bad sequence as the length exceeds the limit {length_limit}."
            sequences_status[target] = {k: v for k, v in
                                        zip(["consider", "status",
                                             "sequence"],
                                            [False,
                                             status,
                                             seq_temp])
                                        }

            continue


        if len(seq_temp) == 1:

            status =  f"{seq_temp} is a bad sequence as there should be at least two functions in a sequence."
            sequences_status[target] = {k: v for k, v in
                                        zip(["consider", "status",
                                             "sequence"],
                                            [False,
                                             status,
                                             seq_temp])
                                        }

            # manually add the target function to form a sequence of length 2.
            seq_temp.append(target)
            status=f'{seq_temp} is a sequence of type [A,A] to fix the sequence of type [A], which is a bad sequence.'
            sequences_of_length1[target]={k: v for k, v in
                                        zip(["consider", "status",
                                             "sequence"],
                                            [True,
                                             status,
                                             seq_temp])
                                        }

            continue


        # ------------------------
        # check if the last function is the target
        last_func_name = seq_temp[-1]
        if last_func_name not in [target]:
            if target in seq_temp[0:-1]:
                status=f"{seq_temp} is bad sequence as the target function {target} is not the last function in the sequence."
            else:
                status=f"{seq_temp} is bad sequence as the target function {target} should be the last function in the sequence."

            sequences_status[target] = {k: v for k, v in
                                        zip(["consider", "status",
                                             "sequence"],
                                            [False,
                                             status,
                                             seq_temp])
                                        }

            continue


        status=f'{seq_temp} is an appropriate sequences satisfying the given instruction guidance.'
        sequences_status[target] = {k: v for k, v in
                                    zip(["consider", "status",
                                         "sequence"],
                                        [True,
                                         status,
                                         seq_temp])
                                    }

    return sequences_status,sequences_of_length1


def check_generated_candidate_sequences(sequences,start_functions,targets,all_functions_pure_name,length_limit=fdg.global_config.seq_len_limit):

    sequences_checked={}

    color_print("Red",f"==== Check generated candidate sequences (remove bad sequences) ==== {os.path.basename(__file__)}")
    for key, seq_list in sequences.items():

        target = key.split(f'(')[0] if "(" in key else key
        #-----------------
        # check if the target is indeed the target we focus on
        if target not in targets:
            color_print("Red", f"{target} is not a target in {targets}.")
            continue

        if len(seq_list)==0:
            color_print("Red", f"{target} has no sequence generated.")
            continue

        keep_sequences=[]
        for seq in seq_list:
            if len(seq) == 0:
                continue

            # clear the sequence by only keeping the pure function names
            seq_temp = [ftn for ftn in seq if isinstance(ftn, str)]  # remove integer
            seq_temp = [ftn.split(f'(')[0] if "(" in ftn else ftn for ftn in seq_temp]
            seq_temp = [ftn for ftn in seq_temp if not ftn.startswith("0x")]
            if len(seq_temp)==0:continue

            # ------------------
            # check if contain not-defined functions
            flag_consider = True
            for func in seq_temp:
                if func not in all_functions_pure_name:
                    flag_consider = False
                    break
            if not flag_consider:
                continue

            # #------------------
            # # if containing no-state-changing functions
            # # to-do-list: check if containing no-state-changing functions (need to distinguish state-changing functions
            # for item in seq_temp:
            #     if item not in self.functionAssignment.all_functions:
            #         ...

            # ------------------------
            # check the first function
            if seq_temp[0] not in start_functions:
                continue



            # ------------------------
            # check the sequence length
            if len(seq_temp) > length_limit:
                continue


            if len(seq_temp) == 1:
                seq_temp.append(target)
                keep_sequences.append(seq_temp)
                continue


            # ------------------------
            # check if the last function is the target
            last_func_name = seq_temp[-1]
            if last_func_name not in [target]:
                continue

            if seq_temp not in keep_sequences:
                keep_sequences.append(seq_temp)

        sequences_checked[target]=keep_sequences
    if len(sequences_checked.keys())>0:
        for k,seq_list in sequences_checked.items():
            color_print('Blue',f'{k}:')
            if len(seq_list)==0:
                color_print("Gray","\t[]")
            else:
                for path in seq_list:
                    color_print("Gray",f'\t{path}')
    else:
        color_print('Red', f'all sequences are bad sequences')

    return sequences_checked

