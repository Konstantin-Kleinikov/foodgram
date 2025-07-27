import string
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from django.utils import timezone


def encode_base62(num):
    alphabet = string.ascii_letters + string.digits
    if num == 0:
        return alphabet[0]
    arr = []
    while num:
        num, rem = divmod(num, 62)
        arr.append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)


def decode_base62(short_code):
    alphabet = string.ascii_letters + string.digits
    num = 0
    for char in short_code:
        num = num * 62 + alphabet.index(char)
    return num


def create_shopping_cart_xml(user, ingredients):
    root = Element('ShoppingCart')
    user_element = SubElement(root, 'User')
    user_element.set('name', user.get_full_name())
    user_element.set('date', timezone.now().strftime('%d.%m.%Y'))

    for ingredient, amount in ingredients.items():
        ingredient_element = SubElement(user_element, 'Ingredient')
        SubElement(ingredient_element, 'Name').text = ingredient
        SubElement(ingredient_element, 'Amount').text = str(amount)
        SubElement(ingredient_element, 'MeasurementUnit').text = 'г.'

    return prettify(root)


def prettify(elem):
    """Возвращает красиво отформатированную XML строку"""
    rough_string = tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="\t", encoding='utf-8').decode('utf-8')
