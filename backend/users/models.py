import re

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from api.constants import (EMAIL_MAX_LENGTH, NAME_MAX_LENGTH,
                           PASSWORD_MAX_LENGTH, USERNAME_FORBIDDEN,
                           USERNAME_MAX_LENGTH, USERNAME_REGEX)


class FoodgramUser(AbstractUser):
    # username = models.CharField(
    #     'Имя пользователя',
    #     max_length=USERNAME_MAX_LENGTH,
    #     unique=True,
    # )
    # email = models.EmailField(
    #     'Адрес электронной почты',
    #     unique=True,
    #     max_length=EMAIL_MAX_LENGTH,
    # )
    # password = models.CharField(
    #     'Пароль',
    #     max_length=PASSWORD_MAX_LENGTH,
    # )
    # first_name=models.CharField(
    #     'Имя',
    #     max_length=NAME_MAX_LENGTH,
    # )
    # last_name = models.CharField(
    #     'Фамилия',
    #     max_length=NAME_MAX_LENGTH,
    # )
    avatar = models.ImageField(
        'Аватар',
        upload_to='avatars/',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username', 'id')

    def __str__(self):
        return self.username

    def clean(self):
        if self.username == USERNAME_FORBIDDEN:
            raise ValidationError(
                f'Username не может быть '
                f'"{USERNAME_FORBIDDEN}"!'
            )
        if len(self.username) > USERNAME_MAX_LENGTH:
            raise ValidationError(
                'Username не может быть длиннее '
                f'{USERNAME_MAX_LENGTH} символов.'
            )
        if not re.match(USERNAME_REGEX, self.username):
            raise ValidationError(
                'Недопустимые символы в username.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)