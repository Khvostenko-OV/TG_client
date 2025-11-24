import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from accounts.models import User
from api.exceptions import ApiError
from api.tasks import parsing_group
from params.models import api_header, api_key
from tasks.models import TGgroup


def group_add(request):
    try:
        if request.method != "POST": raise ApiError("Bad method", 400)
        if request.headers.get(api_header(), "") != api_key(): raise ApiError("Authorization required", 401)
        data = json.loads(request.body)
        chat_id = data.get("chat_id", "")
        link = data.get("link", "")
        if not chat_id and not link: raise ApiError("Bad data. 'chat_id' of 'link' required", 400)
        if chat_id:
            group, created = TGgroup.objects.get_or_create(name=chat_id, chat_id=chat_id)
        else:
            group, created = TGgroup.objects.get_or_create(name=link.split("/")[-1].strip())

    except ApiError as err:
        return JsonResponse({"error": str(err)}, status=err.status)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as err:
        return JsonResponse({"error": str(err)}, status=500)

    return JsonResponse({"created": created, "chat_name": group.name, "chat_id": group.chat_id, "title": group.title})


def group_delete(request):
    try:
        if request.method != "POST": raise ApiError("Bad method", 400)
        if request.headers.get(api_header(), "") != api_key(): raise ApiError("Authorization required", 401)
        data = json.loads(request.body)
        chat_id = data.get("chat_id", "")
        link = data.get("link", "")
        if not chat_id and not link: raise ApiError("Bad data. 'chat_id' of 'link' required", 400)
        if chat_id:
            group = TGgroup.get_by_id(chat_id)
        else:
            group = TGgroup.get_by_name(link.split("/")[-1].strip())
        if not group: raise ApiError("Group not found", 404)
        group.delete()

    except ApiError as err:
        return JsonResponse({"error": str(err)}, status=err.status)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as err:
        return JsonResponse({"error": str(err)}, status=500)

    return JsonResponse({"deleted": 1})


@csrf_exempt
def group_parse(request):
    try:
        if request.method != "POST": raise ApiError("Bad method", 400)
        if request.headers.get(api_header(), "") != api_key(): raise ApiError("Authorization required", 401)
        data = json.loads(request.body)
        chat_id = data.get("chat_id", "")
        link = data.get("link", "")
        if not chat_id and not link: raise ApiError("Bad data. 'chat_id' of 'link' required", 400)
        url = data.get("send_result", "")
        if not url: raise ApiError("Bad data. 'send_result' url required", 400)
        start = int(data.get("start_time", "0"))
        end = int(data.get("end_time", "0"))
        if end and start > end: raise ApiError("Bad data. 'start_time' > 'end_time'", 400)
        admin = User.get_active()
        if admin is None: raise ApiError("No active tg-user found")
        if link:
            group, created = TGgroup.objects.get_or_create(name=link.split("/")[-1].strip(), defaults={"chat_id": chat_id})
        else:
            group = TGgroup.get_by_id(chat_id)
        if not group: raise ApiError(f"Group '{chat_id}' not found", 404)
        parsing_group.delay(group.id, admin.id, url, start, end)

    except ApiError as err:
        return JsonResponse({"error": str(err)}, headers={api_header(): api_key()}, status=err.status)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, headers={api_header(): api_key()}, status=400)
    except Exception as err:
        return JsonResponse({"error": str(err)}, headers={api_header(): api_key()}, status=500)

    return JsonResponse(
        {
        "task": "parsing",
        "chat_name": group.name,
        "chat_id": group.chat_id,
        "tg_user": str(admin)
        },
        headers={api_header(): api_key()}
    )
