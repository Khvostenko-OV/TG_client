from django.urls import path

from accounts.views import sign_in, tg_user_list, tg_user_add, tg_user_change

urlpatterns = [
    path("", sign_in, name="auth"),
    path("accounts/login/", sign_in, name="login"),
    path("user/", tg_user_list, name="tg_users"),
    path("user/add/", tg_user_add, name="tg_add_user"),
    path("user/<int:pk>/change/", tg_user_change, name="tg_change_user"),
]
