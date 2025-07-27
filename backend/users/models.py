import logging

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models

from api.constants import (EMAIL_MAX_LENGTH, NAME_MAX_LENGTH,
                           USERNAME_MAX_LENGTH)
from api.validators import username_validator

logger = logging.getLogger(__name__)


class FoodgramUser(AbstractUser):
    username = models.CharField(
        'Имя пользователя',
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
        validators=[username_validator],
        error_messages={
            'max_length': 'Длина имени пользователя не может '
                          f'превышать {USERNAME_MAX_LENGTH} символов'
        }
    )
    email = models.EmailField(
        'Адрес электронной почты',
        unique=True,
        blank=False,
        max_length=EMAIL_MAX_LENGTH,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/avatars/',
        blank=True,
        null=True,
    )
    first_name = models.CharField(
        'Имя',
        blank=False,
        max_length=NAME_MAX_LENGTH,
    )
    last_name = models.CharField(
        'Фамилия',
        blank=False,
        max_length=NAME_MAX_LENGTH,
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username', 'id')

    def __str__(self):
        return self.username

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
                    logger.info(
                        f'Аватар пользователя {self.username} успешно удален'
                    )
                    return True  # Возвращаем True, если аватар был удален
                else:
                    logger.warning(
                        f'Файл аватара для пользователя {self.username} '
                        'не найден'
                    )
            else:
                logger.warning(f'У пользователя {self.username} нет аватара')
            return False  # Возвращаем False, если аватар не был удален
        except ValidationError as ve:
            logger.error(
                'Ошибка валидации при удалении аватара пользователя '
                f'{self.username}: {str(ve)}'
            )
            raise ValidationError(f'Ошибка при удалении аватара: {str(ve)}')
        except Exception as e:
            logger.error(
                'Ошибка при удалении аватара пользователя '
                f'{self.username}: {str(e)}'
            )
            raise Exception(
                f'Произошла ошибка при удалении аватара: {str(e)}'
            )
