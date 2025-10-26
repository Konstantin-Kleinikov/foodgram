"""
Сериализаторы для модели пользователя, рецептов, ингредиентов и тегов.
Обеспечивают сериализацию данных при работе с API.
"""

from collections import Counter

from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.constants import MIN_COOKING_TIME, MIN_INGREDIENT_AMOUNT
from recipes.models import (Favorite, Follow, Ingredient, IngredientRecipe,
                            Recipe, ShoppingCart, Tag)

User = get_user_model()


class FoodgramUserSerializer(UserSerializer):
    """
    Сериализатор пользователя. Добавляет поле 'is_subscribed' и 'avatar'.
    Используется для получения информации о пользователе и подписке на него.
    """

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (*DjoserUserSerializer.Meta.fields, 'avatar', 'is_subscribed')
        read_only_fields = fields

    def get_is_subscribed(self, user_instance):
        """
        Проверяет, подписан ли текущий пользователь на указанного пользователя.
        Возвращает True, если подписан, иначе False.
        """
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return False

        return (
            request.user.is_authenticated
            and Follow.objects.filter(
                user=request.user,
                following=user_instance
            ).exists()
        )


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения данных об ингредиентах в рецепте."""

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
    """Сериализатор для записи данных об ингредиентах в рецепт."""

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
    """
    Сериализатор для чтения рецепта. Включает информацию о тегах, авторе,
    ингредиентах, избранном и списке покупок.
    """

    tags = TagSerializer(many=True,)
    author = FoodgramUserSerializer()
    ingredients = IngredientRecipeReadSerializer(
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

    def check_user_status_and_recipe_exists(self, model, recipe):
        """
        Проверяет, существует ли связь между пользователем и рецептом
        через указанную модель (Favorite или ShoppingCart).
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        user_id = request.user.id
        return model.objects.filter(
            user_id=user_id, recipe=recipe
        ).exists()

    def get_is_favorited(self, recipe):
        """Проверяет, добавлен ли рецепт в избранное."""
        return self.check_user_status_and_recipe_exists(
            Favorite,
            recipe
        )

    def get_is_in_shopping_cart(self, recipe):
        """Проверяет, добавлен ли рецепт в список покупок."""
        return self.check_user_status_and_recipe_exists(
            ShoppingCart,
            recipe
        )


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания и обновления рецепта.
    Включает проверку ингредиентов, тегов и времени приготовления.
    """

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
        min_value=MIN_COOKING_TIME
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
        """ Проверяет, что обязательные поля переданы. """
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
        """Проверяет корректность переданных ингредиентов."""
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
                f'{duplicate_ids}'
            )

        if errors:
            raise serializers.ValidationError(errors)
        return ingredients

    def validate_tags(self, tags):
        """Проверяет корректность переданных тегов."""
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
        """Проверяет, что изображение передано."""
        if not value:
            raise serializers.ValidationError(
                'Изображение обязательно для заполнения'
            )
        return value

    def create_ingredients(self, ingredients, recipe):
        """Создаёт связи между рецептом и ингредиентами."""
        IngredientRecipe.objects.bulk_create(
            IngredientRecipe(
                recipe=recipe,
                ingredient_id=item['ingredient'].id,
                amount=item['amount']
            )
            for item in ingredients
        )

    def create(self, validated_data):
        """Создаёт новый рецепт с учётом тегов и ингредиентов."""

        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = super().create(validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        """Обновляет существующий рецепт."""
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        # Обработка продуктов
        instance.amount_ingredients.all().delete()
        self.create_ingredients(ingredients_data, instance)

        # Обработка тегов
        instance.tags.set(tags_data)

        # Завершающее обновление остального набора полей
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Возвращает данные рецепта в формате ReadSerializer."""
        return RecipeReadSerializer(
            instance,
            context=self.context
        ).data


class RecipeShortSerializer(serializers.ModelSerializer):
    """Краткий сериализатор рецепта. Используется в списках."""

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
    """
    Расширенный сериализатор пользователя. Добавляет поле 'is_subscribed'.
    """
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (*DjoserUserSerializer.Meta.fields,
                  'avatar', 'is_subscribed')
        read_only_fields = fields

    def get_is_subscribed(self, followed_user):
        """
        Проверяет, подписан ли текущий пользователь на указанного.
        """
        user = self.context['request'].user
        return user.is_authenticated and Follow.objects.filter(
            user=user, following=followed_user
        ).exists()


class UserFollowSerializer(UserSerializer):
    """Сериализатор подписки. Добавляет краткие рецепты и их количество."""

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
        """
        Возвращает краткую информацию о рецептах пользователя.
        Ограничивает количество рецептов, если указан параметр 'recipes_limit'.
        """
        return RecipeShortSerializer(
            user.recipes.all()[
                :int(self.context['request'].
                     GET.get('recipes_limit', 10 ** 10))
            ],
            many=True,
            context=self.context
        ).data
