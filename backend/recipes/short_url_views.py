import logging

from django.shortcuts import get_object_or_404, redirect

from recipes.models import Recipe

logger = logging.getLogger(__name__)


def redirect_short_link(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=int(recipe_id))
    return redirect('public-recipe-detail', pk=recipe.id)
