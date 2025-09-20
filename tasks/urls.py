from django.urls import path

from tasks.views import task_list, task_add, task_change, group_list, log_view

urlpatterns = [
    path("task/", task_list, name="tasks"),
    path("task/<int:pk>/change/", task_change, name="change_task"),
    path("task/add/", task_add, name="add_task"),
    path("group/", group_list, name="groups"),
    path("log/", log_view, name="log"),
]