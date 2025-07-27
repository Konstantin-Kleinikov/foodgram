from django_filters import BaseInFilter, CharFilter
from django_filters import rest_framework as filters

from recipes.models import Recipe


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
    tags = filters.AllValuesMultipleFilter(field_name='tags__slug')

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'author', 'tags']

    def filter_is_favorited(self, queryset, name, value):
        if value and self.request.user and self.request.user.is_authenticated:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if value and self.request.user and self.request.user.is_authenticated:
            return queryset.filter(carts__user=self.request.user)
        return queryset

    def filter_queryset(self, queryset):
        queryset = queryset.select_related('author')
        queryset = queryset.prefetch_related('tags')
        return super().filter_queryset(queryset)
