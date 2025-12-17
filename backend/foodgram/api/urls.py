from django.urls import include, path
from rest_framework import routers

from .views import TagViewSet, UserViewSet

api_v1_router = routers.DefaultRouter()
api_v1_router.register('users', UserViewSet, basename='users')
api_v1_router.register('tags', TagViewSet, basename='tags')

urlpatterns = [
    path('', include(api_v1_router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
