import io
import logging
import os

from django.contrib.auth import get_user_model
from django.db.models import Prefetch, Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from dotenv import load_dotenv
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.permissions import IsAdminAuthorOrReadOnly
from api.serializers import (CustomPasswordSerializer,
                             CustomUserCreateSerializer,
                             FoodgramUserAvatarSerializer,
                             FoodgramUserSerializer, IngredientSerializer,
                             RecipeCreateUpdateSerializer, RecipeSerializer,
                             RecipeShortSerializer, TagSerializer,
                             UserFollowSerializer)
from recipes.models import (Favorite, Follow, Ingredient, IngredientRecipe,
                            Recipe, ShoppingCart, Tag)

load_dotenv()
EXPORT_FORMAT = os.getenv('SHOPPING_CART_EXPORT_FORMAT', 'txt')

logger = logging.getLogger(__name__)

UserModel = get_user_model()


class FoodgramUserViewSet(DjoserUserViewSet):
    queryset = UserModel.objects.all()
    permission_classes = [AllowAny]  # Для создания пользователя

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        elif self.action in [
            'me',
            'set_password',
            'avatar',
            'subscriptions',
            'subscribe'
        ]:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomUserCreateSerializer
        elif self.action == 'set_password':
            return CustomPasswordSerializer
        return FoodgramUserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)

        # Формируем ответ для POST запроса
        response_data = {
            'email': user.email,
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        return serializer.save()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(["post"], detail=False)
    def set_password(self, request):
        serializer = self.get_serializer(
            request.user,
            data=request.data,
            context={'request': request}
        )

        try:
            if not serializer.is_valid():
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as ex:
            # Собираем детальную информацию об ошибке
            error_details = {
                'detail': str(ex),
                'errors': getattr(ex, 'detail', {})
            }
            return Response(
                error_details,
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(["get"], detail=False, url_path="me")
    def me(self, request):
        if not request.user.is_authenticated:
            raise PermissionDenied('Authentication credentials were '
                                   'not provided')

        serializer = self.get_serializer(request.user)
        try:
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar')
    def avatar(self, request):
        """
        Управление аватаром пользователя
        """
        user = request.user
        if request.method == 'PUT':
            serializer = FoodgramUserAvatarSerializer(user, data=request.data)
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
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        elif request.method == 'DELETE':
            user.avatar.delete()
            return Response(status=204)
        return Response(status=405)

    @action(detail=False, methods=['get'], url_path='subscriptions')
    def subscriptions(self, request):
        """
        Список подписок текущего пользователя
        """
        user = request.user
        subscriptions = UserModel.objects.filter(
            pk__in=Follow.objects
            .filter(user=request.user)
            .values_list('following__id', flat=True)
        )
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = UserFollowSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = UserFollowSerializer(
            subscriptions,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe')
    def subscribe(self, request, id=None):
        """
        Управление подпиской на пользователя
        """
        user = get_object_or_404(UserModel, id=id)
        if user == request.user:
            return Response(
                {'detail': 'Нельзя подписаться на себя'},
                status=400
            )

        if request.method == 'POST':
            if Follow.objects.filter(
                    user=request.user,
                    following=user
            ).exists():
                return Response({'detail': 'Уже подписаны'}, status=400)
            Follow.objects.create(user=request.user, following=user)
            serializer = UserFollowSerializer(
                user,
                context={'request': request}
            )
            return Response(serializer.data, status=201)

        if request.method == 'DELETE':
            try:
                follow = Follow.objects.get(
                    user=request.user,
                    following=user
                )
                follow.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Follow.DoesNotExist:
                return Response(
                    {'detail': 'Подписка не существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = 'id'
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['^name']
    ordering_fields = ['name']
    filterset_fields = ['name']
    permission_classes = [AllowAny]
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter
    ]
    filterset_class = RecipeFilter
    permission_classes = (IsAdminAuthorOrReadOnly,)
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if (self.action == 'create'
                or self.action == 'partial_update'):
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

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

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        # Генерируем короткий код
        short_code = str(recipe.id)

        # Формируем URL через reverse
        short_url = reverse(
            'short-link-redirect',
            kwargs={'short_code': short_code}
        )

        # Добавляем полный URL с доменом
        full_short_url = request.build_absolute_uri(short_url)

        return Response(
            {'short-link': full_short_url},
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
    )
    def favorite(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        if user == recipe.author:
            return Response(
                {'detail': 'Нельзя добавлять/удалять свой рецепт '
                           'из избранного'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'POST':
            # Добавление в избранное
            favorite, created = Favorite.objects.get_or_create(
                user=user,
                recipe=recipe
            )
            if not created:
                return Response(
                    {'detail': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            data = {
                'id': recipe.id,
                'name': recipe.name,
                'image': recipe.image.url if recipe.image else None,
                'cooking_time': recipe.cooking_time
            }
            return Response(data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            # Удаление из избранного
            try:
                favorite = Favorite.objects.get(
                    user=user,
                    recipe=recipe
                )
                favorite.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Favorite.DoesNotExist:
                return Response(
                    {'detail': 'Рецепт не найден в избранном'},
                    status=status.HTTP_404_NOT_FOUND
                )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        try:
            if request.method == 'POST':
                if ShoppingCart.objects.filter(
                        user=user, recipe=recipe
                ).exists():
                    return Response(
                        {'detail': 'Рецепт уже в списке покупок'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                ShoppingCart.objects.create(
                    user=user,
                    recipe=recipe
                )
                serializer = RecipeShortSerializer(recipe)
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED
                )

            elif request.method == 'DELETE':
                try:
                    cart_item = ShoppingCart.objects.get(
                        user=user,
                        recipe=recipe
                    )
                    cart_item.delete()
                    return Response(status=status.HTTP_204_NO_CONTENT)

                except ShoppingCart.DoesNotExist:
                    # Возвращаем корректный статус 400 при отсутствии элемента
                    return Response(
                        {'detail': 'Рецепт не найден в списке покупок'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        except Exception as e:
            logger.error(f"Ошибка при работе со списком покупок: {str(e)}")
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        try:
            user = request.user
            recipes = Recipe.objects.filter(
                carts__user=user
            )

            ingredients = IngredientRecipe.objects.filter(
                recipe__in=recipes
            ).values(
                'ingredient__name',
                'ingredient__measurement_unit'
            ).annotate(
                total_amount=Sum('amount')
            ).order_by('ingredient__name')

            if not ingredients:
                return Response(
                    {'error': 'Корзина пуста'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            content = render_to_string('shopping_cart_list.txt', {
                'user': user,
                'date': now().date(),
                'ingredients': ingredients,
                'recipes': recipes,
            })

            return FileResponse(
                io.BytesIO(content.encode('utf-8')),
                as_attachment=True,
                filename='shopping_cart_list.txt',
                content_type='text/plain'
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
