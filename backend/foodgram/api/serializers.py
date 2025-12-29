import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer as BaseCreateSerializer
from djoser.serializers import UserSerializer as BaseSerializer
from rest_framework import serializers

from social.models import (
    Favorite,
    Follow,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag
)


User = get_user_model()


class Base64ImageField(serializers.ImageField):

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='image.' + ext)
        return super().to_internal_value(data)


class UserSerializer(BaseSerializer):

    is_subscribed = serializers.SerializerMethodField()

    class Meta(BaseCreateSerializer.Meta):
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return (
                Follow.objects
                .filter(user=request.user, follows=obj)
                .exists()
            )
        return False


class UserCreateSerializer(BaseCreateSerializer):

    class Meta(BaseCreateSerializer.Meta):
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }


class AvatarUploadSerializer(serializers.Serializer):

    avatar = Base64ImageField(required=True, allow_null=True)

    def update(self, instance, validated_data):
        avatar = validated_data.get('avatar')
        if instance.avatar:
            instance.delete_avatar()
        instance.avatar = avatar
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


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0.01, coerce_to_string=False,
    )

    class Meta():
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount',)


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer()
    is_favorited = serializers.SerializerMethodField()
    tags = TagSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
    )
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta():
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'name',
            'image',
            'text',
            'cooking_time',
            'is_in_shopping_cart',
        )

    def _is_filter_match(self, model, user, recipe):
        return model.objects.filter(user=user, recipe=recipe).exists()

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return self._is_filter_match(Favorite, request.user, obj)
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return self._is_filter_match(ShoppingCart, request.user, obj)
        return False


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        allow_null=False,
        allow_empty=False,
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=True,
        allow_null=False,
        allow_empty=False,
    )
    image = Base64ImageField(required=True)

    class Meta():
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'name',
            'image',
            'text',
            'cooking_time',
        )
        extra_kwargs = {
            'name': {'required': True, 'allow_null': False},
            'text': {'required': True, 'allow_null': False},
            'cooking_time': {'required': True, 'allow_null': False},
        }

    def validate_ingredients(self, value):
        ingredient_ids = []
        for ingredient in value:
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError(
                    'Количество должно быть больше 0.'
                )
            if not Ingredient.objects.filter(pk=ingredient['id']).exists():
                raise serializers.ValidationError(
                    'Вы пытаетесь добавить несуществующий ингредиент.'
                )
            ingredient_ids.append(ingredient['id'])

        if len(ingredient_ids) > len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не могут повторяться.'
            )

        return value

    def validate_tags(self, value):
        tag_ids = [tag_id for tag_id in value]
        if len(tag_ids) > len(set(tag_ids)):
            raise serializers.ValidationError(
                'Теги не могут повторяться.'
            )
        return value

    def validate(self, attrs):
        if 'ingredients' not in attrs:
            raise serializers.ValidationError('Добавьте ингредиенты.')
        if 'tags' not in attrs:
            raise serializers.ValidationError('Добавьте теги.')
        return attrs

    def set_ingredients(self, recipe, ingredients):
        recipe_ingredient_objects = []
        for ingredient_data in ingredients:
            ingredient = Ingredient.objects.get(pk=ingredient_data['id'])
            recipe_ingredient_objects.append(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=ingredient_data['amount']
                )
            )
        RecipeIngredient.objects.bulk_create(recipe_ingredient_objects)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.set_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        image = validated_data.get('image', None)
        if image and instance.image:
            instance.delete_image()
            instance.image = image
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time
        )

        ingredients = validated_data.pop('ingredients')
        instance.recipe_ingredients.all().delete()
        self.set_ingredients(instance, ingredients)

        tags = validated_data.pop('tags')
        instance.tags.set(tags)

        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class RecipeShortenSerializer(serializers.ModelSerializer):

    class Meta():
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time',)
        read_only_fields = ('id', 'name', 'image', 'cooking_time',)


class FollowSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        recipes_limit = self.context.get('recipes_limit')
        following_user_recipes = obj.recipes.all().order_by('id')
        if recipes_limit:
            following_user_recipes = following_user_recipes[:recipes_limit]
        return RecipeShortenSerializer(following_user_recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
