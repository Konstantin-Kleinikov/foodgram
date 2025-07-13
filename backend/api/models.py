from django.db import models

from api.constants import SLUG_MAX_LENGTH, TAG_MAX_LENGTH
from api.validators import slug_validator


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
        validators=[slug_validator],
    )

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        ordering = ('name', 'id')
