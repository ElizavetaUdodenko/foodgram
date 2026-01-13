import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag
)
from users.models import Follow


User = get_user_model()


class RelationWriteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating user-object records for
    Favorite, ShoppingCart, Follow models.
    """

    model = None
    model_field = None
    context_key = None
    response_serializer = None
    error_message = None

    def get_record_data(self):
        return {
            'user': self.context['request'].user,
            self.model_field: self.context[self.context_key]
        }

    def validate(self, attrs):
        if self.model.objects.filter(**self.get_record_data()).exists():
            raise serializers.ValidationError(self.error_message)
        return attrs

    def create(self, validated_data):
        return self.model.objects.create(**self.get_record_data())

    def to_representation(self, instance):
        return self.response_serializer(
            getattr(instance, self.model_field),
            context=self.context
        ).data


class Base64ImageField(serializers.ImageField):

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='image.' + ext)
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
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
        return (
            request
            and request.user.is_authenticated
            and (
                Follow.objects
                .filter(user=request.user, follows=obj)
                .exists()
            )
        )


class AvatarUploadSerializer(serializers.Serializer):

    avatar = Base64ImageField(required=True, allow_null=True)

    def update(self, instance, validated_data):
        avatar = validated_data.get('avatar')
        if instance.avatar is not None:
            instance.avatar.delete(save=False)
            instance.avatar = avatar
            instance.save(update_fields=('avatar',))
        return instance


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug',)


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit',)


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount',)


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipe_ingredients',
        read_only=True
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
            'name',
            'image',
            'text',
            'cooking_time',
            'is_in_shopping_cart',
        )

    @staticmethod
    def is_record_exist(model, user, recipe):
        return model.objects.filter(user=user, recipe=recipe).exists()

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and RecipeReadSerializer.is_record_exist(
                Favorite, request.user, obj
            )
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and RecipeReadSerializer.is_record_exist(
                ShoppingCart, request.user, obj
            )
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipe_ingredients',
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

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def validate(self, attrs):
        if 'recipe_ingredients' not in attrs:
            raise serializers.ValidationError('Добавьте ингредиенты.')
        if 'tags' not in attrs:
            raise serializers.ValidationError('Добавьте теги.')

        ingredient_ids = [
            ingredient_data['ingredient'].pk
            for ingredient_data in attrs['recipe_ingredients']
        ]
        if len(ingredient_ids) > len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не могут повторяться.'
            )
        tag_ids = [tag.pk for tag in attrs['tags']]
        if len(tag_ids) > len(set(tag_ids)):
            raise serializers.ValidationError(
                'Теги не могут повторяться.'
            )

        return super().validate(attrs)

    @staticmethod
    def set_ingredients(recipe, ingredients):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients
        ])

    def create(self, validated_data):
        request = self.context.get('request')
        ingredients = validated_data.pop('recipe_ingredients')
        tags = validated_data.pop('tags')
        validated_data['author'] = request.user
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        RecipeWriteSerializer.set_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('recipe_ingredients', None)
        tags = validated_data.pop('tags', None)

        if instance.image is not None:
            instance.image.delete(save=False)

        instance = super().update(instance, validated_data)

        if ingredients is not None:
            instance.recipe_ingredients.all().delete()
            RecipeWriteSerializer.set_ingredients(instance, ingredients)
        if tags is not None:
            instance.tags.set(tags)

        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeShortenSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time',)


class FavoriteSerializer(RelationWriteSerializer):
    model = Favorite
    model_field = 'recipe'
    context_key = 'recipe'
    response_serializer = RecipeShortenSerializer
    error_message = 'Рецепт уже добавлен в избранное.'

    class Meta:
        model = Favorite
        fields = ('user', 'recipe',)
        read_only_fields = ('user', 'recipe',)


class ShoppingCartSerializer(RelationWriteSerializer):
    model = ShoppingCart
    model_field = 'recipe'
    context_key = 'recipe'
    response_serializer = RecipeShortenSerializer
    error_message = 'Рецепт уже добавлен в список покупок.'

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe',)
        read_only_fields = ('user', 'recipe',)


class FollowReadSerializer(UserSerializer):
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
        request = self.context.get('request')
        following_user_recipes = obj.recipes.all()
        limit = request.query_params.get('recipes_limit')

        if limit is not None:
            try:
                limit = int(limit)
                if limit > 0:
                    following_user_recipes = following_user_recipes[:limit]
            except ValueError:
                pass

        return RecipeShortenSerializer(
            following_user_recipes, many=True, context=self.context
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class FollowWriteSerializer(RelationWriteSerializer):
    model = Follow
    model_field = 'follows'
    context_key = 'author'
    response_serializer = FollowReadSerializer

    class Meta:
        model = Follow
        fields = ('user', 'follows',)
        read_only_fields = ('user', 'follows',)

    def validate(self, attrs):
        user = self.context['request'].user
        author = self.context['author']
        if user == author:
            raise serializers.ValidationError(
                'Вы не можете подписаться на себя.'
            )
        self.error_message = (
            f'Пользоатель {user.username} уже подписан '
            f'на пользователя {author.username}.'
        )
        return super().validate(attrs)
