import logging

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
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (FoodgramUserSerializer, IngredientSerializer,
                             RecipeCreateUpdateSerializer,
                             RecipeReadSerializer, RecipeShortSerializer,
                             TagSerializer, UserFollowSerializer)
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

            serializer = FoodgramUserSerializer(
                instance=user,
                data={'avatar': avatar},
                partial=True,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                {'avatar': user.avatar.url if user.avatar else None},
                status=status.HTTP_200_OK)
        # для метода 'DELETE'
        if user.avatar:
            user.avatar.delete(save=False)
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
            exists = Follow.objects.filter(user=user, following_id=pk).exists()
            if not exists:
                return Response(
                    {'detail': 'Subscription does not exist.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.filter(user=user, following_id=pk).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # для метода 'POST':
        author = get_object_or_404(User, pk=pk)

        if user.id == author.id:
            raise ValidationError('Нельзя подписаться на самого себя')

        _, created = Follow.objects.get_or_create(
            user=user, following=author)
        if not created:
            raise ValidationError(
                f'Вы уже подписаны на пользователя {author.username}')

        serializer = UserFollowSerializer(
            author,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        authors = User.objects.filter(
            pk__in=Follow.objects
            .filter(user=request.user)
            .values_list('following__id', flat=True)
        )
        paginated_qs = self.paginate_queryset(authors)
        serializer = UserFollowSerializer(
            paginated_qs, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


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
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return RecipeCreateUpdateSerializer
        return RecipeReadSerializer

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
        if not Recipe.objects.filter(pk=pk).exists():
            raise ValidationError(f"Рецепт с id={pk} не найден.")
        return Response(
            {'short-link': request.build_absolute_uri(
                reverse('short-link-redirect', args=[pk])
            )},
            status=status.HTTP_200_OK
        )

    def modify_favorite_or_cart(self, model, recipe_id, request):
        if request.method not in {'POST', 'DELETE'}:
            return Response(
                {'error': f'Метод {request.method} не поддерживается'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        if request.method == 'DELETE':
            exists = model.objects.filter(
                user=request.user, recipe_id=recipe_id
            ).exists()
            if not exists:
                return Response(
                    {'detail': 'Item does not exist.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.filter(
                user=request.user, recipe_id=recipe_id
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # для метода 'POST':
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        _, created = model.objects.get_or_create(
            user=request.user, recipe=recipe
        )
        if not created:
            raise ValidationError(
                f'Рецепт с id={recipe.id} '
                f'уже добавлен в {model._meta.verbose_name_plural.lower()}.')

        return Response(
            RecipeShortSerializer(
                recipe,
                context={'request': request}
            ).data,
            status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
    )
    def favorite(self, request, pk=None):
        return self.modify_favorite_or_cart(
            model=Favorite,
            recipe_id=pk,
            request=request,
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        return self.modify_favorite_or_cart(
            model=ShoppingCart,
            recipe_id=pk,
            request=request,
        )

    @action(detail=False, methods=['get'], url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
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

        content = render_to_string('shopping_cart_list.txt', {
            'user': user,
            'date': now().date(),
            'ingredients': ingredients,
            'recipes': recipes,
        })

        return FileResponse(
            content,
            as_attachment=True,
            filename='shopping_cart_list.txt',
            content_type='text/plain'
        )
