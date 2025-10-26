from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CountryViewSet, status_view

router = DefaultRouter(trailing_slash=True)
router.register(r'countries', CountryViewSet)

# Standard URL patterns with trailing slashes (preferred)
urlpatterns = [
    path('', include(router.urls)),
]

# Also expose the same viewset actions without trailing slashes
country_list = CountryViewSet.as_view({'get': 'list', 'post': 'create'})
country_detail = CountryViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'put': 'update', 'patch': 'update'})
country_refresh = CountryViewSet.as_view({'post': 'refresh'})
country_image = CountryViewSet.as_view({'get': 'image'})
country_status = CountryViewSet.as_view({'get': 'status'})

# Additional URL patterns without trailing slashes
urlpatterns += [
    path('countries', country_list, name='country-list-no-slash'),
    path('countries/refresh', country_refresh, name='country-refresh-no-slash'),
    path('countries/image', country_image, name='country-image-no-slash'),
    path('countries/status', country_status, name='country-status-no-slash'),
    path('countries/<str:name>', country_detail, name='country-detail-no-slash'),
]