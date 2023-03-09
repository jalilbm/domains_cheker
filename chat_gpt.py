import asyncio

# from revChatGPT.V1 import Chatbot, AsyncChatbot
from revChatGPT.V3 import Chatbot
from decouple import config
import time


async def query_chatGPT(prompt_):
    # chatbot = AsyncChatbot(
    #     config={
    #         "email": config("chatGPT_email"),
    #         "password": config("chatGPT_password"),
    #     }
    # )
    chatbot = Chatbot(api_key=config("chatGPT_API_API_KEY"))
    prompt = f"""{prompt_}, in json format following this format ```["domain1.com", "domain2.com", "domain3.com"...etc]```"""
    response = ""

    while True:
        # try:
        # async for data in chatbot.ask(prompt):
        for data in chatbot.ask(prompt):
            response += data
        break
    # except Exception:
    #     # await asyncio.sleep(60)
    #     time.sleep(60)
    print(response)
    chatbot.reset()
    return response
