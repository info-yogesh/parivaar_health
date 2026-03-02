from django.db import models
from django.contrib.auth.models import User
import uuid


class Family(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    admin = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_family')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Families'

    def __str__(self):
        return f"{self.name} Family - {self.city}"

    def get_member_count(self):
        return self.members.count()


class FamilyMember(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Primary Caregiver (Admin)'),
        ('member', 'Secondary Member'),
        ('view_only', 'View-Only Member'),
    ]
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    RELATIONSHIP_CHOICES = [
        ('self', 'Self'),
        ('spouse', 'Spouse'),
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('son', 'Son'),
        ('daughter', 'Daughter'),
        ('grandfather', 'Grandfather'),
        ('grandmother', 'Grandmother'),
        ('brother', 'Brother'),
        ('sister', 'Sister'),
        ('other', 'Other'),
    ]
    CHRONIC_CONDITION_CHOICES = [
        ('diabetes', 'Diabetes'),
        ('hypertension', 'Hypertension/BP'),
        ('heart_disease', 'Heart Disease'),
        ('asthma', 'Asthma'),
        ('thyroid', 'Thyroid'),
        ('arthritis', 'Arthritis'),
        ('kidney_disease', 'Kidney Disease'),
        ('cancer', 'Cancer'),
        ('copd', 'COPD'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='members')
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='family_member')
    name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    phone = models.CharField(max_length=15, blank=True)
    abha_id = models.CharField(max_length=50, blank=True, verbose_name='ABHA ID')
    abha_linked = models.BooleanField(default=False)
    abha_consent = models.BooleanField(default=False)
    profile_photo = models.ImageField(upload_to='member_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.relationship}) - {self.family.name}"

    def get_age(self):
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None


class ChronicCondition(models.Model):
    member = models.ForeignKey(FamilyMember, on_delete=models.CASCADE, related_name='chronic_conditions')
    condition = models.CharField(max_length=50, choices=FamilyMember.CHRONIC_CONDITION_CHOICES)
    notes = models.TextField(blank=True)
    diagnosed_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.member.name} - {self.get_condition_display()}"


class ConsentLog(models.Model):
    ACTION_CHOICES = [
        ('abha_link', 'ABHA Linking'),
        ('data_share', 'Data Sharing'),
        ('member_invite', 'Member Invite'),
    ]
    member = models.ForeignKey(FamilyMember, on_delete=models.CASCADE, related_name='consent_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    consented = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.member.name} - {self.action} - {'Yes' if self.consented else 'No'}"
