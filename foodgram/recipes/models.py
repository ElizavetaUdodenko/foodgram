import random
import string

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .constants import (
    AMOUNT_MAX,
    AMOUNT_MIN,
    COOKING_TIME_MAX,
    COOKING_TIME_MIN,
    INGREDIENT_NAME_MAX_LENGTH,
    MEASUREMENT_UNIT_MAX_LENGTH,
    RECIPE_NAME_MAX_LENGTH,
    SHORT_LINK_MAX_LENGTH,
    TAG_NAME_MAX_LENGTH,
    TAG_SLUG_MAX_LENGTH
)


User = get_user_model()


def image_file_name(instance, filename):
    return ''.join(['recipes/images/', str(instance.pk), '_', filename])


class Tag(models.Model):
    name = models.CharField(
        'Tag',
        max_length=TAG_NAME_MAX_LENGTH,
        unique=True
    )
    slug = models.SlugField(
        'Slug',
        max_length=TAG_SLUG_MAX_LENGTH,
        unique=True
    )

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ('name',)

    def __str__(self):
        return f'Tag: {self.name}'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Recipe',
    )
    ingredient = models.ForeignKey(
        'Ingredient',
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Ingredient',
    )
    amount = models.PositiveSmallIntegerField(
        'Amount',
        validators=[
            MinValueValidator(AMOUNT_MIN),
            MaxValueValidator(AMOUNT_MAX)
        ]
    )

    class Meta:
        verbose_name = 'Ingredient'
        verbose_name_plural = 'Ingredients'
        ordering = ('recipe',)
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredients'
            )
        ]

    def __str__(self):
        return (
            f'{self.ingredient.name} '
            f'({self.amount} {self.ingredient.measurement_unit}) '
            f'for {self.recipe.name}'
        )


class Ingredient(models.Model):
    name = models.CharField(
        'Ingredient',
        max_length=INGREDIENT_NAME_MAX_LENGTH,
        unique=True
    )
    measurement_unit = models.CharField(
        'Measurement Unit',
        max_length=MEASUREMENT_UNIT_MAX_LENGTH
    )

    class Meta:
        verbose_name = 'Ingredient'
        verbose_name_plural = 'Ingredients'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'], name='unique_ingredient'
            ),
        ]

    def __str__(self):
        return f'Ingredient {self.name} measured in {self.measurement_unit}.'


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Author',
    )
    name = models.CharField('Name', max_length=RECIPE_NAME_MAX_LENGTH)
    image = models.ImageField(
        'Image',
        upload_to=image_file_name,
        null=True,
        blank=True
    )
    text = models.TextField('Description')
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='recipes',
        verbose_name='Tags'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through=RecipeIngredient,
        blank=True,
        related_name='recipes',
        verbose_name='Ingredients'
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Cooking Time',
        validators=[
            MinValueValidator(COOKING_TIME_MIN),
            MaxValueValidator(COOKING_TIME_MAX)
        ]
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        verbose_name='Created At'
    )
    short_url = models.CharField(
        'Short URL',
        max_length=SHORT_LINK_MAX_LENGTH,
        unique=True
    )

    class Meta:
        verbose_name = 'Recipe'
        verbose_name_plural = 'Recipes'
        ordering = ('-created_at', 'name')

    def __str__(self):
        return (
            f'Recipe "{self.name[:10]}" '
            f'from the author {self.author.username}.'
        )

    @staticmethod
    def generate_short_url():
        while True:
            short_url = ''.join(
                random.choice(string.ascii_letters + string.digits)
                for _ in range(SHORT_LINK_MAX_LENGTH)
            )
            if not Recipe.objects.filter(short_url=short_url).exists():
                return short_url

    def save(self, **kwargs):
        if not self.short_url:
            self.short_url = Recipe.generate_short_url()
        super().save(**kwargs)


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='User'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_favorite',
        verbose_name='Recipe'
    )

    class Meta:
        verbose_name = 'Favorite Recipe'
        verbose_name_plural = 'Favorite Recipes'
        ordering = ('user',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorites'
            )
        ]

    def __str__(self):
        return f'{self.user.username} -> recipe {self.recipe.name}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_carts',
        verbose_name='User'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_cart',
        verbose_name='Recipe'
    )

    class Meta:
        verbose_name = 'Shopping Cart'
        verbose_name_plural = 'Shopping Carts'
        ordering = ('user',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]

    def __str__(self):
        return f'{self.user.username} -> shopping cart for {self.recipe.name}'
