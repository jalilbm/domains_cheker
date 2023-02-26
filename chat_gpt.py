from revChatGPT.V1 import Chatbot, AsyncChatbot
from decouple import config

chatbot = AsyncChatbot(
    config={"email": config("chatGPT_email"), "password": config("chatGPT_password")}
)


async def query_chatGPT(prompt_):
    prompt = f"""{prompt_}, in json format following this format ```["domain1.com", "domain2.com", "domain3.com"...etc]```"""
    response = ""

    async for data in chatbot.ask(prompt):
        response = data["message"]

    return response
