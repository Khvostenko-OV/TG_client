"""  Celery async tasks
"""
import asyncio
import threading

from celery import shared_task
from celery.contrib.abortable import AbortableTask

from TG_client.choices import TaskStatus
from TG_client.settings import Broker
from TG_client.utils import send_results
from params.models import Log
from tasks.models import Task


@shared_task(bind=True, base=AbortableTask)
def task_run(self, task_pk):
    task = Task.get(task_pk)
    if not task:
        Log.set(f"Worker error: Task id={task_pk} not found!")
        return
    if not task.fast_check(): return
    Broker.set(f"Task_id_{task_pk}", self.request.id)
    try:
        check = task.status == TaskStatus.DRAFT
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        threading.Thread(target=loop.run_forever, daemon=True).start()
        future = asyncio.run_coroutine_threadsafe(task.admin.connect(loop), loop)
        task.status = TaskStatus.WAIT
        task.save()
        result = future.result()
        if not result: raise Exception("TG auth error")
        if check:
            if self.is_aborted(): return
            task.status = TaskStatus.CHECK
            task.save()
            future = asyncio.run_coroutine_threadsafe(task.groups_check(), loop)
            errors = future.result()
            if errors:
                task.errors += errors
                task.save()
                Log.set(f"({task}) Error: Fails to connect {errors} TG-group(s)")
    except Exception as err:
        task.status = TaskStatus.DRAFT
        task.save()
        Broker.delete(f"Task_id_{task_pk}")
        Log.set(f"({task}) Error: {err}")
#        loop.close()
        return

    if self.is_aborted(): return
    task.status = TaskStatus.RUN
    task.save()
    try:
        for group in task.groups.all():
            if self.is_aborted(): break
            if not group.chat_id:
                Log.set(f"({task}]) Error: TG-group '{group}' has no chat_id")
                task.errors += 1
                task.save()
                continue
            Log.set(f"[{task.admin}] Parsing chat '{group}'")
            future = asyncio.run_coroutine_threadsafe(task.admin.parse_channel(group.chat_id, task.period, task.limit), loop)
            messages = future.result()
            Log.set(f"[{task.admin}] Received messages - {len(messages)}")
            if messages:
                task.found += len(messages)
                task.save()
                res = send_results(messages, task.url)
                if res:
                    Log.set(f"({task}) Error: [{task.admin}] Can't send results -> {res}")
                    task.errors += 1
                    task.save()
                else:
                    Log.set(f"[{task.admin}] {len(messages)} message{'s' if len(messages) > 1 else ''} sent to {task.url}")

    except Exception as err:
        task.errors += 1
        task.save()
        Log.set(f"({task}) Error: {err}")

    Broker.delete(f"Task_id_{task_pk}")
    if not task.period:
        task.finish()
    future = asyncio.run_coroutine_threadsafe(task.admin.disconnect(), loop)
    result = future.result()
#    loop.close()
