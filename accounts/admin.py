from django.contrib import admin

from accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["pk", "name", "phone", "tg_id"]
    list_display_links = ("name",)
