from datetime import date as date_cls

from rest_framework import serializers

from .models import Booking


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    history = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        required=False,
        help_text='Prior turns: [{"role": "user"|"assistant", "content": "..."}]',
    )


class ChatResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    sources = serializers.ListField(child=serializers.DictField(), required=False)
    crisis = serializers.BooleanField()
    resources = serializers.ListField(child=serializers.DictField(), required=False)


class BookingSerializer(serializers.ModelSerializer):
    time_display = serializers.CharField(source="get_time_display", read_only=True)

    class Meta:
        model = Booking
        fields = ("id", "email", "date", "time", "time_display")
        read_only_fields = ("id",)

    def validate_date(self, value):
        if value < date_cls.today():
            raise serializers.ValidationError("Cannot book a date in the past.")
        return value

    def validate(self, attrs):
        if Booking.objects.filter(date=attrs["date"], time=attrs["time"]).exists():
            raise serializers.ValidationError("That time slot is already booked.")
        return attrs


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField(max_length=5000)
