# from django.urls import re_path
from django.urls import path
from .consumers import MessageConsumer

websocket_urlpatterns = [
    path("ws/geolocation/<uuid:session_id>/", MessageConsumer.as_asgi()),    
]