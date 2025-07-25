# Generated by Django 4.2.23 on 2025-07-13 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Введите название ингредиента (до 128 символов)', max_length=128, verbose_name='Наименование')),
                ('measurement_unit', models.CharField(help_text='Укажите единицу измерения (до 64 символов)', max_length=64, verbose_name='Ингредиент')),
            ],
            options={
                'verbose_name': 'ингредиент',
                'verbose_name_plural': 'Ингредиенты',
                'ordering': ('name', 'id'),
            },
        ),
    ]
