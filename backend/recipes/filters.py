from django.contrib.admin import SimpleListFilter

from recipes.models import Recipe


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
            return (queryset.
                    filter(**{f'{self.related_name}__isnull': False})
                    .distinct()
                    )
        if self.value() == 'no':
            return queryset.filter(**{f'{self.related_name}__isnull': True})
        return queryset


class HasRecipesFilter(BaseHasFilter):
    title = 'Есть рецепты'
    parameter_name = 'has_recipes'
    related_name = 'recipes'


class HasFollowingFilter(BaseHasFilter):
    title = 'Есть подписчики'
    parameter_name = 'has_following'
    related_name = 'authors'


class HasFollowersFilter(BaseHasFilter):
    title = 'Есть подписки'
    parameter_name = 'has_followers'
    related_name = 'followers'


class CookingTimeFilter(SimpleListFilter):
    title = 'Время приготовления'
    parameter_name = 'cooking_time'

    def _range_filter(self, selected, recipes=None):
        bounds = self.thresholds[selected]['range']
        return (
            recipes
            or self.recipes
            or Recipe.objects.all()
        ).filter(cooking_time__range=bounds)

    def lookups(self, request, model_admin):
        self.recipes = model_admin.get_queryset(request)
        times = list(self.recipes.values_list('cooking_time', flat=True))

        if len(set(times)) < 3:
            return []

        times.sort()
        short_time_max = times[len(times) // 3]
        medium_time_max = times[2 * len(times) // 3]

        self.thresholds = {
            'fast': {
                'range': (0, short_time_max - 1),
                'label': f'меньше {short_time_max} мин',
            },
            'medium': {
                'range': (short_time_max, medium_time_max - 1),
                'label': f'не дольше {medium_time_max} мин',
            },
            'long': {
                'range': (medium_time_max, times[-1] + 1),
                'label': 'долгие',
            },
        }

        return [
            (
                key,
                f"{value['label']} "
                f"({self._range_filter(key).count()})"
            )
            for key, value in self.thresholds.items()
        ]

    def queryset(self, request, queryset):
        if self.value():
            return self._range_filter(self.value(), queryset)
        return queryset
