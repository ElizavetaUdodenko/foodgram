from django.contrib import admin

from .models import Ingredient, Recipe, RecipeIngredient, Tag


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug',)
    list_display_links = ('name',)
    list_editable = ('slug',)
    search_fields = ('name', 'slug',)


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit',)
    list_display_links = ('name',)
    list_editable = ('measurement_unit',)
    search_fields = ('name',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 0


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('author', 'name',)
    list_display_links = ('author', 'name',)
    search_fields = ('author__username', 'name',)
    list_filter = ('tags',)
    inlines = (RecipeIngredientInline,)


admin.site.register(Tag, TagAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)