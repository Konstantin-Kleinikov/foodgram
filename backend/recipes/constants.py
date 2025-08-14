NAME_DISPLAY_LENGTH = 20
NAME_MAX_LENGTH = 150
TEXT_FIELDS_DISPLAY_LENGTH = 20

USERNAME_MAX_LENGTH = 150
USERNAME_REGEX = r'^[\w.@+-]+\Z'
PASSWORD_MAX_LENGTH = 128
EMAIL_MAX_LENGTH = 254

RECIPE_NAME_MAX_LENGTH = 256
MIN_RECIPES_LIMIT = 1
COOKING_TIME_MIN_VALUE = 1  # в минутах

TAG_MAX_LENGTH = 32
SLUG_MAX_LENGTH = 32

INGREDIENT_MAX_LENGTH = 128
INGREDIENT_MIN_VALUE = 1
UNIT_OF_MEASURE_MAX_LENGTH = 64


# Константы для фильтрации
FILTER_LESS_THAN = '<10'  # Значение фильтра "меньше 10"
FILTER_BETWEEN = '10-50'  # Значение фильтра "от 10 до 50"
FILTER_MORE_THAN = '>50'  # Значение фильтра "больше 50"
FILTER_LOW_VALUE = 1      # Минимальное значение для первой категории
FILTER_MIDDLE_VALUE = 10  # Граничное значение между первой и второй категорией
FILTER_HIGH_VALUE = 50    # Граничное значение для третьей категории
