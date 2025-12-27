import random
import string

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from core.models import TimeStampedModel

from .constants import (COOKING_TIME_MIN, INGREDIENT_MAX_LENGTH,
                        NAME_MAX_LENGTH, SHORT_LINK_MAX_LENGTH,
                        UNIT_MAX_LENGTH)

User = get_user_model()


def image_file_name(instance, filename):
    return ''.join(['recipes/images/', str(instance.pk), '_', filename])


class Tag(TimeStampedModel):
    name = models.CharField(
        'Тег',
        max_length=UNIT_MAX_LENGTH,
        unique=True,
        blank=False,
        null=False
    )
    slug = models.SlugField(
        'Слаг',
        unique=True,
        blank=False,
        null=False)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return f'Тег: {self.name}'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        'Ingredient',
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Ингредиент',
    )
    amount = models.DecimalField(
        'Количество',
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
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
            f'для {self.recipe.name}'
        )


class Ingredient(models.Model):
    name = models.CharField(
        'Ингредиент',
        max_length=INGREDIENT_MAX_LENGTH,
        unique=True,
        blank=False,
        null=False
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=UNIT_MAX_LENGTH,
        blank=False,
        null=False
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'Ингредиент {self.name} измеряется в {self.measurement_unit}.'


class Recipe(TimeStampedModel):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор',
    )
    name = models.CharField('Название', max_length=NAME_MAX_LENGTH)
    image = models.ImageField(
        'Изображение',
        upload_to=image_file_name,
        null=True,
        blank=True
    )
    text = models.TextField('Описание')
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
        blank=True,
        help_text='Удерживайте Ctrl для выбора нескольких вариантов.',
        related_name='recipes'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through=RecipeIngredient,
        verbose_name='Ингредиенты',
        blank=True,
        help_text='Удерживайте Ctrl для выбора нескольких вариантов.',
        related_name='recipes'
    )
    cooking_time = models.PositiveIntegerField(
        'Время приготовления',
        validators=[MinValueValidator(COOKING_TIME_MIN),]
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return f'Рецепт "{self.name[:10]}" от автора {self.author.username}.'

    def delete_image(self):
        if self.image:
            self.image.delete(save=False)
            self.image = None
            self.save()


class RecipeShortUrl(models.Model):
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        related_name='short_link',
        verbose_name='Рецепт',
    )
    slug = models.SlugField(
        'Короткая ссылка на рецепт',
        max_length=SHORT_LINK_MAX_LENGTH,
        unique=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'slug'], name='unique_short_link'
            )
        ]

    def __str__(self):
        return f'{self.slug} - короткая ссылка на рецепт {self.recipe.name}.'

    @staticmethod
    def generate_slug():
        while True:
            slug = ''.join(
                random.choice(string.ascii_letters+string.digits)
                for _ in range(SHORT_LINK_MAX_LENGTH)
            )
            if not RecipeShortUrl.objects.filter(slug=slug).exists():
                return slug


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follows',
    )
    follows = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'follows'], name='unique_follow'
            ),
            models.CheckConstraint(
                check=~Q(user=F('follows')), name='restrict_self_follow'
            )
        ]

    def __str__(self):
        return (
            f'{self.user.username} subscribed to {self.follows.username}'
        )


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='added_to_favorites'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorites'
            )
        ]
