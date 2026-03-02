from django.db import models
from accounts.models import Family, FamilyMember
import uuid


class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('blood_test', 'Blood Test'),
        ('urine_test', 'Urine Test'),
        ('xray', 'X-Ray'),
        ('mri', 'MRI'),
        ('ct_scan', 'CT Scan'),
        ('ecg', 'ECG'),
        ('echo', 'Echocardiogram'),
        ('prescription', 'Prescription'),
        ('discharge_summary', 'Discharge Summary'),
        ('vaccination', 'Vaccination Card'),
        ('eye_test', 'Eye Test'),
        ('dental', 'Dental Report'),
        ('biopsy', 'Biopsy Report'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='reports')
    member = models.ForeignKey(FamilyMember, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    report_date = models.DateField()
    doctor = models.CharField(max_length=255, blank=True)
    hospital_lab = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to='reports/%Y/%m/', null=True, blank=True)
    notes = models.TextField(blank=True)
    is_abha_fetched = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-report_date']

    def __str__(self):
        return f"{self.member.name} - {self.get_report_type_display()} ({self.report_date})"

    def file_extension(self):
        if self.file:
            name = self.file.name.lower()
            if name.endswith('.pdf'):
                return 'pdf'
            elif name.endswith(('.jpg', '.jpeg', '.png')):
                return 'image'
        return 'other'


class VaultAccessLog(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='access_logs')
    accessed_by = models.ForeignKey(FamilyMember, on_delete=models.SET_NULL, null=True)
    accessed_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, default='view')  # view, download, share

    def __str__(self):
        return f"{self.accessed_by} - {self.report} - {self.action} - {self.accessed_at}"
