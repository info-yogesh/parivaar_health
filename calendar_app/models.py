from django.db import models
from accounts.models import Family, FamilyMember
import uuid


class Appointment(models.Model):
    TYPE_CHOICES = [
        ('checkup', 'General Checkup'),
        ('specialist', 'Specialist Visit'),
        ('lab', 'Lab Test'),
        ('vaccination', 'Vaccination'),
        ('dental', 'Dental'),
        ('eye', 'Eye Checkup'),
        ('physiotherapy', 'Physiotherapy'),
        ('follow_up', 'Follow-up'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='appointments')
    member = models.ForeignKey(FamilyMember, on_delete=models.CASCADE, related_name='appointments')
    doctor_name = models.CharField(max_length=255, blank=True)
    clinic_hospital = models.CharField(max_length=255, blank=True)
    appointment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='checkup')
    date_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True)
    send_whatsapp_reminder = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date_time']

    def __str__(self):
        return f"{self.member.name} - {self.get_appointment_type_display()} on {self.date_time.strftime('%d %b %Y %H:%M')}"

    def is_upcoming(self):
        from django.utils import timezone
        return self.date_time > timezone.now() and self.status == 'scheduled'
