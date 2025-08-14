"""
Командный менеджер для загрузки данных в формате json.

# Для загрузки тегов
python manage.py load_data --data_type=tags

# Для загрузки ингредиентов
python manage.py load_data --data_type=ingredients
"""
import json
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Импорт данных из JSON-файла'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data_type',
            type=str,
            required=True,
            choices=['tags', 'ingredients'],
            help='Тип данных для загрузки (tags или ingredients)'
        )

    def handle(self, *args, **kwargs):
        data_type = kwargs['data_type']

        # Определяем путь к файлу
        file_path = Path(
            settings.BASE_DIR
        ).parent / 'data' / f"{data_type}.json"

        try:
            # Определяем модель на основе типа данных
            if data_type == 'tags':
                model = apps.get_model(
                    'recipes', 'Tag'
                )
            elif data_type == 'ingredients':
                model = apps.get_model(
                    'recipes', 'Ingredient'
                )
            else:
                raise ValueError('Неверный тип данных')

            with open(file_path, encoding='utf-8') as file:
                data = json.load(file)
                created = model.objects.bulk_create(
                    (model(**item) for item in data),
                    ignore_conflicts=True
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Добавлено {len(created)} объектов из '
                        f'файла "{file_path}"'
                    )
                )

        except FileNotFoundError:
            self.stderr.write(
                self.style.ERROR(f'Файл {file_path} не найден')
            )
        except json.JSONDecodeError:
            self.stderr.write(
                self.style.ERROR('Ошибка при чтении JSON файла')
            )
        except LookupError:
            self.stderr.write(
                self.style.ERROR(f'Модель для {data_type} не найдена')
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Произошла ошибка: {e}')
            )
