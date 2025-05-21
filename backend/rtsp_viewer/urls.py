# backend/rtsp_viewer/urls.py

from django.contrib import admin
from django.urls import path, include
from stream.views import index as home

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/', include('stream.urls')),
]
