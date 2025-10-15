# chat_app/urls.py

from django.urls import path
from . import views
from .api import views as api_views

urlpatterns = [
    path('', views.chat_view, name='chat_view'),
    path('api/send_message/', views.send_message_api, name='send_message_api'),
    path('api/chat/history/', api_views.get_chat_history, name='api_chat_history'),
    path('api/chat/send/', api_views.send_chat_message, name='api_chat_send'),
        path('api/room/state/', api_views.room_state_api, name='api_room_state'),
]
