# chat_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat_view'),
    path('api/send_message/', views.send_message_api, name='send_message_api')
]
