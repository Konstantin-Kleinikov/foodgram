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
from djoser.views import UserViewSet as UserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.permissions import IsAdminAuthorOrReadOnly
from api.serializers import (FoodgramUserSerializer, IngredientSerializer,
                             RecipeCreateUpdateSerializer, RecipeSerializer,
                             RecipeShortSerializer, TagSerializer,
                             UserFollowSerializer)
from recipes.models import (Favorite, Follow, Ingredient, IngredientRecipe,
                            Recipe, ShoppingCart, Tag)

logger = logging.getLogger(__name__)

User = get_user_model()


class FoodgramUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = FoodgramUserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(['get'],
            detail=False,
            permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated]
    )
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            avatar = request.data.get('avatar')
            if not avatar:
                raise ValidationError({'avatar': ['Это поле обязательно.']})

            user.avatar = FoodgramUserSerializer(
                context={'request': request}
            ).fields['avatar'].to_internal_value(avatar)

            user.save()

            return Response(
                {'avatar': user.avatar.url if user.avatar else None},
                status=status.HTTP_200_OK)
        # для request.method == 'DELETE'
        if (
                user.avatar
                and user.avatar.path
                and os.path.isfile(user.avatar.path)
        ):
            try:
                os.remove(user.avatar.path)
            except Exception:
                pass

        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated]
            )
    def subscribe(self, request, **kwargs):
        pk = kwargs['id']
        user = request.user

        if request.method == 'DELETE':
            get_object_or_404(Follow,
                              follower=request.user,
                              author_id=pk
                              ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # для request.method == 'POST':
        author = get_object_or_404(User, pk=pk)

        if user.id == author.id:
            raise ValidationError('Нельзя подписаться на самого себя')

        _, created = Follow.objects.get_or_create(
            follower=user, author=author)
        if not created:
            raise ValidationError(
                f'Вы уже подписаны на пользователя {author.username}')

        serializer = UserFollowSerializer(
            author,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def subscriptions(self, request):
        authors = User.objects.filter(
            pk__in=Follow.objects
            .filter(follower=request.user)
            .values_list('author__id', flat=True)
        )
        paginator = self.paginate_queryset(authors)
        return paginator.get_paginated_response(
            UserFollowSerializer(
                paginator.paginate_queryset(authors, request),
                many=True,
                context={'request': request}
            ).data
        )


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
