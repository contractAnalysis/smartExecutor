from statistics import mean

import fdg.global_config

def compute_mine(weights:list)->float:
    return simple_mean(weights) # when using the original weights, this simple_mean is better
    # return weights[-1]

def compute(weights:list)->float:
    # return simple_mean(weights) # when using the original weights, this simple_mean is better
    return weighted_mean(weights)

def simple_mean(weights:list)->float:
    return mean(weights)

def weighted_mean(weights:list)->float:
    w = [0.2, 0.4, 0.6, 0.8, 1]
    final = 0
    if len(weights) > fdg.global_config.seq_len_limit:
        print(
            'Do not need to compute weights as the weights come from the depth {fdg.global_config.seq_len_limit} (maximum)')
    else:

        diff = len(w) - len(weights)
        weighted_w = []
        for idx, weight in enumerate(weights):
            w_idx = idx + diff
            weighted_w.append(weight * w[w_idx])
        final = round(mean(weighted_w), 2)  # round to the second decimal place
    return final



def turn_write_features_to_a_value(data:[bool])->float:
    """
    three featues:[primitive type,concrete write, new write)
    """

    def turn_a_list_to_value_diff_weight(data: [bool]) -> int:
        value = 0
        for index, i in enumerate(range(len(data) - 1, -1, -1)):
            if data[index]:
                value += 1 * 2 ** i
        return value

    def turn_a_list_to_value_diff_weight_1(data: [bool]) -> int:
        assert len(data)==3
        # order: p,c,n (primitive type, concrete value, new value)
        # value=0
        # if data[2]:value+=3
        # if data[1]:value+=1
        # if data[0]:value+=2

        value = 0
        if data[2]:
            if data[0]:
                value+=3
            else:
                value+=2

        if data[1]: value += 1
        if data[0]: value += 2
        return value

    def turn_a_list_to_value_equal_weight(data: [bool]) -> int:
        value = 0
        for index, i in enumerate(range(len(data) - 1, -1, -1)):
            if data[index]:
                value += 1
        return value

    # value=turn_a_list_to_value_equal_weight(data)
    value=turn_a_list_to_value_diff_weight_1(data)
    return value


