from django.http import Http404
from django.shortcuts import redirect

from recipes.models import Recipe


def redirect_short_link(request, recipe_id):
    if not Recipe.objects.filter(id=recipe_id).exists():
        raise Http404("Рецепт не найден")
    return redirect(f'/recipes/{recipe_id}/')
