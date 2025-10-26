"""
URL configuration for HNG3 project.
"""
from django.contrib import admin
from django.urls import path, include
from countries.views import status_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # Include both trailing and non-trailing slash versions of the status endpoint
    path('status/', status_view, name='status-with-slash'),
    path('status', status_view, name='status-no-slash'),
    # Include all countries app URLs (both with and without trailing slashes)
    path('', include('countries.urls')),
]
