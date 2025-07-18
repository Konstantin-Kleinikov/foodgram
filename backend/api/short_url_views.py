from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import reverse

from api.utils import decode_base62
from recipes.models import Recipe


def redirect_short_link(request, short_code):
    try:
        # Удаляем префикс для декодирования
        if short_code.startswith('r-'):
            short_code = short_code[2:]

        # Декодируем короткий код в ID рецепта
        recipe_id = decode_base62(short_code)

        # Получаем рецепт
        recipe = Recipe.objects.get(id=recipe_id)

        # Перенаправляем на детальный просмотр рецепта
        return redirect(reverse('recipe-detail', kwargs={'pk': recipe_id}))

    except (ValueError, Recipe.DoesNotExist):
        return HttpResponseNotFound("Страница не найдена")
