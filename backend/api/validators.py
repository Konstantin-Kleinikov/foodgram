import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from api.constants import (PASSWORD_MAX_LENGTH, SLUG_REGEX,
                           USERNAME_FORBIDDEN, USERNAME_REGEX)


slug_validator = RegexValidator(
    regex=SLUG_REGEX,
    message='Слаг может содержать только буквы, цифры, дефисы и '
            'нижние подчеркивания',
    code='invalid_slug'
)


def username_validator(value):
    """
    Валидатор для проверки имени пользователя.
    Проверяет соответствие регулярному выражению и запрещенные имена.
    """
    if not re.match(USERNAME_REGEX, value):
        raise ValidationError(
            'Допустимы только латинские буквы, цифры, символы '
            '_,., @, + и -',
            code='invalid_username'
        )

    if value.lower() in USERNAME_FORBIDDEN:
        raise ValidationError(
            'Username не может быть "%(forbidden)s"!' % {'forbidden': value},
            code='forbidden_username'
        )


class MaxLengthValidator:
    """
    Валидатор максимальной длины пароля
    """

    def __init__(self, max_length=PASSWORD_MAX_LENGTH):
        self.max_length = max_length

    def validate(self, password, user=None):
        if len(password) > self.max_length:
            raise ValidationError(
                f'Пароль не может быть длиннее {self.max_length} '
                'символов',
                code='password_too_long',
                params={'max_length': self.max_length},
            )

    def get_help_text(self):
        return f'Пароль не должен превышать {self.max_length} символов'
