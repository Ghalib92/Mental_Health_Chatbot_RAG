# pages/forms.py
from django import forms
from .models import Booking, TIME_SLOTS
from django.core.exceptions import ValidationError

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['email', 'date', 'time']

    def __init__(self, *args, **kwargs):
        self.available_slots = kwargs.pop('available_slots', TIME_SLOTS)
        super().__init__(*args, **kwargs)

        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
        self.fields['date'].widget.attrs.update({
            'class': 'form-control datepicker',
        })
        self.fields['time'].widget.attrs.update({
            'class': 'form-select',
        })
        self.fields['time'].choices = self.available_slots

    def clean_time(self):
        time = self.cleaned_data.get('time')
        if time not in dict(self.available_slots).keys():
            raise ValidationError("The selected time slot is no longer available.")
        return time
