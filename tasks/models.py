import asyncio

from asgiref.sync import sync_to_async
from django.db import models
from telethon.tl.functions.channels import JoinChannelRequest

from TG_client.choices import TaskStatus, TaskAction
from TG_client.settings import bg_loop
from TG_client.telegram import tg_parser, tg_listener
from TG_client.utils import sleep_bit
from accounts.models import User
from params.models import Log


class TGgroup(models.Model):
    """  Model for TG-chats/channels
    """

    name = models.CharField("Name", max_length=64,null=False, unique=True)
    chat_id = models.IntegerField("Chat ID", default=0)
    chat_link = models.CharField("Link", max_length=256, blank=True)
    created_at = models.DateTimeField("Created at", auto_now_add=True, null=True)

    class Meta:
        verbose_name = "TGgroup"
        verbose_name_plural = "TGgroups"
        ordering = ["pk"]

    def __str__(self):
        return self.name

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
#    channel = models.ForeignKey(VKgroup, on_delete=models.SET_NULL, null=True, related_name="senders", verbose_name="Send to")
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
            Log.set(f"Check task '{self}'. No admin")
            return False

        if not self.groups_count:
            Log.set(f"Check task '{self}'. No groups for parsing")
            return False
        return True

    async def async_check(self):
        try:
            if not self.admin:
                raise Exception("No admin")
            if not self.admin.password:
                print("------------------")
                raise Exception("No password")
            if not await self.admin.connect(bg_loop):
                raise Exception("TG auth error")

            sleep_bit()
            for group in await sync_to_async(list)(self.groups.all()):
                if not group.chat_id:
                    entity = await self.admin.client.get_entity(group.name)
                    sleep_bit()
                    group.chat_id = entity.id
                    if entity.username:
                        group.chat_link = f"https://t.me/{entity.username}/"
                    else:
                        group.chat_link = f"https://t.me/c/{entity.id}/"
                    await group.asave()
                res = await self.admin.is_channel_member(group.chat_id)
                sleep_bit()
                if res == "Not member":
                    await self.admin.client(JoinChannelRequest(channel=group.name))
                    sleep_bit()
                elif "Error" in res:
                    raise Exception(res)

            self.status = TaskStatus.READY
            await self.asave()
            await Log.aset(f"Checking task '{self}' finished - OK")
        except Exception as e:
            print("++++++++++++")
            self.status = TaskStatus.DRAFT
            self.errors = 1
            await self.asave()
            await Log.aset(f"Error during async check task '{self}': {e}")

    def start(self):
        if not self.fast_check(): return

        Log.set(f"Starting task '{self}'")
        self.status = TaskStatus.RUN
        self.errors = 0
        self.found = 0
        self.save()

        if self.action == TaskAction.PARSE:
            tg_parser(self.id, self.groups_list, self.limit)
            self.status = TaskStatus.FINISH
            self.save()

        elif self.action == TaskAction.LISTEN:
            tg_listener(self.id)

    def stop(self):
        if self.status in [TaskStatus.CHECK, TaskStatus.RUN]:
            if self.admin:
                self.admin.disconnect()
            self.status = TaskStatus.STOP
            self.save()
            Log.set(f"Task '{self}' stopped. Errors - {self.errors}")
