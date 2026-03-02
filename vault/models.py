from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils import timezone
from accounts.models import Family, FamilyMember
import uuid


class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ("blood_test", "Blood Test"),
        ("urine_test", "Urine Test"),
        ("xray", "X-Ray"),
        ("mri", "MRI"),
        ("ct_scan", "CT Scan"),
        ("ecg", "ECG"),
        ("echo", "Echocardiogram"),
        ("prescription", "Prescription"),
        ("discharge_summary", "Discharge Summary"),
        ("vaccination", "Vaccination Card"),
        ("eye_test", "Eye Test"),
        ("dental", "Dental Report"),
        ("biopsy", "Biopsy Report"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="reports")
    member = models.ForeignKey(FamilyMember, on_delete=models.CASCADE, related_name="reports")
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    report_date = models.DateField()
    doctor = models.CharField(max_length=255, blank=True)
    hospital_lab = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to="reports/%Y/%m/", null=True, blank=True)
    notes = models.TextField(blank=True)
    is_abha_fetched = models.BooleanField(default=False)

    # Soft delete — never hard-delete medical records
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-report_date"]

    def __str__(self):
        return f"{self.member.name} - {self.get_report_type_display()} ({self.report_date})"

    def soft_delete(self):
        """Soft-delete this report. Preserves file and extraction data."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def file_extension(self) -> str:
        if self.file:
            name = self.file.name.lower()
            if name.endswith(".pdf"):
                return "pdf"
            elif name.endswith((".jpg", ".jpeg", ".png")):
                return "image"
        return "other"

    def has_extraction(self) -> bool:
        """Returns True if a completed ReportExtraction exists for this report."""
        try:
            return self.extraction.is_completed()
        except ReportExtraction.DoesNotExist:
            return False


class ReportExtraction(models.Model):
    """
    AI-extracted structured health parameters for a Report.

    Lifecycle:
      1. Signal fires after Report.save() with a file attached
      2. Service creates ReportExtraction(report=report, status=PENDING)
      3. Background thread sets status=PROCESSING, calls Azure OpenAI
      4. On success: status=COMPLETED, raw_data=<structured JSON>
      5. On failure: status=FAILED, error_message=<reason>

    Re-extraction:
      Just update status=PENDING and call trigger_extraction() again.
      The existing row is reused — no duplicate records.

    Accessing data (always use typed properties, never raw_data directly):
      report.extraction.sections
      report.extraction.patient_info
      report.extraction.health_score
      report.extraction.concern_parameters
      report.extraction.get_section("complete_blood_count")
      report.extraction.get_key_sections()
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    # OneToOne with Report — same UUID as primary key (no separate id field)
    report = models.OneToOneField(
        Report,
        on_delete=models.CASCADE,
        related_name="extraction",
        primary_key=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    raw_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full structured JSON returned by Azure OpenAI extraction.",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Populated when status=FAILED.",
    )
    extracted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when extraction completed successfully.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Report Extraction"
        verbose_name_plural = "Report Extractions"

    def __str__(self):
        return f"Extraction({self.report.title}) [{self.status}]"

    # -------------------------------------------------------------------------
    # Typed property accessors
    # -------------------------------------------------------------------------

    @property
    def sections(self) -> dict:
        """All extracted sections. Empty dict if not completed."""
        if not self.is_completed():
            return {}
        return self.raw_data.get("sections", {})

    @property
    def patient_info(self) -> dict:
        """Patient metadata extracted from the report document."""
        if not self.is_completed():
            return {}
        return self.raw_data.get("patient", {})

    @property
    def health_summary(self) -> dict:
        if not self.is_completed():
            return {}
        return self.raw_data.get("health_summary", {})

    @property
    def health_score(self):
        return self.health_summary.get("health_score")

    @property
    def concern_parameters(self) -> list:
        """Parameter keys flagged as concern/high/low by the AI."""
        return self.health_summary.get("concern_parameters", [])

    @property
    def normal_parameters(self) -> list:
        return self.health_summary.get("normal_parameters", [])

    def get_section(self, section_key: str) -> dict:
        """
        Safely retrieve one extracted section by key.
        Returns empty dict if section missing or extraction not complete.

        Usage:
            extraction.get_section("complete_blood_count")
            extraction.get_section("liver_function_test")
        """
        return self.sections.get(section_key, {})

    def get_key_sections(self) -> dict:
        """
        Returns clinically critical sections for emergency display.
        Only includes sections that have actual data (non-empty).
        """
        priority_keys = [
            "complete_blood_count",
            "biochemistry",
            "liver_function_test",
            "kidney_function_test",
            "lipid_profile",
            "thyroid_function",
            "vitamins_minerals",
            "urine_routine",
        ]
        return {k: v for k in priority_keys if (v := self.get_section(k))}

    # -------------------------------------------------------------------------
    # Status helpers
    # -------------------------------------------------------------------------

    def is_completed(self) -> bool:
        return self.status == self.Status.COMPLETED

    def is_processing(self) -> bool:
        return self.status in (self.Status.PENDING, self.Status.PROCESSING)

    def is_failed(self) -> bool:
        return self.status == self.Status.FAILED


class VaultAccessLog(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="access_logs")
    accessed_by = models.ForeignKey(FamilyMember, on_delete=models.SET_NULL, null=True)
    accessed_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, default="view")

    def __str__(self):
        return f"{self.accessed_by} — {self.report} — {self.action} — {self.accessed_at}"


class EmergencyShareLink(models.Model):
    """
    Password-protected shareable emergency health link.

    Caregiver creates a link → gets a URL like:
        /vault/emergency/share/<token>/
    Shares URL + chosen password with a doctor.
    Doctor enters password → sees emergency view (read-only, no Django login).

    Design decisions:
        - token is the PK (UUID) — also the URL slug
        - password stored as Django hash (make_password / check_password)
        - member=None → shows all family members
        - member=<obj> → shows only that member (e.g. share just for one patient)
        - is_active=False → revoke without losing audit record
        - last_accessed_at → caregiver can see when doctor last viewed
    """

    token = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="URL token. Regenerate to invalidate old link.",
    )
    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name="emergency_share_links",
    )
    member = models.ForeignKey(
        FamilyMember,
        on_delete=models.CASCADE,
        related_name="emergency_share_links",
        null=True,
        blank=True,
        help_text="Null = all members. Set to restrict to one member.",
    )
    password_hash = models.CharField(
        max_length=255,
        help_text="Django hashed password.",
    )
    label = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional label, e.g. 'Dr. Mehta', 'Apollo Hospital'.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Emergency Share Link"
        verbose_name_plural = "Emergency Share Links"
        ordering = ["-created_at"]

    def __str__(self):
        label = self.label or "Unnamed"
        scope = self.member.name if self.member else "All Members"
        return f"{label} — {scope} ({'Active' if self.is_active else 'Revoked'})"

    def set_password(self, raw_password: str) -> None:
        """Hash and store raw_password."""
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Validate raw_password against stored hash."""
        return check_password(raw_password, self.password_hash)

    def revoke(self) -> None:
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def record_access(self) -> None:
        self.last_accessed_at = timezone.now()
        self.save(update_fields=["last_accessed_at"])
