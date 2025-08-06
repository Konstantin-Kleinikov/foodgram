from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from django.utils import timezone


def create_shopping_cart_xml(user, ingredients):
    """
        Создает XML-представление корзины покупок с группировкой ингредиентов
        по названию и единице измерения.

        Параметры:
            user (User): Объект пользователя, для которого формируется корзина
            ingredients (dict): Словарь ингредиентов, где ключ -
                                объект Ingredient, а значение -
                                количество ингредиента

        Возвращает:
            str: Форматированную XML-строку с данными корзины покупок

        Структура выходного XML:
        <ShoppingCart>
            <User name="Имя пользователя" date="ДД.ММ.ГГГГ">
                <Ingredient>
                    <Name>Название ингредиента</Name>
                    <Amount>Количество</Amount>
                    <MeasurementUnit>Единица измерения</MeasurementUnit>
                </Ingredient>
                ...
            </User>
        </ShoppingCart>

        Особенности работы:
        - Ингредиенты группируются по названию и единице измерения
        - Количества одинаковых ингредиентов суммируются
        - Дата формируется в формате ДД.ММ.ГГГГ
        - XML выводится в отформатированном виде с отступами
        """
    grouped_ingredients = {}
    for ingredient, amount in ingredients.items():
        key = (ingredient.name, ingredient.measurement_unit)
        if key in grouped_ingredients:
            grouped_ingredients[key] += amount
        else:
            grouped_ingredients[key] = amount

    root = Element('ShoppingCart')
    user_element = SubElement(root, 'User')
    user_element.set('name', user.get_full_name())
    user_element.set('date', timezone.now().strftime('%d.%m.%Y'))

    for (name, measurement_unit), total_amount in grouped_ingredients.items():
        ingredient_element = SubElement(user_element, 'Ingredient')
        SubElement(ingredient_element, 'Name').text = name
        SubElement(ingredient_element, 'Amount').text = str(total_amount)
        SubElement(
            ingredient_element,
            'MeasurementUnit'
        ).text = measurement_unit

    return prettify(root)


def prettify(elem):
    """Возвращает красиво отформатированную XML строку"""
    rough_string = tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="\t", encoding='utf-8').decode('utf-8')
