from django.urls import path

from accounts.views import sign_in, user_list, user_add, user_change

urlpatterns = [
    path("", sign_in, name="auth"),
    path("accounts/login/", sign_in, name="login"),
    path("user/", user_list, name="tg_users"),
    path("user/add/", user_add, name="tg_add_user"),
    path("user/<int:pk>/change/", user_change, name="tg_change_user"),
]
