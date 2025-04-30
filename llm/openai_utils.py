import os
import openai
from together import Together
from openai import OpenAI

from llm.llm_config import APK_key
from llm.utils import color_print

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ['OPENAI_API_KEY'],
)

openai.api_key = os.environ['OPENAI_API_KEY']


def gpt_request(model, msg, temperature=0.0):
    response= client.chat.completions.create(
        model=model,
        messages=msg,
        temperature=temperature,
        stream=False,
    )

    # # when stream=True
    # message = ""
    # for chunk in response:
    #     # print(chunk.choices[0].delta.content or "", end="")
    #     message += chunk.choices[0].delta.content or ""


    token_counts = [0, 0]
    message = response.choices[0].message.content
    token_counts = [response.usage.prompt_tokens,
                    response.usage.completion_tokens]
    return message,token_counts

model0="text-embedding-3-small"
model1="text-embedding-3-large"
model2="text-embedding-ada-002"
def get_embedding(text, model=model0):
   text = text.replace("\n", " ")
   # return client.embeddings.create(input = [text], model=model,  encoding_format="float",  dimensions=256).data[0].embedding
   return client.embeddings.create(input = [text], model=model,  encoding_format="float").data[0].embedding


def llama_request(model, msg, temperature=0.0):
    # ----------
    # together
    # # export TOGETHER_API_KEY=your_api_key_here
    # client = Together(
    #     api_key="b4f13d02f690097d11033441dcefce94b10c4aa8081c14a52b2314a8565443f0")
    #
    # response = client.chat.completions.create(
    #     model=model,
    #     messages=msg,
    #     temperature=temperature,
    #     stream=False,
    # )

    #----------
    # nvidia
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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"
    )

    response = client.chat.completions.create(
        model=model,
        messages=msg,
        temperature=temperature,
        stream=False
    )
    token_counts=[0,0]
    message = response.choices[0].message.content
    token_counts = [response.usage.prompt_tokens,
                    response.usage.completion_tokens]
    return message,token_counts

def deepseek_request(model, msg, temperature=0.0):
    # ----------
    # together
    # client = Together(
    #     api_key="b4f13d02f690097d11033441dcefce94b10c4aa8081c14a52b2314a8565443f0")
    #
    # response = client.chat.completions.create(
    #     model=model,
    #     messages=msg,
    #     temperature=temperature,
    #     stream=False,
    # )

    # ----------
    # nvidia
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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"
    )
    response = client.chat.completions.create(
        model=model,
        messages=msg,
        temperature=temperature,
        stream=False,
    )

    token_counts = [0, 0]
    message = response.choices[0].message.content
    token_counts = [response.usage.prompt_tokens,
                    response.usage.completion_tokens]

    return message,token_counts


def starcoder_request(model,msg,temperature=0.0):
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=APK_key
    )

    prompts=""
    for cont in msg:
        prompts+=cont["content"]+"\n"

    response = client.completions.create(
        model=model,
        promt=prompts,
        temperature=temperature,
        stream=False
    )

    token_counts = [0, 0]
    # message = response.choices[0].message.content
    token_counts = [response.usage.prompt_tokens,
                    response.usage.completion_tokens]

    message = response.choices[0].text
    print(repr(response.choices[0].text))
    print(message)

    return message, token_counts


def mistral_request(model,msg,temperature=0.0):
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=APK_key
    )
    # completion = client.chat.completions.create(
    response = client.chat.completions.create(
        model=model,
        messages=msg,
        temperature=temperature,
        stream=False
    )

    token_counts = [0, 0]
    message = response.choices[0].message.content
    token_counts = [response.usage.prompt_tokens,
                    response.usage.completion_tokens]

    return message, token_counts

def qwen_request(model,msg,temperature=0.0):
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=APK_key
    )
    # completion = client.chat.completions.create(
    response = client.chat.completions.create(
        model=model,
        messages=msg,
        temperature=temperature,
        stream=False
    )

    token_counts = [0, 0]
    message = response.choices[0].message.content
    token_counts = [response.usage.prompt_tokens,
                    response.usage.completion_tokens]

    return message, token_counts

def palmyra_request(model,msg,temperature=0.0):
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=APK_key
    )

    response = client.chat.completions.create(
        model=model,
        messages=msg,
        temperature=temperature,
        stream=False
    )

    token_counts = [0, 0]

    """
    possible error:
      message = response.choices[0].message.content
    AttributeError: 'str' object has no attribute 'choices'
    """
    if not isinstance(response,str):
        message = response.choices[0].message.content

        token_counts = [response.usage.prompt_tokens,
                        response.usage.completion_tokens]
    else:
        color_print('Red',f"Warning: why is the response of type str (palmyra_request in {os.path.basename(__file__)})")
        color_print("Gray",f'response:{response}')
        message=response
    return message,token_counts


def gemma_request(model,msg,temperature=0.0):
    from openai import OpenAI

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=APK_key
    )

    msg_=[m_dict for m_dict in msg if m_dict["role"] not in ['system'] ]
    response = client.chat.completions.create(
        model=model,
        messages=msg_,
        temperature=temperature,
        stream=False
    )



    token_counts = [0, 0]
    message = response.choices[0].message.content
    token_counts = [response.usage.prompt_tokens,
                    response.usage.completion_tokens]

    return message, token_counts
