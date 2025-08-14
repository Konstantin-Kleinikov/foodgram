from django.contrib.admin import SimpleListFilter


class BaseHasFilter(SimpleListFilter):
    """Базовый класс для фильтров наличия чего-либо"""

    # Общие параметры для всех фильтров
    LOOKUP_CHOICES = [
        ('yes', 'Да'),
        ('no', 'Нет'),
    ]

    def lookups(self, request, model_admin):
        return self.LOOKUP_CHOICES

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(
                **{f'{self.field_name}__isnull': False}
            ).distinct()
        elif self.value() == 'no':
            return queryset.filter(**{f'{self.field_name}__isnull': True})
        return queryset


class HasRecipesFilter(BaseHasFilter):
    title = 'Есть рецепты'
    parameter_name = 'has_recipes'
    field_name = 'recipes'


class HasFavoritesFilter(BaseHasFilter):
    title = 'Есть избранные'
    parameter_name = 'has_favorites'
    field_name = 'favorites'


class HasFollowersFilter(BaseHasFilter):
    title = 'Есть подписчики'
    parameter_name = 'has_followers'
    field_name = 'followers'
