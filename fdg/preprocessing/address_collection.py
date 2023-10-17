
import re


"""
collect the concrete addresses used in a contract.
put the collected addresses to the value list of msg.sender
"""

# solve case 6: msg.sender must be a particular value
# type 1: msg.sender==a particular value
import fdg.global_config

actors=None

max_value_of_address='1461501637330902918203684832716283019655932542975'

sender_in_condition_pattern=r'.*Extract\s*\(\s*159\s*,\s*0\s*,\s*sender\_\d+\s*\)\s*\=\=\s*\d+\s*,\s*.*'

def collect_value_for_sender(condition:str):
    match = re.match(sender_in_condition_pattern, condition)
    if match is not None:
        value = match.group().split('==')[1].split(',')[0].strip()
        if str(value)=='0':return
        if value not in actors.addresses.values():
            # actors.addresses['somebody'+str(len(actors.addresses.keys()))]=value
            actors.addresses['somebody' + str(len(actors))] = value
            print(f'{value} is added into actors.')
            # print(f'\n existent account:')
            # for key,v in actors.addresses.items():
            #     print(f'{key}:{v}')



# type2: balanceOf(msg.sender) must have ether given in constructor)
def collect_addresses_in_constructor(location:str,value:str):
    if fdg.global_config.optimization == 1:
        # if len(location)<=3: # assume that the number of state variables is less than 999
        # example location:48742052450242675226419400811361861310099883670668719892216195244291216567495
        # from hash function
        if len(value)>=40: # the value should denote an address
            if len(value)<=len(max_value_of_address):
                if value not in actors.addresses.values():
                    # actors.addresses['somebody'+str(len(actors.addresses.keys()))]=value
                    actors.addresses['somebody' + str(len(actors))] = value
                    print(f'{value} is added into actors.')
                # print(f'\n existent account:')
                # for key, v in actors.addresses.items():
                #     print(f'{key}:{v}')

