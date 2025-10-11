import asyncio
from time import sleep

import socks
from django.db import models
from telethon.tl.functions.messages import ImportChatInviteRequest

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, UserNotParticipantError, ChannelPrivateError, PhoneCodeInvalidError
#from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantRequest, JoinChannelRequest

from TG_client.settings import Broker
from TG_client.utils import proxy_check, generate_device_info, sleep_bit
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
        print(f"....... {proxy}")
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
            if not self.proxy: raise Exception("Define proxy!")
            if not self.proxy_check(): raise Exception(f"Proxy '{self.proxy}' not active!")
        except Exception as e:
            await Log.aset(f"[{self}] Error -> {e}")
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
                session=self.api_id,
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

        if not await self.client.is_user_authorized():
            await Log.aset(f"[{self}] Sending SMS request")
            await self.client.send_code_request(self.phone.strip())

            # here we need to wait code from DB and Cloud Password from DB
            limit = await aconfirm_time()
            await Log.aset(f"[{self}] Waiting for confirm code {limit}s.")

            i = 0
            while True:
                i += 1
                if i > limit:
                    await Log.aset(f"[{self}] No confirm code!")
                    return False

                confirm = Broker.get(f"Confirm_{self.id}")
                if confirm:
                    break
                else:
                    sleep(1)

            await Log.aset(f"[{self}] Got confirm code - {confirm}. Authorizing")
            try:
                await self.client.sign_in(phone=self.phone, code=confirm)

            except PhoneCodeInvalidError:
                await Log.aset(f"[{self}] The phone code entered was invalid!")
                Broker.delete(f"Confirm_{self.id}")
                return False
            except SessionPasswordNeededError:
                if not self.password:
                    await Log.aset(f"[{self}] No cloud-password!")
                    Broker.delete(f"Confirm_{self.id}")
                    return False
                # https://github.com/AbirHasan2005/TelegramScraper/issues/7
                await Log.aset(f"[{self}] Sending cloud-password")
                await self.client.sign_in(password=self.password)

            Broker.delete(f"Confirm_{self.id}")

            if not await self.client.is_user_authorized():
                await Log.aset(f"[{self}] Auth error!")
#                self.client = None
                return False

        me = await self.client.get_me()
        print(f"----- Connected me={me.id}")
        sleep_bit()
        self.tg_id = str(me.id)
        await self.asave()
        await Log.aset(f"[{self}] Auth OK")
        return True

    async def disconnect(self):
        if self.client:
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

    async def parse_channel(self, chat_id, limit=1) -> list:
        if not self.client:
            await Log.aset(f"[{self}] No connection!")
            return []
        dialogs = await self.client.get_dialogs()
        sleep_bit()
        for dlg in dialogs:
            if str(dlg.entity.id) == chat_id:
                entity = dlg.entity
                break
        else:
            await Log.aset(f"[{self}] is not member of TG-group id={chat_id}")
            return []
        res = await self.client.get_messages(entity, limit=limit)
        sleep_bit()
        return res
