from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import status_view

urlpatterns = [
    path('', status_view, name='status'),
    path('api/stream/', include('stream.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)