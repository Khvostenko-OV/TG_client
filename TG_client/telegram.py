import asyncio
from asyncio import AbstractEventLoop

from telethon import events
from telethon.tl.patched import Message

from TG_client.utils import sleep_bit
from accounts.models import User
from params.models import Log


def manage(message: Message):
    sender = message.sender

    user_link = f"tg://user?id={sender.id}"
    if sender.username:
        user_link = f"@{sender.username}"

    # Get username or string: "first_name + last_name" for search in group
    username = sender.username
    if not username:
        username = " ".join([f for f in [sender.first_name, sender.last_name] if f])
    if not username:
        username = str(sender.id)

    # link to message
    if message.chat.username:
        message_link = f"https://t.me/{message.chat.username}/{message.id}"
    else:
        message_link = f"https://t.me/c/{message.chat.id}/{message.id}/"

    print("---- Receive message")
    print(f"From: {username} - {user_link}")
    print(message.raw_text)
    print()
    print(f"Link: {message_link}")


def tg_listener(user_id: int):
    user = User.get(user_id)
    if not user:
        Log.set(f"TG-client id={user_id} not found!")
        return

    Log.set(f"[{user}] Listener init")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(loop_run(user=user, loop=loop))
    except Exception as e:
        Log.set(f"[{user}] Listener has fineshed with error: {e}")


async def loop_run(user: User, loop: AbstractEventLoop):

    if not await user.connect(loop):
        return

    await Log.aset(f"[{user}] Set handler for messages")

    @user.client.on(events.NewMessage(forwards=False))
    async def handler(event: events.newmessage.NewMessage.Event):
        message: Message = event.message
        sender = message.sender
        # if not isinstance(sender, TG_User):
        #     print(f"--- Wrong type: {event}")
        #     return

        if any([sender.fake, sender.scam, sender.bot, sender.deleted, not message.raw_text]):
            # bots, fake/scam, deleted is sux
            # skip messages without raw text: suck it
            print(f"--- Skip sucks message")
            return

        manage(message)

    await Log.aset(f"[{user}] Start listening")
    await user.client.run_until_disconnected()


def tg_parser(user_id: int, groups: list[int], limit: int = 10):
    user = User.get(user_id)
    if not user:
        Log.set(f"TG-client id={user_id} not found!")
        return

    Log.set(f"[{user}] Start parsing")

    if not user.connect():
        return

    for group in set(groups):
        Log.set(f"[{user}] Parsing chat id={group}")
        sleep_bit()
        messages = asyncio.run(user.client.get_messages(group, limit=limit))
        Log.set(f"[{user}] Received messages {len(messages)}")
        for message in messages:
            manage(message)

    Log.set(f"[{user}] Parsing finished")
