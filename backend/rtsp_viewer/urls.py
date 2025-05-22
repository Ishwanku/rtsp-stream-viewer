from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'Backend running'})

urlpatterns = [
    path('', health_check, name='health_check'),
    path('api/', include('stream.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)