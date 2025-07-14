from django.contrib import admin

from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag


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
    list_display = ('id', 'name', 'author', 'pub_date')
    search_fields = ('name', 'text')
    list_display_links = ('name',)
    list_filter = ('name',)
    date_hierarchy = 'pub_date'
    ordering = ('name',)
    readonly_fields = ('id',)
    inlines = [IngredientRecipeInline]