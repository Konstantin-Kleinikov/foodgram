from django.urls import path

from recipes.short_url_views import redirect_short_link

urlpatterns = [
    path(
        '<str:short_code>/',
        redirect_short_link,
        name='short-link-redirect'
    ),
]
