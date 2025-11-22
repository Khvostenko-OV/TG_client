import json

from django.http import JsonResponse

from api.exceptions import ApiError
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

    return JsonResponse({"created": created, "name": group.name, "chat_id": group.chat_id, "title": group.title})


def group_delete(request):
    try:
        if request.method != "POST": raise ApiError("Bad method", 400)
        if request.headers.get(api_header(), "") != api_key(): raise ApiError("Authorization required", 401)
        data = json.loads(request.body)
        chat_id = data.get("chat_id", "")
        link = data.get("link", "")
        if not chat_id and not link: raise ApiError("Bad data. 'chat_id' of 'link' required", 400)
        if chat_id:
            group = TGgroup.objects.filter(chat_id=chat_id).first()
        else:
            group = TGgroup.objects.filter(name=link.split("/")[-1].strip()).first()
        if not group: raise ApiError("Group not found", 404)
        group.delete()

    except ApiError as err:
        return JsonResponse({"error": str(err)}, status=err.status)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as err:
        return JsonResponse({"error": str(err)}, status=500)

    return JsonResponse({"deleted": 1})