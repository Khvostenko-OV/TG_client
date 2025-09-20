from django.contrib import admin

from tasks.models import TGgroup, Task


@admin.register(TGgroup)
class GroupAdmin(admin.ModelAdmin):
    list_display = ["pk", "name", "chat_id", "title"]
    list_display_links = ("name",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["pk", "name", "admin", "action", "status"]
    list_display_links = ("name",)
