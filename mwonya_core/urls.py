from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.http import JsonResponse
from django.db import connection


from mwonya_core import  settings

schema_view = get_schema_view(
    openapi.Info(
        title="Mwonya Backend Project",
        default_version='v1',
        description="Mwonya core",
        terms_of_service="https://api.mwonya.com/terms/",
        contact=openapi.Contact(email="contact@mwonya.com"),
        license=openapi.License(name="Mwonya License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny, ],
    authentication_classes=[]
)


def health_check(request):
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "healthy"}, status=200)
    except Exception as e:
        return JsonResponse({"status": "unhealthy", "error": str(e)}, status=500)


urlpatterns = [
    path('admin/', admin.site.urls),
    # health endpoint
    path('health/', health_check, name='health_check'),

    # Swagger endpoints
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/api.json/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # local apps
    path('auth/', include('mwonya_apps.authentication.urls')),
    path('social_auth/', include(('mwonya_apps.social_auth.urls', 'social_auth'), namespace="social_auth")),

    path('creator/', include(('mwonya_apps.creator.urls', 'creator_app'), namespace="creator_app")),
    # path('streaming/', include(('mwonya_apps.streaming.urls', 'streaming_app'), namespace="streaming_app")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)