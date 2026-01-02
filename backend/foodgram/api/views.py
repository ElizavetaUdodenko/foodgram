from io import BytesIO

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django_filters import AllValuesMultipleFilter, NumberFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from djoser.views import UserViewSet as BaseUserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from social.models import (
    Favorite,
    Follow,
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeShortUrl,
    ShoppingCart,
    Tag
)
from .permissions import AuthorOrReadOnly
from .serializers import (
    UserSerializer, UserCreateSerializer,
    AvatarUploadSerializer,
    FollowSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeSerializer,
    RecipeShortenSerializer,
    TagSerializer
)


User = get_user_model()


class RecipeFilter(FilterSet):
    tags = AllValuesMultipleFilter(field_name='tags__slug')
    author = NumberFilter(field_name='author__id')
    is_favorited = NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = NumberFilter(method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('tags',)

    def filter_is_favorited(self, queryset, name, value):
        if self.request.user.is_anonymous or value != 1:
            return queryset
        return queryset.filter(in_favorite__user=self.request.user)

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_anonymous or value != 1:
            return queryset
        return queryset.filter(in_shopping_cart__user=self.request.user)


class UserViewSet(BaseUserViewSet):

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return (AllowAny(),)
        if self.action == 'me':
            return (IsAuthenticated(),)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'me'):
            return UserSerializer
        if self.action == "create":
            return UserCreateSerializer
        if self.action == "avatar":
            return AvatarUploadSerializer
        if self.action in ('subscriptions', 'subscribe'):
            return FollowSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=('put',),
        permission_classes=(IsAuthenticated,),
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
            request.user.delete_avatar()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
        url_path='subscriptions',
    )
    def subscriptions(self, request):
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            recipes_limit = int(recipes_limit)
        following = User.objects.filter(followers__user=request.user)
        page = self.paginate_queryset(following)
        serializer = self.get_serializer(
            page,
            many=True,
            context={
                'request': request,
                'recipes_limit': recipes_limit
            }
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
        url_path='subscribe',
    )
    def subscribe(self, request, id=None):
        following = self.get_object()
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            recipes_limit = int(recipes_limit)
        if request.user.pk == following.pk:
            return Response(
                'Нельзя подписаться на самого себя.',
                status=status.HTTP_400_BAD_REQUEST
            )
        _, created = Follow.objects.get_or_create(
            user=request.user, follows=following
        )
        if not created:
            return Response(
                f'Пользоатель {request.user.username} уже подписан '
                f'на пользователя {following.username}.',
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(
            following,
            context={
                'request': request,
                'recipes_limit': recipes_limit
            }
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscription(self, request, id=None):
        user = request.user
        following = self.get_object()
        deleted, _ = (
            Follow.objects
            .filter(user=user, follows=following).
            delete()
        )
        if deleted == 1:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            f'Нельзя удалить подписку. Пользоатель {user.username} '
            f'не подписан на пользователя {following.username}.',
            status=status.HTTP_400_BAD_REQUEST
        )


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
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (AuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return (AllowAny(),)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeSerializer
        if self.action in ('favorite', 'shopping_cart'):
            return RecipeShortenSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        recipe = serializer.save(author=self.request.user)
        RecipeShortUrl.objects.create(
            recipe=recipe,
            slug=RecipeShortUrl.generate_slug()
        )

    def _create_relationship(self, model, user, recipe, error_message):
        _, created = model.objects.get_or_create(user=user, recipe=recipe)
        if not created:
            return Response(error_message, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(
            recipe, context={'request': self.request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _delete_relationship(self, model, user, recipe, error_message):
        deleted, _ = model.objects.filter(user=user, recipe=recipe).delete()
        if deleted == 1:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=('get',),
        permission_classes=(AllowAny,),
        url_path='get-link'
    )
    def get_short_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = get_object_or_404(RecipeShortUrl, recipe=recipe)
        return Response(
            {
                'short-link': request.build_absolute_uri(
                    reverse('short-link-recipe', args=[short_link.slug])
                )
            },
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
        url_path='favorite'
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        return self._create_relationship(
            Favorite,
            request.user,
            recipe,
            'Рецепт уже добавлен в избранное.'
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        recipe = self.get_object()
        return self._delete_relationship(
            Favorite,
            request.user,
            recipe,
            'Нельзя удалить рецепт. Рецепт не был добавлен в избранное.'
        )

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
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        return self._create_relationship(
            ShoppingCart,
            request.user,
            recipe,
            'Рецепт уже добавлен в список покупок.'
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        return self._delete_relationship(
            ShoppingCart,
            request.user,
            recipe,
            'Нельзя удалить рецепт из списка покупок. '
            'Рецепт не был добавлен в список покупок.'
        )


def redirect_to_recipe(request, short_link):
    short_link = get_object_or_404(RecipeShortUrl, slug=short_link)
    return redirect(f'/recipes/{short_link.recipe.id}/')
