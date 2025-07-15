from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name = 'home'),
    path("chatbot-page/", views.chatbot_page, name="chatbot-page"),
    path('get/',views.get_response, name='get_response'),
    path('booking/',views.booking, name = 'book'),
    path('book/', views.book_view, name='book'),
    path('book/', views.book_view, name='book'),
    path('load-time-slots/', views.load_time_slots, name='load_time_slots'),
    path('send-message/', views.send_message, name='send_message'),
     
     
     ]
