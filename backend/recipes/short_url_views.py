import logging

from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect

from api.utils import decode_base62
from recipes.models import Recipe

logger = logging.getLogger(__name__)


def redirect_short_link(request, recipe_id):
    if recipe_id.startswith('r-'):
        recipe_id = recipe_id[2:]
    elif len(recipe_id) < 2:
        return HttpResponseNotFound('Страница не найдена')

    try:
        decoded_id = decode_base62(recipe_id)
        get_object_or_404(Recipe, id=decoded_id)
    except Exception as e:
        logger.error(f'Ошибка обработки: {e}')
        return HttpResponseNotFound('Страница не найдена')

    return redirect('public-recipe-detail', pk=decoded_id)
