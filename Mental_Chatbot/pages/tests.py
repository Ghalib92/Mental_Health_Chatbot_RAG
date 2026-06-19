from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Booking
from .rag import detect_crisis


class CrisisLayerTests(APITestCase):
    """The safety layer is deterministic and must work without any LLM."""

    def test_detect_crisis_true(self):
        self.assertTrue(detect_crisis("I want to kill myself"))
        self.assertTrue(detect_crisis("lately I feel suicidal"))

    def test_detect_crisis_false(self):
        self.assertFalse(detect_crisis("I feel a bit stressed about work"))

    def test_chat_crisis_returns_resources_without_calling_llm(self):
        resp = self.client.post(reverse("chat"), {"message": "I want to end my life"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["crisis"])
        self.assertTrue(len(resp.data["resources"]) > 0)


class ChatTests(APITestCase):
    @override_settings(OPENAI_API_KEY="", PINECONE_API_KEY="")
    def test_unconfigured_returns_503(self):
        from pages import rag
        rag.reset_cache()
        resp = self.client.post(reverse("chat"), {"message": "How do I manage anxiety?"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_empty_message_rejected(self):
        resp = self.client.post(reverse("chat"), {"message": ""}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("pages.views.answer_question")
    def test_answer_with_sources(self, mock_answer):
        mock_answer.return_value = {
            "answer": "Try slow breathing.",
            "sources": [{"source": "who.pdf", "page": 3}],
            "crisis": False,
        }
        resp = self.client.post(reverse("chat"), {"message": "anxiety tips?"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["answer"], "Try slow breathing.")
        self.assertEqual(resp.data["sources"][0]["source"], "who.pdf")


class BookingTests(APITestCase):
    def setUp(self):
        self.tomorrow = (date.today() + timedelta(days=1)).isoformat()

    def test_create_booking(self):
        resp = self.client.post(
            reverse("bookings"), {"email": "u@example.com", "date": self.tomorrow, "time": "09:00"}
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_double_booking_rejected(self):
        Booking.objects.create(email="a@example.com", date=self.tomorrow, time="09:00")
        resp = self.client.post(
            reverse("bookings"), {"email": "b@example.com", "date": self.tomorrow, "time": "09:00"}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_past_date_rejected(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        resp = self.client.post(
            reverse("bookings"), {"email": "u@example.com", "date": yesterday, "time": "09:00"}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_available_slots_excludes_booked(self):
        Booking.objects.create(email="a@example.com", date=self.tomorrow, time="09:00")
        resp = self.client.get(reverse("booking_slots"), {"date": self.tomorrow})
        times = [s["time"] for s in resp.data["available_slots"]]
        self.assertNotIn("09:00", times)
        self.assertIn("10:00", times)

    def test_listing_requires_admin(self):
        self.assertEqual(self.client.get(reverse("bookings")).status_code, status.HTTP_401_UNAUTHORIZED)
        admin = User.objects.create_superuser("admin", password="Str0ngPass!23")
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get(reverse("bookings")).status_code, status.HTTP_200_OK)


class ContactTests(APITestCase):
    def test_contact_sends(self):
        resp = self.client.post(
            reverse("contact"),
            {"name": "Sam", "email": "s@example.com", "subject": "Hi", "message": "Hello there"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
