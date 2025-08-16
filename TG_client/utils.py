from random import random, randint, choice, uniform
from time import sleep
import requests

from FakeAgent import Fake_Agent
from FakeAgent.types import Browsers

from TG_client.settings import BIT, LANG_CODE, SYS_VER


def dummy(*a, **b):
    pass


def sleep_bit(a=0, b=0):
    min_d = max(float(a), BIT)
    max_d = max(float(b), min_d + BIT)
    sleep(uniform(min_d, max_d))


def proxy_to_dict(proxy: str) -> dict:
    if not proxy: return {}

    if "socks5" in proxy:
        return {"http": proxy, "https": proxy}
    else:
        return {"http": f"http://{proxy}", "https": f"https://{proxy}"}


def proxy_check(proxy: str) -> (bool, str):
    if not proxy: return False, "No proxy!"
    try:
        resp = requests.get("https://api.ipify.org/", proxies=proxy_to_dict(proxy), timeout=5)
    except Exception as err:
        print(f"Connection error for proxy '{proxy}' -> {err}")
        return False, str(err)
    if resp.status_code != 200:
        print(f"Connection error for proxy '{proxy}' -> {resp.content}")
        return False, resp.content.decode("utf-8")
    print(f"Connection OK for proxy '{proxy}' - {resp.content}")
    return True, resp.content.decode("utf-8")


def generate_mac_device() -> str:
    fa = Fake_Agent(browser=choice([Browsers.FIREFOX, Browsers.SAFARI, Browsers.CHROME]))
    while True:
        ua = fa.random().lower()
        is_mac = ("mac" in ua) or ("safari" in ua) or ("apple" in ua)
        is_win = "windows" in ua
        is_linux = "linux" in ua
        if not any((is_win, is_linux)) and is_mac:
            return ua


def generate_device_info() -> dict:
    sys_ver = choice(SYS_VER)
    if sys_ver.lower().startswith("mac"):
        dev_model = generate_mac_device()
    else:
        fa = Fake_Agent(browser=choice([Browsers.FIREFOX, Browsers.EDGE, Browsers.CHROME, Browsers.OPERA]))
        dev_model = choice(["x86_64", "arm64", fa.random()])
    info = {
        "sys_ver": sys_ver,
        "dev_model": dev_model,
        "app_ver": str(random() + randint(1, 10))[0:4],
        "lang_code": choice(LANG_CODE),
    }
    return info
