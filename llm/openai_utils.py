import os
import openai
from together import Together
from openai import OpenAI

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
    return message

model0="text-embedding-3-small"
model1="text-embedding-3-large"
model2="text-embedding-ada-002"
def get_embedding(text, model=model0):
   text = text.replace("\n", " ")
   # return client.embeddings.create(input = [text], model=model,  encoding_format="float",  dimensions=256).data[0].embedding
   return client.embeddings.create(input = [text], model=model,  encoding_format="float").data[0].embedding


def llama_request(model, msg, temperature=0.0):
    # export TOGETHER_API_KEY=your_api_key_here
    client = Together(
        api_key="b4f13d02f690097d11033441dcefce94b10c4aa8081c14a52b2314a8565443f0")

    response = client.chat.completions.create(
        model=model,
        messages=msg,
        temperature=temperature,
        stream=False,
    )

    token_counts=[0,0]
    message = response.choices[0].message.content
    token_counts = [response.usage.prompt_tokens,
                    response.usage.completion_tokens]
    return message,token_counts

def deepseek_request(model, msg, temperature=0.0):
    client = Together(
        api_key="b4f13d02f690097d11033441dcefce94b10c4aa8081c14a52b2314a8565443f0")

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





