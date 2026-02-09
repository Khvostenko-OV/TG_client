from django.urls import path

from api.views import group_add, group_delete, group_parse, list_parse

urlpatterns = [
    path("group/add/", group_add, name="api_group_add"),
    path("group/delete/", group_delete, name="api_group_del"),
    path("group/parse/", group_parse, name="api_group_parse"),
    path("group/list/", list_parse, name="api_list_parse"),
    # path("task/add/", group_delete, name="api_task_add"),
    # path("task/delete/", group_delete, name="api_task_del"),
    # path("task/update/", group_delete, name="api_task_change"),
    # path("task/start/", group_delete, name="api_task_start"),
    # path("task/stop/", group_delete, name="api_task_del"),
]
