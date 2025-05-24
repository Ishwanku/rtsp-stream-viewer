from django.urls import path
from .views import StreamView, TestRTSPView, StopStreamView

urlpatterns = [
    path('stream/start/', StreamView.as_view(), name='stream-start'),
    path('test-rtsp/', TestRTSPView.as_view(), name='test-rtsp'),
    path('stream/stop/', StopStreamView.as_view(), name='stream-stop'),
]