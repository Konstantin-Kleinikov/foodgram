import logging
from collections import Counter

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from djoser.serializers import UserSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.constants import MIN_COOKING_TIME, MIN_INGREDIENT_AMOUNT
from recipes.models import (Favorite, Follow, Ingredient, IngredientRecipe,
                            Recipe, ShoppingCart, Tag)

logger = logging.getLogger(__name__)

User = get_user_model()


class FoodgramUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (*DjoserUserSerializer.Meta.fields, 'avatar', 'is_subscribed')
        read_only_fields = fields

    def get_is_subscribed(self, user_instance):
        request = self.context.get('request')
        # Сначала проверяем наличие аутентификации.
        if not (request and getattr(request, 'user', None)
                and request.user.is_authenticated):
            return False

        # Выполняем запрос к Follow.
        return Follow.objects.filter(
            user=request.user,
            following=user_instance
        ).exists()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientUpdateSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
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


class IngredientRecipeWriteSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    amount = serializers.IntegerField(
        min_value=MIN_INGREDIENT_AMOUNT,
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
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

    def check_user_status_and_recipe_exists(self, queryset, recipe):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and queryset.filter(user=request.user, recipe=recipe).exists()
        )

    def get_is_favorited(self, recipe):
        """Проверить наличие рецепта в избранном."""
        return self.check_user_status_and_recipe_exists(
            Favorite.objects.all(),
            recipe
        )

    def get_is_in_shopping_cart(self, recipe):
        """Проверить наличие рецепта в списке покупок."""
        return self.check_user_status_and_recipe_exists(
            ShoppingCart.objects.all(),
            recipe
        )


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    ingredients = IngredientRecipeWriteSerializer(
        many=True,
        required=True,
        label='Продукты',
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=True,
        label='Теги',
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

    def validate(self, data):
        request_method = self.context['request'].method

        if request_method in ('POST', 'PATCH'):
            if 'ingredients' not in data:
                raise serializers.ValidationError(
                    {'ingredients': 'Это поле обязательно.'})
            if 'tags' not in data:
                raise serializers.ValidationError(
                    {'tags': 'Это поле обязательно.'})

        return data

    def validate_ingredients(self, ingredients):
        errors = []

        if not ingredients:
            errors.append('Список продуктов не может быть пустым')

        # Проверка дублирования
        duplicate_ids = {
            id_ for id_, count in
            Counter(item['ingredient'].id for item in ingredients).items()
            if count > 1
        }
        if duplicate_ids:
            errors.append(
                'Дублируются продукты с ID: '
                f'{sorted(duplicate_ids)}'
            )

        if errors:
            raise serializers.ValidationError(errors)
        return ingredients

    def validate_tags(self, tags):
        errors = []

        if not tags:
            errors.append('Список тегов не может быть пустым')

        # Находим дубликаты
        duplicate_ids = {
            id_ for id_, count in Counter(tags).items() if count > 1}

        if duplicate_ids:
            errors.append(
                f'Повторяются теги с ID: {sorted(duplicate_ids)}'
            )

        if errors:
            raise serializers.ValidationError(errors)
        return tags

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                'Изображение обязательно для заполнения'
            )
        return value

    def create_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create(
            IngredientRecipe(
                recipe=recipe,
                ingredient_id=item['ingredient'].id,
                amount=item['amount']
            )
            for item in ingredients
        )

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

        self.create_ingredients(ingredients, recipe)
        logger.info('Продукты успешно добавлены для ID рецепта: '
                    f'{recipe.id}')

        logger.info(f'Рецепт успешно создан с ID: {recipe.id}')
        return recipe

    def update(self, instance, validated_data):
        logger.info(
            f'Начинаем обновление ID рецепта: {instance.id} '
            f'с данными: {validated_data}'
        )
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        # Обработка продуктов
        if ingredients_data is not None:
            logger.debug(
                f'Обновляем продукты для ID рецепта: {instance.id}'
            )
            instance.amount_ingredients.all().delete()
            self.create_ingredients(ingredients_data, instance)
            logger.debug(f'Продукты обновлены: {ingredients_data}')

        # Обработка тегов
        if tags_data is not None:
            logger.debug(f'Обновляем теги для ID рецепта: {instance.id}')
            instance.tags.set(tags_data)
            logger.debug(f'Теги обновлены: {tags_data}')

        # Завершающее обновление остального набора полей
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(
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
        read_only_fields = fields


class UserSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    def get_is_subscribed(self, followed_user):
        user = self.context['request'].user
        return user.is_authenticated and Follow.objects.filter(
            user=user, following=followed_user
        ).exists()

    class Meta:
        model = User
        fields = (*DjoserUserSerializer.Meta.fields,
                  'avatar', 'is_subscribed')
        read_only_fields = fields


class UserFollowSerializer(UserSerializer):
    """Сериализатор получения информации о подписке текущего пользователя."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )

    class Meta:
        model = User
        fields = (*UserSerializer.Meta.fields,
                  'recipes', 'recipes_count')
        read_only_fields = fields

    def get_recipes(self, user):
        return RecipeShortSerializer(
            user.recipes.all()[
                :int(self.context['request'].
                     GET.get('recipes_limit', 10 ** 10))
            ],
            many=True,
            context=self.context
        ).data
