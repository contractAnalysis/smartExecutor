def add_edges_test():
    def belong_relation(seq1: list, seq2: list):
        s1 = seq1
        s2 = seq2
        if len(seq1) > len(seq2):
            s1 = seq2
            s2 = seq1
        if [True for e in s1 if e not in s2].count(True) > 0:
            return False
        else:
            return True


    def common_elements(seq1: list, seq2: list):
        common = []
        s1 = seq1
        s2 = seq2
        if len(seq1) > len(seq2):
            s1 = seq2
            s2 = seq1
        for e in s1:
            if e in s2:
                common.append(e)
        return common
    def find_edges(seq1: list, seq2: list,common:list):
        edges = []
        s1 = seq1
        s2 = seq2
        if len(seq1) > len(seq2):
            s1 = seq2
            s2 = seq1

        f1=-1
        t1=-1
        f2=-1
        t2=-1
        idx2=0
        for idx,e in enumerate(s1):
            if e not in common:
                if t1==-1:
                    t1=idx
                f1=idx
            else:

                # check s2 if there are elements before e
                for i in range(idx2, len(s2)):
                    if not s2[i] == e:
                        if t2 == -1:
                            t2 = i
                        f2 = i
                    else:

                        break

                if f2 >= 0 and t2 >= 0 and t1 >= 0 and f1 >= 0:
                    edges.append((s2[f2], s1[t1]))
                    edges.append((s1[f1], s2[t2]))


                idx2 = i+1
                f1 = f2 = t1 = t2 = -1
                continue

        if t1>=0 and f1>=0:
            if idx2 > len(s2) - 1:
                return edges
            for i in range(idx2, len(s2)):
                if not s2[i] == e:
                    if t2 == -1:
                        t2 = i
                    f2 = i
                else:
                    break
            if f2 >= 0 and t2 >= 0:
                edges.append((s2[f2], s1[t1]))
                edges.append((s1[f1], s2[t2]))

        return edges

    # sequences=[[1,2,3],[2,4],[4,5],[2,4,5]]
    # sequences = [[2, 4], [4, 5]]
    # sequences = [[2, 5], [4, 5]]
    # sequences = [[2, 1], [2, 4]]
    sequences = [[2, 1,4,5], [2,3, 4,6],[1,2,3],[2,4],[4,5],[2,4,5]]
    all_pairs = [(a, b) for idx, a in enumerate(sequences) for b in sequences[idx + 1:]]


    for seq1, seq2 in all_pairs:
        edges = []
        if belong_relation(seq1, seq2):
            # do not add edges
            continue
        common = common_elements(seq1, seq2)
        if len(common) == 0:
            # add edges
            edges.append((seq1[-1], seq2[0]))
            edges.append((seq2[-1], seq1[0]))

        else:
            edges+=find_edges(seq1,seq2,common)
        print(f'seq1:{seq1}')
        print(f'seq2:{seq2}')
        print(f'edges={edges}')


def remove_trivial_state_keys_test():
    def get_key_1_prefix(key: str) -> str:
        idx = key.rindex("#")
        return key[0:idx]

    def remove_trivial_state_key(state_keys:list,state_priority:dict):
        """
        find the state keys that have the same function sequence but ended with different indices
        keep one state key if they have the same priority value.
        :param state_keys:
        :return:
        """
        left_keys=[]
        count={}
        for key in state_keys:
            key_prefix=get_key_1_prefix(key)
            if key_prefix not in count.keys():
                count[key_prefix]=[key]
            else:
                count[key_prefix]+=[key]
        for key_prefix,keys  in count.items():
            if len(keys)==1:
                left_keys.append(keys[0])
                continue
            key_value_pairs=[(key,state_priority[key]) for key in keys]
            key_value_pairs.sort(key=lambda x: x[1])
            cur_value=0
            for key,value in key_value_pairs:
                if not cur_value==value:
                    left_keys.append(key)
                    cur_value=value
        return left_keys
    keys=['a#1','a#2','a#3','a#b#4','a#c#5']
    key_priority = {'a#1':2, 'a#2':2, 'a#3':2, 'a#b#4':2, 'a#c#5':2}
    left=remove_trivial_state_key(keys,key_priority)
    print(f'keys:{keys}')
    print(f'key priority:{key_priority}')
    print(f'left keys:{left}')
    print(f'----------------------------')
    keys=['a#1','a#2','a#3','a#b#4','a#c#5']
    key_priority = {'a#1':2, 'a#2':3, 'a#3':2, 'a#b#4':2, 'a#c#5':2}
    left=remove_trivial_state_key(keys,key_priority)
    print(f'keys:{keys}')
    print(f'key priority:{key_priority}')
    print(f'left keys:{left}')

def get_address_from_argument(int_tuple) -> int:
    value = 0
    exp=0
    for item in reversed(int_tuple):
        value+=item*256**exp
        exp+=1
    return value

def test_get_address_from_argument():
    va = [(9,), (0,), (255,), (256,)]
    va = [(0, 1), (0, 3), (0, 255), (1, 0), (1, 3), (1, 255), (255, 255)]
    va = [(0, 0, 1), (1, 1, 1)]
    for item in va:
        print(f'{item}=>{get_address_from_argument(item)}')



if __name__=="__main__":
    # add_edges_test()
    # remove_trivial_state_keys_test()
    keys = ['', 'a#2', 'a#3', 'a#b#4', 'a#c#5']
    key_priority = {'a#1': 2, 'a#2': 3, 'a#3': 2, 'a#b#4': 2, 'a#c#5': 2}
    key_priority_value = [ key_priority[key] if len(key) > 0 else 0 for key in keys]

    print(key_priority_value)


