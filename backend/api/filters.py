from django_filters import BaseInFilter, CharFilter
from django_filters import rest_framework as filters

from recipes.models import Recipe, Tag


class CharListFilter(BaseInFilter, CharFilter):
    pass


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_is_in_shopping_cart')
    author = filters.NumberFilter(field_name='author__id', lookup_expr='exact')
    tags = CharListFilter(field_name='tags__slug', lookup_expr='in')

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'author', 'tags']

    def filter_is_favorited(self, queryset, name, value):
        if value and self.request.user.is_authenticated:  # Добавляем проверку на None
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if value and self.request.user.is_authenticated:  # Добавляем проверку на None
            return queryset.filter(shopping_cart__user=self.request.user)
        return queryset

    def filter_tags(self, queryset, name, value):
        if value:
            return queryset.filter(tags__slug__in=value).distinct()
        return queryset

    def filter_queryset(self, queryset):
        queryset = queryset.select_related('author')
        queryset = queryset.prefetch_related('tags')  # TODO добавить is_favorited и is_in_shopping_cart после создания моделей
        return super().filter_queryset(queryset)
