from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

from django.contrib.auth import authenticate, login
from django.urls import reverse

from TG_client.utils import proxy_check
from accounts.models import User
from params.models import Log


def sign_in(request):
    if request.method == "POST":
        lgn = request.POST["login"]
        psw = request.POST["psw"]
        next_page = request.GET.get("next", "/user/")
        if lgn and psw:
            user = authenticate(request, username=lgn, password=psw)
            if user:
                login(request, user)
                return redirect(next_page, permanent=True)
            else:
                return render(request, "auth.html", {"message": "Invalid pair login/password!"})

    return render(request, "auth.html", {"message": "Input login and password"})


def tg_users_delete(pk_list: list):
    del_users = User.objects.filter(pk__in=pk_list)
    deleted = del_users.count()
    del_users.delete()
    Log.set(f"{deleted} TG-user(s) deleted")


@login_required
def tg_user_list(request):

    if request.method == "POST":
        if "selected_item" in request.POST:
            users = User.objects.filter(pk__in=request.POST.getlist("selected_item"))
            return render(request, "delete.html", {"name": "TG-users", "list": users})
        elif request.POST["action"] == "delete_confirm":
            tg_users_delete(request.POST.getlist("pk_list"))

    context = {
        "users": User.objects.all(),
        "lines": Log.get(0, 24),
        "menu": 1,
    }
    return render(request, "user_list.html", context)


@login_required
def tg_user_add(request):
    messages = []
    if request.method == "POST":
        user, created = User.objects.get_or_create(
            name=request.POST.get("name"),
            defaults={
                "phone": request.POST.get("phone"),
                "password": request.POST.get("password"),
                "api_id": request.POST.get("api_id"),
                "api_hash": request.POST.get("api_hash"),
                "proxy": request.POST.get("proxy"),
            }
        )
        if created:
            Log.set(f"TG-user '{user}' created")
            return HttpResponseRedirect(reverse("tg_users"))
        else:
            messages.append({"type": "w", "text": f"TG-user '{user}' already exists!"})

    return render(request, "tg_user_add.html", {"messages": messages, "menu": 1})


@login_required
def tg_user_change(request, pk):
    user = User.get(pk)
    if not user: return HttpResponseRedirect(reverse("tg_users"))

    messages = []
    if request.method == "POST":
        if "check_proxy" in request.POST:
            user.proxy = request.POST.get("proxy")
            user.save()
            ok, text = proxy_check(user.proxy)
            messages.append({"type": "i" if ok else "e", "text": text})
        else:
            name = request.POST.get("name")
            phone = request.POST.get("phone")
            password = request.POST.get("password")
            api_id = request.POST.get("api_id")
            api_hash = request.POST.get("api_hash")
            proxy = request.POST.get("proxy")
            if any([
                name != user.name,
                phone != user.phone,
                password != user.password,
                api_id != user.api_id,
                api_hash != user.api_hash,
                proxy != user.proxy,
            ]):
                if name != user.name and not User.get_by_name(name):
                    user.name = name
                user.phone = phone
                user.password = password
                user.api_id = api_id
                user.api_hash = api_hash
                user.proxy = proxy
                user.save()
                Log.set(f"TG-user '{user}' changed")
            return HttpResponseRedirect(reverse("tg_users"))

    context = {
        "user": user,
        "messages": messages,
        "menu": 1,
    }
    return render(request, "tg_user_change.html", context)
