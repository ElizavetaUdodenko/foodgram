from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django_filters import AllValuesMultipleFilter, NumberFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from djoser.views import UserViewSet as BaseUserViewSet
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from social.models import Ingredient, Recipe, RecipeShortUrl, Tag
from .permissions import AuthorOrReadOnly
from .serializers import (
    AvatarUploadSerializer,
    IngredientSerializer,
    RecipeSerializer,
    RecipeCreateSerializer,
    TagSerializer
)


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

    @action(detail=True, methods=['get'], url_path='get-link')
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


def redirect_to_recipe(request, short_link):
    short_link = get_object_or_404(RecipeShortUrl, slug=short_link)
    return redirect(f'/api/recipes/{short_link.recipe.id}/')
