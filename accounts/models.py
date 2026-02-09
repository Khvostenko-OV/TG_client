import asyncio
import json
from time import sleep
from datetime import datetime, timedelta, timezone

import socks
from django.db import models

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, UserNotParticipantError, ChannelPrivateError, PhoneCodeInvalidError
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantRequest, JoinChannelRequest
from telethon.tl.functions.chatlists import CheckChatlistInviteRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from TG_client.settings import Broker
from TG_client.utils import proxy_check, generate_device_info, sleep_bit, to_dict, message_to_dict, message_is_valid, \
    erase_file, group_to_dict
from params.models import Log, aconfirm_time


class User(models.Model):
    """ Model for TG-clients (TG-users)
    """

    name = models.CharField("Name", max_length=64, null=False)

    api_id = models.CharField("ApiId", max_length=64, default="")
    api_hash = models.CharField("ApiHash", max_length=64, default="")
    tg_id = models.CharField("TG ID", max_length=64, default="")

    phone = models.CharField("Phone", max_length=16, default="")
    password = models.CharField("Cloud Password", max_length=32, default="")
    proxy = models.CharField("Proxy", max_length=128, default="")

    session = models.TextField("Telethon Session", default="", blank=True)

    device_model = models.CharField("Device", max_length=256, default="")
    system_version = models.CharField("System ver", max_length=32, default="")
    app_version = models.CharField("App ver", max_length=4, default="")
    lang_code = models.CharField("Lang code", max_length=4, default="")
    system_lang_code = models.CharField("System lang", max_length=4, default="")

    created_at = models.DateTimeField("Created at", auto_now_add=True, null=True)

    class Meta:
        verbose_name = "TG-user"
        verbose_name_plural = "TG-users"
        ordering = ["pk"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None

    def __str__(self):
        return self.name or self.phone

    @classmethod
    def get(cls, pk):
        return cls.objects.filter(id=int(pk)).first()

    @classmethod
    def get_by_name(cls, name):
        return cls.objects.filter(name=name).first()

    @classmethod
    def get_active(cls):
        users = list(cls.objects.exclude(session=""))
        if not users: return
        users.sort(key=lambda x: x.tasks.count())
        return users[0]

    @property
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pk": self.id,
            "name": self.name,
            "api_id": self.api_id,
            "api_hash": self.api_hash,
            "tg_id": self.tg_id,
            "phone": self.phone,
            "password": self.password,
            "proxy": self.proxy,
            "session": True if self.session else False,
            "device_model": self.device_model,
            "system_version": self.system_version,
            "app_version": self.app_version,
            "lang_code": self.lang_code,
            "system_lang_code": self.system_lang_code,
            "created_at": str(self.created_at),
            "tasks": self.tasks.count(),
        }

    @property
    def proxy_to_dict(self) -> dict:
        if not self.proxy: return {}

        if "://" in self.proxy:
            proxy_type, proxy_str = self.proxy.split("://")
            proxy_type = proxy_type.lower()
        else:
            proxy_type = "http"
            proxy_str = self.proxy
        if "@" in proxy_str:
            creds, addr_port = proxy_str.split("@")
            if ":" in creds:
                username, password = creds.split(":")
            else:
                creds = username = password = None
        else:
            creds = username = password = None
            addr_port = proxy_str
        if ":" in addr_port:
            addr, port = addr_port.split(":")
        else:
            addr = addr_port
            port = ""
        types = {"socks5": socks.SOCKS5, "socks4": socks.SOCKS4, "http": socks.HTTP}
        proxy = {"proxy_type": types.get(proxy_type, socks.HTTP), "addr": addr}
        if port.isdigit():
            proxy["port"] = int(port)
        if creds:
            proxy["username"] = username
            proxy["password"] = password
        return proxy

    def proxy_check(self) -> bool:
        res, msg = proxy_check(self.proxy)
        return res

    def is_active(self) -> bool:
        return self.client.is_connected() if self.client else False

    async def async_check(self) -> bool:
        try:
            if not self.phone: raise Exception("Define phone_number!")
            if not self.api_id: raise Exception("Define api_id!")
            if not self.api_hash: raise Exception("Define api_hash!")
            # if not self.proxy: raise Exception("Define proxy!")
            if self.proxy and not self.proxy_check(): raise Exception(f"Proxy '{self.proxy}' not active!")
        except Exception as e:
            await Log.aset(f"[{self}] Check error -> {e}")
            return False
        if not self.device_model:
            info = generate_device_info()
            self.device_model = info.get("dev_model", "")
            self.system_version = info.get("sys_ver", "")
            self.app_version = info.get("app_ver", "")
            self.lang_code = info.get("lang_code", "")
            self.system_lang_code = info.get("lang_code", "")
            await self.asave()
        return True

    async def connect(self, loop: asyncio.AbstractEventLoop) -> bool:
        if self.is_active(): return True
        if not await self.async_check(): return False

        if not self.client:
            self.client = TelegramClient(
                session=StringSession(self.session or None),
                loop=loop,
                api_id=int(self.api_id),
                api_hash=self.api_hash,
                proxy=self.proxy_to_dict,
                auto_reconnect=True,
                retry_delay=60,
                connection_retries=10,
                request_retries=3,
                device_model=self.device_model,
                system_version=self.system_version,
                app_version=self.app_version,
                lang_code=self.lang_code,
                system_lang_code=self.system_lang_code,
            )

        await Log.aset(f"[{self}] Start connection")
        await self.client.connect()

        if await self.client.is_user_authorized():
            await Log.aset(f"[{self}] Authorized with session")
            return True

        self.session = ""
        await self.asave()
        await Log.aset(f"[{self}] Sending SMS request")
        await self.client.send_code_request(self.phone.strip())

        # here we need to wait confirmation code
        limit = await aconfirm_time()
        await Log.aset(f"[{self}] Waiting for confirm code {limit}s.")

        i = 0
        confirm = None
        while i < limit:
            i += 1
            confirm = Broker.get(f"Confirm_{self.id}")
            if confirm:
                i = limit
            else:
                sleep(1)

        if not confirm:
            await Log.aset(f"[{self}] No confirm code!")
            return False

        Broker.delete(f"Confirm_{self.id}")
        await Log.aset(f"[{self}] Got confirm code - {confirm}. Authorizing")
        try:
            await self.client.sign_in(phone=self.phone, code=confirm)

        except PhoneCodeInvalidError:
            await Log.aset(f"[{self}] The phone code entered was invalid!")
            return False
        except SessionPasswordNeededError:
            if not self.password:
                await Log.aset(f"[{self}] No cloud-password!")
                return False
            await Log.aset(f"[{self}] Sending cloud-password")
            await self.client.sign_in(password=self.password)

        if not await self.client.is_user_authorized():
            await Log.aset(f"[{self}] Auth error!")
#                self.client = None
            return False

        me = await self.client.get_me()
        print(f"----- Connected me={me.id}")
        sleep_bit()
        self.tg_id = str(me.id)
        self.session = self.client.session.save()
        await self.asave()
        await Log.aset(f"[{self}] Auth OK")
        return True

    async def disconnect(self):
        if self.client:
            try:
                self.session = self.client.session.save()
                await self.asave()
                await Log.aset(f"[{self}] Disconnect. Session saved")
            except Exception as e:
                await Log.aset(f"[{self}] Disconnect. Error saving session: {e}")

            await self.client.disconnect()
            self.client = None

    async def is_channel_member(self, channel) -> str:
        if not self.client: return f"Error: [{self}] - No client"

        try:
            await self.client(GetParticipantRequest(channel=channel, participant="me"))
            sleep_bit()
        except UserNotParticipantError:
            return "Not member"
        except ChannelPrivateError:
            return f"Error: [{self}] No access"
        except Exception as e:
            return f"Error: [{self}] - {e}"

        return "Member"

    async def join_channel(self, invite: str):
        if not self.client: return
        entity = None
        try:
            if invite.startswith("+"):
                result = await self.client(ImportChatInviteRequest(invite.lstrip("+")))
                entity = result.chats[0]
            else:
                entity = await self.client.get_entity(invite)
                await self.client(JoinChannelRequest(entity))
            sleep_bit()
        except Exception as e:
            await Log.aset(f"[{self}] Error: {e}")
            return

        return entity

    async def parse_channel(self, chat_id, period=0, limit=0, start=0, end=0) -> dict:
        resp = {"count": 0, "error": ""}
        count = 0
        filename = f"{chat_id}_{self.tg_id}.json"
        messages = []
        try:
            if not self.client: raise Exception(f"No connection!")
            dialogs = await self.client.get_dialogs()
            sleep_bit()
            for dlg in dialogs:
                if str(dlg.entity.id) == chat_id:
                    entity = dlg.entity
                    break
            else: raise Exception(f"Is not member of TG-group id={chat_id}")

            if period:
                since = datetime.now(timezone.utc) - timedelta(hours=period)
                till = datetime.now(timezone.utc)
            else:
                since = datetime.fromtimestamp(start, tz=timezone.utc)
                till = datetime.fromtimestamp(end, tz=timezone.utc) if end else datetime.now(timezone.utc)

            if since > till: raise Exception(f"Bad time interval for parsing {since} > {till}")

            if limit and not period and not start:
                get = await self.client.get_messages(entity, limit=min(limit, 100))
                sleep_bit()
                messages = [message_to_dict(m) for m in get if message_is_valid(m)]
                if messages:
                    resp["count"] = len(messages)
                    resp["messages"] = messages
                return resp

            stop = False
            offset = 0
            print(f"Parsing {chat_id} from {since} till {till}")
            with open(filename, "w", encoding="utf-8") as file:
                while not stop:
                    get = await self.client.get_messages(entity, limit=100, offset_id=offset)
                    sleep_bit()

                    if not get: break
                    if len(get) < 100 or get[-1].date < since:
                        stop = True

                    offset = get[-1].id
                    l = len(messages)
                    messages += [
                        message_to_dict(m)
                        for m in get
                        if (since <= m.date <= till) and message_is_valid(m)
                    ]
                    count += len(messages) - l
                    if len(messages) > 100:
                        for msg in messages:
                            file.write(json.dumps(msg) + "\n")
                        messages = []
        except Exception as err:
            resp["error"] = str(err)

        if count > 100:
            resp["filename"] = filename
        else:
            resp["messages"] = messages
            erase_file(filename)
        resp["count"] = count
        return resp

    async def parse_list(self, link: str) -> dict:
        resp = {"chats": [], "error": ""}
        try:
            if not self.client: raise Exception(f"No connection!")
            result = await self.client(CheckChatlistInviteRequest(slug=link))
            if hasattr(result, "chats"):
                resp["chats"] = [group_to_dict(chat) for chat in result.chats]
            else:
                resp["error"] = f"Cant read list of chats from '{link}'"
        except Exception as err:
            resp["error"] = str(err)

        return resp