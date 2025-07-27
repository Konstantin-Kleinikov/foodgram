import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import reverse

from api.utils import decode_base62
from recipes.models import Recipe

logger = logging.getLogger(__name__)


def redirect_short_link(request, short_code):
    try:
        # Обработка префикса
        if short_code.startswith('r-'):
            short_code = short_code[2:]
        elif len(short_code) < 2:
            raise ValueError("Для короткой ссылки меньше 2.")

        # Декодирование ID
        try:
            recipe_id = decode_base62(short_code)
        except Exception as e:
            logger.error(f"Ошибка декодирования: {e}")
            raise ValueError("Ошибка декодирования")

        # Получение рецепта
        try:
            Recipe.objects.only('id').get(id=recipe_id)
        except ObjectDoesNotExist:
            raise Recipe.DoesNotExist("Рецепт не найден")

        # Перенаправление
        return redirect(reverse(
            'recipe-detail',
            kwargs={'pk': recipe_id})
        )

    except (ValueError, Recipe.DoesNotExist) as e:
        logger.error(f"Ошибка перенаправления: {e}")
        return HttpResponseNotFound("Страница не найдена")
