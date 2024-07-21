



  
from copy import deepcopy

from rl.config import seq_len_limit,output_path


def output_fwrg_data(graph:dict,file_name:str,description:str):
  
    with open(output_path + file_name, 'w') as fw:
        fw.write(f'\n====== {description} ======\n')
        for ftn, data in graph.items():
            fw.write(f'\n{ftn}:\n')
            fw.write(f'\t{data}\n')


class FWRG():
    def __init__(self,ftn_reads_in_condition:dict,ftn_writes:dict):
        self.ftn_reads_in_condition = ftn_reads_in_condition
        self.ftn_writes = ftn_writes
        self.fwrg_dict={}
        self.frwg_dict={}

        self._generate_fwrg()
        self._generate_frwg()

    def _generate_fwrg(self):
        for ftn,writes in self.ftn_writes.items():
            if len(writes)==0:
                self.fwrg_dict[ftn]={}
                continue

            children={}
            for ftn_read,reads in self.ftn_reads_in_condition.items():
                for write in writes:
                    if write in reads:
                        if ftn_read not in children.keys():
                            children[ftn_read]=[write]
                        else:
                            children[ftn_read]+=[write]
            self.fwrg_dict[ftn]=children

    def _generate_frwg(self):
        for ftn, reads in self.ftn_reads_in_condition.items():
            if len(reads)==0:
                self.frwg_dict[ftn]={}
                continue
            for ftn_write,writes in self.ftn_writes.items():
                for read in reads:
                    if read in writes:
                        if ftn not in self.frwg_dict.keys():
                            self.frwg_dict[ftn]=[ftn_write]
                        else:
                            if ftn_write not in self.frwg_dict[ftn]:
                                self.frwg_dict[ftn]+=[ftn_write]
                        break

    def get_reads_in_conditions(self,ftn_name:str):
        if ftn_name in self.ftn_reads_in_condition.keys():
            return self.ftn_reads_in_condition[ftn_name]
        else:return []

class AcyclicPath():
    def __init__(self, start_functions:list, dk_functions:list, fwrg:FWRG):
        self.path_len_limit = seq_len_limit
        self.fwrg=fwrg
        self.start_functions=start_functions
        # self.dk_functions=[ftn for ftn,_ in dk_functions]
        self.dk_functions=dk_functions
        self.paths = {}
        self._get_path()
        self.paths_df={}
        self.organize_paths()

    def _get_path(self):
        """
        get all acyclic paths from starting functions (bounded by sequence length)
        :return:
        """
        def get_children(ftn:str):
            if ftn in self.fwrg.fwrg_dict.keys():
                children=self.fwrg.fwrg_dict[ftn]
                if len(children)>0:
                    return list(children.keys())
            return []
        def derive_paths(start_ftn:str):
            all_paths=[]
            paths=[[start_ftn]]
            for i in range(self.path_len_limit-1):
                derived_paths=[]
                for path in paths:
                    children=get_children(path[-1])
                    if len(children)==0:
                        if path not in all_paths:
                            all_paths.append(path)
                    else:
                        for child in children:
                            if child in path:
                                # think of the case [A(),A()](self dependency)
                                if child==path[0] and len(path)==1:
                                    path.append(child)
                                if path not in all_paths:
                                    all_paths.append(path)
                            else:
                                derived_paths.append(path+[child])
                paths=derived_paths

            all_paths+=paths
            return all_paths


        for sf in self.start_functions:
            sf_path=derive_paths(sf)
            self.paths[sf]=sf_path

    def organize_paths(self):
        for paths in self.paths.values():
            for path in paths:
                for idx,ftn in enumerate(path):
                    if ftn in self.dk_functions and idx>0:# deep function can not be the frist function in a sequence
                        t_path=path[0:idx+1]
                        # add t_path
                        if ftn not in self.paths_df.keys():
                            self.paths_df[ftn]={}
                        if len(t_path)-1 not in self.paths_df[ftn].keys():
                            self.paths_df[ftn][len(t_path)-1]=[t_path]
                        else:
                            if t_path not in self.paths_df[ftn][len(t_path)-1]:
                                self.paths_df[ftn][len(t_path)-1] += [t_path]

class UpdateFWRG():
    def __init__(self, fdg:FWRG, paths:AcyclicPath):
        self.fwrg=fdg
        self.acyclicPaths=paths

        self.fwrg_targets={}

        self.construct_fwrg_targets()

        # self.print_graphs(self.fwrg_targets,'fwrg_targets_data.txt')

        self.fwrg_targets_augmented=deepcopy(self.fwrg_targets)
        self.add_edges_1()
        # self.print_graphs(self.fwrg_targets_augmented,'fwrg_targets_augmented_data_update.txt')

        self.dk_not_reachable=[]
        
        self.identity_dk_function_not_reachable()
        


    def print_graphs(self,data:dict,file_name:str):
        output_fwrg_data(data, file_name, 'funtion write-read graph data')


    def add_edge_to_graph(self,from_:str,to_:str):
        if from_ in self.fwrg_targets_augmented.keys():
            if to_ not in self.fwrg_targets_augmented[from_]:
                self.fwrg_targets_augmented[from_].append(to_)
        else:
            self.fwrg_targets_augmented[from_]=[to_]


    def construct_fwrg_targets(self):
        # reconstruct edges from given acyclic paths
        for value in self.acyclicPaths.paths_df.values():
            if not isinstance(value,dict):continue
            for paths in value.values():
                for path in paths:
                    # add edges
                    for i in range(len(path) - 1):
                        if path[i] not in self.fwrg_targets.keys():
                            self.fwrg_targets[path[i]] = [path[i + 1]]
                        else:
                            if path[i+1] not in self.fwrg_targets[path[i]]:
                                self.fwrg_targets[path[i]] += [path[i + 1]]



    def add_edges_1(self):
        """
        for each deep function, add edges to connect some of its paths

        for each deep function, try to find a combined path
        :return:
        """
        def belong_relation(seq1:list,seq2:list):
            s1=seq1
            s2=seq2
            if len(seq1)>len(seq2):
                s1=seq2
                s2=seq1
            if [True for e in s1 if e not in s2].count(True)>0:
                return False
            else:
                return True

        def common_elements(seq1: list, seq2: list):
            common=[]
            s1 = seq1
            s2 = seq2
            if len(seq1) > len(seq2):
                s1 = seq2
                s2 = seq1
            for e in s1:
                if e in s2:
                    common.append(e)
            return common

        def find_edges(seq1: list, seq2: list, common: list):
            edges = []
            s1 = seq1
            s2 = seq2
            if len(seq1) > len(seq2):
                s1 = seq2
                s2 = seq1

            f1 = -1
            t1 = -1
            f2 = -1
            t2 = -1
            idx2 = 0
            for idx, e in enumerate(s1):
                if e not in common:
                    if t1 == -1:
                        t1 = idx
                    f1 = idx
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

                    idx2 = i + 1
                    f1 = f2 = t1 = t2 = -1
                    continue

            if t1 >= 0 and f1 >= 0:
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
        for df,value in self.acyclicPaths.paths_df.items():

            if isinstance(value,dict):
                sequences=[]
                for seq_list in value.values():
                    for seq in seq_list:
                        sequences.append(seq[0:-1])

                all_pairs=[(a,b) for idx,a in enumerate(sequences) for b in sequences[idx+1:]]

                for seq1,seq2 in all_pairs:
                    if belong_relation(seq1, seq2):
                        # do not add edges
                        continue
                    common = common_elements(seq1, seq2)
                    if len(common) == 0:
                        # add edges
                        self.add_edge_to_graph(seq1[-1], seq2[0])
                        self.add_edge_to_graph(seq2[-1], seq1[0])

                    else:
                        edges=find_edges(seq1, seq2, common)
                        for f,t in edges:
                            self.add_edge_to_graph(f, t)

    def identity_dk_function_not_reachable(self):
        for dk in self.acyclicPaths.dk_functions:
            if dk not in self.acyclicPaths.paths_df.keys():
                self.dk_not_reachable.append(dk)
                print(f'{dk} is not reachable(based on w/r data dependency)')
            else:
                if len(self.acyclicPaths.paths_df[dk])==0:
                    self.dk_not_reachable.append(dk)
                    print(f'{dk} is not reachable(based on w/r data dependency)')


class FWRG_manager():
    def __init__(self, start_functions:list, dk_functions:list, function_reads_in_conditions:dict,function_writes:dict):
        
        self.start_functions= start_functions[0] if isinstance(start_functions,tuple) else start_functions
        
       
        self.targets=dk_functions
        self.path_len_limit=seq_len_limit
        
        self.fwrg=FWRG(function_reads_in_conditions,
                       function_writes)
        


        
        # self.fwrg_all_reads={}
        # self.generate_graph_all_reads(preprocess.write_read_info.write_slots,preprocess.write_read_info.read_slots)

        self.acyclicPaths=AcyclicPath(start_functions, dk_functions, self.fwrg)
        self.updateFWRG=UpdateFWRG(self.fwrg, self.acyclicPaths)
        
        self.all_sequences=[]
        self.target_sequences={target:[] for target in self.targets}
        

    def generate_graph_all_reads(self,writes:dict,all_reads:dict):
        for ftn,writes in writes.items():
            if len(writes)==0:
                self.fwrg_all_reads[ftn]={}
                continue
            children={}
            for ftn_read,reads in all_reads.items():
                for write in writes:
                     if write in reads:
                         if ftn_read not in children.keys():
                             children[ftn_read]=[write]
                         else:
                             children[ftn_read]+=[write]
            self.fwrg_all_reads[ftn]=children
                
    def get_children_all_reads(self,ftn:str):
        if ftn in self.fwrg_all_reads.keys():
            return list(self.fwrg_all_reads[ftn].keys())
        else:
            return []
    def get_children_fwrg(self,ftn:str):
        if ftn in self.fwrg.fwrg_dict.keys():
            return list(self.fwrg.fwrg_dict[ftn])
        else:
            return []

    def get_children_fwrg_T_A(self, ftn:str)->list:
        if ftn in self.updateFWRG.fwrg_targets_augmented.keys():
            return self.updateFWRG.fwrg_targets_augmented[ftn]
        else: return []

    def get_parents_frwg(self, ftn:str)->list:
        if ftn in self.fwrg.frwg_dict.keys():
            return self.fwrg.frwg_dict[ftn]
        else:
            return []

    def get_children_bf_update(self, ftn:str)->list:
        if ftn in self.updateFWRG.fwrg_targets.keys():
            return self.updateFWRG.fwrg_targets[ftn]
        else: return []
        
    def obtain_sequences(self):
        def derive_paths(start_ftn:str):
            all_paths=[]
            paths=[[start_ftn]]
            for i in range(self.path_len_limit-1):
                derived_paths=[]
                for path in paths:
                    children=self.get_children_fwrg_T_A(path[-1])
                    if len(children)==0:
                        if path not in all_paths:
                            all_paths.append(path)
                    else:
                        for child in children:
                            if child in path:
                                # think of the case [A(),A()](self dependency)
                                if child==path[0] and len(path)==1:
                                    new_path=path+[child]
                                    if new_path not in all_paths:
                                        all_paths.append(new_path)
                            else:
                                derived_paths.append(path+[child])
                
                paths=derived_paths
                for p in derived_paths:
                    if p[-1] in self.targets:
                        if p not in self.all_sequences:
                            self.all_sequences.append(p)
                        

            all_paths+=paths
            
            return all_paths
        
        all_collection_paths=[]
        for start in self.start_functions:
            all_collection_paths+=derive_paths(start)
        
        for p in self.all_sequences:
            for target in self.targets:
                if target in p:
                    kept_seq=[func for func in p[0:p.index(target)+1]]
                    if kept_seq not in self.target_sequences[target]:
                        self.target_sequences[target].append(kept_seq)
        return self.all_sequences

        




def test_1():
    ftn_r_in_condi = {'f2': ['a'], 'f3': ['b'], 'f4': ['c'], 'f5': ['c']}
    ftn_w = {'f2': ['b'], 'f3': ['a', 'c'], 'f4': [], 'f5': []}
    fdg = FWRG(ftn_r_in_condi, ftn_w)

    starts = ['f1', 'f2', 'f3']
    df = ['f4', 'f5']
    paths = AcyclicPath(starts, df, fdg)
    print(f'{paths.paths}')

def test_2():
    ftn_r_in_condi = {'f1': ['a'], 'f2': [], 'f3': ['b'], 'f4': ['c','a']}
    ftn_w = {'f1': ['a'], 'f2': ['b'], 'f3': ['c'], 'f4': []}
    fdg = FWRG(ftn_r_in_condi, ftn_w)

    starts = ['f1', 'f2' ]
    df = ['f3', 'f4']
    paths = AcyclicPath(starts, df, fdg)
    print(f'{paths.paths}')
    print(f'{paths.paths_df}')

    updateFDG=UpdateFWRG(fdg, paths)
    updateFDG.construct_fwrg_targets()
    updateFDG.add_edges()
    
    print(f'{updateFDG.fwrg_targets}')
    


