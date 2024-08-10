import os
import sys


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_path=f'{get_project_root()}/'
sys.path.append(project_path)

FLAG_exp=True

contract_code=""

# ChatGPT_model="gpt-3.5-turbo-0301"  # the response format is more flexible
# ChatGPT_model="gpt-4-1106-preview"
GPT4_model= "gpt-4o-2024-05-13"
sleep_time=0

SEQ_iteration=5

FLAG_single_prompt=False
Flag_gpt=True

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
