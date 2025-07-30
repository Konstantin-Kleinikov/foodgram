from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (FavoriteViewSet, FoodgramUserViewSet, IngredientViewSet,
                       RecipeViewSet, ShoppingCartViewSet, TagViewSet)

router = DefaultRouter()
router.register('ingredients', IngredientViewSet, basename='ingredient')
router.register('recipes', RecipeViewSet, basename='recipe')
router.register('tags', TagViewSet, basename='tag')
router.register('users', FoodgramUserViewSet, basename='user')

# Рецепты
recipe_urls = [
    path('<int:recipe_id>/favorite/',
         FavoriteViewSet.as_view({'delete': 'destroy', 'post': 'create'}),
         name='favorite'
         ),
    path('<int:pk>/shopping_cart/',
         ShoppingCartViewSet.as_view({'post': 'create', 'delete': 'destroy'}),
         name='shopping-cart'
         ),
    path('download_shopping_cart/',
         ShoppingCartViewSet.as_view({'get': 'download_xml'}),
         name='download-shopping-cart'
         ),
]

urlpatterns = [
    path('auth/', include('djoser.urls.authtoken'), name='api-token-auth'),
    path('recipes/', include((recipe_urls, 'recipes'))),
    path('', include(router.urls)),
]
