from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.short_url_views import redirect_short_link
from api.views import (FavoriteViewSet, FollowListViewSet, FollowView,
                       FoodgramUserAvatarViewSet, IngredientViewSet,
                       RecipeViewSet, ShoppingCartViewSet, TagViewSet)

router_v1 = DefaultRouter()
router_v1.register('ingredients', IngredientViewSet, basename='ingredient')
router_v1.register('recipes', RecipeViewSet, basename='recipe')
router_v1.register('tags', TagViewSet, basename='tag')

# Рецепты
recipe_urls_v1 = [
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

# Пользователи
user_urls_v1 = [
    path('me/avatar/',
         FoodgramUserAvatarViewSet.as_view({'put': 'update', 'delete': 'destroy'}),
         name='user-avatar'
    ),
    path('subscriptions/',
         FollowListViewSet.as_view({'get': 'list'}),
         name='subscriptions'
    ),
    path('<int:user_id>/subscribe/',
         FollowView.as_view(),
         name='subscribe'
    ),
]

urlpatterns = [
    path('auth/', include('djoser.urls.authtoken'), name='api-token-auth'),
    path('recipes/', include((recipe_urls_v1, 'recipes'))),
    path('users/', include((user_urls_v1, 'users'))),
    path('', include(router_v1.urls)),
    path('', include('djoser.urls')),
]