from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class Clinic(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    operating_hours_start = models.TimeField()
    operating_hours_end = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class VisitType(models.Model):
    name = models.CharField(max_length=100)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(480)]
    )
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.duration_minutes} mins)"


class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    clinics = models.ManyToManyField(Clinic, through="DoctorClinicAvailability")

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField()
    phone = models.CharField(max_length=20)
    emergency_contact = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.get_full_name()


class DoctorClinicAvailability(models.Model):
    DAYS_OF_WEEK = [
        (1, "Monday"),
        (2, "Tuesday"),
        (3, "Wednesday"),
        (4, "Thursday"),
        (5, "Friday"),
        (6, "Saturday"),
        (7, "Sunday"),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ["doctor", "clinic", "day_of_week"]
        verbose_name_plural = "Doctor clinic availabilities"

    def __str__(self):
        return f"{self.doctor} at {self.clinic} on {self.get_day_of_week_display()}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    visit_type = models.ForeignKey(VisitType, on_delete=models.CASCADE)
    scheduled_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_time"]

    def __str__(self):
        return f"{self.patient} with {self.doctor} at {self.scheduled_time}"

    def save(self, *args, **kwargs):
        # Calculate end_time if not set
        self.calculate_end_time()

        # Run validation
        self.full_clean()
        super().save(*args, **kwargs)

    def calculate_end_time(self):
        """Calculate end_time based on visit_type duration"""
        if self.visit_type and self.scheduled_time and not self.end_time:
            from datetime import timedelta

            self.end_time = self.scheduled_time + timedelta(
                minutes=self.visit_type.duration_minutes
            )

    def clean(self):
        """Validate that appointment doesn't overlap with existing appointments"""
        super().clean()

        # Ensure end_time is calculated
        self.calculate_end_time()

        if self.doctor and self.scheduled_time and self.end_time:
            # Check for overlapping appointments with the same doctor
            overlapping = (
                Appointment.objects.filter(doctor=self.doctor, status="scheduled")
                .exclude(pk=self.pk if self.pk else None)
                .filter(
                    scheduled_time__lt=self.end_time, end_time__gt=self.scheduled_time
                )
            )

            if overlapping.exists():
                raise ValidationError(
                    f"This appointment overlaps with an existing appointment. "
                    f"Doctor has an appointment from {overlapping.first().scheduled_time} "
                    f"to {overlapping.first().end_time}."
                )
