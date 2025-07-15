from django.db import models

# Create your models here.
TIME_SLOTS = [
        ('08:00', '8:00 AM'), ('09:00', '9:00 AM'),
        ('10:00', '10:00 AM'), ('11:00', '11:00 AM'),
        ('12:00', '12:00 PM'), ('13:00', '1:00 PM'),
        ('14:00', '2:00 PM'), ('15:00', '3:00 PM'),
        ('16:00', '4:00 PM'), ('17:00', '5:00 PM'),
    ]
class Booking(models.Model):
    email = models.EmailField()
    date = models.DateField()
    

    time = models.CharField(max_length=5, choices=TIME_SLOTS)

    class Meta:
        unique_together = ('date', 'time')  # Prevent duplicate bookings for same slot

    def __str__(self):
        return f"{self.email} booked on {self.date} at {self.time}"
