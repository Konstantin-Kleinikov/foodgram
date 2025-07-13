from django.db import models

from api.constants import SLUG_MAX_LENGTH, TAG_MAX_LENGTH, INGREDIENT_MAX_LENGTH, UNIT_OF_MEASURE_MAX_LENGTH
from api.validators import slug_validator


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
