from django.conf import settings
from django.http import JsonResponse
from django.urls import path, re_path

from adminpanel.site import admin_site
from api.router import api



def api_not_found(request):
    return JsonResponse({"code": "not_found", "message": "Das gibt es nicht oder es ist für dich nicht sichtbar."}, status=404)


urlpatterns = [
    path("api/", api.urls),
    re_path(r"^api/", api_not_found),
    path(f"{settings.ADMIN_PATH}/", admin_site.urls),
]
