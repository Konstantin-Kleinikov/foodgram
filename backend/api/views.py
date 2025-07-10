from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import (FoodgramUserAvatarSerializer,
                             FoodgramUserCreateSerializer,
                             FoodgramUserListSerializer,
                             PasswordChangeSerializer)


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
    def put(self, request):
        user = request.user
        serializer = FoodgramUserAvatarSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        user = request.user
        if user.avatar:
            default_storage.delete(user.avatar.name)
            user.avatar = None
            user.save()
        return Response({'message': 'Avatar успешно удален'}, status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            current_password = serializer.validated_data['current_password']
            new_password = serializer.validated_data['new_password']
            user = request.user
            if not user.check_password(current_password):
                return Response(
                    {'detail': 'Incorrect current password'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if new_password == current_password:
                return Response(
                    {'detail': 'New and current passwords are similar.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(new_password)
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )