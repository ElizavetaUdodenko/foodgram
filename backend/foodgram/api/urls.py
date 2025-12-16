from django.urls import include, path
from rest_framework import routers

from users.views import UserViewSet


api_v1_router = routers.DefaultRouter()
api_v1_router.register('users', UserViewSet, basename='users')

urlpatterns = [
    path('', include(api_v1_router.urls)),
    # path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
