NAME_DISPLAY_LENGTH = 20
NAME_MAX_LENGTH = 150
TEXT_FIELDS_DISPLAY_LENGTH = 20

USERNAME_MAX_LENGTH = 150
USERNAME_REGEX = r'^[\w.@+-]+\Z'
EMAIL_MAX_LENGTH = 254

RECIPE_NAME_MAX_LENGTH = 256
MIN_RECIPES_QTY = 1
MIN_COOKING_TIME = 1  # в минутах

TAG_MAX_LENGTH = 32
SLUG_MAX_LENGTH = 32

INGREDIENT_MAX_LENGTH = 128
INGREDIENT_MIN_QTY = 1
UNIT_OF_MEASURE_MAX_LENGTH = 64
MIN_INGREDIENT_AMOUNT = 1

# Константы для фильтрации
FILTER_LESS_THAN = '<10'  # Значение фильтра "меньше ..."
FILTER_BETWEEN = '10-50'  # Значение фильтра "от ... до ..."
FILTER_MORE_THAN = '>50'  # Значение фильтра "больше ..."
FILTER_LESS_THAN_NAME = 'Менее 10 рецептов'  # Имя фильтра "меньше ..."
FILTER_BETWEEN_NAME = 'От 10 до 50 рецептов'  # Имя фильтра "от ... до ..."
FILTER_MORE_THAN_NAME = 'Более 50 рецептов'  # Имя фильтра "больше ..."
FILTER_LOW_VALUE = 1      # Минимальное значение для первой категории
FILTER_MIDDLE_VALUE = 10  # Граничное значение между первой и второй категорией
FILTER_HIGH_VALUE = 50    # Граничное значение для третьей категории
