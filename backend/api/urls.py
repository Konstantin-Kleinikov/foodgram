from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.short_url_views import redirect_short_link
from api.views import (FoodgramUserAvatarViewSet, IngredientViewSet,
                       RecipeViewSet, TagViewSet, FavoriteViewSet, FollowViewSet)

router_v1 = DefaultRouter()
router_v1.register('tags', TagViewSet, basename='tag')
router_v1.register('ingredients', IngredientViewSet, basename='ingredient')
router_v1.register('recipes', RecipeViewSet, basename='recipe')
follow_urls = [
    path(
        'subscriptions/',
        FollowViewSet.as_view({'get': 'subscriptions'}),
        name='subscriptions'
    ),
    path(
        '<int:user_id>/subscribe/',
        FollowViewSet.as_view({
            'post': 'subscribe',
            'delete': 'unsubscribe'
        }),
        name='subscribe'
    )
]

urlpatterns = [
    path('auth/', include("djoser.urls.authtoken"), name='api-token-auth'),
    path('users/me/avatar/', FoodgramUserAvatarViewSet.as_view(
        {'put': 'update', 'delete': 'destroy'}
    ), name='user-avatar'),
    path('s/<str:short_code>/', redirect_short_link, name='short-link-redirect'),
    path('recipes/<int:recipe_id>/favorite/',
         FavoriteViewSet.as_view({'delete': 'destroy', 'post': 'create'}),
         name='favorite'
         ),
    path('users/', include(follow_urls)),
    path('', include(router_v1.urls)),
    path('', include("djoser.urls")),
]
