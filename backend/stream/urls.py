from django.urls import path
from .views import StreamView, TestRTSPView, StopStreamView

urlpatterns = [
    path('stream/', StreamView.as_view(), name='stream'),
    path('test-rtsp/', TestRTSPView.as_view(), name='test-rtsp'),
    path('stop-stream/', StopStreamView.as_view(), name='stop-stream'),
]