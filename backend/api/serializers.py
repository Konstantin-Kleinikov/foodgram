import base64
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from api.constants import (EMAIL_MAX_LENGTH, NAME_MAX_LENGTH,
                           USERNAME_MAX_LENGTH, USERNAME_REGEX)
from api.models import Tag

UserModel = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
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
