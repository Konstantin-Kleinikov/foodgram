import math
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Count, Min, Max
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe as mark_safe_decorator, mark_safe

from recipes.filters import (HasFavoritesFilter, HasFollowersFilter,
                             HasRecipesFilter)
from recipes.models import (Favorite, Follow, FoodgramUser, Ingredient,
                            IngredientRecipe, Recipe, ShoppingCart, Tag)


class RecipeCountFilter(SimpleListFilter):
    title = 'Количество рецептов'
    parameter_name = 'recipe_count'

    def lookups(self, request, model_admin):
        return [
            ('<10', 'Менее 10 рецептов'),
            ('10-50', 'От 10 до 50 рецептов'),
            ('>50', 'Более 50 рецептов'),
        ]

    def queryset(self, request, queryset):
        if self.value() == '<10':
            return queryset.filter(recipe_count__lt=10, recipe_count__gt=0)
        if self.value() == '10-50':
            return queryset.filter(recipe_count__gte=10, recipe_count__lte=50)
        if self.value() == '>50':
            return queryset.filter(recipe_count__gt=50)
        return queryset


class CookingTimeFilter(SimpleListFilter):
    title = ('Время приготовления')
    parameter_name = 'cooking_time'

    # Добавляем атрибуты для хранения порогов
    short_threshold = None
    medium_threshold = None

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)
        # Сохраняем параметры для последующего использования
        self.request = request
        self.model_admin = model_admin

        # Откладываем расчет порогов до момента, когда они точно понадобятся
        self._calculate_thresholds_if_needed()

    def _calculate_thresholds(self):
        try:
            time_stats = Recipe.objects.aggregate(
                min_time=Min('cooking_time'),
                max_time=Max('cooking_time')
            )

            if time_stats['max_time'] is None or time_stats['min_time'] is None:
                self.short_threshold = 0
                self.medium_threshold = 0
            else:
                range_time = time_stats['max_time'] - time_stats['min_time']
                self.short_threshold = math.ceil(time_stats['min_time'] + range_time / 3)
                self.medium_threshold = math.ceil(time_stats['min_time'] + (range_time * 2) / 3)

            # Добавляем отладочный вывод
            print(f"min_time: {time_stats['min_time']}")
            print(f"max_time: {time_stats['max_time']}")
            print(f"short_threshold: {self.short_threshold}")
            print(f"medium_threshold: {self.medium_threshold}")

        except Exception as e:
            print(f"Ошибка при расчете порогов: {e}")
            self.short_threshold = 0
            self.medium_threshold = 0

    def _calculate_thresholds_if_needed(self):
        if self.short_threshold is None or self.medium_threshold is None:
            self._calculate_thresholds()

    def lookups(self, request, model_admin):
        # Гарантированно рассчитываем пороги перед формированием опций
        self._calculate_thresholds_if_needed()

        # Форматируем значения с проверкой на корректность
        short_value = self.short_threshold if self.short_threshold is not None else 0
        medium_value = self.medium_threshold if self.medium_threshold is not None else 0

        return (
            ('short', f'Быстрое (до {short_value} мин)'),
            ('medium', f'Среднее (до {medium_value} мин)'),
            ('long', f'Долгое (более {medium_value} мин)'),
        )

    def queryset(self, request, queryset):
        # Гарантированно рассчитываем пороги перед фильтрацией
        self._calculate_thresholds_if_needed()

        if self.value() == 'short':
            return queryset.filter(cooking_time__lte=self.short_threshold)
        if self.value() == 'medium':
            return queryset.filter(
                cooking_time__gt=self.short_threshold,
                cooking_time__lte=self.medium_threshold
            )
        if self.value() == 'long':
            return queryset.filter(cooking_time__gt=self.medium_threshold)
        return queryset


@admin.register(FoodgramUser)
class FoodgramUserAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'username',
        'full_name',
        'email',
        'avatar_image',
        'last_login',
        'is_active',
        'recipe_count',
        'favorite_count',
        'follower_count'
    ]
    list_editable = ('is_active',)
    list_filter = [
        'is_superuser',
        'is_staff',
        'is_active',
        HasRecipesFilter,
        HasFavoritesFilter,
        HasFollowersFilter
    ]
    search_fields = ['username', 'email']
    search_help_text = 'Поиск по username и email'
    date_hierarchy = 'last_login'
    readonly_fields = ['last_login', 'date_joined']
    fieldsets = [
        (
            'Основные сведения о пользователе',
            {
                'fields': [
                    ('username', 'is_active'),
                    'email',
                    ('first_name', 'last_name'),
                    ('is_superuser', 'is_staff')
                ],
            },
        ),
        (
            'Дополнительная информация',
            {
                'description': 'Дополнительные сведения о пользователе.',
                'fields': [
                    ('last_login', 'date_joined'), 'avatar', 'password'
                ],
            },
        ),
        (
            'Группы и Полномочия',
            {
                'fields': ['groups', 'user_permissions'],
            },
        ),
    ]

    @admin.display(description='Имя фамилия')
    def full_name(self, user):
        """Получение полного имени"""
        return user.get_full_name()

    @admin.display(description='Количество рецептов')
    def recipe_count(self, user):
        return user.recipes.count()

    @admin.display(description='Количество подписок')
    def favorite_count(self, user):
        return user.favorites.count()

    @admin.display(description='Количество подписчиков')
    def follower_count(self, user):
        return user.followers.count()

    @method_decorator(mark_safe_decorator)
    @admin.display(description='Аватар')
    def avatar_image(self, user):
        if user.avatar:
            return f'<img src="{user.avatar.url}" width="50" height="50">'
        return 'Нет аватара'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related(
            'recipes',
            'favorites',
            'followers'
        )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'recipe_count')
    search_fields = ('name', 'slug')
    list_display_links = ('name',)
    ordering = ('name',)
    readonly_fields = ('id',)

    def get_queryset(self, request):
        # Добавляем аннотацию для подсчета количества рецептов
        return super().get_queryset(request).annotate(
            recipe_count=Count('recipes')
        )

    @admin.display(description='Количество рецептов')
    def recipe_count(self, tag):
        # Возвращаем количество рецептов
        return tag.recipe_count


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit', 'recipe_count')
    search_fields = ('name', 'measurement_unit')
    list_display_links = ('name',)
    list_filter = (RecipeCountFilter,)
    ordering = ('name',)
    readonly_fields = ('id',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            recipe_count=Count(
                'amount_ingredients__recipe',
                distinct=True
            )
        )

    @admin.display(description='Количество рецептов')
    def recipe_count(self, ingredient):
        return ingredient.recipe_count


class IngredientRecipeInline(admin.TabularInline):
    model = IngredientRecipe
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'cooking_time',
        'author',
        'favorites_count',
        'ingredients_list',
        'tags_list',
        'recipe_image'
    )
    search_fields = ('author__username', 'name')
    list_display_links = ('name',)
    list_filter = ('tags', 'author', CookingTimeFilter,)
    date_hierarchy = 'pub_date'
    ordering = ('name',)
    readonly_fields = ('id',)
    inlines = [IngredientRecipeInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            favorites_count=Count('favorites')
        )

    @mark_safe
    @admin.display(description='Добавлено в избранное')
    def favorites_count(self, recipe):
        count = recipe.favorites_count
        if count > 0:
            return f'<span style="color:green">{count}</span>'
        return count

    @method_decorator(mark_safe_decorator)
    @admin.display(description='Изображение рецепта')
    def recipe_image(self, recipe):
        if recipe.image:
            return f'<img src="{recipe.image.url}" width="50" height="50">'
        return 'Нет изображения'

    @mark_safe
    @admin.display(description='Продукты')
    def ingredients_list(self, recipe):
        ingredients = recipe.amount_ingredients.all()
        return '<br>'.join(
            f'{ingredient.ingredient.name} ({ingredient.amount} {ingredient.ingredient.measurement_unit})'
            for ingredient in ingredients
        )

    @mark_safe
    @admin.display(description='Теги')
    def tags_list(self, recipe):
        tags = recipe.tags.all()
        return ', '.join(tag.name for tag in tags)

    @admin.display(description='Время приготовления (мин.)')
    def cooking_time_display(self, recipe):
        return f'{recipe.cooking_time} мин'

    @admin.display(description='Автор')
    def author_display(self, recipe):
        return recipe.author.username


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'following_display')
    search_fields = ('user__username', 'following__username')
    list_filter = ('user',)
    readonly_fields = ('id',)

    @admin.display(description='Кто подписан')
    def user_display(self, follow):
        return follow.user.username

    @admin.display(description='На кого подписан')
    def following_display(self, follow):
        return follow.following.username

    user_display.admin_order_field = 'user__username'
    following_display.admin_order_field = 'following__username'


class BaseRecipeAdmin(admin.ModelAdmin):
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user',)
    readonly_fields = ('id',)
    list_select_related = ('user', 'recipe')  # Оптимизация запросов
    list_display = ('id', 'user_display', 'recipe_display')  # Выносим сюда

    @admin.display(description=('Пользователь'))
    def user_display(self, obj):
        return obj.user.username

    @admin.display(description=('Рецепт'))
    def recipe_display(self, obj):
        return obj.recipe.name

    recipe_display.admin_order_field = 'recipe__name'
    user_display.admin_order_field = 'user__username'


admin.site.register(Favorite, BaseRecipeAdmin)
admin.site.register(ShoppingCart, BaseRecipeAdmin)
