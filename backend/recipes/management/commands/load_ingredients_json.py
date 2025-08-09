import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from recipes.models import Ingredient

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Command(BaseCommand):
    help = 'Сверхбыстрая загрузка продуктов из JSON'

    def handle(self, *args, **kwargs):
        file_path = Path(
            settings.BASE_DIR
        ).parent / 'data' / 'ingredients.json'

        try:
            logger.info('Начинается загрузка данных')

            with open(file_path, 'r', encoding='utf-8') as file:
                logger.debug(f'Открыт файл: {file_path}')
                ingredients_data = json.load(file)
                logger.debug(f'Получено {len(ingredients_data)} записей')

            # Предварительная валидация и подготовка данных
            valid_data = self.validate_data(ingredients_data)

            # Оптимизированная массовая вставка с параллелизмом
            with transaction.atomic():
                self.parallel_bulk_insert(valid_data)

            logger.info('Загрузка завершена успешно')
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

    def validate_data(self, data):
        """Предварительная валидация и подготовка данных"""
        valid_ingredients = []
        for item in data:
            try:
                name = item['name']
                unit = item['measurement_unit']
                if not name or not unit:
                    raise ValueError('Неполные данные')
                valid_ingredients.append((name, unit))
            except (KeyError, ValueError) as e:
                logger.warning(f'Пропущена запись {item}: {str(e)}')
        return valid_ingredients

    def parallel_bulk_insert(self, data):
        """Параллельная массовая вставка"""
        batch_size = 10000  # Размер батча для параллельной вставки
        batches = [data[i:i + batch_size]
                   for i in range(0, len(data), batch_size)]

        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(self.bulk_insert_batch, batches)

    def bulk_insert_batch(self, batch):
        """Вставка одного батча"""
        objects = [
            Ingredient(name=name, measurement_unit=unit)
            for name, unit in batch
        ]
        Ingredient.objects.bulk_create(objects, batch_size=len(batch))

        # Очищаем кеш запросов после каждого батча
        connection.close()

    def optimize_db_settings(self):
        """Оптимизация настроек БД перед массовой вставкой"""
        if connection.vendor == 'postgresql':
            # Отключаем триггеры и индексы для PostgreSQL
            with connection.cursor() as cursor:
                cursor.execute('SET synchronous_commit = off;')
                cursor.execute(
                    'ALTER TABLE recipes_ingredient DISABLE TRIGGER ALL;'
                )
                cursor.execute(
                    'LOCK TABLE recipes_ingredient IN EXCLUSIVE MODE;'
                )

        elif connection.vendor == 'sqlite':
            # Оптимизация для SQLite
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA synchronous = OFF;')
                cursor.execute('PRAGMA journal_mode = MEMORY;')

    def post_insert_cleanup(self):
        """Восстановление настроек БД после вставки"""
        try:
            if connection.vendor == 'postgresql':
                # Включаем обратно триггеры и индексы
                with connection.cursor() as cursor:
                    cursor.execute(
                        'ALTER TABLE recipes_ingredient ENABLE TRIGGER ALL;'
                    )
                    cursor.execute('ANALYZE recipes_ingredient;')
                    cursor.execute('VACUUM recipes_ingredient;')
                    cursor.execute('SET synchronous_commit = on;')

            elif connection.vendor == 'sqlite':
                # Возвращаем стандартные настройки
                with connection.cursor() as cursor:
                    cursor.execute('PRAGMA synchronous = NORMAL;')
                    cursor.execute('PRAGMA journal_mode = DELETE;')
                    cursor.execute('VACUUM;')

            # Очищаем кеш запросов
            connection.close()
            logger.info('Настройки БД восстановлены')

        except Exception as e:
            logger.error(f'Ошибка при восстановлении настроек БД: {str(e)}')
            raise
