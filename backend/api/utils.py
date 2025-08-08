import os
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring

from django.template import Context, Template
from dotenv import load_dotenv
from rest_framework.request import Request

# Загрузка переменных окружения
load_dotenv()
EXPORT_FORMAT = os.getenv('SHOPPING_CART_EXPORT_FORMAT', 'txt')


def create_shopping_cart(request: Request, user, ingredients, recipes):
    """
    Создает представление корзины покупок в формате, заданном в окружении
    """
    grouped_ingredients = group_ingredients(ingredients)

    if EXPORT_FORMAT == 'txt':
        return create_shopping_cart_txt(user, grouped_ingredients, recipes)
    else:
        return create_shopping_cart_xml(user, grouped_ingredients)


def group_ingredients(ingredients):
    grouped = {}
    for ingredient_with_unit, amount in ingredients.items():
        key = (ingredient_with_unit)
        if key in grouped:
            grouped[key] += amount
        else:
            grouped[key] = amount
    return grouped


def create_shopping_cart_txt(user, ingredients, recipes):
    # Преобразуем ингредиенты в удобный формат
    formatted_ingredients = [
        (name, amount)  # Оставляем просто кортеж
        for name, amount in ingredients.items()
    ]

    # Создаем контекст для шаблона
    context = {
        'user_name': user.get_full_name(),
        'date': datetime.now().strftime('%d.%m.%Y'),
        'ingredients': formatted_ingredients,
        'recipes': recipes
    }

    # Определяем шаблон для TXT формата
    template = Template('''
        Отчёт по покупкам для {{ user_name }}
        Дата: {{ date }}

        Список продуктов:
        ----------------
        {% for ingredient_name, amount in ingredients %}
        {{ forloop.counter }}. {{ ingredient_name|title }} - {{ amount }}
        {% endfor %}

        Рецепты:
        --------
        {% for recipe in recipes %}
        * {{ recipe.name|title }} (автор: {{ recipe.author.get_full_name }})
        {% endfor %}
        ''')

    return template.render(Context(context))


def create_shopping_cart_xml(user, ingredients):
    root = Element('ShoppingCart')
    user_element = SubElement(root, 'User')
    user_element.set('name', user.get_full_name())
    user_element.set('date', datetime.now().strftime('%d.%m.%Y'))

    for (name, measurement_unit), total_amount in ingredients.items():
        ingredient_element = SubElement(user_element, 'Ingredient')
        SubElement(ingredient_element, 'Name').text = name
        SubElement(ingredient_element, 'Amount').text = str(total_amount)
        SubElement(
            ingredient_element, 'MeasurementUnit'
        ).text = measurement_unit

    return prettify(root)


def prettify(elem):
    from xml.dom import minidom
    rough_string = tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="\t", encoding='utf-8').decode('utf-8')
