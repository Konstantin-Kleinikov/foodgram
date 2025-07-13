from django.contrib import admin

from api.models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    list_display_links = ('name',)
    list_filter = ('name',)
    ordering = ('name',)
    readonly_fields = ('id', 'slug')
