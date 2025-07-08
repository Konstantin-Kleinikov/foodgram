from django.urls import path
from rest_framework.authtoken import views

from api.views import CustomObtainAuthToken, FoodgramUserCreateView

urlpatterns = [
    path('auth/token/login/', CustomObtainAuthToken.as_view(), name='api_token_auth'),
    path('users/', FoodgramUserCreateView.as_view(), name='user-create'),
]