from io import BytesIO

from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as BaseUserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag
)
from users.models import Follow
from .filters import RecipeFilter
from .permissions import AuthorOrReadOnly
from .serializers import (
    AvatarUploadSerializer,
    FavoriteSerializer,
    FollowReadSerializer,
    FollowWriteSerializer,
    IngredientSerializer,
    RecipeWriteSerializer,
    ShoppingCartSerializer,
    TagSerializer
)


User = get_user_model()


class UserViewSet(BaseUserViewSet):

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(
        detail=False,
        methods=('put',),
        permission_classes=(IsAuthenticated,),
        serializer_class=AvatarUploadSerializer,
        url_path='me/avatar'
    )
    def avatar(self, request):
        serializer = self.get_serializer(
            instance=request.user,
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'avatar': request.build_absolute_uri(request.user.avatar.url)},
            status=status.HTTP_200_OK
        )

    @avatar.mapping.delete
    def delete_avatar(self, request):
        if request.user.avatar:
            request.user.avatar.delete(save=False)
            request.user.save(update_fields=('avatar',))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
        serializer_class=FollowReadSerializer,
        url_path='subscriptions',
    )
    def subscriptions(self, request):
        following = User.objects.filter(followers__user=request.user)
        page = self.paginate_queryset(following)
        serializer = self.get_serializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
        serializer_class=FollowWriteSerializer,
        url_path='subscribe',
    )
    def subscribe(self, request, id=None):
        serializer = self.get_serializer(
            data={
                'user': request.user.id,
                'follows': self.get_object().id
            },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscription(self, request, id=None):
        author = self.get_object()
        deleted, _ = (
            Follow.objects
            .filter(user=request.user, follows=author)
            .delete()
        )
        if not deleted:
            return Response(
                f'Пользователь {request.user.username} '
                f'не подписан на пользователя {author.username}.',
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeWriteSerializer
    permission_classes = (AuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_queryset(self):
        user = self.request.user
        recipes = (
            Recipe.objects
            .select_related('author')
            .prefetch_related(
                'tags',
                'recipe_ingredients__ingredient'
            )
        )
        if user.is_authenticated:
            recipes = recipes.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                )
            )

        return recipes

    @action(
        detail=True,
        methods=('get',),
        permission_classes=(AllowAny,),
        url_path='get-link'
    )
    def get_short_url(self, request, pk=None):
        recipe = self.get_object()
        return Response(
            {
                'short-link': request.build_absolute_uri(
                    reverse('short-url-recipe', args=[recipe.short_url])
                )
            },
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
        serializer_class=FavoriteSerializer,
        url_path='favorite'
    )
    def favorite(self, request, pk=None):
        serializer = self.get_serializer(
            data={
                'user': request.user.id,
                'recipe': self.get_object().pk
            },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        deleted, _ = (
            Favorite.objects
            .filter(user=request.user, recipe=self.get_object())
            .delete()
        )
        if not deleted:
            return Response(
                'Нельзя удалить рецепт. Рецепт не был добавлен в избранное.',
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
        url_path='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        recipes = Recipe.objects.filter(in_shopping_cart__user=request.user)
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__in=recipes)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(amount=Sum('amount'))
            .order_by('ingredient__name')
        )

        buffer = BytesIO()
        text = ['Продукт — Количество\n']
        for ingredient in ingredients:
            text.append(
                f'{ingredient["ingredient__name"]} — '
                f'{ingredient["amount"]} '
                f'{ingredient["ingredient__measurement_unit"]}'
            )
        text = '\n'.join(text)
        buffer.write(text.encode('utf-8'))
        buffer.seek(0)
        return FileResponse(
            buffer,
            as_attachment=True,
            filename='shopping_list.txt',
            content_type='text/plain'
        )

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
        serializer_class=ShoppingCartSerializer,
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        serializer = self.get_serializer(
            data={
                'user': request.user.id,
                'recipe': self.get_object().pk
            },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        deleted, _ = (
            ShoppingCart.objects
            .filter(user=request.user, recipe=self.get_object())
            .delete()
        )
        if not deleted:
            return Response(
                'Нельзя удалить рецепт из списка покупок. '
                'Рецепт не был добавлен в список покупок.',
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


def redirect_to_recipe(request, short_url):
    """Redirects from a short URL to the recipe's detail page."""
    recipe = get_object_or_404(Recipe, short_url=short_url)
    return redirect(f'/recipes/{recipe.pk}/')
