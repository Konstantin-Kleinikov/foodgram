from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (FoodgramUserViewSet, IngredientViewSet, RecipeViewSet,
                       TagViewSet)

router = DefaultRouter()
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('tags', TagViewSet, basename='tags')
router.register('users', FoodgramUserViewSet, basename='users')

# Рецепты

urlpatterns = [
    path(
        'auth/',
        include('djoser.urls.authtoken'),
        name='api-token-auth'
    ),
    path('', include(router.urls)),
]
