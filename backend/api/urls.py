from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (FoodgramUserViewSet, IngredientViewSet, RecipeViewSet,
                       TagViewSet)

router = DefaultRouter()
router.register('ingredients', IngredientViewSet, basename='ingredient')
router.register('recipes', RecipeViewSet, basename='recipe')
router.register('tags', TagViewSet, basename='tag')
router.register('users', FoodgramUserViewSet, basename='user')

# Рецепты

urlpatterns = [
    path(
        'auth/',
        include('djoser.urls.authtoken'),
        name='api-token-auth'
    ),
    path('', include(router.urls)),
]
