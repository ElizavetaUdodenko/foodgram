from django.contrib import admin

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


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author_username',)
    list_display_links = ('author_username', 'name',)
    search_fields = ('author__username', 'name',)
    readonly_fields = ('favorites_count', 'short_url',)
    list_filter = ('tags',)
    inlines = (RecipeIngredientInline,)

    @admin.display(description='Автор')
    def author_username(self, obj):
        return obj.author.username

    @admin.display(description='В избранном')
    def favorites_count(self, obj):
        return obj.in_favorite.count()
