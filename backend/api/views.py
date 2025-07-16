import logging

from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.serializers import (FoodgramUserAvatarSerializer,
                             IngredientSerializer, RecipeCreateSerializer,
                             RecipeDetailSerializer, RecipeListSerializer,
                             TagSerializer)
from recipes.models import Ingredient, Recipe, Tag

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    encoding='utf-8'
)

UserModel = get_user_model()


class FoodgramUserAvatarViewSet(mixins.UpdateModelMixin,
                                mixins.DestroyModelMixin,
                                viewsets.GenericViewSet):
    queryset = UserModel.objects.all()
    serializer_class = FoodgramUserAvatarSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Возвращаем текущего авторизованного пользователя
        return self.request.user

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            if 'avatar' not in serializer.validated_data:
                return Response(
                    {'detail': 'Файл аватара не был предоставлен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not serializer.validated_data['avatar']:
                return Response(
                    {'avatar': 'Файл аватара не может быть пустым'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            # Здесь обрабатываем удаление только аватара
            if hasattr(instance, 'remove_avatar'):
                avatar_deleted = instance.remove_avatar()
                if avatar_deleted:
                    return Response(status=status.HTTP_204_NO_CONTENT)

            # Если метод remove_avatar не существует или вернул False
            instance.avatar.delete()  # Удаляем файл аватара
            instance.avatar = None  # Очищаем поле в базе данных
            instance.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logging.error(f"Ошибка при удалении аватара для пользователя {instance.id}: {str(e)}")
            return Response(
                {'detail': 'Ошибка при удалении аватара'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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