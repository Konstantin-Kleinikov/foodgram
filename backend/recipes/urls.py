from django.urls import path

from recipes.short_url_views import redirect_short_link

urlpatterns = [
    path(
        '<int:recipe_id>/',
        redirect_short_link,
        name='short-link-redirect'
    ),
]
