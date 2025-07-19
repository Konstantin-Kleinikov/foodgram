from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import Truncator

from api.constants import (INGREDIENT_MAX_LENGTH, RECIPE_DISPLAY_WORDS_LENGTH,
                           RECIPE_NAME_MAX_LENGTH, SLUG_MAX_LENGTH,
                           TAG_MAX_LENGTH, UNIT_OF_MEASURE_MAX_LENGTH)
from api.validators import slug_validator

UserModel = get_user_model()


class Tag(models.Model):
    """
    Модель для хранения тегов рецептов
    """
    name = models.CharField(
        'Наименование',
        max_length=TAG_MAX_LENGTH,
        unique=True,
        help_text=f'Введите название тега (до {TAG_MAX_LENGTH} символов)'
    )
    slug = models.SlugField(
        verbose_name='Слаг',
        max_length=SLUG_MAX_LENGTH,
        unique=True,
        validators=[slug_validator],
    )

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        ordering = ('name', 'id')

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """
    Модель для хранения ингредиентов
    """
    name = models.CharField(
        'Наименование',
        max_length=INGREDIENT_MAX_LENGTH,
        help_text=f'Введите название ингредиента (до {INGREDIENT_MAX_LENGTH} символов)'
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=UNIT_OF_MEASURE_MAX_LENGTH,
        help_text=f'Укажите единицу измерения (до {UNIT_OF_MEASURE_MAX_LENGTH} символов)'
    )

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name', 'id')
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient_unit'
            )
        ]

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'


class Recipe(models.Model):
    name = models.CharField(
        'Название рецепта',
        max_length=RECIPE_NAME_MAX_LENGTH,
        help_text=f'Введите название рецепта (до {RECIPE_NAME_MAX_LENGTH} символов)'
    )
    image = models.ImageField(
        'Изображение рецепта',
        upload_to='recipes/images',
        null=True,
        blank=True,
        help_text='Загрузите изображение рецепта'
    )
    text = models.TextField(
        'Описание',
        help_text='Введите подробное описание рецепта'
    )
    author = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        verbose_name='Ингредиенты'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги'
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=(MinValueValidator(
            1, message='Время приготовления не может быть меньше единицы'),),
        help_text='Укажите время приготовления в минутах'
    )
    pub_date = models.DateTimeField(
        'Дата и время публикации',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)
        default_related_name = 'recipes'

    def __str__(self) -> str:
        truncator = Truncator(self.name)
        return truncator.words(RECIPE_DISPLAY_WORDS_LENGTH, truncate="...")


class IngredientRecipe(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        'Количество',
        validators=(MinValueValidator(
            1, message='Кол-во не может быть меньше единицы'),)
    )

    class Meta:
        ordering = ('recipe',)
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'
        default_related_name = 'amount_ingredients'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient',),
                name='unique_ingredient'
            ),
        )

    def __str__(self) -> str:
        return f'{self.amount} {self.ingredient}'


class Favorite(models.Model):
    """ Модель для избранных рецептов. """
    user = models.ForeignKey(
        UserModel,
        verbose_name='Пользователь',
        on_delete=models.CASCADE)
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт блюда',
        on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        ordering = ('user', 'recipe')
        default_related_name = 'favorites'

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'


class Follow(models.Model):
    user = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        verbose_name='Кто подписан',
        related_name='followers',
    )
    following = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        verbose_name='На кого подписан',
        related_name='following',
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'following'],
                name='unique_user_following',
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('following')),
                name='prevent_self_follow'
            ),
        ]
        ordering = ['user__username', 'following__username', 'id']
        indexes = [
            models.Index(
                fields=['user', 'following'],
            )
        ]

    def __str__(self):
        return (f'Пользователь: {self.user}, подписан на '
                f'автора: {self.following}.')
