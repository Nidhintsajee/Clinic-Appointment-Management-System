from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import datetime, timedelta, time
from .models import (
    Clinic,
    VisitType,
    Doctor,
    Patient,
    DoctorClinicAvailability,
    Appointment,
)


class AppointmentSchedulingTests(APITestCase):
    def setUp(self):
        # Create clinic
        self.clinic = Clinic.objects.create(
            name="Test Clinic",
            address="123 Test St",
            phone="555-1234",
            email="test@clinic.com",
            operating_hours_start=time(9, 0),
            operating_hours_end=time(17, 0),
        )

        # Create visit type
        self.visit_type = VisitType.objects.create(
            name="Consultation", duration_minutes=30, clinic=self.clinic
        )

        # Create doctor
        doctor_user = User.objects.create_user(
            username="doctor", password="doctor123", first_name="John", last_name="Doe"
        )
        self.doctor = Doctor.objects.create(
            user=doctor_user, specialization="Cardiology", license_number="DOC123"
        )

        # Create availability
        self.availability = DoctorClinicAvailability.objects.create(
            doctor=self.doctor,
            clinic=self.clinic,
            day_of_week=1,  # Monday
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

    def test_available_slots(self):
        """Test available slots endpoint (no auth required)"""
        url = "/api/available-slots/"
        params = {
            "doctor_id": self.doctor.id,
            "clinic_id": self.clinic.id,
            "visit_type_id": self.visit_type.id,
            "date": "2024-01-01",  # This should be a Monday
        }

        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("available_slots", response.data)

    def test_appointment_creation_as_patient(self):
        """Test creating an appointment as a patient user"""
        # Create patient user
        patient_user = User.objects.create_user(
            username="patient",
            password="patient123",
            first_name="Jane",
            last_name="Smith",
        )
        patient = Patient.objects.create(
            user=patient_user, date_of_birth="1990-01-01", phone="555-5678"
        )

        # Force authenticate as patient user
        self.client.force_authenticate(user=patient_user)

        # Create appointment - DON'T include patient field
        appointment_data = {
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:00:00Z",
            "notes": "Test appointment",
        }

        response = self.client.post(
            "/api/appointments/", appointment_data, format="json"
        )

        # Debug output
        print(f"Appointment Creation Response Status: {response.status_code}")
        print(f"Appointment Creation Response Data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify appointment was created with correct patient
        appointment = Appointment.objects.first()
        self.assertEqual(appointment.patient.id, patient.id)
        self.assertEqual(appointment.doctor.id, self.doctor.id)

        # Clean up authentication
        self.client.force_authenticate(user=None)

    def test_appointment_creation_as_staff(self):
        """Test creating an appointment as staff/admin user"""
        # Create staff user
        staff_user = User.objects.create_user(
            username="staff",
            password="staff123",
            first_name="Staff",
            last_name="User",
            is_staff=True,
        )

        # Create patient
        patient_user = User.objects.create_user(
            username="patient2",
            password="patient123",
            first_name="John",
            last_name="Doe",
        )
        patient = Patient.objects.create(
            user=patient_user, date_of_birth="1990-01-01", phone="555-5678"
        )

        # Force authenticate as staff user
        self.client.force_authenticate(user=staff_user)

        # Staff can specify patient field
        appointment_data = {
            "patient": patient.id,
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T11:00:00Z",
            "notes": "Staff created appointment",
        }

        response = self.client.post(
            "/api/appointments/", appointment_data, format="json"
        )

        # Debug output
        print(f"Staff Appointment Creation Response Status: {response.status_code}")
        print(f"Staff Appointment Creation Response Data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify appointment was created
        self.assertTrue(Appointment.objects.filter(patient=patient).exists())

        # Clean up authentication
        self.client.force_authenticate(user=None)

    def test_no_double_booking(self):
        """Test that double booking is prevented"""
        # Create patient
        patient_user = User.objects.create_user(
            username="patient3",
            password="patient123",
            first_name="Jane",
            last_name="Smith",
        )
        patient = Patient.objects.create(
            user=patient_user, date_of_birth="1990-01-01", phone="555-5678"
        )

        # Force authenticate as patient
        self.client.force_authenticate(user=patient_user)

        # Create first appointment
        appointment_data1 = {
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:00:00Z",
        }

        response1 = self.client.post(
            "/api/appointments/", appointment_data1, format="json"
        )

        print(f"First Appointment Response Status: {response1.status_code}")
        print(f"First Appointment Response Data: {response1.data}")

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Try to create overlapping appointment (15 minutes later - should overlap)
        appointment_data2 = {
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:15:00Z",  # Overlaps with first
        }

        response2 = self.client.post(
            "/api/appointments/", appointment_data2, format="json"
        )

        print(
            f"Second Appointment (Overlapping) Response Status: {response2.status_code}"
        )
        print(f"Second Appointment Response Data: {response2.data}")

        # Should fail with 400 Bad Request
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("overlap", str(response2.data).lower())

        # Try to create non-overlapping appointment (should succeed)
        appointment_data3 = {
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:30:00Z",  # Right after first ends
        }

        response3 = self.client.post(
            "/api/appointments/", appointment_data3, format="json"
        )

        print(
            f"Third Appointment (Non-overlapping) Response Status: {response3.status_code}"
        )
        print(f"Third Appointment Response Data: {response3.data}")

        self.assertEqual(response3.status_code, status.HTTP_201_CREATED)

        # Clean up authentication
        self.client.force_authenticate(user=None)
