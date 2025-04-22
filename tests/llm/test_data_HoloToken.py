import os.path

"""
functions related to candidate sequences generation and refining

get_candidate_sequences() # called once in llm.py 

prune_candidate_sequences() # called iteratively in llm.py

find_start_states()
get_feedback()

"""

print(os.path.basename(__file__))

gen_seq = {
    'iteration_1': {'transferFrom':
                        ['setMinter', 'finishMinting', 'approve',
                         'transferFrom'],
                    'mint':
                        ['setMinter', 'mint'],
                    'burn':
                        ['setDestroyer', 'burn'],
                    'transfer':
                        ['setMinter', 'finishMinting', 'mint', 'transfer'],
                    'approve':
                        ['setMinter', 'finishMinting', 'approve'],
                    'finishMinting':
                        ['setMinter', 'finishMinting'],
                    'decreaseApproval':
                        ['increaseApproval', 'decreaseApproval']
                    },
    'iteration_2':{
        'transfer':
            ['setMinter', 'mint', 'finishMinting', 'transfer'],
        'burn':
            ['setMinter', 'mint', 'setDestroyer', 'burn']
    }
}

queue_all = {
    "queue_1": [
        "setDestroyer(address)#1",
        "setMinter(address)#2",
        "transferOwnership(address)#3",
        "decreaseApproval(address,uint256)#4",
        "increaseApproval(address,uint256)#5",
    ],

}

graph = {"increaseApproval":['transferFrom', 'decreaseApproval', 'setDestroyer', 'setMinter', 'transferOwnership'],
"decreaseApproval":['transferFrom', 'increaseApproval', 'setDestroyer', 'setMinter', 'transferOwnership'],
"setDestroyer":['transferFrom', 'approve', 'mint', 'burn', 'transfer', 'increaseApproval', 'decreaseApproval', 'setMinter', 'transferOwnership'],
"setMinter":['mint', 'finishMinting', 'setDestroyer', 'transferOwnership', 'increaseApproval', 'decreaseApproval'],
"mint":['transferFrom', 'burn', 'transfer', 'increaseApproval', 'decreaseApproval', 'setDestroyer', 'finishMinting', 'transferOwnership', 'setMinter', 'approve'],
"finishMinting":['transferFrom', 'approve', 'mint', 'burn', 'transfer', 'increaseApproval', 'decreaseApproval', 'setDestroyer', 'transferOwnership'],
"transferOwnership":['setDestroyer', 'transferOwnership', 'setMinter'],
"approve":['transferFrom', 'increaseApproval', 'decreaseApproval', 'setDestroyer', 'setMinter', 'mint', 'transferOwnership', 'burn', 'transfer'],
"burn":['transferFrom', 'mint', 'transfer', 'increaseApproval', 'decreaseApproval', 'setDestroyer', 'setMinter', 'finishMinting', 'transferOwnership', 'approve'],
"transfer":['transferFrom', 'burn', 'increaseApproval', 'decreaseApproval', 'setDestroyer', 'setMinter', 'mint', 'finishMinting', 'transferOwnership', 'approve'],
"transferFrom":['burn', 'transfer', 'setMinter', 'transferOwnership', 'setDestroyer', 'mint', 'finishMinting']
}


candidate_sequences_in_iterations={
    "iteration_2_before_prune":{
        'transfer':[
            ['increaseApproval', 'transferFrom', 'burn', 'transfer'],
            ['increaseApproval', 'transferFrom', 'transfer'],
            ['increaseApproval', 'transferFrom', 'setDestroyer', 'transfer'],
            ['increaseApproval', 'transferFrom', 'mint', 'transfer'],
            ['increaseApproval', 'transferFrom', 'finishMinting', 'transfer'],
            ['increaseApproval', 'decreaseApproval', 'transferFrom', 'transfer'],
            ['increaseApproval', 'decreaseApproval', 'setDestroyer', 'transfer'],
            ['increaseApproval', 'setDestroyer', 'transferFrom', 'transfer'],
            ['increaseApproval', 'setDestroyer', 'approve', 'transfer'],
            ['increaseApproval', 'setDestroyer', 'mint', 'transfer'],
            ['increaseApproval', 'setDestroyer', 'burn', 'transfer'],
            ['increaseApproval', 'setDestroyer', 'transfer'],
            ['increaseApproval', 'setMinter', 'mint', 'transfer'],
            ['increaseApproval', 'setMinter', 'finishMinting', 'transfer'],
            ['increaseApproval', 'setMinter', 'setDestroyer', 'transfer'],
            ['increaseApproval', 'transferOwnership', 'setDestroyer', 'transfer'],
            ['decreaseApproval', 'transferFrom', 'burn', 'transfer'],
            ['decreaseApproval', 'transferFrom', 'transfer'],
            ['decreaseApproval', 'transferFrom', 'setDestroyer', 'transfer'],
            ['decreaseApproval', 'transferFrom', 'mint', 'transfer'],
            ['decreaseApproval', 'transferFrom', 'finishMinting', 'transfer'],
            ['decreaseApproval', 'increaseApproval', 'transferFrom', 'transfer'],
            ['decreaseApproval', 'increaseApproval', 'setDestroyer', 'transfer'],
            ['decreaseApproval', 'setDestroyer', 'transferFrom', 'transfer'],
            ['decreaseApproval', 'setDestroyer', 'approve', 'transfer'],
            ['decreaseApproval', 'setDestroyer', 'mint', 'transfer'],
            ['decreaseApproval', 'setDestroyer', 'burn', 'transfer'],
            ['decreaseApproval', 'setDestroyer', 'transfer'],
            ['decreaseApproval', 'setMinter', 'mint', 'transfer'],
            ['decreaseApproval', 'setMinter', 'finishMinting', 'transfer'],
            ['decreaseApproval', 'setMinter', 'setDestroyer', 'transfer'],
            ['decreaseApproval', 'transferOwnership', 'setDestroyer', 'transfer'],
            ['setMinter', 'mint', 'transferFrom', 'transfer'],
            ['setMinter', 'mint', 'burn', 'transfer'],
            ['setMinter', 'mint', 'transfer'],
            ['setMinter', 'mint', 'setDestroyer', 'transfer'],
            ['setMinter', 'mint', 'finishMinting', 'transfer'],
            ['setMinter', 'mint', 'approve', 'transfer'],
            ['setMinter', 'finishMinting', 'transferFrom', 'transfer'],
            ['setMinter', 'finishMinting', 'approve', 'transfer'],
            ['setMinter', 'finishMinting', 'mint', 'transfer'],
            ['setMinter', 'finishMinting', 'burn', 'transfer'],
            ['setMinter', 'finishMinting', 'transfer'],
            ['setMinter', 'finishMinting', 'setDestroyer', 'transfer'],
            ['setMinter', 'setDestroyer', 'transferFrom', 'transfer'],
            ['setMinter', 'setDestroyer', 'approve', 'transfer'],
            ['setMinter', 'setDestroyer', 'mint', 'transfer'],
            ['setMinter', 'setDestroyer', 'burn', 'transfer'],
            ['setMinter', 'setDestroyer', 'transfer'],
            ['setMinter', 'transferOwnership', 'setDestroyer', 'transfer'],
            ['setMinter', 'increaseApproval', 'transferFrom', 'transfer'],
            ['setMinter', 'increaseApproval', 'setDestroyer', 'transfer'],
            ['setMinter', 'decreaseApproval', 'transferFrom', 'transfer'],
            ['setMinter', 'decreaseApproval', 'setDestroyer', 'transfer'],
            ['transferOwnership', 'setDestroyer', 'transferFrom', 'transfer'],
            ['transferOwnership', 'setDestroyer', 'approve', 'transfer'],
            ['transferOwnership', 'setDestroyer', 'mint', 'transfer'],
            ['transferOwnership', 'setDestroyer', 'burn', 'transfer'],
            ['transferOwnership', 'setDestroyer', 'transfer'],
            ['transferOwnership', 'setMinter', 'mint', 'transfer'],
            ['transferOwnership', 'setMinter', 'finishMinting', 'transfer'],
            ['transferOwnership', 'setMinter', 'setDestroyer', 'transfer'],
            ['setDestroyer', 'transferFrom', 'burn', 'transfer'],
            ['setDestroyer', 'transferFrom', 'transfer'],
            ['setDestroyer', 'transferFrom', 'mint', 'transfer'],
            ['setDestroyer', 'transferFrom', 'finishMinting', 'transfer'],
            ['setDestroyer', 'approve', 'transferFrom', 'transfer'],
            ['setDestroyer', 'approve', 'mint', 'transfer'],
            ['setDestroyer', 'approve', 'burn', 'transfer'],
            ['setDestroyer', 'approve', 'transfer'],
            ['setDestroyer', 'mint', 'transferFrom', 'transfer'],
            ['setDestroyer', 'mint', 'burn', 'transfer'],
            ['setDestroyer', 'mint', 'transfer'],
            ['setDestroyer', 'mint', 'finishMinting', 'transfer'],
            ['setDestroyer', 'mint', 'approve', 'transfer'],
            ['setDestroyer', 'burn', 'transferFrom', 'transfer'],
            ['setDestroyer', 'burn', 'mint', 'transfer'],
            ['setDestroyer', 'burn', 'transfer'],
            ['setDestroyer', 'burn', 'finishMinting', 'transfer'],
            ['setDestroyer', 'burn', 'approve', 'transfer'],
            ['setDestroyer', 'transfer'],
            ['setDestroyer', 'increaseApproval', 'transferFrom', 'transfer'],
            ['setDestroyer', 'decreaseApproval', 'transferFrom', 'transfer'],
            ['setDestroyer', 'setMinter', 'mint', 'transfer'],
            ['setDestroyer', 'setMinter', 'finishMinting', 'transfer'],
        ],
        'burn':[
            ['increaseApproval', 'transferFrom', 'burn'],
            ['increaseApproval', 'transferFrom', 'transfer', 'burn'],
            ['increaseApproval', 'transferFrom', 'setDestroyer', 'burn'],
            ['increaseApproval', 'transferFrom', 'mint', 'burn'],
            ['increaseApproval', 'transferFrom', 'finishMinting', 'burn'],
            ['increaseApproval', 'decreaseApproval', 'transferFrom', 'burn'],
            ['increaseApproval', 'decreaseApproval', 'setDestroyer', 'burn'],
            ['increaseApproval', 'setDestroyer', 'transferFrom', 'burn'],
            ['increaseApproval', 'setDestroyer', 'approve', 'burn'],
            ['increaseApproval', 'setDestroyer', 'mint', 'burn'],
            ['increaseApproval', 'setDestroyer', 'burn'],
            ['increaseApproval', 'setDestroyer', 'transfer', 'burn'],
            ['increaseApproval', 'setMinter', 'mint', 'burn'],
            ['increaseApproval', 'setMinter', 'finishMinting', 'burn'],
            ['increaseApproval', 'setMinter', 'setDestroyer', 'burn'],
            ['increaseApproval', 'transferOwnership', 'setDestroyer', 'burn'],
            ['decreaseApproval', 'transferFrom', 'burn'],
            ['decreaseApproval', 'transferFrom', 'transfer', 'burn'],
            ['decreaseApproval', 'transferFrom', 'setDestroyer', 'burn'],
            ['decreaseApproval', 'transferFrom', 'mint', 'burn'],
            ['decreaseApproval', 'transferFrom', 'finishMinting', 'burn'],
            ['decreaseApproval', 'increaseApproval', 'transferFrom', 'burn'],
            ['decreaseApproval', 'increaseApproval', 'setDestroyer', 'burn'],
            ['decreaseApproval', 'setDestroyer', 'transferFrom', 'burn'],
            ['decreaseApproval', 'setDestroyer', 'approve', 'burn'],
            ['decreaseApproval', 'setDestroyer', 'mint', 'burn'],
            ['decreaseApproval', 'setDestroyer', 'burn'],
            ['decreaseApproval', 'setDestroyer', 'transfer', 'burn'],
            ['decreaseApproval', 'setMinter', 'mint', 'burn'],
            ['decreaseApproval', 'setMinter', 'finishMinting', 'burn'],
            ['decreaseApproval', 'setMinter', 'setDestroyer', 'burn'],
            ['decreaseApproval', 'transferOwnership', 'setDestroyer', 'burn'],
            ['setMinter', 'mint', 'transferFrom', 'burn'],
            ['setMinter', 'mint', 'burn'],
            ['setMinter', 'mint', 'transfer', 'burn'],
            ['setMinter', 'mint', 'setDestroyer', 'burn'],
            ['setMinter', 'mint', 'finishMinting', 'burn'],
            ['setMinter', 'mint', 'approve', 'burn'],
            ['setMinter', 'finishMinting', 'transferFrom', 'burn'],
            ['setMinter', 'finishMinting', 'approve', 'burn'],
            ['setMinter', 'finishMinting', 'mint', 'burn'],
            ['setMinter', 'finishMinting', 'burn'],
            ['setMinter', 'finishMinting', 'transfer', 'burn'],
            ['setMinter', 'finishMinting', 'setDestroyer', 'burn'],
            ['setMinter', 'setDestroyer', 'transferFrom', 'burn'],
            ['setMinter', 'setDestroyer', 'approve', 'burn'],
            ['setMinter', 'setDestroyer', 'mint', 'burn'],
            ['setMinter', 'setDestroyer', 'burn'],
            ['setMinter', 'setDestroyer', 'transfer', 'burn'],
            ['setMinter', 'transferOwnership', 'setDestroyer', 'burn'],
            ['setMinter', 'increaseApproval', 'transferFrom', 'burn'],
            ['setMinter', 'increaseApproval', 'setDestroyer', 'burn'],
            ['setMinter', 'decreaseApproval', 'transferFrom', 'burn'],
            ['setMinter', 'decreaseApproval', 'setDestroyer', 'burn'],
            ['transferOwnership', 'setDestroyer', 'transferFrom', 'burn'],
            ['transferOwnership', 'setDestroyer', 'approve', 'burn'],
            ['transferOwnership', 'setDestroyer', 'mint', 'burn'],
            ['transferOwnership', 'setDestroyer', 'burn'],
            ['transferOwnership', 'setDestroyer', 'transfer', 'burn'],
            ['transferOwnership', 'setMinter', 'mint', 'burn'],
            ['transferOwnership', 'setMinter', 'finishMinting', 'burn'],
            ['transferOwnership', 'setMinter', 'setDestroyer', 'burn'],
            ['setDestroyer', 'transferFrom', 'burn'],
            ['setDestroyer', 'transferFrom', 'transfer', 'burn'],
            ['setDestroyer', 'transferFrom', 'mint', 'burn'],
            ['setDestroyer', 'transferFrom', 'finishMinting', 'burn'],
            ['setDestroyer', 'approve', 'transferFrom', 'burn'],
            ['setDestroyer', 'approve', 'mint', 'burn'],
            ['setDestroyer', 'approve', 'burn'],
            ['setDestroyer', 'approve', 'transfer', 'burn'],
            ['setDestroyer', 'mint', 'transferFrom', 'burn'],
            ['setDestroyer', 'mint', 'burn'],
            ['setDestroyer', 'mint', 'transfer', 'burn'],
            ['setDestroyer', 'mint', 'finishMinting', 'burn'],
            ['setDestroyer', 'mint', 'approve', 'burn'],
            ['setDestroyer', 'burn'],
            ['setDestroyer', 'transfer', 'transferFrom', 'burn'],
            ['setDestroyer', 'transfer', 'burn'],
            ['setDestroyer', 'transfer', 'mint', 'burn'],
            ['setDestroyer', 'transfer', 'finishMinting', 'burn'],
            ['setDestroyer', 'transfer', 'approve', 'burn'],
            ['setDestroyer', 'increaseApproval', 'transferFrom', 'burn'],
            ['setDestroyer', 'decreaseApproval', 'transferFrom', 'burn'],
            ['setDestroyer', 'setMinter', 'mint', 'burn'],
            ['setDestroyer', 'setMinter', 'finishMinting', 'burn'],
            ]
    },

    "iteration_2_after_prune":{
        "transfer":
            [
            ['setMinter', 'mint', 'transferFrom', 'transfer'],
            ['setMinter', 'mint', 'burn', 'transfer'],
            ['setMinter', 'mint', 'transfer'],
            ['setMinter', 'mint', 'finishMinting', 'transfer'],
            ['setMinter', 'mint', 'setDestroyer', 'transfer'],
            ['setMinter', 'mint', 'approve', 'transfer'],
            ['setMinter', 'finishMinting', 'burn', 'transfer'],
            ['setMinter', 'finishMinting', 'transferFrom', 'transfer'],
            ['setMinter', 'finishMinting', 'approve', 'transfer'],
            ['setMinter', 'finishMinting', 'transfer'],
            ['setMinter', 'finishMinting', 'setDestroyer', 'transfer'],
            ['increaseApproval', 'decreaseApproval', 'transferFrom', 'transfer'],
            ['increaseApproval', 'decreaseApproval', 'setDestroyer', 'transfer'],
            ],
        "burn":
            [['setMinter', 'mint', 'transferFrom', 'burn'],
            ['setMinter', 'mint', 'burn'],
            ['setMinter', 'mint', 'transfer', 'burn'],
            ['setMinter', 'mint', 'finishMinting', 'burn'],
            ['setMinter', 'mint', 'setDestroyer', 'burn'],
            ['setMinter', 'mint', 'approve', 'burn'],
            ['setMinter', 'finishMinting', 'mint', 'burn'],
            ['setMinter', 'finishMinting', 'burn'],
            ['setMinter', 'finishMinting', 'transferFrom', 'burn'],
            ['setMinter', 'finishMinting', 'approve', 'burn'],
            ['setMinter', 'finishMinting', 'transfer', 'burn'],
            ['setMinter', 'finishMinting', 'setDestroyer', 'burn'],
            ['increaseApproval', 'decreaseApproval', 'transferFrom', 'burn'],
            ['increaseApproval', 'decreaseApproval', 'setDestroyer', 'burn']
        ]
    }

}
"""
current
"""
current_sequences_in_interations={
    'all_iteration_1':{
        'transferFrom':
            ['setMinter', 'finishMinting', 'approve', 'transferFrom'],
        'mint':
            ['setMinter', 'mint'],
        'burn':
            ['setDestroyer', 'burn'],
        'transfer':
            ['setMinter', 'finishMinting', 'mint', 'transfer'],
        'approve':
            ['setMinter', 'finishMinting', 'approve'],
        'finishMinting':
            ['setMinter', 'finishMinting'],
        'decreaseApproval':
            ['increaseApproval', 'decreaseApproval'],
      },
    'exe_iteration_1':[
        ['setMinter', 'finishMinting'],
        ['setMinter', 'mint'],
        ['increaseApproval', 'decreaseApproval'],
        ['setMinter', 'finishMinting', 'approve'],
        ['setMinter', 'finishMinting', 'approve', 'transferFrom'],
    ]
}
