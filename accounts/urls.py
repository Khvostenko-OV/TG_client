from django.urls import path

from accounts.views import sign_in, user_list, user_add, user_change

urlpatterns = [
    path("", sign_in, name="auth"),
    path("accounts/login/", sign_in, name="login"),
    path("user/", user_list, name="users"),
    path("user/add/", user_add, name="add_user"),
    path("user/<int:pk>/change/", user_change, name="change_user"),
]
