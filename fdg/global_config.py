
"""
Important parameters 
"""
#===============================================
# parameters that can be set by users
#--------------------------------------------

# indicate if a graph strategy is used to direct the symbolic execution
global flag_fwrg
fdg_fwrg=False

solidity_name=""
contract_name=""
top_k=2

# set the search strategy when guiding the symolic execution using a graph structure
global function_search_strategy
function_search_strategy='mine'


# having value larger than 0 means brandom baseline is active
# the value indicates the percentage of functions to be selected
# 1: 10%, 5:50%,...
global random_baseline
random_baseline=0


# indicate the code coverage that a function should reach
global function_coverage_threshold
function_coverage_threshold=98


# set the timeout for the preprocessing
global preprocess_timeout
preprocess_timeout=300


# indicate if functions' coverage will be printed.1:yes, 0:no
global print_function_coverage
print_function_coverage=1

# set to 1 if optimization is considered or not
# optimizations:
#    collect concrete addresses and treat them as the possible address msg.sender can take
#    add initial ether for the contract
global optimization
optimization=1


# indicate if all the state variables read in functions should be considered.
# by default, only the state varibles read in conditions are considered.
global flag_consider_all_reads
flag_consider_all_read=1


# set the limit on the times a function can be executed
global execution_times_limit
execution_times_limit=5


# provide the sequences to  be executed
global sequences
sequences=[]

#===============================================
# currently, does not support to change them through command line
#----------------------------------------------
global output_path
output_path='C:\\Users\\18178\\Desktop\\temp\\'

# set maximum number of iterations of the symbolic execution engine
global transaction_count
transaction_count=100

# the max length of a sequence
global seq_len_limit
seq_len_limit=4


#===============================================
# their values are set based on the execution
#----------------------------------------------
# save the contract address
global contract_address
contract_address=''

# save the function signatures from the disassembler
global method_identifiers
method_identifiers={}

# set True if there is an exception in the preprocessing
global preprocessing_exception
preprocessing_exception=False

# indicate if the execution is in the preprocessing
global flag_preprocessing
flag_preprocessing=False

# set True if there is timeout in the preprocessing
global flag_preprocess_timeout
flag_preprocess_timeout=False

# save the runtime bytecode of the target function
global target_runtime_bytecode
target_runtime_bytecode= ''

# there are used by the modules (no need to set their values)
global flag_query_solver
flag_query_solver=[]

# indicate the length of the transaction sequence
global tx_len
tx_len=0

global flag_fallback
flag_fallback=False

global p1_dl
p1_dl=1

#===============================================

global temp_count
temp_count=0

global time_temp
time_temp=0

global count
count=0


IGNORE_FUNC=['decimals()', 'symbol()', 'owner()','name()', 'version()']
