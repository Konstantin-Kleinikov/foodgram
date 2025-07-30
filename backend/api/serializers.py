import base64
import logging
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from django.core.validators import (MaxLengthValidator, MinLengthValidator,
                                    MinValueValidator)
from djoser.serializers import UserCreateSerializer, UserSerializer
from PIL import Image
from rest_framework import exceptions, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from recipes.constants import (MAX_INGREDIENTS, MAX_RECIPES_LIMIT, MAX_TAGS,
                               MIN_RECIPES_LIMIT, RECIPE_NAME_MAX_LENGTH,
                               USERNAME_FORBIDDEN)
from recipes.models import (Favorite, Follow, Ingredient, IngredientRecipe,
                            Recipe, ShoppingCart, Tag)

logger = logging.getLogger(__name__)

UserModel = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            try:
                # Разделяем формат и данные
                format, imgstr = data.split(';base64,')
                ext = format.split('/')[-1]
                # Декодируем base64
                decoded_data = base64.b64decode(imgstr)
                # Проверяем, что это действительно изображение
                image = Image.open(BytesIO(decoded_data))
                image.verify()
                image.close()
                # Создаем файл
                data = ContentFile(decoded_data, name=f'temp.{ext}')
            except Exception as e:
                raise ValidationError(
                    f'Ошибка при обработке изображения: {str(e)}'
                )
        return super().to_internal_value(data)


class FoodgramUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
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

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user,  # кто подписан (текущий пользователь)
            ).exists()
        return False

    def get_avatar(self, obj):
        # Возвращаем URL аватара или None, если нет изображения
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None

    def to_representation(self, instance):
        # Проверяем тип пользователя
        if isinstance(instance, AnonymousUser):
            raise exceptions.AuthenticationFailed(
                'Не предоставлены данные для аутентификации'
            )
        return super().to_representation(instance)


class FoodgramUserCreateSerializer(UserCreateSerializer):
    def validate_username(self, value):
        if value.lower() in USERNAME_FORBIDDEN:
            raise serializers.ValidationError(
                f'Указанное значение пользователя "{value}" запрещено'
            )
        return value

    def validate(self, data):
        # Проверяем обязательные поля
        if not data.get('first_name'):
            raise serializers.ValidationError(
                {'first_name': 'Это поле обязательно'}
            )
        if not data.get('last_name'):
            raise serializers.ValidationError(
                {'last_name': 'Это поле обязательно'}
            )
        return data

    class Meta(UserCreateSerializer.Meta):
        model = UserModel
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password'
        )
        extra_kwargs = {
            'password': {'write_only': True}
        }


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
        read_only_fields = ['id']
        extra_kwargs = {
            'slug': {'required': False}
        }


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']
        read_only_fields = ['id']


class IngredientUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(
        validators=[MinValueValidator(1)],
        error_messages={
            'min_value': 'ID ингредиента должен быть положительным'
        }
    )
    amount = serializers.IntegerField(
        validators=[MinValueValidator(1)],
        error_messages={
            'min_value': 'Количество должно быть положительным'
        }
    )


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = FoodgramUserSerializer(read_only=True)
    ingredients = IngredientRecipeSerializer(
        many=True,
        read_only=True,
        source='amount_ingredients'
    )
    is_favorited = serializers.SerializerMethodField(
        read_only=True,
    )
    is_in_shopping_cart = serializers.SerializerMethodField(
        read_only=True,
    )

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

    def get_is_favorited(self, obj):
        """Проверить наличие рецепта в избранном."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Favorite.objects.filter(user=request.user, recipe=obj)
            .exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Проверить наличие рецепта в списке покупок."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and ShoppingCart.objects.filter(user=request.user, recipe=obj)
            .exists()
        )


class RecipeDetailSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = FoodgramUserSerializer(read_only=True)
    ingredients = IngredientRecipeSerializer(
        many=True,
        read_only=True,
        source='amount_ingredients'
    )
    is_favorited = serializers.SerializerMethodField(
        read_only=True,
    )
    is_in_shopping_cart = serializers.SerializerMethodField(
        read_only=True,
    )

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

    def get_is_favorited(self, obj):
        """Проверить наличие рецепта в избранном."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Favorite.objects.filter(user=request.user, recipe=obj)
            .exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Проверить наличие рецепта в списке покупок."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and ShoppingCart.objects.filter(user=request.user, recipe=obj)
            .exists()
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
    name = serializers.CharField(
        required=True,
        validators=[
            MaxLengthValidator(
                RECIPE_NAME_MAX_LENGTH,
                message='Название рецепта не может превышать 256 символов'
            ),
            MinLengthValidator(
                1,
                message='Название рецепта не может быть пустым'
            ),
        ]
    )
    text = serializers.CharField(required=True)
    cooking_time = serializers.IntegerField(
        required=True,
        validators=[
            MinValueValidator(
                1,
                message='Время приготовления должно быть больше 0'
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_update = kwargs.get('context', {}).get('is_update', False)
        if self.is_update:
            self.fields['ingredients'] = IngredientUpdateSerializer(
                many=True,
                required=True
            )

    def validate(self, attrs):
        if 'ingredients' not in attrs:
            raise serializers.ValidationError({
                'ingredients': 'Поле ingredients обязательно для создания '
                               'и обновления рецепта'
            })

        if 'tags' not in attrs:
            raise serializers.ValidationError({
                'tags': 'Поле tags обязательно для создания '
                        'и обновления рецепта'
            })

        return attrs

    def validate_ingredients(self, value):
        if self.is_update:
            # Логика для обновления
            if value:
                ingredient_ids = [item['id'] for item in value]
                existing_ids = set(
                    Ingredient.objects.filter(id__in=ingredient_ids)
                    .values_list('id', flat=True)
                )
                if len(ingredient_ids) != len(existing_ids):
                    raise serializers.ValidationError(
                        'Указаны несуществующие ID ингредиентов'
                    )
        else:
            # Логика для создания
            if len(value) > MAX_INGREDIENTS:
                raise serializers.ValidationError(
                    f'Нельзя добавить более {MAX_INGREDIENTS} '
                    'ингредиентов в рецепт'
                )

            if not value:
                raise serializers.ValidationError(
                    'Список ингредиентов не может быть пустым'
                )

            ingredient_ids = set()
            for ingredient in value:
                if 'amount' not in ingredient:
                    raise serializers.ValidationError(
                        'Отсутствует поле amount у ингредиента'
                    )
                if 'id' not in ingredient:
                    raise serializers.ValidationError(
                        'Отсутствует поле id у ингредиента'
                    )
                ingredient_id = ingredient['id']
                if ingredient_id in ingredient_ids:
                    raise serializers.ValidationError(
                        f'Ингредиент с ID {ingredient_id} уже добавлен '
                        'в рецепт'
                    )
                ingredient_ids.add(ingredient_id)
                try:
                    Ingredient.objects.get(id=ingredient_id)
                except Ingredient.DoesNotExist:
                    raise serializers.ValidationError(
                        f'Ингредиент с ID {ingredient_id} не найден'
                    )
                if ingredient['amount'] <= 0:
                    raise serializers.ValidationError(
                        'Количество ингредиента должно быть больше 0'
                    )
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                'Список тегов не может быть пустым'
            )

        if len(value) > MAX_TAGS:
            raise serializers.ValidationError(
                f'Нельзя добавить более {MAX_TAGS} тегов в рецепт'
            )

        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                'Список тегов содержит повторяющиеся значения'
            )

        existing_tags = set(
            Tag.objects.filter(id__in=value).values_list(
                'id', flat=True
            )
        )
        missing_tags = set(value) - existing_tags
        if missing_tags:
            raise serializers.ValidationError(
                f'Теги с ID {", ".join(map(str, missing_tags))} не найдены '
                'в базе данных'
            )
        return value

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                'Изображение обязательно для заполнения'
            )
        return value

    def create(self, validated_data):
        try:
            logger.info(
                f'Начинаем создание рецепта с данными: {validated_data}'
            )
            tags = validated_data.pop('tags')
            ingredients = validated_data.pop('ingredients')

            recipe = Recipe.objects.create(**validated_data)
            logger.debug(f'Рецепт создан с ID: {recipe.id}')

            recipe.tags.set(tags)
            logger.debug(f'Теги установлены: {tags}')

            try:
                for ingredient_data in ingredients:
                    ingredient_id = ingredient_data['id']
                    amount = ingredient_data['amount']

                    try:
                        ingredient = Ingredient.objects.get(id=ingredient_id)
                    except Ingredient.DoesNotExist:
                        logger.error(
                            f'Ингредиент с ID {ingredient_id} не найден'
                        )
                        raise serializers.ValidationError(
                            f'Ингредиент с ID {ingredient_id} не найден'
                        )

                    IngredientRecipe.objects.create(
                        recipe=recipe,
                        ingredient=ingredient,
                        amount=amount
                    )
            except Exception as e:
                recipe.delete()
                logger.error(f'Ошибка при создании рецепта: {str(e)}')
                raise serializers.ValidationError(
                    f'Ошибка при создании рецепта: {str(e)}'
                )
            logger.info(f'Рецепт успешно создан с ID: {recipe.id}')
            return recipe
        except Exception as e:
            logger.critical(
                f'Критическая ошибка при создании рецепта: {str(e)}'
            )
            raise serializers.ValidationError(
                f'Произошла критическая ошибка: {str(e)}'
            )

    def update(self, instance, validated_data):
        try:
            logger.info(
                f'Начинаем обновление рецепта ID: {instance.id} '
                f'с данными: {validated_data}'
            )

            if 'ingredients' in validated_data:
                ingredient_data = validated_data.pop('ingredients')
                logger.debug(
                    f'Обновляем ингредиенты для рецепта ID: {instance.id}'
                )

                instance.ingredients.clear()
                logger.debug(
                    f'Ингредиенты для рецепта ID: {instance.id} очищены'
                )

                for item in ingredient_data:
                    ingredient_id = item['id']
                    amount = item['amount']

                    try:
                        ingredient = Ingredient.objects.get(id=ingredient_id)
                        logger.debug(
                            f'Найден ингредиент с ID: {ingredient_id}'
                        )
                    except Ingredient.DoesNotExist:
                        logger.error(
                            f'Ингредиент с ID {ingredient_id} не найден '
                            'при обновлении'
                        )
                        raise serializers.ValidationError(
                            f'Ингредиент с ID {ingredient_id} не найден'
                        )

                    instance.ingredients.add(
                        ingredient, through_defaults={'amount': amount}
                    )
                    logger.debug(
                        f'Добавлен ингредиент ID: {ingredient_id} '
                        f'с количеством {amount} в рецепт ID: {instance.id}'
                    )

            if 'tags' in validated_data:
                tags = validated_data.pop('tags')
                logger.debug(f'Обновляем теги для рецепта ID: {instance.id}')
                instance.tags.set(tags)
                logger.debug(f'Теги обновлены: {tags}')

            for attr, value in validated_data.items():
                setattr(instance, attr, value)
                logger.debug(
                    f'Обновлено поле {attr} = {value} для рецепта '
                    f'ID: {instance.id}'
                )

            instance.save()
            logger.info(f'Рецепт ID: {instance.id} успешно обновлен')
            return instance

        except Exception as e:
            logger.error(
                f'Ошибка при обновлении рецепта ID: {instance.id}: {str(e)}'
            )
            raise serializers.ValidationError(
                f'Ошибка при обновлении рецепта: {str(e)}'
            )

    def to_representation(self, instance):
        return RecipeDetailSerializer(
            instance,
            context=self.context
        ).data


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']


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

    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )
        read_only_fields = (
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')

        try:
            recipes_limit = int(request.query_params.get('recipes_limit', 0))
            limit = int(request.query_params.get('limit', 0))
        except ValueError:
            return []

        if recipes_limit:
            limit = min(max(
                recipes_limit, MIN_RECIPES_LIMIT), MAX_RECIPES_LIMIT
            )
        elif limit:
            limit = min(max(limit, MIN_RECIPES_LIMIT), MAX_RECIPES_LIMIT)
        else:
            limit = MAX_RECIPES_LIMIT  # По умолчанию возвращаем максимум

        recipes = obj.recipes.all()[:limit]

        return RecipeShortSerializer(
            recipes,
            many=True,
            context={'request': request}
        ).data

    def get_recipes_count(self, obj):
        # Кэшируем результат, чтобы избежать лишних запросов
        if not hasattr(obj, '_recipes_count'):
            obj._recipes_count = obj.recipes.count()
        return obj._recipes_count

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user,
                following=obj
            ).exists()
        return False


class UserFollowUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=('user', 'following'),
                message='Вы уже подписаны на этого пользователя'
            )
        ]

    def validate(self, data):
        if data['user'] == data['following']:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя!'
            )
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        return UserFollowSerializer(
            instance.following,
            context={'request': request}
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ['id', 'user', 'recipe']
        read_only_fields = ['user']

    def validate_recipe(self, value):
        try:
            Recipe.objects.get(pk=value.pk)
            return value
        except Recipe.DoesNotExist:
            raise serializers.ValidationError('Рецепт не найден')
