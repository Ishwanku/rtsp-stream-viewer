from django.urls import re_path
from stream.consumers import StreamConsumer

websocket_urlpatterns = [
    re_path(r'ws/streams/$', StreamConsumer.as_view()),
]