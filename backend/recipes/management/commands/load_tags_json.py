# management/commands/load_tags.py
import json
import os
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from foodgram import settings
from recipes.models import Tag


class Command(BaseCommand):
    help = 'Загрузка тегов из JSON файла'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        file_path = Path(
            settings.BASE_DIR
        ).parent / 'data' / 'tags.json'

        # Проверяем существование файла
        if not os.path.exists(file_path):
            self.stderr.write(
                self.style.ERROR(f'Файл {file_path} не найден')
            )
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                tags_data = json.load(file)
        except json.JSONDecodeError:
            self.stderr.write(
                self.style.ERROR('Ошибка при чтении JSON файла')
            )
            return

        created_count = 0
        updated_count = 0

        for tag_data in tags_data:
            try:
                # Проверяем наличие обязательных полей
                if 'name' not in tag_data or 'slug' not in tag_data:
                    self.stderr.write(
                        self.style.ERROR(f'Пропущена запись: {tag_data}')
                    )
                    continue

                tag, created = Tag.objects.update_or_create(
                    slug=tag_data['slug'],
                    defaults={
                        'name': tag_data['name']
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except ValidationError as e:
                self.stderr.write(
                    self.style.ERROR(
                        f'Ошибка валидации для тега {tag_data}: {e}')
                )

        self.stdout.write(self.style.SUCCESS(
            f'Успешно обработано: {created_count} новых, '
            f'{updated_count} обновленных тегов'
        ))
