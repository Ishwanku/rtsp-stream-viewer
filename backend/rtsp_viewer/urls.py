# backend/rtsp_viewer/urls.py

from django.contrib import admin
from django.urls import path, include # Import include
from .views import status_view # Assuming you have a status view here

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('stream.urls')), # Include your stream app's URLs under '/api/'
    path('status/', status_view, name='status'), # Your status view
]