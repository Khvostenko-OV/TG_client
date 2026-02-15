import asyncio
import threading

from celery import shared_task

from TG_client.utils import send_results, send_chats, save_json
from accounts.models import User
from params.models import Log
from tasks.models import TGgroup


@shared_task
def parsing_group(group_pk: int, admin_pk: int, url: str, start=0, end=0):
    if not url: return
    group = TGgroup.get(group_pk)
    admin = User.get(admin_pk)
    if not group or not admin: return
    Log.set(f"API: [{admin}] start parsing TG-group '{group}'")
    info = {}
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    threading.Thread(target=loop.run_forever, daemon=True).start()
    try:
        future = asyncio.run_coroutine_threadsafe(admin.connect(loop), loop)
        result = future.result()
        if not result: raise Exception(f"TG auth error")
        future = asyncio.run_coroutine_threadsafe(group.admin_check(admin), loop)
        info = future.result()
        if not info: raise Exception(f"Can't connect TG-group '{group}'")

        future = asyncio.run_coroutine_threadsafe(admin.parse_channel(group.chat_id, start=start, end=end), loop)
        result = future.result()
        count = result["count"]
        error = result["error"]
        Log.set(f"API: [{admin}] from tg-chat '{group}' parsed messages - {count}")
        if count > 100:
            err = send_results(url, count, info, filename=result["filename"])
        else:
            err = send_results(url, count, info, messages=result["messages"])
        if err:
            Log.set(f"API: [{admin}] Error: Can't send results -> {err}")
        else:
            Log.set(f"API: [{admin}] {count} message{'s' if count != 1 else ''} sent to {url}")

    except Exception as err:
        error = str(err)

    if error:
        Log.set(f"API: [{admin}] parsing tg-chat '{group}'. Error: {error}")
        err = send_results(url, info=info, error=f"TG-parsing chat '{group}' Error: {error}")
        if err:
            Log.set(f"API: [{admin}] Error: Can't send error report -> {err}")

    future = asyncio.run_coroutine_threadsafe(admin.disconnect(), loop)
    result = future.result()
    return


@shared_task
def parsing_list(link: str, admin_pk: int, url: str):
    admin = User.get(admin_pk)
    if not all([link, admin, url]): return
    Log.set(f"API: [{admin}] start parsing invite-list '{link}'")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    threading.Thread(target=loop.run_forever, daemon=True).start()
    try:
        future = asyncio.run_coroutine_threadsafe(admin.connect(loop), loop)
        result = future.result()
        if not result: raise Exception(f"TG auth error")

        future = asyncio.run_coroutine_threadsafe(admin.parse_list(link), loop)
        result = future.result()
        if result["error"]: raise Exception(result["error"])
        chats = result["chats"]
#        save_json(chats, link)
        Log.set(f"API: [{admin}] from invite-link '{link}' parsed chats - {len(chats)}")
        err = send_chats(url, chats=chats)
        if err:
            Log.set(f"API: [{admin}] Error: Can't send results -> {err}")
        else:
            Log.set(f"API: [{admin}] {len(chats)} chats sent to {url}")

    except Exception as err:
        error = str(err)
        Log.set(f"API: [{admin}] parsing invite-link '{link}'. Error: {error}")
        err = send_chats(url, error=error)
        if err:
            Log.set(f"API: [{admin}] Error: Can't send error report -> {err}")

    future = asyncio.run_coroutine_threadsafe(admin.disconnect(), loop)
    result = future.result()
    return
