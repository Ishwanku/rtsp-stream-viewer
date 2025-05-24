# backend/rtsp_viewer/urls.py

from django.contrib import admin
from django.urls import path, include # Import include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from .views import status_view # Assuming you have a status view here

urlpatterns = [
    path('', RedirectView.as_view(url='status/', permanent=False), name='index'),  # Add root URL pattern
    path('admin/', admin.site.urls),
    path('api/', include('stream.urls')), # Include your stream app's URLs under '/api/'
    path('status/', status_view, name='status'), # Your status view
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)