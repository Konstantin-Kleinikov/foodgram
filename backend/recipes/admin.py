from django.contrib import admin

from recipes.models import Tag, Ingredient


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
