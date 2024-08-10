#https://colab.research.google.com/drive/1SoAajN8CBYTl79VyTwxtxncfCWlHlyy9
import os

import anthropic

from llm.llm_config import Claude_model

anthropic.api_key = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic()

# ANTHROPIC_API_KEY=""
# client = anthropic.Client(api_key=ANTHROPIC_API_KEY)


def claude_create(engine,prompts,temperature=0.0):
    system_message=""
    user_message=[]
    for msg in prompts:
        if "role" in msg.keys():
            if msg['role'] in ['system']:
                system_message=msg['content']
            else:
                user_message.append(msg)

    message = client.messages.create(
        model=engine,
        max_tokens=1000,
        temperature=temperature,
        system=system_message,
        messages=user_message,

    )

    return message.content[0].text




if __name__=="__main__":

    prompts=messages=[
        {
            "role":"system",
            "content":"you are good text generator."
        },

        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Why is the ocean salty?"
                }
            ]
        }
        ]
    re=claude_create(Claude_model,prompts)
    print(f'{re}')


