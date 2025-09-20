from asgiref.sync import sync_to_async
from django.db import models

from TG_client.celery import app
from TG_client.choices import TaskStatus, TaskAction
from TG_client.settings import Broker
from TG_client.utils import sleep_bit, to_dict, save_json
from accounts.models import User
from params.models import Log


class TGgroup(models.Model):
    """  Model for TG-chats/channels
    """

    name = models.CharField("Name", max_length=64, null=False, unique=True)
    chat_id = models.CharField("Chat ID", max_length=64, default="")
    title = models.CharField("Title", max_length=256, default="")
    created_at = models.DateTimeField("Created at", auto_now_add=True, null=True)

    class Meta:
        verbose_name = "TGgroup"
        verbose_name_plural = "TGgroups"
        ordering = ["pk"]

    def __str__(self):
        return self.title or self.name

    @classmethod
    def get(cls, pk):
        return cls.objects.filter(id=int(pk)).first()

    @classmethod
    def get_by_id(cls, chat_id):
        return cls.objects.filter(chat_id=int(chat_id)).first()

    @classmethod
    def get_by_name(cls, name):
        return cls.objects.filter(name=name).first()


class Task(models.Model):
    """ Model for tasks
    name
    admin - TG-client
    period - frequency of parsing (hours)
    limit - how many messages get at once
    action - LISTENER or PARSER
    status - working status
    groups - TG-groups for parsing
    errors - errors during parsing
    found - total parsed messages
    """

    name = models.CharField("Task", max_length=64, null=False, unique=True)
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="tasks", verbose_name="Admin")
    groups = models.ManyToManyField(TGgroup, related_name="tasks", verbose_name="To parse")
    period = models.IntegerField("Period", default=0)
    limit = models.IntegerField("Limit", default=1)
    action: TaskAction = models.CharField(
        "Action",
        max_length=16,
        choices=TaskAction.CHOICES,
        default=TaskAction.LISTEN,
    )
    status: TaskStatus = models.CharField(
        "Status",
        max_length=16,
        choices=TaskStatus.CHOICES,
        default=TaskStatus.DRAFT,
    )
    errors = models.IntegerField("Errors counter", default=0)
    found = models.IntegerField("Messages counter", default=0)
    created_at = models.DateTimeField("Created at", auto_now_add=True, null=True)

    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ["pk"]

    def __str__(self):
        return self.name

    @classmethod
    def get(cls, pk):
        return cls.objects.filter(id=int(pk)).first()

    @classmethod
    def get_by_name(cls, name):
        return cls.objects.filter(name=name).first()

    @property
    def groups_count(self) -> int:
        return self.groups.count()

    @property
    def groups_list(self) -> list:
        return [g.chat_id for g in self.groups.all()]

    def fast_check(self) -> bool:
        if not self.admin:
            Log.set(f"Checking task '{self}'. No admin")
            return False

        if not self.groups_count:
            Log.set(f"Checking task '{self}'. No groups for parsing")
            return False
        return True

    async def groups_check(self) -> int:
        if not self.admin: raise Exception("No admin!")
        if not self.admin.client: raise Exception(f"[{self.admin}] No connection!")
        errors = 0
        print("======= Groups check")
        dialogs = await self.admin.client.get_dialogs()
        sleep_bit()
        print(f"----- Dialogs - {len(dialogs)}")
        for group in await sync_to_async(list)(self.groups.all()):
            print(f"======= Group {group}")
            for dlg in dialogs:
                if str(dlg.entity.id) == group.chat_id:
                    entity = dlg.entity
                    print(f"[{self.admin}] already member of '{group}'")
                    break
            else:
                print(f"[{self.admin}] is not member of '{group}'")
                entity = await self.admin.join_channel(group.name)
            if not entity:
                errors += 1
                await Log.aset(f"[{self.admin}] Error during connecting TG-group '{group}'")
            else:
                print(f"===== Got entity id={entity.id}")
                save_json(to_dict(entity), str(entity.id))
                if not group.chat_id or entity.title != group.title:
                    group.chat_id = str(entity.id)
                    group.title = entity.title[:256]
                    await group.asave()

        return errors

    # def start(self):
    #     if not self.fast_check(): return
    #
    #     Log.set(f"Starting task '{self}'")
    #     self.status = TaskStatus.RUN
    #     self.errors = 0
    #     self.found = 0
    #     self.save()
    #
    #     if self.action == TaskAction.PARSE:
    #         tg_parser(self.id, self.groups_list, self.limit)
    #         self.status = TaskStatus.FINISH
    #         self.save()
    #
    #     elif self.action == TaskAction.LISTEN:
    #         tg_listener(self.id)

    def stop(self, msg=""):
        self.status = TaskStatus.STOP
        self.save()
        Broker.delete(f"Task_id_{self.id}")
        Log.set(f"Task '{self}' stopped. {msg}")

    def finish(self):
        self.status = TaskStatus.FINISH
        self.save()
        Broker.delete(f"Task_id_{self.id}")
        Log.set(f"Task '{self}' finished")
