from django.contrib import admin

from .models import Tag, Ingredient, Recipe


class TagAdmin(admin.ModelAdmin):
    list_display = ('tag', 'slug',)
    list_display_links = ('tag',)
    list_editable = ('slug',)
    search_fields = ('tag', 'slug',)


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'unit',)
    list_display_links = ('ingredient',)
    list_editable = ('unit',)
    search_fields = ('ingredient',)


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('author', 'name')
    list_display_links = ('author', 'name',)
    search_fields = ('author', 'name',)
    list_filter = ('tags',)


admin.site.register(Tag, TagAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)