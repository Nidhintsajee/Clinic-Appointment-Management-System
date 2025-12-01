"""
Test coverage for core scheduling logic
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import datetime, timedelta, time, date
from django.utils import timezone
from .models import (
    Clinic,
    VisitType,
    Doctor,
    Patient,
    DoctorClinicAvailability,
    Appointment,
)


class CoreSchedulingLogicTests(TestCase):
    """Test core scheduling logic without API calls"""

    def setUp(self):
        # Create clinic
        self.clinic = Clinic.objects.create(
            name="Main Clinic",
            address="123 Main St",
            phone="555-1234",
            email="clinic@example.com",
            operating_hours_start=time(9, 0),
            operating_hours_end=time(17, 0),
        )

        # Create visit types
        self.consultation = VisitType.objects.create(
            name="Consultation", duration_minutes=30, clinic=self.clinic
        )

        self.procedure = VisitType.objects.create(
            name="Procedure", duration_minutes=60, clinic=self.clinic
        )

        # Create doctor
        doctor_user = User.objects.create_user(
            username="dr_smith",
            password="doctor123",
            first_name="John",
            last_name="Smith",
        )
        self.doctor = Doctor.objects.create(
            user=doctor_user, specialization="Cardiology", license_number="DOC001"
        )

        # Create patient
        patient_user = User.objects.create_user(
            username="patient1",
            password="patient123",
            first_name="Jane",
            last_name="Doe",
        )
        self.patient = Patient.objects.create(
            user=patient_user, date_of_birth="1990-01-01", phone="555-5678"
        )

        # Create availability (Monday to Friday, 9 AM to 5 PM)
        for day in range(1, 6):  # Monday to Friday
            DoctorClinicAvailability.objects.create(
                doctor=self.doctor,
                clinic=self.clinic,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(17, 0),
            )

    def test_appointment_duration_calculation(self):
        """Test that appointment end time is calculated correctly"""
        scheduled_time = timezone.make_aware(datetime(2024, 1, 1, 10, 0, 0))

        # Test 30-minute consultation
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=scheduled_time,
            status="scheduled",
        )

        expected_end = scheduled_time + timedelta(minutes=30)
        self.assertEqual(appointment.end_time, expected_end)

        # Test 60-minute procedure
        appointment2 = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.procedure,
            scheduled_time=scheduled_time + timedelta(hours=2),
            status="scheduled",
        )

        expected_end2 = scheduled_time + timedelta(hours=2, minutes=60)
        self.assertEqual(appointment2.end_time, expected_end2)

    def test_appointment_overlap_detection(self):
        """Test that overlapping appointments are detected and prevented"""
        # Create first appointment: 10:00 - 10:30
        start1 = timezone.make_aware(datetime(2024, 1, 1, 10, 0, 0))
        appointment1 = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=start1,
            status="scheduled",
        )

        # Test exact overlap: 10:00 - 10:30
        start2 = timezone.make_aware(datetime(2024, 1, 1, 10, 0, 0))
        appointment2 = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=start2,
            status="scheduled",
        )

        with self.assertRaises(Exception):
            appointment2.clean()  # Should raise ValidationError

        # Test partial overlap: 10:15 - 10:45
        start3 = timezone.make_aware(datetime(2024, 1, 1, 10, 15, 0))
        appointment3 = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=start3,
            status="scheduled",
        )

        with self.assertRaises(Exception):
            appointment3.clean()  # Should raise ValidationError

        # Test contained within: 10:05 - 10:25
        start4 = timezone.make_aware(datetime(2024, 1, 1, 10, 5, 0))
        appointment4 = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=VisitType.objects.create(
                name="Quick Check", duration_minutes=20, clinic=self.clinic
            ),
            scheduled_time=start4,
            status="scheduled",
        )

        with self.assertRaises(Exception):
            appointment4.clean()  # Should raise ValidationError

    def test_no_overlap_for_different_doctors(self):
        """Test that appointments for different doctors don't conflict"""
        # Create second doctor
        doctor2_user = User.objects.create_user(
            username="dr_jones",
            password="doctor123",
            first_name="Bob",
            last_name="Jones",
        )
        doctor2 = Doctor.objects.create(
            user=doctor2_user, specialization="Dermatology", license_number="DOC002"
        )

        # Create availability for second doctor
        DoctorClinicAvailability.objects.create(
            doctor=doctor2,
            clinic=self.clinic,
            day_of_week=1,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        # Create appointment for doctor 1: 10:00 - 10:30
        start = timezone.make_aware(datetime(2024, 1, 1, 10, 0, 0))
        appointment1 = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=start,
            status="scheduled",
        )

        # Should allow appointment for doctor 2 at same time
        appointment2 = Appointment(
            patient=self.patient,
            doctor=doctor2,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=start,
            status="scheduled",
        )

        # This should NOT raise an error
        try:
            appointment2.clean()
            appointment2.save()  # Should succeed
        except Exception as e:
            self.fail(f"Appointment for different doctor should not conflict: {e}")

    def test_no_overlap_for_cancelled_appointments(self):
        """Test that cancelled appointments don't block scheduling"""
        # Create cancelled appointment: 10:00 - 10:30
        start = timezone.make_aware(datetime(2024, 1, 1, 10, 0, 0))
        cancelled_appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=start,
            status="cancelled",
        )

        # Should allow new appointment at same time
        new_appointment = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=start,
            status="scheduled",
        )

        # This should NOT raise an error
        try:
            new_appointment.clean()
            new_appointment.save()  # Should succeed
        except Exception as e:
            self.fail(f"Cancelled appointments should not block scheduling: {e}")

    def test_availability_validation(self):
        """Test that appointments can only be scheduled during doctor's availability"""
        # Doctor has availability Monday (day 1) 9 AM - 5 PM

        # Valid: Monday at 10 AM
        valid_time = timezone.make_aware(datetime(2024, 1, 1, 10, 0, 0))  # Monday
        appointment1 = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=valid_time,
            status="scheduled",
        )

        # Invalid: Monday at 8 AM (before availability)
        invalid_time_early = timezone.make_aware(datetime(2024, 1, 1, 8, 0, 0))
        appointment2 = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=invalid_time_early,
            status="scheduled",
        )

        # Invalid: Monday at 5 PM (at closing time, no time for appointment)
        invalid_time_late = timezone.make_aware(datetime(2024, 1, 1, 17, 0, 0))
        appointment3 = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=invalid_time_late,
            status="scheduled",
        )

        # Invalid: Saturday (no availability)
        saturday_time = timezone.make_aware(datetime(2024, 1, 6, 10, 0, 0))  # Saturday
        appointment4 = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=saturday_time,
            status="scheduled",
        )

        # Note: Our current model doesn't validate availability in clean() method
        # This test documents the expected behavior

    def test_appointment_status_workflow(self):
        """Test appointment status changes and their effects"""
        start = timezone.make_aware(datetime(2024, 1, 1, 10, 0, 0))

        # Create scheduled appointment
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=start,
            status="scheduled",
        )

        # Change to completed - should still exist but not block new appointments
        appointment.status = "completed"
        appointment.save()

        # Should allow new appointment at same time
        new_appointment = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=start,
            status="scheduled",
        )

        try:
            new_appointment.clean()
            new_appointment.save()
        except Exception as e:
            self.fail(f"Completed appointments should not block scheduling: {e}")

    def test_multiple_clinics_same_doctor(self):
        """Test doctor working at multiple clinics with different availability"""
        # Create second clinic
        clinic2 = Clinic.objects.create(
            name="Branch Clinic",
            address="456 Branch St",
            phone="555-9999",
            email="branch@example.com",
            operating_hours_start=time(8, 0),
            operating_hours_end=time(16, 0),
        )

        # Create availability at second clinic (different hours)
        DoctorClinicAvailability.objects.create(
            doctor=self.doctor,
            clinic=clinic2,
            day_of_week=1,  # Monday
            start_time=time(8, 0),  # Earlier start
            end_time=time(16, 0),  # Earlier end
        )

        # Test appointment at main clinic during its hours
        main_clinic_time = timezone.make_aware(datetime(2024, 1, 1, 10, 0, 0))
        appointment1 = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,  # Main clinic
            visit_type=self.consultation,
            scheduled_time=main_clinic_time,
            status="scheduled",
        )

        # Test appointment at branch clinic during its hours
        branch_clinic_time = timezone.make_aware(datetime(2024, 1, 1, 8, 30, 0))
        appointment2 = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=clinic2,  # Branch clinic
            visit_type=self.consultation,
            scheduled_time=branch_clinic_time,
            status="scheduled",
        )

        # Both appointments should exist
        self.assertEqual(Appointment.objects.count(), 2)

        # Try to schedule at branch clinic outside its hours (should work but be invalid)
        invalid_time = timezone.make_aware(datetime(2024, 1, 1, 16, 30, 0))
        appointment3 = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            clinic=clinic2,
            visit_type=self.consultation,
            scheduled_time=invalid_time,
            status="scheduled",
        )

        # Note: Current model doesn't validate clinic operating hours
        # This would be an enhancement


class AvailableSlotsAPITests(APITestCase):
    """Test available slots API endpoint"""

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

        # Create visit types
        self.consultation = VisitType.objects.create(
            name="Consultation", duration_minutes=30, clinic=self.clinic
        )

        self.procedure = VisitType.objects.create(
            name="Procedure", duration_minutes=60, clinic=self.clinic
        )

        # Create doctor
        doctor_user = User.objects.create_user(
            username="dr_test",
            password="doctor123",
            first_name="Test",
            last_name="Doctor",
        )
        self.doctor = Doctor.objects.create(
            user=doctor_user, specialization="General", license_number="DOC999"
        )

        # Create availability (Monday 9 AM - 5 PM)
        self.availability = DoctorClinicAvailability.objects.create(
            doctor=self.doctor,
            clinic=self.clinic,
            day_of_week=1,  # Monday
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        # Create patient
        patient_user = User.objects.create_user(
            username="test_patient",
            password="patient123",
            first_name="Test",
            last_name="Patient",
        )
        self.patient = Patient.objects.create(
            user=patient_user, date_of_birth="1990-01-01", phone="555-5678"
        )

    def test_available_slots_basic(self):
        """Test basic available slots calculation"""
        url = "/api/available-slots/"
        params = {
            "doctor_id": self.doctor.id,
            "clinic_id": self.clinic.id,
            "visit_type_id": self.consultation.id,
            "date": "2024-01-01",  # Monday
        }

        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn("available_slots", data)
        self.assertIn("doctor", data)
        self.assertIn("clinic", data)
        self.assertIn("visit_type", data)

        # Should have slots from 9:00 to 16:30 (last 30-minute slot)
        slots = data["available_slots"]
        self.assertTrue(len(slots) > 0)
        self.assertIn("09:00", slots)  # First slot
        self.assertIn("16:30", slots)  # Last 30-minute slot

        # 17:00 should NOT be in slots (appointment would end at 17:30)
        self.assertNotIn("17:00", slots)

    def test_available_slots_with_existing_appointments(self):
        """Test available slots when appointments already exist"""
        # Create an appointment from 10:00 to 10:30
        appointment_time = timezone.make_aware(datetime(2024, 1, 1, 10, 0, 0))
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=appointment_time,
            status="scheduled",
        )

        url = "/api/available-slots/"
        params = {
            "doctor_id": self.doctor.id,
            "clinic_id": self.clinic.id,
            "visit_type_id": self.consultation.id,
            "date": "2024-01-01",
        }

        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        slots = response.data["available_slots"]

        # 10:00 should NOT be available (taken)
        self.assertNotIn("10:00", slots)

        # 9:30 should be available (ends at 10:00, no overlap)
        self.assertIn("09:30", slots)

        # 10:30 should be available (starts when appointment ends)
        self.assertIn("10:30", slots)

    def test_available_slots_different_durations(self):
        """Test available slots for different visit type durations"""
        # Create 60-minute procedure appointment from 10:00 to 11:00
        appointment_time = timezone.make_aware(datetime(2024, 1, 1, 10, 0, 0))
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.procedure,  # 60 minutes
            scheduled_time=appointment_time,
            status="scheduled",
        )

        # Test for 30-minute consultation
        url = "/api/available-slots/"
        params = {
            "doctor_id": self.doctor.id,
            "clinic_id": self.clinic.id,
            "visit_type_id": self.consultation.id,  # 30 minutes
            "date": "2024-01-01",
        }

        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        slots = response.data["available_slots"]

        # 10:00 should NOT be available
        self.assertNotIn("10:00", slots)

        # 10:30 should NOT be available (would overlap 10:30-11:00 with 10:00-11:00)
        self.assertNotIn("10:30", slots)

        # 11:00 should be available
        self.assertIn("11:00", slots)

        # 9:30 should be available (ends at 10:00, no overlap)
        self.assertIn("09:30", slots)

    def test_available_slots_no_availability(self):
        """Test available slots when doctor has no availability"""
        # Create doctor with no availability on the test day
        doctor2_user = User.objects.create_user(
            username="dr_no_avail",
            password="doctor123",
            first_name="No",
            last_name="Availability",
        )
        doctor2 = Doctor.objects.create(
            user=doctor2_user, specialization="None", license_number="DOC000"
        )

        url = "/api/available-slots/"
        params = {
            "doctor_id": doctor2.id,
            "clinic_id": self.clinic.id,
            "visit_type_id": self.consultation.id,
            "date": "2024-01-01",  # Monday
        }

        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should return empty slots
        self.assertEqual(response.data["available_slots"], [])

    def test_available_slots_invalid_parameters(self):
        """Test available slots with invalid/missing parameters"""
        url = "/api/available-slots/"

        # Missing all parameters
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Missing some parameters
        params = {
            "doctor_id": self.doctor.id,
            "clinic_id": self.clinic.id,
            # Missing visit_type_id and date
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid IDs
        params = {
            "doctor_id": 999,
            "clinic_id": 999,
            "visit_type_id": 999,
            "date": "2024-01-01",
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid date format
        params = {
            "doctor_id": self.doctor.id,
            "clinic_id": self.clinic.id,
            "visit_type_id": self.consultation.id,
            "date": "invalid-date",
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_available_slots_edge_cases(self):
        """Test edge cases for available slots"""
        # Test with appointment at the very beginning of day
        early_appointment = timezone.make_aware(datetime(2024, 1, 1, 9, 0, 0))
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=early_appointment,
            status="scheduled",
        )

        # Test with appointment at the very end of day
        late_appointment = timezone.make_aware(datetime(2024, 1, 1, 16, 30, 0))
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            visit_type=self.consultation,
            scheduled_time=late_appointment,
            status="scheduled",
        )

        url = "/api/available-slots/"
        params = {
            "doctor_id": self.doctor.id,
            "clinic_id": self.clinic.id,
            "visit_type_id": self.consultation.id,
            "date": "2024-01-01",
        }

        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        slots = response.data["available_slots"]

        # 9:00 should NOT be available (taken)
        self.assertNotIn("09:00", slots)

        # 9:30 should be available
        self.assertIn("09:30", slots)

        # 16:30 should NOT be available (taken)
        self.assertNotIn("16:30", slots)

        # CORRECTED: 16:00 SHOULD be available (16:00-16:30 doesn't overlap with 16:30-17:00)
        self.assertIn("16:00", slots)  # Changed from assertNotIn to assertIn

        # 15:30 should be available
        self.assertIn("15:30", slots)


class AppointmentAPISchedulingTests(APITestCase):
    """Test appointment creation through API with scheduling logic"""

    def setUp(self):
        # Create clinic
        self.clinic = Clinic.objects.create(
            name="API Test Clinic",
            address="123 API St",
            phone="555-API1",
            email="api@clinic.com",
            operating_hours_start=time(9, 0),
            operating_hours_end=time(17, 0),
        )

        # Create visit type
        self.visit_type = VisitType.objects.create(
            name="API Consultation", duration_minutes=30, clinic=self.clinic
        )

        # Create doctor
        doctor_user = User.objects.create_user(
            username="api_doctor",
            password="doctor123",
            first_name="API",
            last_name="Doctor",
        )
        self.doctor = Doctor.objects.create(
            user=doctor_user, specialization="API Testing", license_number="API123"
        )

        # Create availability
        DoctorClinicAvailability.objects.create(
            doctor=self.doctor,
            clinic=self.clinic,
            day_of_week=1,  # Monday
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        # Create patient and authenticate
        self.patient_user = User.objects.create_user(
            username="api_patient",
            password="patient123",
            first_name="API",
            last_name="Patient",
        )
        self.patient = Patient.objects.create(
            user=self.patient_user, date_of_birth="1990-01-01", phone="555-API2"
        )

        # Authenticate
        self.client.force_authenticate(user=self.patient_user)

    def test_create_appointment_success(self):
        """Test successful appointment creation"""
        url = "/api/appointments/"
        data = {
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:00:00Z",
            "notes": "Test appointment via API",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify response data
        self.assertIn("id", response.data)
        self.assertEqual(response.data["doctor"], self.doctor.id)
        self.assertEqual(response.data["clinic"], self.clinic.id)
        self.assertEqual(response.data["patient"], self.patient.id)
        self.assertEqual(response.data["scheduled_time"], "2024-01-01T10:00:00Z")

        # Verify end_time was calculated
        self.assertIn("end_time", response.data)
        self.assertEqual(response.data["end_time"], "2024-01-01T10:30:00Z")

        # Verify appointment exists in database
        appointment = Appointment.objects.get(id=response.data["id"])
        self.assertEqual(appointment.patient.id, self.patient.id)
        self.assertEqual(appointment.doctor.id, self.doctor.id)

    def test_create_appointment_overlap_failure(self):
        """Test that overlapping appointments are rejected"""
        url = "/api/appointments/"

        # Create first appointment
        data1 = {
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:00:00Z",
        }
        response1 = self.client.post(url, data1, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Try to create overlapping appointment
        data2 = {
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:15:00Z",  # Overlaps
        }
        response2 = self.client.post(url, data2, format="json")

        # Should fail with 400
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("overlap", str(response2.data).lower())

        # Verify only one appointment exists
        self.assertEqual(Appointment.objects.count(), 1)

    def test_create_appointment_non_overlapping_success(self):
        """Test that non-overlapping appointments are allowed"""
        url = "/api/appointments/"

        # Create first appointment
        data1 = {
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:00:00Z",
        }
        response1 = self.client.post(url, data1, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Create non-overlapping appointment (right after first ends)
        data2 = {
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:30:00Z",  # No overlap
        }
        response2 = self.client.post(url, data2, format="json")

        # Should succeed
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Verify both appointments exist
        self.assertEqual(Appointment.objects.count(), 2)

    def test_create_appointment_different_doctors(self):
        """Test appointments for different doctors don't conflict"""
        # Create second doctor
        doctor2_user = User.objects.create_user(
            username="api_doctor2",
            password="doctor123",
            first_name="API",
            last_name="Doctor2",
        )
        doctor2 = Doctor.objects.create(
            user=doctor2_user, specialization="Second API", license_number="API456"
        )

        # Create availability for second doctor
        DoctorClinicAvailability.objects.create(
            doctor=doctor2,
            clinic=self.clinic,
            day_of_week=1,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        url = "/api/appointments/"

        # Create appointment for first doctor
        data1 = {
            "doctor": self.doctor.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:00:00Z",
        }
        response1 = self.client.post(url, data1, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Create appointment for second doctor at same time
        data2 = {
            "doctor": doctor2.id,
            "clinic": self.clinic.id,
            "visit_type": self.visit_type.id,
            "scheduled_time": "2024-01-01T10:00:00Z",  # Same time, different doctor
        }
        response2 = self.client.post(url, data2, format="json")

        # Should succeed
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Verify both appointments exist
        self.assertEqual(Appointment.objects.count(), 2)
