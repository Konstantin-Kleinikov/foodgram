"""
Модуль содержит пользовательские фильтры для Django REST Framework.
Используется для реализации сложных условий фильтрации рецептов и ингредиентов.
"""

from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe, Tag


class RecipeFilter(filters.FilterSet):
    """
    Фильтр для модели Recipe. Позволяет фильтровать рецепты по:
    - is_favorited: проверяет, добавлен ли рецепт в избранное.
    - is_in_shopping_cart: проверяет, добавлен ли рецепт в список покупок.
    - author: фильтрует рецепты по ID автора.
    - tags: фильтрует рецепты по тегам (по slug).
    """

    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )
    author = filters.NumberFilter(
        field_name='author__id',
        lookup_expr='exact'
    )
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug',
    )

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'author', 'tags']

    def filter_is_favorited(self, recipes, name, value):
        """
        Фильтрует рецепты, которые находятся в избранном у текущего
        пользователя.

        :param recipes: QuerySet рецептов.
        :param name: Имя фильтра (в данном случае 'is_favorited').
        :param value: Логическое значение True/False.
        :return: Отфильтрованный QuerySet.
        """
        if value and self.request.user and self.request.user.is_authenticated:
            return recipes.filter(favorites__user=self.request.user)
        return recipes

    def filter_is_in_shopping_cart(self, recipes, name, value):
        """
        Фильтрует рецепты, которые находятся в списке покупок у текущего
        пользователя.

        :param recipes: QuerySet рецептов.
        :param name: Имя фильтра (в данном случае 'is_in_shopping_cart').
        :param value: Логическое значение True/False.
        :return: Отфильтрованный QuerySet.
        """
        if value and self.request.user and self.request.user.is_authenticated:
            return recipes.filter(carts__user=self.request.user)
        return recipes

    def filter_queryset(self, recipes):
        """
        Добавляет оптимизацию к запросу: выбирает связанные поля автора и
        тегов.
        Вызывается перед основной фильтрацией.

        :param recipes: QuerySet рецептов.
        :return: Оптимизированный QuerySet.
        """
        recipes = recipes.select_related('author')
        recipes = recipes.prefetch_related('tags')
        return super().filter_queryset(recipes)


class IngredientSearchFilter(filters.FilterSet):
    """
    Фильтр для модели Ingredient. Позволяет искать ингредиенты по началу
    названия.
    """

    name = filters.CharFilter(method='filter_name_startswith')

    class Meta:
        model = Ingredient
        fields = ['name']

    def filter_name_startswith(self, queryset, name, value):
        """
        Возвращает ингредиенты, имя которых начинается с указанного значения,
        не чувствительно к регистру.

        :param queryset: QuerySet ингредиентов.
        :param name: Имя фильтра (в данном случае 'name').
        :param value: Значение для фильтрации.
        :return: Отфильтрованный QuerySet.
        """
        return queryset.filter(name__istartswith=value)
