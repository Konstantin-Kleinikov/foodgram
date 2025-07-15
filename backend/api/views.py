import logging

from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.serializers import (FoodgramUserAvatarSerializer,
                             FoodgramUserCreateResponseSerializer,
                             FoodgramUserCreateSerializer,
                             FoodgramUserListSerializer, IngredientSerializer,
                             PasswordChangeSerializer, RecipeCreateSerializer,
                             RecipeDetailSerializer, RecipeListSerializer,
                             TagSerializer)
from recipes.models import Ingredient, Recipe, Tag

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    encoding='utf-8'
)
# logger = logging.getLogger(__name__)
# import olefile
# print(olefile.__version__)

UserModel = get_user_model()


class FoodgramUserViewSet(viewsets.ModelViewSet):
    queryset = UserModel.objects.all()

    def get_permissions(self):
        # Определяем разрешения в зависимости от метода
        if self.action == 'create' or self.action == 'list' or self.action == 'retrieve':
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'list':
            return FoodgramUserListSerializer
        elif self.action == 'create':
            return FoodgramUserCreateSerializer
        return FoodgramUserListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        response_serializer = FoodgramUserCreateResponseSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        return serializer.save()

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        user = request.user
        serializer = FoodgramUserListSerializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar')
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = FoodgramUserAvatarSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                if 'avatar' not in serializer.validated_data:
                    return Response(
                        {'detail': 'Файл аватара не был предоставлен'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Проверяем, что значение аватара не пустое
                if not serializer.validated_data['avatar']:
                    return Response(
                        {'avatar': 'Файл аватара не может быть пустым'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            try:
                if user.avatar:
                    logging.info(f"Попытка удалить аватар для пользователя {user.id}")
                    user.avatar.delete()
                    user.save()
                    return Response({'message': 'Avatar успешно удален'}, status=status.HTTP_204_NO_CONTENT)
                return Response({'detail': 'Аватар отсутствует'}, status=status.HTTP_204_NO_CONTENT)
            except Exception as e:
                logging.error(f"Ошибка при удалении аватара: {str(e)}")
                return Response({'detail': 'Ошибка при удалении аватара'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='set_password')
    def change_password(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            current_password = serializer.validated_data['current_password']
            new_password = serializer.validated_data['new_password']
            user = request.user
            if not user.check_password(current_password):
                return Response(
                    {'detail': 'Текущий пароль указан неверно'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if new_password == current_password:
                return Response(
                    {'detail': 'Новый и текущий пароль совпадают.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(new_password)
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )



class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = 'id'
    ordering_fields = ['name', 'id']
    ordering = ['name']
    http_method_names = ['get', 'head', 'options']
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response(response.data['results'])


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['^name']
    ordering_fields = ['name']
    filterset_fields = ['name']
    http_method_names = ['get', 'head', 'options']
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response(response.data['results'])


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter
    ]
    filterset_class = RecipeFilter

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'list':
            return RecipeListSerializer
        elif self.action == 'retrieve':
            return RecipeDetailSerializer
        elif self.action == 'create':
            return RecipeCreateSerializer
        # elif self.action == 'update' or self.action == 'partial_update':
        #     return RecipeUpdateSerializer
        return RecipeDetailSerializer

    def get_queryset(self):
        return Recipe.objects.prefetch_related(
            Prefetch('tags', queryset=Tag.objects.all()),
            Prefetch('author'),
            Prefetch('ingredients', queryset=Ingredient.objects.all())
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Проверка прав доступа
        if instance.author != request.user and not request.user.is_superuser:
            self.permission_denied(request, message="Только автор может редактировать рецепт")

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Проверка прав доступа
        if instance.author != request.user and not request.user.is_superuser:
            self.permission_denied(request, message="Только автор может удалять рецепт")

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)