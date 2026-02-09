# Parsing Telegram groups

## Run Application

```bash
git clone https://github.com/Khvostenko-OV/TG_client.git
cd TG_client
docker-compose pull
docker-compose up -d
```

- After startup nginx will be running on port **9999**

## Create admin user

```bash
docker exec -it tg_backend bash
> python manage.py createsuperuser
input username & password (email can be skipped)
> exit
```

## Add TG-user

**Credentials:**
- phone number
- api_id
- api_hash

**Proxy format:**
- SOCKS5: socks5://username:password@host:port
- HTTP: username:password@host:port

## Add TG-groups

Add TG-chats/channels. Enter invite-link or channel's name

## Create task

**Parameters:**
- *admin* - TG-user
- *period* - frequency of parsing (hours). If 0 parses once *limit* last messages
- *limit* - how many messages get at once (only works when period=0)
- *endpoint* - endpoint to send results (requests.post)
- *action* - LISTENER or PARSER (doesn't work for now)
- *groups* - list of TG-chats for parsing

## Parsing

After starting parser enter confirmation code (once for each TG-user)

# API

## Group parsing: /api/group/parse/  : POST

headers: 
key: X-API-key  | value: api key

body (JSON):
{
    link: invite-link or chat-name
    chat_id: TG chat_id
    send_result: url to send results of parsing
    start_time:
    end_time:
}

**Response (JSON):**
{
    info: chat-info json
    count: total number of messages
    messages: 0-100 chat-messages
    chunk: number of posting
    error: error if any
    uid: uid of task
}


## Invite-list parsing: /api/group/list/  : POST

headers: 
key: X-API-key  | value: api key

body (JSON):
{
    link: link to Telegram invite-list
    send_result: url to send results of parsing
}

**Response (JSON):**
{
    chats: list of chat-info jsons
    error: error if any
    uid: uid of task
}


