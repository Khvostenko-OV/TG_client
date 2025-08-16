import asyncio
import multiprocessing

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from TG_client.choices import TaskStatus, TASK_TODO, TaskAction
from TG_client.settings import run_async_bg
from TG_client.utils import dummy, sleep_bit
from accounts.models import User, Confirmation
from params.models import Log
from tasks.models import Task, TGgroup


@login_required
def log_view(request):

    if request.method == "POST":
        if request.POST["action"] == "delete":
            return render(request, "delete.html", {"name": "Log file", "list": [f"logs {Log.count(0)}"]})
        elif request.POST["action"] == "delete_confirm":
            Log.objects.filter(user_id=0).delete()

    return render(request, "log.html", {"lines": Log.get(), "menu": 4})


def tasks_delete(pk_list: list):
    del_task = Task.objects.filter(pk__in=pk_list)
    for task in del_task:
        task.stop()

    deleted = del_task.count()
    del_task.delete()
    Log.set(f"{deleted} tasks(s) deleted")


def task_check(task: Task):
    if not task.fast_check(): return

    task.status = TaskStatus.CHECK
    task.errors = 0
    task.found = 0
    task.save()
    Log.set(f"Start checking task '{task}'")

    run_async_bg(task.async_check())
    sleep_bit(0.6)

    # asyncio.run_coroutine_threadsafe(task.async_check, bg_loop)
    # spawn = multiprocessing.get_context("spawn")
    # process = spawn.Process(target=task.sync_check)
    # sleep_bit(3)
    # process.daemon = True
    # process.start()
    # print(f"------ Start process '{task}', pid={process.pid}")


def task_start(task: Task):
    task.start()


def task_stop(task: Task):
    task.stop()


task_action = {
    TaskStatus.DRAFT: task_check,
    TaskStatus.CHECK: dummy,
    TaskStatus.READY: task_start,
    TaskStatus.RUN: task_stop,
    TaskStatus.STOP: task_start,
    TaskStatus.FINISH: task_start,
    TaskStatus.WAIT: dummy,
}


@login_required
def task_list(request):

    if request.method == "POST":
        if "click_task" in request.POST:
            task = Task.get(request.POST.get("click_task"))
            task_action[task.status](task)
        elif "confirm" in request.POST:
            user = int(request.POST.get("confirm"))
            code = request.POST.get("confirm_code")
            if code:
                Confirmation.objects.update_or_create(user=user, defaults={"code": code})
        elif "selected_item" in request.POST:
            return render(request, "delete.html",
                          {"name": "Tasks",
                           "list": Task.objects.filter(pk__in=request.POST.getlist("selected_item"))
                           }
                          )
        elif request.POST["action"] == "delete_confirm":
            tasks_delete(request.POST.getlist("pk_list"))

    tasks = Task.objects.all().prefetch_related("admin")

    context = {
        "tasks": tasks,
        "acts": [TASK_TODO[t.status] for t in tasks],
        "lines": Log.get(0, 24),
        "menu": 3,
    }
    return render(request, "task_list.html", context)


@login_required
def task_add(request):
    messages = []
    if request.method == "POST":
        task, created = Task.objects.get_or_create(name=request.POST.get("name"))
        if created:
            task.limit = max(int(request.POST.get("limit")), 0)
            task.period = int(request.POST.get("period", 0))
            task.action = request.POST.get("action")
            if int(request.POST.get("admin_id")):
                task.admin = User.get(request.POST.get("admin_id"))
            task.save()

            for pk in request.POST.getlist("groups"):
                task.groups.add(pk)

            Log.set(f"Task '{task}' created")
            return HttpResponseRedirect(reverse("tasks"))
        else:
            messages.append({"type": "w", "text": f"Task '{task}' already exists!"})

    context = {
        "admins": User.objects.all(),
        "actions": TaskAction.LIST,
        "groups": TGgroup.objects.all(),
        "groups_in": [],
        "messages": messages,
        "menu": 3,
    }
    return render(request, "task_add.html", context)


@login_required
def task_change(request, pk):

    task = Task.get(pk)
    if not task: return HttpResponseRedirect(reverse("tasks"))

    if request.method == "POST":
        name = request.POST.get("name")
        limit = int(request.POST.get("limit", 1))
        period = int(request.POST.get("period", 0))
        action = request.POST.get("action")
        admin = User.get(request.POST["admin_id"])

        selected_groups = set([int(pk) for pk in request.POST.getlist("groups")])
        old_groups = set([gr.pk for gr in task.groups.all()])
        del_groups = old_groups - selected_groups
        new_groups = selected_groups - old_groups

        if all([name == task.name, limit == task.limit, period == task.period,
                action == task.action, admin == task.admin, not del_groups, not new_groups]
               ):
            return HttpResponseRedirect(reverse("tasks"))

        task.stop()
        if any([admin != task.admin, new_groups]):
            task.status = TaskStatus.DRAFT
        if name != task.name and not Task.get_by_name(name):
            task.name = name
        task.limit = limit
        task.period = period
        task.action = action
        task.admin = admin

        task.groups.through.objects.filter(task_id=task.pk, tggroup_id__in=del_groups).delete()
        for pk in new_groups:
            task.groups.add(pk)

        task.save()
        Log.set(f"Task '{task}' changed")
        return HttpResponseRedirect(reverse("tasks"))

    context = {
        "task": task,
        "admins": User.objects.all(),
        "actions": TaskAction.LIST,
        "admin_id": task.admin.pk if task.admin else 0,
        "groups": TGgroup.objects.all(),
        "groups_in": task.groups.all(),
        "menu": 3,
    }
    return render(request, "task_change.html", context)


def groups_delete(pk_list: list):
    del_groups = TGgroup.objects.filter(pk__in=pk_list)
    deleted = del_groups.count()
    del_groups.delete()
    Log.set(f"{deleted} group(s) deleted")


@login_required
def group_list(request):
    messages = []
    if request.method == "POST":
        if "add_group" in request.POST and request.POST["group_name"]:
            group, created = TGgroup.objects.get_or_create(name=request.POST["group_name"], )
            if created:
                Log.set(f"TG-group '{group}' created")
            else:
                messages.append({"type": "w", "text": f"TG-group '{request.POST['group_name']}' already exists!"})
        elif "selected_item" in request.POST:
            return render(request, "delete.html",
                          {"name": "Groups",
                           "list": TGgroup.objects.filter(pk__in=request.POST.getlist("selected_item"))
                           })
        elif request.POST["action"] == "delete_confirm":
            groups_delete(request.POST.getlist("pk_list"))

    context = {
        "groups": TGgroup.objects.all(),
        "messages": messages,
        "lines": Log.get(0, 24),
        "menu": 2,
    }
    return render(request, "group_list.html", context)
