import os
import sys

APK_key= "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"
def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_path=f'{get_project_root()}/'
sys.path.append(project_path)

FLAG_exp=True

times=1

contract_code=""

# ChatGPT_model="gpt-3.5-turbo-0301"  # the response format is more flexible
# ChatGPT_model="gpt-4-1106-preview"
LLM_model= "gpt"

gpt_model= "gpt-4o-2024-05-13"
# deepseek_model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free" # together.ai
deepseek_model="deepseek-ai/deepseek-r1-distill-qwen-32b"
# llama_model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free" # together.ai
llama_model="meta/llama-3.1-70b-instruct"
starcoder_model="bigcode/starcoder2-15b"
mistral_model="nv-mistralai/mistral-nemo-12b-instruct"
qwen_model="qwen/qwen2.5-coder-32b-instruct"
palmyra_model="writer/palmyra-creative-122b"
gemma_model="google/gemma-2-27b-it"
temperature=0



sleep_time=0
LLM_Mode='gen'  #gen, gen_sel, xxx

SEQ_iteration=4


NUM_max_candidate_sequences=10
candi_percentage=0.5

Candi_prune=False

FLAG_single_prompt=False
Flag_gpt=True
FLAG_conversation=False


Claude_model="claude-3-5-sonnet-20240620"
Claude_model="claude-3-opus-20240229"

color_prefix={
"Black": "\033[30m",
"Red": "\033[31m",
"Green": "\033[32m",
"Yellow": "\033[33m",
"Blue": "\033[34m",
"Magenta": "\033[35m",
"Cyan": "\033[36m",
"White": "\033[37m",
"Gray": "\033[0m",
}

time_records=[]
input_tokens=[]
output_tokens=[]
