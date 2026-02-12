from django_filters import AllValuesMultipleFilter, NumberFilter
from django_filters.rest_framework import FilterSet

from recipes.models import Recipe


class RecipeFilter(FilterSet):
    tags = AllValuesMultipleFilter(field_name='tags__slug')
    author = NumberFilter(field_name='author__id')
    is_favorited = NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = NumberFilter(method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('tags', 'author', )

    def filter_is_favorited(self, queryset, name, value):
        if not self.request.user.is_authenticated:
            return queryset
        filter_map = {
            1: queryset.filter(in_favorite__user=self.request.user),
            0: queryset.exclude(in_favorite__user=self.request.user)
        }
        return filter_map.get(value, queryset)

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if not self.request.user.is_authenticated:
            return queryset
        filter_map = {
            1: queryset.filter(in_shopping_cart__user=self.request.user),
            0: queryset.exclude(in_shopping_cart__user=self.request.user)
        }
        return filter_map.get(value, queryset)
