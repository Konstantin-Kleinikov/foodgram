from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.password_validation import validate_password
from django.db.models import Count
from django.utils.safestring import mark_safe

from recipes.filters import (CookingTimeFilter, HasFollowersFilter,
                             HasFollowingFilter, HasRecipesFilter)
from recipes.models import (Favorite, Follow, FoodgramUser, Ingredient,
                            IngredientRecipe, Recipe, ShoppingCart, Tag)


class FoodgramUserChangeForm(forms.ModelForm):
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput,
        required=False,
        help_text="Оставьте пустым, если не хотите менять пароль.",
    )
    new_password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput,
        required=False,
    )

    class Meta:
        model = FoodgramUser
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 or p2:
            if not p1 or not p2:
                raise forms.ValidationError("Введите оба поля нового пароля.")
            if p1 != p2:
                raise forms.ValidationError("Пароли не совпадают.")
            validate_password(p1, self.instance)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        p1 = self.cleaned_data.get("new_password1")
        if p1:
            user.set_password(p1)
        if commit:
            user.save()
            self.save_m2m()
        return user


@admin.register(FoodgramUser)
class FoodgramUserAdmin(BaseUserAdmin):
    form = FoodgramUserChangeForm

    list_display = [
        'id',
        'username',
        'full_name',
        'email',
        'avatar_image',
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
        HasFollowersFilter,
        HasFollowingFilter
    ]
    search_fields = ['username', 'email']
    search_help_text = 'Поиск по username и email'
    date_hierarchy = 'last_login'
    readonly_fields = ['last_login', 'date_joined', 'avatar_image']
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
        ("Смена пароля", {"fields": ("new_password1", "new_password2")}),
        (
            'Дополнительная информация',
            {
                'description': 'Дополнительные сведения о пользователе.',
                'fields': [
                    ('last_login', 'date_joined'),
                    'avatar', 'avatar_image'
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

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "avatar",
                ),
            },
        ),
    )

    @admin.display(description='Имя фамилия')
    def full_name(self, user):
        """Получение полного имени"""
        return user.get_full_name()

    @admin.display(description='Рецептов')
    def recipe_count(self, user):
        return user.recipes.count()

    @admin.display(description='Подписчиков')
    def favorite_count(self, user):
        return user.authors.count()

    @admin.display(description='Подписок')
    def follower_count(self, user):
        return user.followers.count()

    @admin.display(description='Аватар')
    def avatar_image(self, user):
        if user.avatar:
            return mark_safe(
                f'<img src="{user.avatar.url}" width="50" height="50">'
            )
        return '-'

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

    @admin.display(description='Рецептов')
    def recipe_count(self, tag):
        # Возвращаем количество рецептов
        return tag.recipe_count


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit', 'recipe_count')
    search_fields = ('name', 'measurement_unit')
    list_display_links = ('name',)
    list_filter = ('measurement_unit', HasRecipesFilter)
    ordering = ('name',)
    readonly_fields = ('id',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            recipe_count=Count(
                'amount_ingredients__recipe',
                distinct=True
            )
        )

    @admin.display(description='Рецептов')
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
    readonly_fields = ('id', 'recipe_image')
    inlines = [IngredientRecipeInline]

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'author',
                'text',
                'cooking_time',
                'image',
                'recipe_image',
            )
        }),
        ('Теги', {
            'fields': ('tags',)
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            favorites_count=Count('favorites')
        )

    @mark_safe
    @admin.display(description='В избранном')
    def favorites_count(self, recipe):
        count = recipe.favorites_count
        return count

    @admin.display(description='Изображение')
    def recipe_image(self, recipe):
        if recipe.image:
            return mark_safe(
                f'<img src="{recipe.image.url}" width="50" height="50">'
            )
        return '-'

    @admin.display(description='Продукты')
    def ingredients_list(self, recipe):
        return mark_safe('<br>'.join(
            f'{ingredient.ingredient.name} ({ingredient.amount} '
            f'{ingredient.ingredient.measurement_unit})'
            for ingredient in recipe.amount_ingredients.all()
        ))

    @admin.display(description='Теги')
    def tags_list(self, recipe):
        return mark_safe('<br>'.join(tag.name for tag in recipe.tags.all()))

    @admin.display(description='Время (мин.)')
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
