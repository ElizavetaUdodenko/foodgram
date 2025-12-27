from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django_filters import AllValuesMultipleFilter, NumberFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from djoser.views import UserViewSet as BaseUserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from social.models import Favorite, Follow, Ingredient, Recipe, RecipeShortUrl, Tag
from core.pagination import PageNumberLimitPagination
from .permissions import AuthorOrReadOnly
from .serializers import (AvatarUploadSerializer, RecipeShortenSerializer,
                          IngredientSerializer, RecipeCreateSerializer,
                          RecipeSerializer, TagSerializer, FollowSerializer)


User = get_user_model()


class RecipeFilter(FilterSet):
    tags = AllValuesMultipleFilter(field_name='tags__slug')
    author = NumberFilter(field_name='author__id')
    is_favorited = NumberFilter(method='filter_is_favorited')
    # is_in_shopping_cart = NumberFilter(method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('tags',)

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if user.is_anonymous or value != 1:
            return queryset
        return queryset.filter(added_to_favorites__user=user)

    # def filter_is_in_shopping_cart(self, queryset, name, value):
    #     user = self.request.user
    #     if user.is_anonymous or value != 1:
    #         return queryset
    #     return queryset.filter(cart__user=user)


class UserViewSet(BaseUserViewSet):

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'me':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(
        detail=False,
        methods=['put'],
        permission_classes=(IsAuthenticated,),
        url_path='me/avatar'
    )
    def avatar(self, request):
        serializer = AvatarUploadSerializer(
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
        user = request.user
        if user.avatar:
            user.delete_avatar()
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
        serializer = FollowSerializer(
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
        user = request.user
        following = self.get_object()
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            recipes_limit = int(recipes_limit)
        if user.pk == following.pk:
            return Response(
                'Нельзя подписаться на самого себя.',
                status=status.HTTP_400_BAD_REQUEST
            )
        _, created = Follow.objects.get_or_create(user=user, follows=following)
        if not created:
            return Response(
                f'Пользоатель {user.username} уже подписан '
                f'на пользователя {following.username}.',
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = FollowSerializer(
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
        deleted, _ = Follow.objects.filter(
            user=user, follows=following
        ).delete()
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
    filter_backends = (DjangoFilterBackend, filters.SearchFilter,)
    filterset_class = RecipeFilter
    # search_fields = ('author__id',)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        recipe = serializer.save(author=self.request.user)
        RecipeShortUrl.objects.create(
            recipe=recipe,
            slug=RecipeShortUrl.generate_slug()
        )

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[AllowAny],
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
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='favorite'
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        _, created = Favorite.objects.get_or_create(
            user=request.user, recipe=recipe
        )
        if not created:
            return Response(
                'Рецепт уже добавлен в избранное.',
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = RecipeShortenSerializer(
            recipe, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        recipe = self.get_object()
        deleted, _ = Favorite.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if deleted == 1:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            'Нельзя удалить рецепт. Рецепт не был добавлен в избранное.',
            status=status.HTTP_400_BAD_REQUEST
        )


def redirect_to_recipe(request, short_link):
    short_link = get_object_or_404(RecipeShortUrl, slug=short_link)
    return redirect(f'/api/recipes/{short_link.recipe.id}/')
