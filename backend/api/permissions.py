"""
Модуль содержит пользовательские разрешения (permissions) для Django REST
Framework.
Определяет, кто имеет право выполнять те или иные действия над ресурсами API.
"""

from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Пользовательское разрешение: разрешает только GET-запросы анонимным
    пользователям и даёт полный доступ автору объекта.

    Используется для защиты ресурсов, таких как рецепты — только автор может
    редактировать или удалять свой рецепт, остальные могут только
    просматривать.
    """

    def has_object_permission(self, request, view, obj):
        """
        Проверяет, имеет ли текущий пользователь право на выполнение действия
        с конкретным объектом.

        :param request: Объект HTTP-запроса.
        :param view: Представление, вызывающее данный метод.
        :param obj: Объект модели, к которому требуется получить доступ.
        :return: True, если доступ разрешён, иначе False.
        """
        return (
            request.method in SAFE_METHODS
            or obj.author == request.user
        )
