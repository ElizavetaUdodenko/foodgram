from django.contrib import admin
from django.db.models import Count

from .models import Ingredient, Recipe, RecipeIngredient, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug',)
    list_display_links = ('name',)
    list_editable = ('slug',)
    search_fields = ('name', 'slug',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit',)
    list_display_links = ('name',)
    list_editable = ('measurement_unit',)
    search_fields = ('name',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 0
    min_num = 1

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('ingredient')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author_username',)
    list_display_links = ('author_username', 'name',)
    search_fields = ('author__username', 'name',)
    readonly_fields = ('favorites_count', 'short_url',)
    list_filter = ('tags',)
    filter_horizontal = ('tags',)
    inlines = (RecipeIngredientInline,)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return (
            queryset.select_related('author')
            .annotate(favorites_count=Count('in_favorite'))
        )

    @admin.display(description='Author')
    def author_username(self, obj):
        return obj.author.username

    @admin.display(description='In Favorite')
    def favorites_count(self, obj):
        return obj.favorites_count
