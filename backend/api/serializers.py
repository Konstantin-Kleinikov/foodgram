import base64
import re
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile
from PIL import Image
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.constants import (EMAIL_MAX_LENGTH, NAME_MAX_LENGTH,
                           USERNAME_MAX_LENGTH, USERNAME_REGEX)
from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag

UserModel = get_user_model()


class Base64ImageField(serializers.ImageField):
    # def to_internal_value(self, data):
    #     if isinstance(data, str) and data.startswith('data:image'):
    #         format, imgstr = data.split(';base64,')
    #         ext = format.split('/')[-1]
    #         data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
    #     return super().to_internal_value(data)
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
                raise ValidationError(f"Ошибка при обработке изображения: {str(e)}")
        return super().to_internal_value(data)


class FoodgramUserBaseSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для пользователей"""
    email = serializers.EmailField(
        max_length=EMAIL_MAX_LENGTH,
    )
    username = serializers.CharField(
        max_length=USERNAME_MAX_LENGTH,
        # validators=[UniqueValidator(queryset=UserModel.objects.all())]
    )
    first_name = serializers.CharField(
        required=True,
        max_length=NAME_MAX_LENGTH,
    )
    last_name = serializers.CharField(
        required=True,
        max_length=NAME_MAX_LENGTH,
    )

    def validate_username(self, value):
        if not re.match(USERNAME_REGEX, value):
            raise serializers.ValidationError(
                "Недопустимые символы в username. Разрешены буквы, цифры и символы @ . _ + -"
            )
        if UserModel.objects.filter(username=value).exists():
            raise serializers.ValidationError(f'Указанный логин пользователя {value} уже используется.')
        return value

    def validate_email(self, value):
        if UserModel.objects.filter(email=value).exists():
            raise serializers.ValidationError(f'Указанный адрес электронной почты {value} уже используется.')
        return value

    class Meta:
        model = UserModel
        fields = ('email', 'username', 'first_name', 'last_name', 'avatar')


class FoodgramUserCreateResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ('email', 'id', 'username', 'first_name', 'last_name')
        read_only_fields = ('id',)


class FoodgramUserCreateSerializer(FoodgramUserBaseSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        style={'input_type': 'password'}
    )

    class Meta(FoodgramUserBaseSerializer.Meta):
        fields = FoodgramUserBaseSerializer.Meta.fields + ('password',)
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = UserModel(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value


class FoodgramUserListSerializer(FoodgramUserBaseSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(read_only=True)

    class Meta(FoodgramUserBaseSerializer.Meta):
        fields = FoodgramUserBaseSerializer.Meta.fields + ('id', 'is_subscribed')
        read_only_fields = ('id',)

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        # if request and request.user.is_authenticated:  # TODO
        #     return obj.followers.filter(user=request.user).exists()
        return False


class FoodgramUserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = UserModel
        fields = ('avatar',)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        max_length=128,
        style={'input_type': 'password'}
    )

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise ValidationError("Неверный существующий пароль")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, data):
        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError("Новый пароль должен отличаться от текущего")
        return data


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


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeListSerializer(serializers.ModelSerializer):
 tags = TagSerializer(many=True, read_only=True)
 author = FoodgramUserListSerializer(read_only=True)
 ingredients = IngredientRecipeSerializer(many=True, read_only=True, source='amount_ingredients')
 is_favorited = serializers.BooleanField(read_only=True, default=False)  # TODO Убрать дефолты
 is_in_shopping_cart = serializers.BooleanField(read_only=True, default=False)  # TODO Убрать дефолты

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


class RecipeDetailSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = FoodgramUserListSerializer(read_only=True)
    ingredients = IngredientRecipeSerializer(many=True, read_only=True, source='amount_ingredients')
    is_favorited = serializers.BooleanField(read_only=True, default=False)  # TODO Убрать дефолты)
    is_in_shopping_cart = serializers.BooleanField(read_only=True, default=False)  # TODO Убрать дефолты)

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


class RecipeCreateSerializer(serializers.ModelSerializer):
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
    name = serializers.CharField(required=True)
    text = serializers.CharField(required=True)
    cooking_time = serializers.IntegerField(required=True)

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

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Список ингредиентов не может быть пустым")
        return value

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError("Время приготовления должно быть больше 0")
        return value

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError("Изображение обязательно для заполнения")
        return value

    def create(self, validated_data):
        # Сохраняем рецепт
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')

        recipe = Recipe.objects.create(**validated_data)

        # Связываем теги
        recipe.tags.set(tags)

        # Обрабатываем ингредиенты
        for ingredient_data in ingredients:
            ingredient_id = ingredient_data['id']
            amount = ingredient_data['amount']

            try:
                ingredient = Ingredient.objects.get(id=ingredient_id)
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(f"Ингредиент с ID {ingredient_id} не найден")

            IngredientRecipe.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
            )

        return recipe

    def to_representation(self, instance):
        # Используем существующий RecipeDetailSerializer для корректной сериализации
        return RecipeDetailSerializer(instance).data
