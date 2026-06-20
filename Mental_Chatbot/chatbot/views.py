import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking, TIME_SLOTS
from .rag import ChatbotUnavailable, answer_question
from .serializers import (
    BookingSerializer,
    ChatRequestSerializer,
    ChatResponseSerializer,
    ContactSerializer,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Chatbot
# --------------------------------------------------------------------------- #
class ChatView(APIView):
    """
    Ask the mental-health assistant a question.

    Retrieval-augmented over a curated knowledge base, history-aware (pass prior
    turns in `history`) and guarded by a crisis-safety layer. Returns 503 if the
    chatbot is not configured.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=ChatRequestSerializer, responses={200: ChatResponseSerializer})
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = answer_question(
                serializer.validated_data["message"],
                serializer.validated_data.get("history"),
            )
        except ChatbotUnavailable as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception:  # pragma: no cover - upstream/model failures
            logger.exception("Chatbot failed to answer")
            return Response(
                {"detail": "The assistant failed to answer. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(result)


# --------------------------------------------------------------------------- #
# Bookings
# --------------------------------------------------------------------------- #
class AvailableSlotsView(APIView):
    """List unbooked appointment slots for a given date (defaults to today)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("date", str, description="YYYY-MM-DD")],
        responses={200: OpenApiResponse(description="Available slots.")},
    )
    def get(self, request):
        date_str = request.query_params.get("date")
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.today().date()
        except ValueError:
            return Response({"detail": "Invalid date format, use YYYY-MM-DD."},
                            status=status.HTTP_400_BAD_REQUEST)

        booked = set(Booking.objects.filter(date=day).values_list("time", flat=True))
        available = [
            {"time": time, "label": label} for time, label in TIME_SLOTS if time not in booked
        ]
        return Response({"date": day.isoformat(), "available_slots": available})


class BookingView(generics.ListCreateAPIView):
    """
    Create an appointment booking (public) or list all bookings (staff only).
    """

    serializer_class = BookingSerializer
    queryset = Booking.objects.all().order_by("-date", "time")

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def perform_create(self, serializer):
        booking = serializer.save()
        send_mail(
            "Booking Confirmed",
            f"Your booking for {booking.date} at {booking.get_time_display()} is confirmed.",
            settings.DEFAULT_FROM_EMAIL,
            [booking.email],
            fail_silently=True,
        )


# --------------------------------------------------------------------------- #
# Contact
# --------------------------------------------------------------------------- #
class ContactView(APIView):
    """Send a message to the team via the contact form."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=ContactSerializer, responses={200: OpenApiResponse(description="Sent.")})
    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        send_mail(
            subject=f"[Contact] {data['subject']}",
            message=f"From: {data['name']} <{data['email']}>\n\n{data['message']}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_RECIPIENT_EMAIL],
            fail_silently=True,
        )
        return Response({"detail": "Your message was sent successfully."})
