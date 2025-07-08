from django.contrib.auth import get_user_model
from rest_framework import generics
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import CustomAuthTokenSerializer
from api.serializers import FoodgramUserCreateSerializer


UserModel = get_user_model()


class FoodgramUserCreateView(generics.CreateAPIView):
    queryset = UserModel.objects.all()
    serializer_class = FoodgramUserCreateSerializer
    permission_classes = [AllowAny]


class CustomObtainAuthToken(APIView):
    serializer_class = CustomAuthTokenSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({'auth_token': token.key})
