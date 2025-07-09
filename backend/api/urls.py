from django.urls import include, path
from rest_framework.authtoken import views

from api.views import (FoodgramUserAvatarView, FoodgramUserDetailView, FoodgramUserListCreateView,
                       FoodgramUserMeView)

urlpatterns = [
    path('auth/', include("djoser.urls.authtoken"), name='api-token-auth'),
    path('users/<int:pk>/', FoodgramUserDetailView.as_view(), name='user-detail'),
    path('users/me/', FoodgramUserMeView.as_view(), name='user-me'),
    path('users/me/avatar/', FoodgramUserAvatarView.as_view(), name='user-avatar-update'),
    path('users/', FoodgramUserListCreateView.as_view(), name='user-list-create'),
]
