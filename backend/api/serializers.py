import logging
import re

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from djoser.serializers import (PasswordSerializer, UserCreateSerializer,
                                UserSerializer)
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from recipes.constants import (MIN_COOKING_TIME, MIN_INGREDIENT_AMOUNT,
                               MIN_INGREDIENT_ID, MIN_RECIPES_QTY)
from recipes.models import (Favorite, Follow, Ingredient, IngredientRecipe,
                            Recipe, ShoppingCart, Tag)

logger = logging.getLogger(__name__)

UserModel = get_user_model()


class FoodgramUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta(UserSerializer.Meta):
        model = UserModel
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        )

    def get_is_subscribed(self, user_instance):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user,
                following=user_instance
            ).exists()
        return False


class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = UserModel
        fields = ('email', 'username', 'first_name', 'last_name', 'password')

    def validate_username(self, value):
        # Обновленное регулярное выражение, разрешающее дефисы
        if not re.match(r'^[a-zA-Z0-9._-]+$', value):
            raise serializers.ValidationError(
                'Имя пользователя может содержать только буквы, цифры, '
                'точки, дефисы и нижние подчеркивания'
            )
        return value


class CustomPasswordSerializer(PasswordSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем явное указание полей
        self.fields['current_password'] = serializers.CharField(
            write_only=True,
            required=True
        )
        self.fields['new_password'] = serializers.CharField(
            write_only=True,
            required=True
        )

    def validate(self, attrs):
        # Получаем текущего пользователя из контекста
        user = self.context['request'].user

        # Получаем текущий пароль из данных запроса
        current_password = attrs.get('current_password')

        # Проверяем пароль
        if not user.check_password(current_password):
            raise ValidationError({
                'current_password': 'Неверный текущий пароль'
            })

        return super().validate(attrs)

    def update(self, instance, validated_data):
        # Метод update обязателен для работы сериализатора
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance


class FoodgramUserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(
        required=False,
        allow_null=True,
        help_text='Формат изображения: PNG, JPG, JPEG'
    )

    class Meta:
        model = UserModel
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class IngredientUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(
        validators=[
            MinValueValidator(MIN_INGREDIENT_ID),
            UniqueValidator(queryset=Ingredient.objects.all())
        ],
    )
    amount = serializers.IntegerField(
        validators=[MinValueValidator(MIN_INGREDIENT_AMOUNT)],
    )


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = fields


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True,)
    author = FoodgramUserSerializer()
    ingredients = IngredientRecipeSerializer(
        many=True,
        source='amount_ingredients'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )
        read_only_fields = fields

    def get_is_favorited(self, recipe):
        """Проверить наличие рецепта в избранном."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Favorite.objects.filter(
                user=request.user,
                recipe=recipe
            ).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        """Проверить наличие рецепта в списке покупок."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and ShoppingCart.objects.filter(
                user=request.user,
                recipe=recipe
            ).exists()
        )


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    ingredients = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField(),
            required=True
        ),
        required=True
    )
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(
        required=True,
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
            ),
        ]
    )

    class Meta:
        model = Recipe
        fields = [
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time'
        ]

    def _collect_validation_errors(self, errors):
        if errors:
            raise serializers.ValidationError(errors)
        return True

    def validate_ingredients(self, ingredients_list):
        errors = []

        if not ingredients_list:
            errors.append('Список ингредиентов не может быть пустым')

        ingredient_ids = set()
        non_existent_ids = set()
        duplicate_ids = set()

        for ingredient in ingredients_list:
            ingredient_id = ingredient['id']
            ingredient_amount = ingredient['amount']

            # Проверка на существование ингредиента
            if not Ingredient.objects.filter(id=ingredient_id).exists():
                non_existent_ids.add(ingredient_id)

            # Проверка на дубликаты
            if ingredient_id in ingredient_ids:
                duplicate_ids.add(ingredient_id)
            ingredient_ids.add(ingredient_id)

            # Проверка количества
            if ingredient_amount <= 0:
                errors.append(f'Количество ингредиента с ID {ingredient_id} '
                              'должно быть больше 0')

        # Формируем сообщения об ошибках
        if non_existent_ids:
            errors.append(
                'Не найдены ингредиенты с ID: '
                f'{", ".join(map(str, non_existent_ids))}'
            )

        if duplicate_ids:
            errors.append(
                'Дублируются ингредиенты с ID: '
                f'{", ".join(map(str, duplicate_ids))}'
            )

        self._collect_validation_errors(errors)
        return ingredients_list

    def validate_tags(self, tags_list):
        errors = []

        if not tags_list:
            errors.append('Список тегов не может быть пустым')

        # Находим дубликаты
        seen = set()
        duplicates = set()

        for tag_id in tags_list:
            if tag_id in seen:
                duplicates.add(tag_id)
            seen.add(tag_id)

        if duplicates:
            errors.append(
                f'Повторяются теги с ID: {", ".join(map(str, duplicates))}'
            )

        # Проверяем существование тегов
        existing_tags = set(
            Tag.objects.filter(
                id__in=tags_list
            ).values_list('id', flat=True)
        )
        non_existent_tags = set(tags_list) - existing_tags

        if non_existent_tags:
            errors.append(
                'Не найдены теги с ID: '
                f'{", ".join(map(str, non_existent_tags))}'
            )

        self._collect_validation_errors(errors)
        return tags_list

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                'Изображение обязательно для заполнения'
            )
        return value

    def create(self, validated_data):

        logger.info(
            f'Начинаем создание рецепта с данными: {validated_data}'
        )
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')

        recipe = super().create(validated_data)
        logger.debug(f'Рецепт создан с ID: {recipe.id}')

        recipe.tags.set(tags)
        logger.debug(f'Теги установлены: {tags}')

        # Подготавливаем данные для bulk_create
        ingredient_recipes = [
            IngredientRecipe(
                recipe=recipe,
                ingredient_id=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients
        ]

        # Массовая вставка данных
        IngredientRecipe.objects.bulk_create(ingredient_recipes)
        logger.info('Ингредиенты успешно добавлены для рецепта ID: '
                    f'{recipe.id}')

        logger.info(f'Рецепт успешно создан с ID: {recipe.id}')
        return recipe

    def update(self, instance, validated_data):
        logger.info(
            f'Начинаем обновление рецепта ID: {instance.id} '
            f'с данными: {validated_data}'
        )
        # Проверяем наличие обязательных полей
        required_fields = ['tags', 'ingredients']
        missing_fields = [
            field for field in required_fields if field not in validated_data
        ]

        if missing_fields:
            raise serializers.ValidationError({
                field: 'Это поле обязательно' for field in missing_fields
            })

        # Обработка ингредиентов
        ingredient_data = validated_data.pop('ingredients', [])
        logger.debug(
            f'Обновляем ингредиенты для рецепта ID: {instance.id}'
        )

        # Очищаем текущие ингредиенты
        instance.ingredients.clear()
        logger.debug(
            f'Ингредиенты для рецепта ID: {instance.id} очищены'
        )

        # Собираем все ID ингредиентов
        ingredient_ids = [item['id'] for item in ingredient_data]

        # Получаем существующие ингредиенты одним запросом
        existing_ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
        existing_ingredient_ids = set(existing_ingredients.values_list(
            'id', flat=True)
        )

        # Проверяем наличие всех ингредиентов
        missing_ids = set(ingredient_ids) - existing_ingredient_ids
        if missing_ids:
            raise serializers.ValidationError(
                'Не найдены ингредиенты с ID: '
                f'{", ".join(map(str, missing_ids))}'
            )

        # Создаем словарь для быстрого доступа
        ingredient_map = {
            ingredient.id: ingredient for ingredient in existing_ingredients
        }

        # Формируем список объектов для bulk_create
        ingredient_recipes = [
            IngredientRecipe(
                recipe=instance,
                ingredient=ingredient_map[item['id']],
                amount=item['amount']
            )
            for item in ingredient_data
        ]

        # Массовая вставка данных
        IngredientRecipe.objects.bulk_create(ingredient_recipes)
        logger.info(
            f'Ингредиенты успешно обновлены для рецепта ID: {instance.id}'
        )

        # Обработка тегов
        tags = validated_data.pop('tags', [])
        logger.debug(f'Обновляем теги для рецепта ID: {instance.id}')
        instance.tags.set(tags)
        logger.debug(f'Теги обновлены: {tags}')

        # Обновление остальных полей
        update_data = {
            attr: value
            for attr, value in validated_data.items()
            if hasattr(instance, attr)
        }

        # Обновляем поля
        for attr, value in update_data.items():
            setattr(instance, attr, value)
            logger.debug(
                f'Обновлено поле {attr} = {value} для рецепта '
                f'ID: {instance.id}'
            )

        instance.save()
        logger.info(f'Рецепт ID: {instance.id} успешно обновлен')
        return instance

    def to_representation(self, instance):
        return RecipeSerializer(
            instance,
            context=self.context
        ).data


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )


class UserFollowSerializer(FoodgramUserSerializer):
    """Сериализатор получения информации о подписке текущего пользователя."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )

    class Meta(FoodgramUserSerializer.Meta):
        # Получаем базовые поля из родительского Meta
        fields = FoodgramUserSerializer.Meta.fields + (
            'recipes',
            'recipes_count'
        )
        read_only_fields = fields

    def get_recipes(self, user):
        request = self.context.get('request')
        # Используем "бесконечность" для максимального значения
        recipes_limit = int(request.GET.get('recipes_limit', 10 ** 10))
        limit = int(request.GET.get('limit', 10 ** 10))

        # Определяем финальное значение limit
        final_limit = max(min(recipes_limit, limit), MIN_RECIPES_QTY)

        # Получаем рецепты с учетом лимита
        recipes = user.recipes.all()[:final_limit]
        return RecipeShortSerializer(
            recipes,
            many=True,
            context={'request': request}
        ).data
