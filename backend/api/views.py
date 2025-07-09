from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.serializers import (FoodgramUserAvatarSerializer, FoodgramUserCreateSerializer,
                             FoodgramUserListSerializer)
from rest_framework.views import APIView

from backend.api.serializers import FoodgramUserAvatarSerializer

UserModel = get_user_model()


class FoodgramUserListCreateView(generics.ListCreateAPIView):
    queryset = UserModel.objects.all()
    serializer_class = FoodgramUserCreateSerializer
    # permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return FoodgramUserListSerializer
        return FoodgramUserCreateSerializer


class FoodgramUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserModel.objects.all()
    serializer_class = FoodgramUserListSerializer


class FoodgramUserMeView(generics.RetrieveAPIView):
    queryset = UserModel.objects.all()
    serializer_class = FoodgramUserListSerializer

    def get_object(self):
        return self.request.user


class FoodgramUserAvatarView(APIView):
    def put(self, request, format=None):
        user = request.user
        serializer = FoodgramUserAvatarSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
