from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import FoodgramUser

@admin.register(FoodgramUser)
class FoodgramAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'full_name', 'last_login', 'is_active',]
    list_editable = ('is_active',)
    list_filter = ['is_superuser', 'is_staff', 'is_active']
    search_fields = ['username', 'email']
    search_help_text = 'Поиск по username и email'
    date_hierarchy = 'last_login'
    readonly_fields = ['last_login', 'date_joined']
    fieldsets = [
        (
            'Основные сведения о пользователе',
            {
                'fields': [
                    ('username', 'is_active' ), 'email', ('first_name', 'last_name'),
                    ('is_superuser', 'is_staff')
                ],
            },
        ),
        (
            'Дополнительная информация',
            {
                'description': 'Дополнительные сведения о пользователе.',
                'fields': [('last_login', 'date_joined'), 'avatar', 'password'],
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
    def full_name(self, obj):
        """Получение полного имени"""
        return obj.get_full_name()
