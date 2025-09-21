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

## Add TG_user

**Conoted1**
- phone: +38268300959
- api_id: 25096736
- api_hash: ab4b968da5404967df672d99e2862a08

**Conoted2**
- phone: +38267827026
- api_id:  24315515
- api_hash: 89a0c057532f7da3ff20fb7a1d96d58e

**Proxy:**
- socks5://username:password@host:port
- username:password@host:port (http proxy)

