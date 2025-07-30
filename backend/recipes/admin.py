from django.contrib import admin
from django.db.models import Count
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.safestring import mark_safe as mark_safe_decorator

from recipes.filters import (HasFavoritesFilter, HasFollowersFilter,
                             HasRecipesFilter)
from recipes.models import (Favorite, Follow, FoodgramUser, Ingredient,
                            IngredientRecipe, Recipe, ShoppingCart, Tag)


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
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    list_display_links = ('name',)
    list_filter = ('name',)
    ordering = ('name',)
    readonly_fields = ('id',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name', 'measurement_unit')
    list_display_links = ('name',)
    list_filter = ('name',)
    ordering = ('name',)
    readonly_fields = ('id',)


class IngredientRecipeInline(admin.TabularInline):
    model = IngredientRecipe
    extra = 1  # Количество пустых форм для добавления


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'pub_date', 'favorites_count')
    search_fields = ('author__username', 'name')
    list_display_links = ('name',)
    list_filter = ('tags',)
    date_hierarchy = 'pub_date'
    ordering = ('name',)
    readonly_fields = ('id',)
    inlines = [IngredientRecipeInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            favorites_count=Count('favorites')
        )

    def favorites_count(self, obj):
        count = obj.favorites_count
        if count > 0:
            return format_html('<span style="color:green">{}</span>', count)
        return count
    favorites_count.is_safe = True
    favorites_count.short_description = 'Добавлено в избранное'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'recipe_display')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user',)
    readonly_fields = ('id',)

    def user_display(self, obj):
        return obj.user.username
    user_display.short_description = 'Пользователь'

    def recipe_display(self, obj):
        return obj.recipe.name
    recipe_display.short_description = 'Рецепт'


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'following_display')
    search_fields = ('user__username', 'following__username')
    list_filter = ('user',)
    readonly_fields = ('id',)

    def user_display(self, obj):
        return obj.user.username
    user_display.short_description = 'Кто подписан'

    def following_display(self, obj):
        return obj.following.username
    following_display.short_description = 'На кого подписан'


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'recipe_name')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user',)
    list_select_related = ('user', 'recipe')
    readonly_fields = ('id',)

    def user_display(self, obj):
        return obj.user.username
    user_display.short_description = 'Пользователь'

    def recipe_name(self, obj):
        return obj.recipe.name
    recipe_name.short_description = 'Рецепт'
    recipe_name.admin_order_field = 'recipe__name'
