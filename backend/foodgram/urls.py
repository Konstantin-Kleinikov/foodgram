"""foodgram URL Configuration"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from api.short_url_views import redirect_short_link

short_urls_v1 = [
    path(
        '<str:short_code>/',
        redirect_short_link,
        name='short-link-redirect'
    ),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('s/', include(short_urls_v1)),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
