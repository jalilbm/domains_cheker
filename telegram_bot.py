import asyncio
from pprint import pprint
import random
import threading
import time
import traceback
from decouple import config
import telegram
from telegram.ext import (
    MessageHandler,
    filters,
    Application,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
)
from telegram import Update
from godaddy import Godaddy
from chat_gpt import query_chatGPT
import utils
from functools import wraps
import settings
import concurrent.futures


telegram_bot_token = config("telegram_bot_token")
telegram_bot_allowed_ids = config("allowed_ids")
bot = telegram.Bot(token=telegram_bot_token)
godaddy = Godaddy()
lucky_shot_topics = settings.LUCKY_GUESS_TOPICS


def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        if utils.check_sender_allowance(update):
            return await func(update, context, *args, **kwargs)
        else:
            await update.message.reply_text(
                "You are not allowed to message this bot, contact the owner @jalil_bm"
            )

    return wrapped


async def cancel(update, context):
    await update.message.reply_text("Canceled!")
    return ConversationHandler.END


def check_domain_availability(domain, results):
    try:
        available = godaddy.check_domains(domain)
        results[domain] = available
    except Exception as e:
        pprint(traceback.format_exc())
        results[domain] = e


async def chatGPT_guess(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt_=None,
    min_valuation_value=None,
) -> None:
    prompt = prompt_ or update.message.text
    if not prompt.replace("/chatgpt", ""):
        await update.message.reply_text(
            "ERROR: Please enter a prompt (query) for ChatGPT\nDemo:\n/chatgpt YOUR QUERY\nExample:\n/chatgpt give me 5 domain names which might not be taken yet"
        )
        return
    await update.message.reply_text("ChatGPT is thinking 🤔...")
    chatGPT_response = await query_chatGPT(prompt)
    response = utils.get_json_from_chatGPT_response(chatGPT_response)
    if not response:
        await update.message.reply_text(
            f"ERROR: Invalid response from ChatGPT, please try again\n\nChatGPT Response:\n{chatGPT_response}"
        )
        print(chatGPT_response)
        return
    await update.message.reply_text(
        "Investigating generated domain names 🕵️..."
        + (
            f"\nGetting domain names valuated at ${min_valuation_value:,} or more"
            if min_valuation_value
            else ""
        )
    )
    raw_domains = [utils.get_domain_name_without_extension(r) for r in response]
    domains_to_check = [
        utils.generate_domains_with_multiple_extension(d) for d in raw_domains
    ]
    godaddy_response = [
        g_r
        for g_r in [
            await godaddy.check_domains(domains) for domains in domains_to_check
        ]
    ]
    number_of_domains_tested = sum([len(d.get("domains")) for d in godaddy_response])
    if min_valuation_value:
        godaddy_response = [
            available_domain_names
            for available_domain_names in [
                utils.get_only_available_domain_names_from_godaddy_response(g_r)
                for g_r in godaddy_response
            ]
            if len(available_domain_names.get("domains")) > 0
        ]
        godaddy_response_iter = iter(godaddy_response)
        async for g_r in utils.async_iter(godaddy_response_iter):
            r = await godaddy.get_multiple_domains_values(g_r)
            if len(r.get("domains")) > 0:
                await update.message.reply_text(
                    utils.message_reply_after_godaddy_check(r)
                )
    else:
        for g_r in godaddy_response:
            if len(g_r.get("domains")) > 0:
                await update.message.reply_text(
                    utils.message_reply_after_godaddy_check(g_r)
                )
    await update.message.reply_text(
        f"Done!\nTested {number_of_domains_tested} domain names"
    )


async def check_domains(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    domains_to_check = utils.generate_domains_with_multiple_extension(
        update.message.text
    )
    godaddy_response = await godaddy.check_domains(domains_to_check)
    await update.message.reply_text(
        utils.message_reply_after_godaddy_check(godaddy_response)
    )


async def chatGPT_by_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Enter commas separated topics\nExample:\nsports,fitness,health"
    )
    return TOPICS


async def get_chatGPT_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if topics := [t.strip() for t in update.message.text.split(",")]:
        context.user_data["topics"] = topics
        await update.message.reply_text(
            "Enter max number of characters desired\nExample:\n15"
        )
        return NUMBER_OF_CHARACTERS
    else:
        await update.message.reply_text("ERROR: Invalid input format")


async def get_chatGPT_number_of_characters(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if number_of_characters := utils.get_number_from_string(update.message.text):
        context.user_data["number_of_characters"] = number_of_characters
        await update.message.reply_text("Enter number of domains desired\nExample:\n5")
        return NUMBER_OF_DOMAINS
    else:
        await update.message.reply_text("ERROR: Invalid input format")


async def get_chatGPT_number_of_domains(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if number_of_domains := utils.get_number_from_string(update.message.text):
        context.user_data["number_of_domains"] = number_of_domains
        await update.message.reply_text(
            f"Searching for topics:\n{str(context.user_data['topics'])}\nMax domain length:\n{str(context.user_data['number_of_characters'])}"
        )
        prompt = f"""Give me {number_of_domains} easy to remember domain names which might not been taken yet, related to {' '.join(context.user_data['topics'])}, and each domain name must not exceed {context.user_data['number_of_characters']} characters"""
        await chatGPT_guess(update=update, context=context, prompt_=prompt)
        return ConversationHandler.END
    else:
        await update.message.reply_text("ERROR: Invalid input format")


async def chatGPT_lucky_shot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topics = sorted(lucky_shot_topics, key=lambda x: random.random())[:1]
    await update.message.reply_text(f"TOPICS:\n{topics}")
    prompt = f"""give me 40 ".com" domain names of your choice{f' which are related to famous cities and places in the world and  {", ".join(topics)}' if lucky_shot_topics else ''} that are valuable and might not been taken yet. The less the length of the domain name is is, the better it will be. It must also not contain any prefixes or suffixes such as "guru" or "hq" or whatever, I know that you are an AI chat bot and you might not be able to do that, but just make a lucky guess"""
    await chatGPT_guess(
        update=update,
        context=context,
        prompt_=prompt,
        min_valuation_value=settings.LUCKY_GUESS_MIN_VALUE,
    )


periodic_lucky_shot = False


async def periodic_chatGPT_lucky_shots(update, context):
    print("kakakakak")
    global periodic_lucky_shot
    if periodic_lucky_shot:
        await update.message.reply_text("Already ON!")
    else:
        await update.message.reply_text("Automatic periodic chaGPT ON!")
        periodic_lucky_shot = True
        job_queue.run_repeating(
            lambda x: chatGPT_lucky_shot(update, context),
            interval=settings.PERIODIC_LUCKY_SHOT_TIME,
            first=0,
        )


async def stop_periodic_chatGPT_lucky_shots(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    global periodic_lucky_shot
    if not periodic_lucky_shot:
        await update.message.reply_text("Already OFF!")
    else:
        periodic_lucky_shot = False
        await update.message.reply_text("Turned OFF!")


print("Starting bot...")
# Wrapping functions
check_domains = restricted(check_domains)
chatGPT_guess = restricted(chatGPT_guess)
chatGPT_by_topics = restricted(chatGPT_by_topics)
chatGPT_lucky_shot = restricted(chatGPT_lucky_shot)
periodic_chatGPT_lucky_shots = restricted(periodic_chatGPT_lucky_shots)
stop_periodic_chatGPT_lucky_shots = restricted(stop_periodic_chatGPT_lucky_shots)
# States
TOPICS, NUMBER_OF_CHARACTERS, NUMBER_OF_DOMAINS = range(3)
# Application
application = Application.builder().token(telegram_bot_token).build()
job_queue = application.job_queue
application.add_handler(CommandHandler("chatgpt", chatGPT_guess))
application.add_handler(CommandHandler("chatgpt_lucky_shot", chatGPT_lucky_shot))
application.add_handler(
    CommandHandler("chatgpt_periodic_lucky_shot_on", periodic_chatGPT_lucky_shots)
)
application.add_handler(
    CommandHandler("chatgpt_periodic_lucky_shot_off", stop_periodic_chatGPT_lucky_shots)
)
application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("chatgpt_by_topic", chatGPT_by_topics)],
        states={
            TOPICS: [
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT, get_chatGPT_topics),
            ],
            NUMBER_OF_CHARACTERS: [
                CommandHandler("cancel", cancel),
                MessageHandler(
                    filters.TEXT,
                    get_chatGPT_number_of_characters,
                ),
            ],
            NUMBER_OF_DOMAINS: [
                CommandHandler("cancel", cancel),
                MessageHandler(
                    filters.TEXT,
                    get_chatGPT_number_of_domains,
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
)
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_domains))
application.run_polling()
