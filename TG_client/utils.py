"""
    Utilities
"""
import json
import os
import uuid
from random import random, randint, choice, uniform
from time import sleep, time
from datetime import datetime, timedelta

import requests
from telethon.tl.patched import Message

from TG_client.settings import BIT, LANG_CODE, SYS_VER, MESSAGE_FIELDS
from params.models import api_header, api_key


def dummy(*a, **b):
    pass


def sleep_bit(a=0, b=0):
    min_d = max(float(a), BIT)
    max_d = max(float(b), min_d + BIT)
    sleep(uniform(min_d, max_d))


def formatted_time(duration=0.0) -> str:
    seconds = int(duration)
    if seconds < 70:
        return f"{duration:.1f} sec"
    elif seconds < 3601:
        return f"{seconds // 60}min {seconds % 60}sec"
    else:
        hours = seconds // 3600
        seconds -= hours * 3600
        return f"{hours}h {seconds // 60}min {seconds % 60}sec"


# def check_time(date, period: int) -> bool:
#     return datetime.utcnow() - datetime.fromisoformat(str(date)) <= timedelta(hours=period)


def to_int(s):
    try:
        num = float(s)
        return int(num)
    except ValueError:
        return None


def to_dict(obj) -> dict:
    return {
        attr: str(getattr(obj, attr))
        for attr in dir(obj)
        if not attr.startswith("_") and not callable(getattr(obj, attr))
    }


def erase_file(filename):
    if not filename: return
    try:
        filename = str(filename)
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        print(e)


def save_json(obj: dict, filename="obj"):
    with open(filename + ".json", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)


def proxy_to_dict(proxy: str) -> dict:
    if not proxy: return {}

    if "socks5" in proxy:
        return {"http": proxy, "https": proxy}
    else:
        return {"http": f"http://{proxy}", "https": f"https://{proxy}"}


def proxy_check(proxy: str) -> (bool, str):
    if not proxy: return False, "No proxy!"
    start = time()
    try:
        resp = requests.get("https://api.ipify.org/", proxies=proxy_to_dict(proxy), timeout=5)
    except Exception as err:
        return False, str(err)
    if resp.status_code != 200:
        return False, resp.content.decode("utf-8")
    print(f"Connection OK for proxy '{proxy}' - {resp.content}")
    return True, f"{resp.content.decode('utf-8')} ({formatted_time(time()-start)})"


def generate_mac_device() -> str:
    return choice(["x86_64", "arm64"])
    # fa = Fake_Agent(browser=choice([Browsers.FIREFOX, Browsers.SAFARI, Browsers.CHROME]))
    # while True:
    #     ua = fa.random().lower()
    #     is_mac = ("mac" in ua) or ("safari" in ua) or ("apple" in ua)
    #     is_win = "windows" in ua
    #     is_linux = "linux" in ua
    #     if not any((is_win, is_linux)) and is_mac:
    #         return ua


def generate_device_info() -> dict:
    sys_ver = choice(SYS_VER)
    if sys_ver.lower().startswith("mac"):
        dev_model = generate_mac_device()
    else:
#        fa = Fake_Agent(browser=choice([Browsers.FIREFOX, Browsers.EDGE, Browsers.CHROME, Browsers.OPERA]))
        dev_model = choice(["x86_64", "arm64"])
    info = {
        "sys_ver": sys_ver,
        "dev_model": dev_model,
        "app_ver": str(random() + randint(1, 10))[0:4],
        "lang_code": choice(LANG_CODE),
    }
    return info


def message_to_dict(message: Message) -> dict:
    return {attr: str(getattr(message, attr, "None")) for attr in MESSAGE_FIELDS}


def message_is_valid(message: Message) -> bool:
    return True


def send_results(url: str, count: int = 0, messages: list = None, filename: str = "", error: str = "") -> str:
    result = ""
    try:
        if not url: raise Exception("No endpoint to send results!")
        hdrs = {
            "Accept": "application/json",
            api_header(): api_key(),
        }
        uid = str(uuid.uuid4())

        if messages is not None:
            resp = requests.post(url, json={"count": count, "messages": messages, "chunk": 0, "uid": uid}, headers=hdrs)
            resp.raise_for_status()
        elif filename:
            messages = []
            chunk = 0
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    messages.append(line.rstrip("\n"))
                    if len(messages) == 100:
                        resp = requests.post(
                            url,
                            json={"count": count, "messages": messages, "chunk": chunk, "uid": uid},
                            headers=hdrs,
                        )

                        resp.raise_for_status()
                        messages = []
                        chunk += 1

            if messages:
                resp = requests.post(
                    url,
                    json={"count": len(messages), "messages": messages, "chunk": chunk, "uid": uid},
                    headers=hdrs,
                )
                resp.raise_for_status()

        if error:
            resp = requests.post(url, json={"error": error, "uid": uid}, headers=hdrs)
            resp.raise_for_status()

    except Exception as err:
        print(f"Error: {err}")
        result = str(err)

    erase_file(filename)
    return result


# def manage(message: Message):
#     sender = message.sender
#
#     user_link = f"tg://user?id={sender.id}"
#     if sender.username:
#         user_link = f"@{sender.username}"
#
#     # Get username or string: "first_name + last_name" for search in group
#     username = sender.username
#     if not username:
#         username = " ".join([f for f in [sender.first_name, sender.last_name] if f])
#     if not username:
#         username = str(sender.id)
#
#     # link to message
#     if message.chat.username:
#         message_link = f"https://t.me/{message.chat.username}/{message.id}"
#     else:
#         message_link = f"https://t.me/c/{message.chat.id}/{message.id}/"
#
#     save_json(message_to_dict(message), f"{username}_{message.id}")
#     print("---- Receive message")
#     print(f"From: {username} - {user_link}")
#     print(f"Text: {message.raw_text}")
#     print()
#     print(f"Link: {message_link}")
