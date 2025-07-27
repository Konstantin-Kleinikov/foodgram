import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from recipes.models import Ingredient

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из JSON-файла с использованием bulk_create'

    def handle(self, *args, **kwargs):
        file_path = (Path(settings.BASE_DIR)
                     .parent / 'data' / 'ingredients.json'
                     )
        ingredients_list = []

        try:
            logger.info('Начинается загрузка данных')

            with open(file_path, 'r', encoding='utf-8') as file:
                logger.debug(f'Открыт файл: {file_path}')
                ingredients_data = json.load(file)
                logger.debug(f'Получено {len(ingredients_data)} записей')

            success_count = 0
            fail_count = 0

            # Собираем список объектов для массовой вставки
            for ingredient_data in ingredients_data:
                try:
                    ingredients_list.append(
                        Ingredient(
                            name=ingredient_data['name'],
                            measurement_unit=ingredient_data[
                                'measurement_unit'
                            ]
                        )
                    )
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    logger.error(
                        'Ошибка при обработке ингредиента '
                        f'{ingredient_data}: {str(e)}')

            # Массовая вставка данных
            with transaction.atomic():
                try:
                    created_count = len(
                        Ingredient.objects.bulk_create(
                            ingredients_list, batch_size=1000)
                    )
                    logger.info(f'Успешно создано {created_count} записей')

                except Exception as e:
                    logger.critical(f'Ошибка при массовой загрузке: {str(e)}')
                    raise

            logger.info(
                f'Загрузка завершена. Обработано: {success_count}, '
                f'Ошибок: {fail_count}'
            )
            self.stdout.write(self.style.SUCCESS('Данные успешно загружены'))

        except FileNotFoundError:
            logger.error(f'Файл не найден: {file_path}')
            self.stdout.write(self.style.ERROR('Файл не найден'))

        except json.JSONDecodeError:
            logger.error('Ошибка декодирования JSON')
            self.stdout.write(self.style.ERROR('Ошибка декодирования JSON'))

        except Exception as e:
            logger.critical(f'Критическая ошибка: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Произошла ошибка: {str(e)}'))
