from django.urls import path

from .views import AvailableSlotsView, BookingView, ChatView, ContactView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("bookings/", BookingView.as_view(), name="bookings"),
    path("bookings/slots/", AvailableSlotsView.as_view(), name="booking_slots"),
    path("contact/", ContactView.as_view(), name="contact"),
]
