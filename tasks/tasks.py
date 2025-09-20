"""  Celery async tasks
"""
import asyncio
import threading

from celery import shared_task
from celery.contrib.abortable import AbortableTask

from TG_client.choices import TaskStatus
from TG_client.settings import Broker
from TG_client.utils import manage
from params.models import Log
from tasks.models import Task


@shared_task(bind=True, base=AbortableTask)
def task_run(self, task_pk):
    task = Task.get(task_pk)
    if not task:
        Log.set(f"Worker error: Task id={task_pk} not found!")
        return
    if not task.fast_check(): return
    task.errors = 0
    task.found = 0
    task.status = TaskStatus.CHECK
    task.save()
    try:
        Log.set(f"Start task '{task}'")
        Broker.set(f"Task_id_{task_pk}", self.request.id)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        threading.Thread(target=loop.run_forever, daemon=True).start()
        future = asyncio.run_coroutine_threadsafe(task.admin.connect(loop), loop)
        result = future.result()
        if not result: raise Exception("TG auth error")
        future = asyncio.run_coroutine_threadsafe(task.groups_check(), loop)
        errors = future.result()
        if errors:
            task.errors = errors
            task.save()
            raise Exception(f"Fails to connect {errors} TG-group(s)")
    except Exception as e:
        task.status = TaskStatus.DRAFT
        task.save()
        Broker.delete(f"Task_id_{task_pk}")
        Log.set(f"Checking task '{task}': {e}")
        return

    task.status = TaskStatus.RUN
    task.save()
    try:
        print("====== Start parsing")
        for group in task.groups.all():
            if self.is_aborted(): raise Exception(f"Aborted by user")
            Log.set(f"[{task.admin}] Parsing chat {group}")
            future = asyncio.run_coroutine_threadsafe(task.admin.parse_channel(group.chat_id, task.limit), loop)
            messages = future.result()
            Log.set(f"[{task.admin}] Received messages {len(messages)}")
            task.found += len(messages)
            task.save()
            for message in messages:
                manage(message)

    except Exception as e:
        task.stop(str(e))
        return

    task.finish()
    return
