import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (filters, generics, mixins, permissions, status,
                            viewsets)
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.serializers import (FavoriteRecipeSerializer,
                             FoodgramUserAvatarSerializer,
                             IngredientSerializer,
                             RecipeCreateUpdateSerializer,
                             RecipeDetailSerializer, RecipeListSerializer,
                             RecipeShortSerializer, ShoppingCartSerializer,
                             TagSerializer, UserFollowSerializer,
                             UserFollowUpdateSerializer)
from api.utils import create_shopping_cart_xml, encode_base62
from recipes.constants import TIMEOUT_FOR_SHORT_LINK_CAСHES
from recipes.models import (Favorite, Follow, Ingredient, Recipe, ShoppingCart,
                            Tag)

logger = logging.getLogger(__name__)

UserModel = get_user_model()


class FoodgramUserAvatarViewSet(mixins.UpdateModelMixin,
                                mixins.DestroyModelMixin,
                                viewsets.GenericViewSet):
    queryset = UserModel.objects.all()
    serializer_class = FoodgramUserAvatarSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True
        )

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
            # if hasattr(instance, 'remove_avatar'):
            #     avatar_deleted = instance.remove_avatar()
            #     if avatar_deleted:
            #         return Response(status=status.HTTP_204_NO_CONTENT)
            if instance.avatar:
                instance.avatar.delete()  # Удаляем файл аватара
            instance.avatar = None  # Очищаем поле в базе данных
            instance.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error('Ошибка при удалении аватара для '
                         f'пользователя {instance.id}: {str(e)}')
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
        if self.request.user.is_superuser:
            return [permissions.AllowAny()]
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        if instance.author != request.user and not request.user.is_superuser:
            self.permission_denied(
                request,
                message='Только автор может редактировать рецепт'
            )

        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.author != request.user and not request.user.is_superuser:
            self.permission_denied(
                request, message='Только автор может удалять рецепт'
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        try:
            if not pk.isdigit():
                return Response(
                    {'error': 'ID должен содержать только цифры, '
                              f'а не {pk}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            recipe = self.get_object()
            prefix = 'r-'  # префикс для безопасности
            short_code = encode_base62(recipe.id)
            base_url = request.build_absolute_uri('/')
            short_url = f'{base_url}s/{prefix}{short_code}'

            cache_key = f'recipe_short_link_{recipe.id}'
            cached_link = cache.get(cache_key)

            if not cached_link:
                cache.set(
                    cache_key,
                    short_url,
                    timeout=TIMEOUT_FOR_SHORT_LINK_CAСHES
                )

            return Response(
                {'short-link': short_url},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

        if recipe.author == user:
            return Response(
                {'detail': 'Нельзя подписаться на свой рецепт'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {'detail': 'Рецепт уже в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            favorite = Favorite.objects.get(user=user, recipe=recipe)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            return Response({'detail': 'Рецепт не найден в избранном'},
                            status=status.HTTP_400_BAD_REQUEST)


class FollowListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Получение списка всех подписок на пользователей."""

    serializer_class = UserFollowSerializer

    def get_queryset(self):
        return UserModel.objects.filter(following__user=self.request.user)


class FollowView(generics.GenericAPIView):
    serializer_class = UserFollowUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        author = get_object_or_404(UserModel, id=user_id)

        serializer = self.get_serializer(
            data={
                'user': request.user.id,  # Добавляем ID текущего пользователя
                'following': author.id
            },
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        following_user = get_object_or_404(UserModel, id=user_id)
        try:
            follow = Follow.objects.get(
                user=request.user,
                following_id=following_user
            )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Follow.DoesNotExist:
            return Response(
                {'detail': 'Подписка не найдена'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ShoppingCartViewSet(mixins.CreateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    serializer_class = ShoppingCartSerializer
    permission_classes = [IsAuthenticated]
    queryset = ShoppingCart.objects.all()

    def get_queryset(self):
        return ShoppingCart.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Получаем ID рецепта из запроса
        recipe_id = kwargs.get('pk')
        if not recipe_id:
            return Response(
                {'detail': 'ID рецепта не указан'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем существование рецепта
        recipe = get_object_or_404(Recipe, id=recipe_id)

        try:
            # Проверяем, существует ли уже такая запись
            if ShoppingCart.objects.filter(
                    user=request.user, recipe=recipe
            ).exists():
                return Response(
                    {'detail': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Создаем запись в корзине
            ShoppingCart.objects.create(
                user=request.user,
                recipe=recipe
            )
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Ошибка при добавлении в корзину: {str(e)}")
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='download-xml')
    def download_xml(self, request):
        try:
            # Собираем все ингредиенты из корзины
            ingredients = {}
            carts = ShoppingCart.objects.filter(user=request.user)

            for cart in carts:
                for ingredient in cart.recipe.amount_ingredients.all():
                    # Используем объект Ingredient вместо строки
                    ingredient_obj = ingredient.ingredient
                    amount = ingredient.amount

                    # Формируем ключ как кортеж (объект Ingredient, количество)
                    if ingredient_obj not in ingredients:
                        ingredients[ingredient_obj] = amount
                    else:
                        ingredients[ingredient_obj] += amount

            # Создаем XML
            xml_content = create_shopping_cart_xml(request.user, ingredients)

            response = HttpResponse(
                xml_content,
                content_type='application/xml; charset=utf-8'
            )
            response['Content-Disposition'] = ('attachment; '
                                               'filename="shopping_cart.xml"'
                                               )
            return response
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        if not recipe_id:
            return Response(
                {'detail': 'ID рецепта не указан'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Проверяем существование рецепта
        recipe = get_object_or_404(Recipe, id=recipe_id)
        try:
            # Одно обращение к базе данных для проверки существования
            cart_item = ShoppingCart.objects.get(
                user=request.user,
                recipe_id=recipe
            )
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ShoppingCart.DoesNotExist:
            return Response(
                {'detail': 'Рецепт не найден в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PublicRecipeDetailView(View):
    def get(self, request, pk):
        try:
            get_object_or_404(Recipe, id=pk)
            return HttpResponseRedirect(f'/recipes/{pk}/')
        except ObjectDoesNotExist:
            logger.error(f"Рецепт с ID {pk} не найден")
            return HttpResponseRedirect('/404/')
