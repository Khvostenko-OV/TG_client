from django.contrib import admin

from params.models import Parameter, Log


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ["pk", "name", "value"]
    list_display_links = ("name",)


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ["pk", "stream", "text"]
    list_display_links = ("text",)
