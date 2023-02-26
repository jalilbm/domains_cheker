import json
from settings import DOMAIN_EXTENSIONS_TO_CHECK
from decouple import config
import re
import asyncio


telegram_allowed_usernames = config("telegram_allowed_usernames")
domains_pattern = r"\b[A-Za-z0-9]+\.[A-Za-z0-9]{2,}\b"


def get_json_from_chatGPT_response(response):

    try:
        domains = re.findall(domains_pattern, response)
        print("--------------------------------", len(domains))
        return domains
    except Exception:
        return False


def get_domain_name_without_extension(input):
    return ".".join(input.split(".")[:-1])


def generate_domains_with_multiple_extension(domain_without_extension):
    return [
        domain_without_extension + domain_extension
        for domain_extension in DOMAIN_EXTENSIONS_TO_CHECK
    ]


def message_reply_after_godaddy_check(godaddy_response):
    return (
        "".join(
            f"""{result['domain']} {'✅ $'+str(result['price'] / 10**6) if result['available'] else '❌ UNAVAILABLE'} {f'➡️ ${result["estimation_value"]:,}' if result.get('estimation_value') else ''}\n"""
            for result in godaddy_response.get("domains")
        )
        if godaddy_response.get("domains")
        else "ERROR: Godaddy did not reply with a valid response"
    )


def check_sender_allowance(update):
    username = update.message.from_user.username
    return bool(username and username in telegram_allowed_usernames)


def get_number_from_string(input):
    return int(match.group()) if (match := re.search(r"\d+", input)) else False


def get_only_available_domain_names_from_godaddy_response(godaddy_response):
    available_domains = {"domains": []}
    if not godaddy_response.get("domains"):
        return available_domains
    for result in godaddy_response.get("domains"):
        if result["available"]:
            available_domains["domains"].append(result)
    return available_domains


def get_proxies():
    return {
        "http": f"http://user-{config('smartproxy_username')}:{config('smartproxy_password')}@gate.smartproxy.com:7000",
        "https": f"http://user-{config('smartproxy_username')}:{config('smartproxy_password')}@gate.smartproxy.com:7000",
    }


async def async_iter(iterable):
    queue = asyncio.Queue()

    async def fill_queue():
        for item in iterable:
            await queue.put(item)
        await queue.put(None)

    async def get_from_queue():
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    task = asyncio.create_task(fill_queue())
    async for item in get_from_queue():
        yield item

    await task  # Wait for the fill_queue task to complete
