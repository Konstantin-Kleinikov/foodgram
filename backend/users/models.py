import logging
import re

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models

from api.constants import (EMAIL_MAX_LENGTH, NAME_MAX_LENGTH,
                           PASSWORD_MAX_LENGTH, USERNAME_FORBIDDEN,
                           USERNAME_MAX_LENGTH, USERNAME_REGEX)
from api.validators import username_validator


class FoodgramUser(AbstractUser):
    username = models.CharField(
        'Имя пользователя',
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
        validators=[username_validator]
    )
    email = models.EmailField(
        'Адрес электронной почты',
        unique=True,
        max_length=EMAIL_MAX_LENGTH,
    )
    password = models.CharField(
        'Пароль',
        max_length=PASSWORD_MAX_LENGTH,
    )
    first_name=models.CharField(
        'Имя',
        max_length=NAME_MAX_LENGTH,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=NAME_MAX_LENGTH,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/avatars/',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username', 'id')

    def __str__(self):
        return self.username

    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def remove_avatar(self):
        try:
            if self.avatar:
                # Проверяем существование файла
                if default_storage.exists(self.avatar.name):
                    # Удаляем файл из хранилища
                    default_storage.delete(self.avatar.name)
                    # Очищаем поле аватара
                    self.avatar = None
                    # Сохраняем изменения
                    self.save()
                    logging.info(f'Аватар пользователя {self.username} успешно удален')
                    return True  # Возвращаем True, если аватар был удален
                else:
                    logging.warning(f'Файл аватара для пользователя {self.username} не найден')
            else:
                logging.warning(f'У пользователя {self.username} нет аватара')
            return False  # Возвращаем False, если аватар не был удален
        except ValidationError as ve:
            logging.error(f'Ошибка валидации при удалении аватара пользователя {self.username}: {str(ve)}')
            raise ValidationError(f'Ошибка при удалении аватара: {str(ve)}')
        except Exception as e:
            logging.error(f'Ошибка при удалении аватара пользователя {self.username}: {str(e)}')
            raise Exception(f'Произошла ошибка при удалении аватара: {str(e)}')
