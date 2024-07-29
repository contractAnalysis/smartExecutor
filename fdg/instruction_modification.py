from copy import copy

from fdg.output_data import print_list, print_dict
from mythril.laser.ethereum.state.world_state import WorldState



class InstructionModification():
    """
    change the function dispatcher at the beginning part of the instruction list
    """

    def __init__(self,ftn_identifier:dict):
        self.function_identifier=ftn_identifier
        self.contract_address=None # used to identity the instructions of the contract

        self.instruction_list = []

        self.functions_to_positions = {}
        self.positions_to_instructions = {} # divide instructions into groups and use the positions to indicate the order
        self.all_positions_related_function=[]
        self.jumpdest_in_dispatcher=[]# record the number of jumpdest in the function dispatcher
        self.address_jumpdest_revert_block=0
        self.positions_contain_GT = [] # the positions are kept in this case as they involve in branches in dispatcher

    def feed_instructions(self, state:WorldState, contract_address):
        """
        new way to group instructions.
        :argument
        """
        self.contract_address = contract_address
        key = contract_address.value
        code = state.accounts[key].code
        self.instruction_list=code.instruction_list

        # print_list(self.instruction_list, "instruction list")

        if len(self.function_identifier)>0:
            self._feed_instructions_update()

        print(f'total instructions: {len(self.instruction_list)}')

    def _feed_instructions(self):
        """
        new way to group instructions.
        :argument
        """

        def record_position(position:int,instruction:dict):

            self.positions_to_instructions[position] = []

            # get the function's signature as a key
            function_key = instruction['argument']
            if len(function_key) == 8:
                function_key = '0x00' + function_key[2:]
                print(f'convert {instruction["argument"]} to {function_key}')

            if function_key not in self.functions_to_positions.keys():
                self.functions_to_positions[function_key] = [position]
            else:
                self.functions_to_positions[function_key] += [position]


        # ============================================
        # through PHSH4 and JUMPDEST to sperate instructions
        offset_instr = 0
        flag_status = 0  # change its value when "CALLDATASIZE" is met and the first PUSH after "CALLDATASIZE" is met

        position = 0
        self.positions_to_instructions[0] = []
        self.address_jumpdest_revert_block = 0  # signal the end of function dispatcher
        self.positions_contain_GT=[]

        for instruction in self.instruction_list:
            print(f'instruction:{instruction}')
            opcode = instruction['opcode']
            if str(opcode).__eq__('CALLDATASIZE'):
                flag_status = 1  # ready to get address of JUMPDEST for the block of revert

            elif str(opcode).startswith('PUSH'):
                if flag_status==1:
                    print(f'flag_status==1:{instruction}')
                    jumpdest_address = int(instruction["argument"], 0)
                    if jumpdest_address > 0:
                        self.address_jumpdest_revert_block = jumpdest_address
                if flag_status == 2:
                    if not str(instruction['argument']).__eq__('0xffffffff'):
                        if str(opcode).__eq__('PUSH4') or str(opcode).__eq__('PUSH3'):
                            if len(self.positions_to_instructions[position]) > 0:
                                if self.positions_to_instructions[position][-1]['opcode'] == 'DUP1':
                                    # get a new key-value pair to hold instructions for the function whose signature specified by this PUSH instruction
                                    position += 1
                                    record_position(position, instruction)


            elif str(opcode).__eq__('JUMPDEST'):  # the entry to the revert block when call data size is less than 4(before the code of functions)
                if flag_status == 2:
                    if self.address_jumpdest_revert_block == instruction["address"]:
                        # stop when reaching the end of function dispatcher
                        break
                    else:
                        position += 1
                        self.jumpdest_in_dispatcher.append((position,offset_instr))
                        self.positions_to_instructions[position] = []
            elif str(opcode).__eq__(
                'CALLDATALOAD'): # assume that CALLDATALOAD appears before funcion matching

                flag_status=2 # ready to get matching instructions

            elif str(opcode)in ['GT']:
                if flag_status == 2:
                    self.positions_contain_GT.append(position)# get the positions that contain GT

            # save the current instruction
            self.positions_to_instructions[position] += [instruction]

            offset_instr += 1

        print_dict(self.positions_to_instructions,'instruction grouping in instruction modification')


        # end of instruction iteration at the beginning section
        last_position=position+1

        # keep the last portion of instructions
        self.positions_to_instructions[last_position] = self.instruction_list[offset_instr:]




        # find all positions that are corresponding to functions
        positions=[]
        for p in self.functions_to_positions.values():
            positions+=p
        self.all_positions_related_function=positions
    def _feed_instructions_update(self):
        """
        new way to group instructions.
        :argument
        """

        def record_position(position:int,instruction:dict):

            self.positions_to_instructions[position] = []

            # get the function's signature as a key
            function_key = get_back_functin_signature(instruction['argument'])

            # if len(function_key) == 8:
            #     function_key = '0x00' + function_key[2:]
            #     print(f'convert {instruction["argument"]} to {function_key}')

            if function_key not in self.functions_to_positions.keys():
                self.functions_to_positions[function_key] = [position]
            else:
                self.functions_to_positions[function_key] += [position]

        def get_back_functin_signature(byte_tuple)->str:
            key='0x'
            if len(byte_tuple)==3:
                key+='00'
            for item in byte_tuple:
                v=hex(item)[2:]
                key+=v if len(v)==2 else '0'+v
            # print(f'{byte_tuple}=>{key}')
            return key

        def get_address_from_argument(int_tuple) -> int:
            value = 0
            exp = 0
            for item in reversed(int_tuple):
                value += item * 256 ** exp
                exp += 1
            return value

        # ============================================
        # through PHSH4 and JUMPDEST to sperate instructions
        offset_instr = 0
        flag_status = 0  # change its value when "CALLDATASIZE" is met and the first PUSH after "CALLDATASIZE" is met

        position = 0
        self.positions_to_instructions[0] = []
        self.address_jumpdest_revert_block = 0  # signal the end of function dispatcher
        self.positions_contain_GT=[]

        for instruction in self.instruction_list:
            # print(f'instruction:{instruction}')
            opcode = instruction['opcode']
            if str(opcode).__eq__('CALLDATASIZE'):
                flag_status = 1  # ready to get address of JUMPDEST for the block of revert

            elif str(opcode).startswith('PUSH'):
                if flag_status==1:
                    jumpdest_address=get_address_from_argument( instruction["argument"])
                    if jumpdest_address> 0:
                        self.address_jumpdest_revert_block = jumpdest_address
                if flag_status == 2:
                    if not get_back_functin_signature(instruction['argument']).__eq__('0xffffffff'):
                        if str(opcode).__eq__('PUSH4') or str(opcode).__eq__('PUSH3'):
                            if len(self.positions_to_instructions[position]) > 0:
                                if self.positions_to_instructions[position][-1]['opcode'] == 'DUP1':
                                    # get a new key-value pair to hold instructions for the function whose signature specified by this PUSH instruction
                                    position += 1
                                    record_position(position, instruction)


            elif str(opcode).__eq__('JUMPDEST'):  # the entry to the revert block when call data size is less than 4(before the code of functions)
                if flag_status == 2:
                    if self.address_jumpdest_revert_block == instruction["address"]:
                        # stop when reaching the end of function dispatcher
                        break
                    else:
                        position += 1
                        self.jumpdest_in_dispatcher.append((position,offset_instr))
                        self.positions_to_instructions[position] = []
            elif str(opcode).__eq__(
                'CALLDATALOAD'): # assume that CALLDATALOAD appears before funcion matching

                flag_status=2 # ready to get matching instructions

            elif str(opcode)in ['GT']:
                if flag_status == 2:
                    self.positions_contain_GT.append(position)# get the positions that contain GT

            # save the current instruction
            self.positions_to_instructions[position] += [instruction]

            offset_instr += 1

        # print_dict(self.positions_to_instructions,'instruction grouping in instruction modification')


        # end of instruction iteration at the beginning section
        last_position=position+1

        # keep the last portion of instructions
        self.positions_to_instructions[last_position] = self.instruction_list[offset_instr:]




        # find all positions that are corresponding to functions
        positions=[]
        for p in self.functions_to_positions.values():
            positions+=p
        self.all_positions_related_function=positions
    def modify_on_a_state__str(self, state: WorldState, functions: list):
        """
            update the instructions on multiple states
        """
        if len(functions)>=len(self.function_identifier.keys()):
            final_instructions=self.instruction_list
            state.accounts[self.contract_address.value].code.instruction_list = final_instructions

        else:
            fct_selectors=[]
            for ftn in functions:
                if ftn in ['fallback']:continue
                if ftn not in self.function_identifier.keys():continue # can  not do anything
                fct_selectors.append(self.function_identifier[ftn])
            final_instructions=self._get_modified_instructions_1(fct_selectors)

            # update instructions for states
            state.accounts[self.contract_address.value].code.instruction_list = final_instructions
            state.accounts[self.contract_address.value].code.func_hashes = fct_selectors

    def modity_on_multiple_states(self,states:[WorldState],functions:list):
        if 'original_instruction_list' in functions:
            final_instructions = self.instruction_list
            print(f'keep the original instruction list in instruction_modification.py')
            for state in states:
                state.accounts[self.contract_address.value].code.instruction_list = final_instructions
            return


        if len(functions) >= len(self.function_identifier.keys()):
            final_instructions = self.instruction_list
            for state in states:
                state.accounts[self.contract_address.value].code.instruction_list = final_instructions
            return


        fct_selectors = []
        for ftn in functions:
            if ftn in ['fallback']: continue
            if ftn not in self.function_identifier.keys():
                pure_name=ftn.split(f'(')[0] if '(' in ftn else ftn
                for func_full_name in self.function_identifier.keys():
                    if pure_name in func_full_name:
                        fct_selectors.append(self.function_identifier[func_full_name])
                        break
                continue  # can  not do anything
            fct_selectors.append(self.function_identifier[ftn])

        final_instructions = self._get_modified_instructions_1(fct_selectors)

        for state in states:
           # update instructions for states
            state.accounts[self.contract_address.value].code.instruction_list = final_instructions
            state.accounts[self.contract_address.value].code.func_hashes = fct_selectors

    def _get_modified_instructions_1(self, fct_selectors: list) -> list:
        """
            replace the matching instructions of other functions with EMPTY instruction
            keep the matching instructions of the specified functions
            * handle fallback() which has no selector
            * make sure that the last "DUP1" is replaced when the max position of the kept functions is not the last function
        """

        ftn_selectors_valid = [selector for selector in fct_selectors if selector in self.functions_to_positions.keys()]
        ftn_selectors_valid=list(set(ftn_selectors_valid))

        # find positions not kept
        # keep the functions having two positions(there are branches in the function dispatcher)
        keep = copy(self.positions_contain_GT)
        for ftn_selector in ftn_selectors_valid:
            keep += self.functions_to_positions[ftn_selector]

        not_kept = [p for p in self.all_positions_related_function if p not in keep]

         # combine instruction groups
        combined_instructions = []
        for p in range(0,len(self.positions_to_instructions) - 1):
            if p not in not_kept:
                combined_instructions += self.positions_to_instructions[p]
            else:
                # replace with EMPTY instructions
                empty_instructions = []  # do not remove them, it will cause inconsistency in terms of the total number of instructions
                for instruction in self.positions_to_instructions[p]:
                    empty_instructions.append({"address": instruction["address"], "opcode": "EMPTY"})

                combined_instructions += empty_instructions

        # before combining the last instruction group (the instructions of regular functions)
        # If the last non-EMPTY opcode is DUP,remove it in the already combined instructions
        for index in range(len(combined_instructions) - 1, 0, -1):
            if str(combined_instructions[index]['opcode']).__eq__('EMPTY'):
                continue
            else:
                if str(combined_instructions[index]['opcode']).__eq__('DUP1'):
                    instruction = combined_instructions[index]
                    combined_instructions[index] = {"address": instruction["address"], "opcode": "EMPTY"}

                break


        #
        for p,idx in self.jumpdest_in_dispatcher:
            idx=idx-1
            while True:
                instruction=combined_instructions[idx]
                opcode=instruction['opcode']
                if str(opcode).__eq__('EMPTY'):
                    idx = idx - 1
                    continue
                else:
                    if str(opcode) in ['JUMPDEST','PUSH4']:
                        break
                    if str(opcode).__eq__('DUP1'):
                        combined_instructions[idx] = {"address": instruction["address"], "opcode": "EMPTY"}
                    break

        # print_list(combined_instructions)
        combined_instructions += self.positions_to_instructions[len(self.positions_to_instructions) - 1]


        return combined_instructions

    def modify_no_modification(self,state:WorldState):
        state.accounts[self.contract_address.value].code.instruction_list = self.instruction_list

