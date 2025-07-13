import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from api.constants import SLUG_REGEX, USERNAME_FORBIDDEN, USERNAME_REGEX


def username_validator(value):
    """
    Валидатор для проверки имени пользователя.
    Проверяет соответствие регулярному выражению и запрещенные имена.
    """
    if not re.match(USERNAME_REGEX, value):
        raise ValidationError(
            'Допустимы только латинские буквы, цифры, символы _,., @, + и -',
            code='invalid_username'
        )

    if value.lower() in USERNAME_FORBIDDEN:
        raise ValidationError(
            'Username не может быть "%(forbidden)s"!' % {'forbidden': value},
            code='forbidden_username'
        )


slug_validator = RegexValidator(
    regex=SLUG_REGEX,
    message='Слаг может содержать только буквы, цифры, дефисы и нижние подчеркивания',
    code='invalid_slug'
)
