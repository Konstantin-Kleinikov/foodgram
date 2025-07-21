from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from recipes.models import (Favorite, Follow, Ingredient, IngredientRecipe,
                            Recipe, ShoppingCart, Tag)


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
    search_fields = ('author', 'name')
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