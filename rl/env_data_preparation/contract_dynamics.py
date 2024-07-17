from collections import defaultdict


class ContractDynamics():
    def __init__(self, sequences: list,sequence_writes:dict,goals:list=[]):
        self.sequences = sequences
        self.sequence_writes=sequence_writes
        self.tree = None
        self.get_tree_presentation()
        
        self.search_results={}
        self.goals=goals
        self.goal_sequences_counts={}
        self.goal_sequences={}
        self.obtain_goal_sequences()

    def get_tree_presentation(self):   
        tree = defaultdict(dict)
        for seq in self.sequences:
            curr_node = tree
            for i, value in enumerate(seq):
                if i == len(seq) - 1:
                    # Last node is leaf
                    curr_node[value] = {}
                else:
                    # Create child node
                    next_node = curr_node.get(value)
                    if next_node is None:
                        # Key does not exist, create it
                        next_node = {}
                        curr_node[value] = next_node
                    curr_node = next_node
        self.tree = tree

    def is_prefix(self, sequence: list):
        node = self.tree
        for value in sequence:
            if node is None:
                return False
            if value not in node:
                return False
            node = node[value]
        return True
    

    def obtain_goal_sequences(self):
        self.goal_sequences_counts={goal:0 for goal in self.goals}
        self.goal_sequences={goal:[] for goal in self.goals}
        for seq in self.sequences:
            for goal in self.goals:
                if goal in seq:
                    self.goal_sequences_counts[goal]+=1
                    if seq not in self.goal_sequences[goal]:
                        self.goal_sequences[goal].append(seq)
                        
       
    def reach_to_the_goal(self,sequence:list,goal:int)->bool:
        assert len(sequence)>0
        assert goal in self.goal_sequences.keys()
        
        if not self.is_prefix(sequence): return False
        flag=False
        for seq in self.goal_sequences[goal]:
            flag=True
            if len(seq)>=len(sequence):
                for idx,e in enumerate(sequence):
                    if seq[idx]!=e:
                        flag=False
                        break
            else:
                flag=False
            if flag:
                return True
        
        return flag
                        
                        
       
    
    def valid_seq_of_a_sequence(self, sequence: list)->list:
        valid_seq=[]
        node = self.tree
        for value in sequence:
            if node is None:
                return valid_seq
            if value not in node:
                return valid_seq
            node = node[value]
            valid_seq.append(value)
            
        return valid_seq

    def get_children(self, sequence: list):
        node = self.tree
        for value in sequence:
            if node is None:
                return []
            if value not in node:
                return []
            else:
                node = node[value]
        return list(node.keys())
    
    def last_writes_of_a_sequence(self,sequence:list)->list:
      def get_key_from_seq(seq: list) -> str:
          if len(seq) == 0: return ""
          key = str(seq[0])
          for ele in seq[1:]:
              key += f'#{ele}'
          return key
      key=get_key_from_seq(sequence)
      if key in self.sequence_writes.keys():
        return self.sequence_writes[key]
      else:
        return []
    
    def get_search_key(self,partial_seq:list)->str:
        assert len(partial_seq)==4
        temp=[ ele if ele!=-1 else '_' for ele in partial_seq]
        key=str(temp[0])
        for e in temp[1:]:
            key+=f'#{e}'
        return key
        
            
    def part_of_a_valid_sequence(self,partial_seq:list)->bool:
        key=self.get_search_key(partial_seq)
        if key in self.search_results.keys():
            return self.search_results[key]
        else:
            
            for seq in self.sequences:
                flag=True
                for idx,e in enumerate(partial_seq):
                    if e>0:
                        if idx >=len(seq):
                            flag=False
                            break
                        else:
                            if e!=seq[idx]:
                                flag=False
                                break
                if flag:
                    self.search_results[key]=True
                    return True
            # end of going through sequences    
            self.search_results[key]=False    
            return False
                                
                
                    
   
        
