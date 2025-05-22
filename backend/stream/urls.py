# backend/stream/urls.py
# from rest_framework.urls import path
# # from rtsp_viewer.urls import path
# from .views import index as StreamView

# urlpatterns = [
#     path('stream/', StreamView, name='stream'),
# ]
from django.urls import path
from .views import StreamView, TestRTSPView

urlpatterns = [
    path('stream/', StreamView.as_view(), name='stream'),
    path('test-rtsp/', TestRTSPView.as_view(), name='test-rtsp'),
]