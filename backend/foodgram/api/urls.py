from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    IngredientViewSet,
    RecipeViewSet,
    TagViewSet,
    UserViewSet,
    redirect_to_recipe
)

api_v1_router = DefaultRouter()
api_v1_router.register('users', UserViewSet, basename='users')
api_v1_router.register('tags', TagViewSet, basename='tags')
api_v1_router.register('recipes', RecipeViewSet, basename='recipes')
api_v1_router.register(
    'ingredients', IngredientViewSet, basename='ingredients'
)

api_urls = [
    path('', include(api_v1_router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]

urlpatterns = [
    path('api/', include(api_urls)),
    path('s/<slug:slug>/', redirect_to_recipe, name='short-link-recipe'),
]
