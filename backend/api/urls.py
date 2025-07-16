from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (FoodgramUserAvatarViewSet, IngredientViewSet,
                       RecipeViewSet, TagViewSet)

router_v1 = DefaultRouter()
router_v1.register('tags', TagViewSet, basename='tag')
router_v1.register('ingredients', IngredientViewSet, basename='ingredient')
router_v1.register('recipes', RecipeViewSet, basename='recipe')



urlpatterns = [
    path('auth/', include("djoser.urls.authtoken"), name='api-token-auth'),
    path('users/me/avatar/', FoodgramUserAvatarViewSet.as_view(
        {'put': 'update', 'delete': 'destroy'}
    ), name='user-avatar'),
    path('', include(router_v1.urls)),
    path('', include("djoser.urls")),
]
