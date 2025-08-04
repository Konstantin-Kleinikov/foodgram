from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models

from recipes.constants import (COOKING_TIME_MIN_VALUE, EMAIL_MAX_LENGTH,
                               INGREDIENT_MAX_LENGTH, INGREDIENT_MIN_VALUE,
                               NAME_MAX_LENGTH, RECIPE_NAME_MAX_LENGTH,
                               SLUG_MAX_LENGTH, TAG_MAX_LENGTH,
                               TEXT_FIELDS_DISPLAY_LENGTH,
                               UNIT_OF_MEASURE_MAX_LENGTH, USERNAME_MAX_LENGTH)


class FoodgramUserManager(BaseUserManager):
    """
    Менеджер пользовательской модели FoodgramUser, где email является
    уникальным идентификатором для аутентификации вместо username.
    """

    def create_user(
            self,
            username=None,
            email=None,
            password=None,
            **extra_fields
    ):
        """
        Создает и сохраняет пользователя с указанным email и паролем.
        """
        if not email:
            raise ValueError('Email должен быть указан')

        email = self.normalize_email(email)

        # Если username не указан, создаем его из email
        if not username:
            username = email.split('@')[0]
            # Проверка уникальности username
            i = 1
            temp_username = username
            while self.model.objects.filter(username=temp_username).exists():
                temp_username = f"{username}{i}"
                i += 1
            username = temp_username

        user = self.model(
            username=username,
            email=email,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


class FoodgramUser(AbstractUser):
    username = models.CharField(
        'Никнейм пользователя',
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
    )
    email = models.EmailField(
        'Адрес электронной почты',
        unique=True,
        blank=False,
        max_length=EMAIL_MAX_LENGTH,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/avatars/',
        blank=True,
        null=True,
    )
    first_name = models.CharField(
        'Имя',
        blank=False,
        max_length=NAME_MAX_LENGTH,
    )
    last_name = models.CharField(
        'Фамилия',
        blank=False,
        max_length=NAME_MAX_LENGTH,
    )
    objects = FoodgramUserManager()

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username


class Tag(models.Model):
    """
    Модель для хранения тегов рецептов
    """
    name = models.CharField(
        'Наименование',
        max_length=TAG_MAX_LENGTH,
        unique=True,
    )
    slug = models.SlugField(
        verbose_name='Слаг',
        max_length=SLUG_MAX_LENGTH,
        unique=True,
    )

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """
    Модель для хранения продуктов
    """
    name = models.CharField(
        'Наименование',
        max_length=INGREDIENT_MAX_LENGTH,
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=UNIT_OF_MEASURE_MAX_LENGTH,
    )

    class Meta:
        verbose_name = 'продукт'
        verbose_name_plural = 'Продукты'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient_unit'
            )
        ]

    def __str__(self):
        return (f'{self.name[:TEXT_FIELDS_DISPLAY_LENGTH]} '
                f'({self.measurement_unit})')


UserModel = get_user_model()


class Recipe(models.Model):
    name = models.CharField(
        'Название рецепта',
        max_length=RECIPE_NAME_MAX_LENGTH,
    )
    image = models.ImageField(
        'Изображение рецепта',
        upload_to='recipes/images',
        null=True,
        blank=True,
    )
    text = models.TextField(
        'Описание',
    )
    author = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        verbose_name='Продукты',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
    )
    cooking_time = models.PositiveIntegerField(
        'Время приготовления (мин.)',
        validators=(MinValueValidator(
            COOKING_TIME_MIN_VALUE,
            message='Время приготовления не может быть меньше '
                    f'{COOKING_TIME_MIN_VALUE} минут.'
        ),
        ),
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
        return f'{self.name[:TEXT_FIELDS_DISPLAY_LENGTH]}'


class IngredientRecipe(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Продукт'
    )
    amount = models.PositiveSmallIntegerField(
        'Количество',
        validators=(MinValueValidator(
            INGREDIENT_MIN_VALUE,
            message=f'Кол-во не может быть меньше {INGREDIENT_MIN_VALUE}.'),
        )
    )

    class Meta:
        ordering = ('recipe',)
        verbose_name = 'Продукт рецепта'
        verbose_name_plural = 'Продукты рецептов'
        default_related_name = 'amount_ingredients'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient',),
                name='unique_ingredient'
            ),
        )

    def __str__(self) -> str:
        return f'{self.amount} {self.ingredient}'


class BaseUserRecipeModel(models.Model):
    """Базовый класс для моделей, связывающих пользователя с рецептом."""

    user = models.ForeignKey(
        UserModel,
        verbose_name='Пользователь',
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE
    )

    class Meta:
        abstract = True
        ordering = ('user', 'recipe')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='%(class)rs_unique_user_recipe'
            )
        ]

    def __str__(self):
        return (f'{self.user.username[:TEXT_FIELDS_DISPLAY_LENGTH]} '
                f'- {self.recipe.name[:TEXT_FIELDS_DISPLAY_LENGTH]}')


class ShoppingCart(BaseUserRecipeModel):
    """Модель списка покупок."""

    class Meta:
        verbose_name = 'список покупок'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'carts'


class Favorite(BaseUserRecipeModel):
    """Модель для избранных рецептов."""

    class Meta:
        verbose_name = 'избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        default_related_name = 'favorites'


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
        related_name='authors',
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
        ordering = ('user__username', 'following__username')

    def __str__(self):
        return (f'Пользователь: {self.user}, подписан на '
                f'автора: {self.following}.')
