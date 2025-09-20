from django.db import models

from TG_client.settings import CONFIRM_TIME


class Log(models.Model):
    """ Model for logs stored in DB
    """

    text = models.TextField("Text", default="")
    stream = models.IntegerField("Stream", default=0)
    created_at = models.DateTimeField("Created at", auto_now_add=True, null=True)

    class Meta:
        verbose_name = "Log"
        verbose_name_plural = "Logs"
        ordering = ["-pk"]

    def __str__(self):
        return str(self.created_at)[:19] + f": {self.text}"

    @classmethod
    def set(cls, text: str, stream=0):
        print(f"--Logger: {text}")
        cls.objects.create(text=text, stream=int(stream))

    @classmethod
    async def aset(cls, text: str, stream=0):
        print(f"--Logger: {text}")
        await cls.objects.acreate(text=text, stream=int(stream))

    @classmethod
    def get(cls, stream=0, limit=0, offset=0) -> list:
        return list(cls.objects.filter(stream=int(stream))[offset: offset+limit if limit else None])

    @classmethod
    def count(cls, stream=0) -> int:
        return cls.objects.filter(stream=int(stream)).count()


class Parameter(models.Model):
    """ Models for global parameters stored in DB
    """

    name = models.CharField("Parameter", max_length=64, unique=True)
    value = models.CharField("Value", max_length=2048, default="")
    created_at = models.DateTimeField("Created at", auto_now_add=True, null=True)
    updated_at = models.DateTimeField("Updated at", auto_now=True, null=True)

    class Meta:
        verbose_name = "Parameter"
        verbose_name_plural = "Parameters"

    def __str__(self):
        return f"{self.name}: {self.value}"

    @classmethod
    def get(cls, name: str):
        if not name: return
        param = Parameter.objects.filter(name=name).first()
        return param.value if param else None


def confirm_time(secs=None) -> int:
    if secs is None:
        param, created = Parameter.objects.get_or_create(name="CONFIRM_TIME", defaults={"value": str(CONFIRM_TIME)})
    else:
        param, created = Parameter.objects.update_or_create(name="CONFIRM_TIME", defaults={"value": str(secs)})
    return int(param.value)


async def aconfirm_time(secs=None) -> int:
    if secs is None:
        param, created = await Parameter.objects.aget_or_create(name="CONFIRM_TIME", defaults={"value": str(CONFIRM_TIME)})
    else:
        param, created = await Parameter.objects.aupdate_or_create(name="CONFIRM_TIME", defaults={"value": str(secs)})
    return int(param.value)
