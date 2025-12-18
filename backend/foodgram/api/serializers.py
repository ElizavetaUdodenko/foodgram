import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer as BaseCreateSerializer
from djoser.serializers import UserSerializer as BaseSerializer
from rest_framework import serializers

from social.models import Ingredient, Recipe, Tag


User = get_user_model()


class Base64ImageField(serializers.ImageField):

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='image.' + ext)

        return super().to_internal_value(data)


class UserSerializer(BaseSerializer):

    class Meta(BaseCreateSerializer.Meta):
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'avatar',
        )


class UserCreateSerializer(BaseCreateSerializer):

    class Meta(BaseCreateSerializer.Meta):
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'password'
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }


class AvatarUploadSerializer(serializers.Serializer):

    avatar = Base64ImageField(required=True, allow_null=True)

    def update(self, instance, validated_data):
        data = validated_data.get('avatar')

        if instance.avatar:
            instance.avatar.delete(save=False)
            instance.avatar = data
            instance.save()
        else:
            instance.avatar = data
            instance.save()

        return instance


class TagSerializer(serializers.ModelSerializer):

    class Meta():
        model = Tag
        fields = ('id', 'name', 'slug',)
        read_only_fields = ('id', 'name', 'slug',)


class IngredientSerializer(serializers.ModelSerializer):

    class Meta():
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit',)
        read_only_fields = ('id', 'name', 'measurement_unit',)


class RecipeSerializer(serializers.ModelSerializer):

    class Meta():
        model = Recipe
        fields = ('__all__',)