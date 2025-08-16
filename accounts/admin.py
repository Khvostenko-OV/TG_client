from django.contrib import admin

from accounts.models import User, Confirmation


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["pk", "name", "phone", "tg_id"]
    list_display_links = ("name",)


@admin.register(Confirmation)
class ConfirmAdmin(admin.ModelAdmin):
    list_display = ["pk", "user", "code"]
    list_display_links = ("user",)
