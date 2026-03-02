from django.db import models
from accounts.models import FamilyMember
import uuid
from datetime import date


class Medicine(models.Model):
    FREQUENCY_CHOICES = [
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily'),
        ('thrice_daily', 'Three Times Daily'),
        ('four_times', 'Four Times Daily'),
        ('every_6h', 'Every 6 Hours'),
        ('every_8h', 'Every 8 Hours'),
        ('every_12h', 'Every 12 Hours'),
        ('weekly', 'Once a Week'),
        ('alternate', 'Alternate Days'),
        ('as_needed', 'As Needed (SOS)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(FamilyMember, on_delete=models.CASCADE, related_name='medicines')
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, help_text='e.g., 500mg, 1 tablet')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    quantity_purchased = models.PositiveIntegerField(default=0, help_text='Total tablets/units purchased')
    quantity_remaining = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField(null=True, blank=True)
    low_stock_threshold = models.PositiveIntegerField(default=7, help_text='Alert when remaining < this value')
    instructions = models.TextField(blank=True, help_text='With food, Before meal, etc.')
    photo = models.ImageField(upload_to='medicine_photos/', null=True, blank=True)
    prescribed_by = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.member.name} ({self.dosage})"

    def is_low_stock(self):
        return self.quantity_remaining <= self.low_stock_threshold

    def is_expired(self):
        if self.expiry_date:
            return date.today() > self.expiry_date
        return False

    def expiry_soon(self):
        if self.expiry_date:
            from datetime import timedelta
            return date.today() + timedelta(days=7) >= self.expiry_date
        return False

    def daily_doses(self):
        freq_map = {
            'once_daily': 1, 'twice_daily': 2, 'thrice_daily': 3,
            'four_times': 4, 'every_6h': 4, 'every_8h': 3,
            'every_12h': 2, 'weekly': 1/7, 'alternate': 0.5,
            'as_needed': 0
        }
        return freq_map.get(self.frequency, 1)

    def estimated_days_remaining(self):
        daily = self.daily_doses()
        if daily > 0 and self.quantity_remaining:
            return int(self.quantity_remaining / daily)
        return None

    def save(self, *args, **kwargs):
        if self._state.adding and self.quantity_remaining == 0:
            self.quantity_remaining = self.quantity_purchased
        super().save(*args, **kwargs)


class MedicineReminder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('taken', 'Taken'),
        ('missed', 'Missed'),
        ('skipped', 'Skipped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='reminders')
    scheduled_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    taken_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-scheduled_time']

    def __str__(self):
        return f"{self.medicine.name} - {self.scheduled_time} ({self.status})"


class MedicineRefillRequest(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='refill_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    quantity_requested = models.PositiveIntegerField(default=30)
    notes = models.TextField(blank=True)
    fulfilled = models.BooleanField(default=False)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Refill: {self.medicine.name} ({self.quantity_requested} units)"
