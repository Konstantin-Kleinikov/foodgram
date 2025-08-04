from django_filters import BaseInFilter, CharFilter
from django_filters import rest_framework as filters

from recipes.models import Recipe, Tag


class CharListFilter(BaseInFilter, CharFilter):
    pass


class RecipeFilter(filters.FilterSet):
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
        if value and self.request.user and self.request.user.is_authenticated:
            return recipes.filter(favorites__user=self.request.user)
        return recipes

    def filter_is_in_shopping_cart(self, recipes, name, value):
        if value and self.request.user and self.request.user.is_authenticated:
            return recipes.filter(carts__user=self.request.user)
        return recipes

    def filter_queryset(self, recipes):
        recipes = recipes.select_related('author')
        recipes = recipes.prefetch_related('tags')
        return super().filter_queryset(recipes)
