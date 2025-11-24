import asyncio
import threading

from celery import shared_task

from TG_client.utils import send_results
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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    threading.Thread(target=loop.run_forever, daemon=True).start()
    try:
        future = asyncio.run_coroutine_threadsafe(admin.connect(loop), loop)
        result = future.result()
        if not result: raise Exception(f"TG auth error")
        future = asyncio.run_coroutine_threadsafe(group.admin_check(admin), loop)
        result = future.result()
        if not result: raise Exception(f"Can't connect TG-group '{group}'")

        future = asyncio.run_coroutine_threadsafe(admin.parse_channel(group.chat_id, start=start, end=end), loop)
        result = future.result()
        count = result['count']
        error = result["error"]
        if error:
            Log.set(f"API: [{admin}] Error: {error}")
            error = f"TG-parsing chat '{group}' error: " + error
        Log.set(f"API: [{admin}] parsed messages - {count}")
        if count > 100:
            res = send_results(url, filename=result["filename"], error=error)
        else:
            res = send_results(url, messages=result["messages"], error=error)
        if res: raise Exception(f"Can't send results -> {res}")
        else:
            Log.set(f"API: [{admin}] {count} message(s) sent to {url}")

    except Exception as err:
        Log.set(f"API: [{admin}] Error: {err}")

    future = asyncio.run_coroutine_threadsafe(admin.disconnect(), loop)
    result = future.result()
    return
