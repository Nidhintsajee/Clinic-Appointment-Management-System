from django.contrib import admin
from .models import (
    Clinic,
    VisitType,
    Doctor,
    Patient,
    DoctorClinicAvailability,
    Appointment,
)


# Inline for DoctorClinicAvailability
class DoctorClinicAvailabilityInline(admin.TabularInline):
    model = DoctorClinicAvailability
    extra = 1
    fields = ["clinic", "day_of_week", "start_time", "end_time"]


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ["user", "specialization", "license_number", "get_clinics"]
    search_fields = [
        "user__first_name",
        "user__last_name",
        "specialization",
        "license_number",
    ]
    inlines = [DoctorClinicAvailabilityInline]  # Add inline for availability

    def get_clinics(self, obj):
        return ", ".join([clinic.name for clinic in obj.clinics.all()])

    get_clinics.short_description = "Clinics"


# Rest of the admin classes remain the same...
@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "phone",
        "email",
        "operating_hours_start",
        "operating_hours_end",
    ]
    search_fields = ["name", "email"]


@admin.register(VisitType)
class VisitTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "duration_minutes", "clinic"]
    list_filter = ["clinic"]
    search_fields = ["name"]


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["user", "date_of_birth", "phone", "emergency_contact"]
    search_fields = ["user__first_name", "user__last_name", "phone"]


@admin.register(DoctorClinicAvailability)
class DoctorClinicAvailabilityAdmin(admin.ModelAdmin):
    list_display = ["doctor", "clinic", "day_of_week", "start_time", "end_time"]
    list_filter = ["clinic", "day_of_week", "doctor"]
    search_fields = [
        "doctor__user__first_name",
        "doctor__user__last_name",
        "clinic__name",
    ]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        "patient",
        "doctor",
        "clinic",
        "scheduled_time",
        "status",
        "visit_type",
    ]
    list_filter = ["status", "clinic", "scheduled_time", "doctor"]
    search_fields = [
        "patient__user__first_name",
        "patient__user__last_name",
        "doctor__user__first_name",
        "doctor__user__last_name",
    ]
    date_hierarchy = "scheduled_time"
