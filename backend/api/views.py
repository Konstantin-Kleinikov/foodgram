import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Prefetch, Count
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.constants import TIMEOUT_FOR_SHORT_LINK_CAСHES
from api.filters import RecipeFilter
from api.serializers import (FoodgramUserAvatarSerializer,
                             IngredientSerializer,
                             RecipeCreateUpdateSerializer,
                             RecipeDetailSerializer, RecipeListSerializer,
                             TagSerializer, FavoriteRecipeSerializer, UserFollowSerializer)
from api.utils import encode_base62
from recipes.models import Ingredient, Recipe, Tag, Favorite, Follow

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
        elif self.action == 'create' or self.action == 'partial_update':
            return RecipeCreateUpdateSerializer
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

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        try:
            # Проверяем формат ID
            if not pk.isdigit():
                return Response({'error': f'ID должен содержать только цифры, а не {pk}'}, status=status.HTTP_400_BAD_REQUEST)
            recipe = self.get_object()
            prefix = 'r-'  # префикс для безопасности
            short_code = encode_base62(recipe.id)
            base_url = request.build_absolute_uri('/')
            short_url = f"{base_url}s/{prefix}{short_code}"

            cache_key = f'recipe_short_link_{recipe.id}'
            cached_link = cache.get(cache_key)

            if not cached_link:
                cache.set(cache_key, short_url, timeout=TIMEOUT_FOR_SHORT_LINK_CAСHES)

            return Response({
                "short-link": short_url
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FavoriteViewSet(mixins.CreateModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteRecipeSerializer

    def get_queryset(self):
        return Recipe.objects.select_related('image').all()

    def create(self, request, *args, **kwargs):
        user = request.user
        recipe_id = kwargs.get('recipe_id')  # Получаем recipe_id из kwargs
        recipe = get_object_or_404(Recipe, id=recipe_id)

        # Проверка на автора рецепта
        if recipe.author == user:
            return Response({'detail': 'Нельзя подписаться на свой рецепт'},
                           status=status.HTTP_400_BAD_REQUEST)

        # Проверка на существование связи
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            return Response({'detail': 'Рецепт уже в избранном'},
                           status=status.HTTP_400_BAD_REQUEST)

        # Создание связи
        Favorite.objects.create(user=user, recipe=recipe)
        serializer = self.get_serializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        recipe_id = kwargs.get('recipe_id')  # Получаем recipe_id из kwargs
        recipe = get_object_or_404(Recipe, id=recipe_id)
        # Проверка прав доступа
        if user == recipe.author:
            return Response(
                {'detail': 'Нельзя удалять подписку на свой рецепт'},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            favorite = Favorite.objects.get(user=user, recipe=recipe)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            return Response({'detail': 'Рецепт не найден в избранном'},
                            status=status.HTTP_400_BAD_REQUEST)


class FollowViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = UserModel.objects.all()
    serializer_class = UserFollowSerializer
    #pagination_class = LimitOffsetPagination

    def get_queryset(self):
        return UserModel.objects.annotate(
            recipes_count=Count('recipes')
        ).prefetch_related('recipes')

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        user = request.user
        subscriptions = user.following.all()

        # Получаем параметры пагинации
        limit = request.query_params.get('limit')

        try:
            limit = int(limit) if limit else None
        except ValueError:
            limit = None

        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
                context={
                    'request': request,
                    'limit': limit
                }
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            subscriptions,
            many=True,
            context={
                'request': request,
                'limit': limit
            }
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def subscribe(self, request, user_id):
        user_to_follow = get_object_or_404(UserModel, id=user_id)
        if user_to_follow == request.user:
            return Response({'detail': 'Нельзя подписаться на самого себя'}, status=status.HTTP_400_BAD_REQUEST)

        if Follow.objects.filter(user=request.user, following=user_to_follow).exists():
            return Response({'detail': 'Вы уже подписаны на этого пользователя'}, status=status.HTTP_400_BAD_REQUEST)

        Follow.objects.create(user=request.user, following=user_to_follow)
        serializer = self.get_serializer(user_to_follow, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, user_id):
        user_to_follow = get_object_or_404(UserModel, id=user_id)
        follow = get_object_or_404(Follow, user=request.user, following=user_to_follow)
        follow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
