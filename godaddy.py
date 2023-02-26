from pprint import pprint
import requests
from decouple import config
import requests
from fake_headers import Headers
import time
import utils
import concurrent.futures
import settings
import aiohttp


headers = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"sso-key {config('godaddy_key')}:{config('godaddy_secret')}",
}

params = {"checkType": "FAST"}

min_valuation_value = settings.LUCKY_GUESS_MIN_VALUE


class Godaddy:
    def __init__(self):
        self.session = aiohttp.ClientSession(headers=headers)
        self.proxies = utils.get_proxies()

    async def check_domains(self, domains):
        while True:
            try:
                response = await self.session.post(
                    "https://api.godaddy.com/v1/domains/available",
                    params=params,
                    json=domains,
                    timeout=10,
                )
                json_data = await response.json()
                print(json_data)
                if json_data.get("domains"):
                    return json_data
                elif json_data.get("errors"):
                    return {"domains": []}
            except Exception as e:
                print(e)
            time.sleep(3)

    def get_domain_value_estimation(self, domain):
        headers_ = Headers(os="mac", headers=True).generate()
        response = {}
        while True:
            try:
                response = requests.get(
                    f"https://api.godaddy.com/v1/appraisal/{domain}",
                    headers=headers_,
                    timeout=10,
                    proxies=self.proxies,
                )
                if not response.json().get("govalue"):
                    time.sleep(2)
                    continue
                print(response.json().get("domain"), response.json().get("govalue"))
                break
            except Exception as e:
                print(e)
                time.sleep(2)
        return response.json().get("govalue")

    async def get_multiple_domains_values(self, domains):
        domains = domains.get("domains")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(
                executor.map(
                    self.get_domain_value_estimation, [d["domain"] for d in domains]
                )
            )
            executor.shutdown(wait=True)
            pprint(results)
            for i in range(len(domains)):
                domains[i]["estimation_value"] = results[i]
        return {
            "domains": [
                d
                for d in domains
                if d.get("estimation_value")
                and d.get("estimation_value") > min_valuation_value
            ]
        }
