from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db.models import Q
from datetime import datetime, timedelta, time
from django.utils import timezone
from .models import (
    Clinic,
    VisitType,
    Doctor,
    Patient,
    DoctorClinicAvailability,
    Appointment,
)
from .serializers import (
    LoginSerializer,
    PatientRegistrationSerializer,
    DoctorRegistrationSerializer,
    PatientSerializer,
    DoctorSerializer,
    ChangePasswordSerializer,
    ClinicSerializer,
    VisitTypeSerializer,
    DoctorClinicAvailabilitySerializer,
    AppointmentSerializer,
)
from .permissions import (
    IsPatient,
    IsDoctor,
    IsClinicStaff,
    IsOwnerOrReadOnly,
    IsPatientOwner,
    IsDoctorOwner,
)


# Authentication Views
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "token": token.key,
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_doctor": hasattr(user, "doctor"),
                    "is_patient": hasattr(user, "patient"),
                    "is_staff": user.is_staff,
                }
            )
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        request.user.auth_token.delete()
        return Response({"message": "Successfully logged out"})
    except:
        return Response(
            {"error": "Error logging out"}, status=status.HTTP_400_BAD_REQUEST
        )


# Registration Views
@api_view(["POST"])
@permission_classes([AllowAny])
def patient_register(request):
    serializer = PatientRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        patient = serializer.save()
        token, created = Token.objects.get_or_create(user=patient.user)

        return Response(
            {
                "message": "Patient registered successfully",
                "patient_id": patient.id,
                "user_id": patient.user.id,
                "token": token.key,
                "username": patient.user.username,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def doctor_register(request):
    serializer = DoctorRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        doctor = serializer.save()
        token, created = Token.objects.get_or_create(user=doctor.user)

        return Response(
            {
                "message": "Doctor registered successfully",
                "doctor_id": doctor.id,
                "user_id": doctor.user.id,
                "token": token.key,
                "username": doctor.user.username,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Profile Views
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user profile"""
    user = request.user
    profile_data = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_doctor": hasattr(user, "doctor"),
        "is_patient": hasattr(user, "patient"),
        "is_staff": user.is_staff,
    }

    if hasattr(user, "patient"):
        profile_data["patient"] = PatientSerializer(user.patient).data
    if hasattr(user, "doctor"):
        profile_data["doctor"] = DoctorSerializer(user.doctor).data

    return Response(profile_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user

        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"error": "Old password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save()

        # Update token
        Token.objects.filter(user=user).delete()
        new_token = Token.objects.create(user=user)

        return Response(
            {"message": "Password changed successfully", "token": new_token.key}
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Clinic Views - Public read, Admin write
class ClinicListCreateView(generics.ListCreateAPIView):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]


class ClinicDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    permission_classes = [IsAdminUser]


# Visit Type Views - Authenticated read, Clinic staff write
class VisitTypeListCreateView(generics.ListCreateAPIView):
    queryset = VisitType.objects.all()
    serializer_class = VisitTypeSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsClinicStaff()]


class VisitTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VisitType.objects.all()
    serializer_class = VisitTypeSerializer
    permission_classes = [IsClinicStaff]


# Doctor Views
class DoctorListCreateView(generics.ListCreateAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdminUser()]


class DoctorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAdminUser]


# Patient Views - Admin only for list, patients can view own
class PatientListCreateView(generics.ListCreateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAdminUser]


class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAdminUser]


# Availability Views
class DoctorClinicAvailabilityListCreateView(generics.ListCreateAPIView):
    serializer_class = DoctorClinicAvailabilitySerializer
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_queryset(self):
        if hasattr(self.request.user, "doctor"):
            return DoctorClinicAvailability.objects.filter(
                doctor=self.request.user.doctor
            )
        return DoctorClinicAvailability.objects.all()

    def perform_create(self, serializer):
        if hasattr(self.request.user, "doctor"):
            serializer.save(doctor=self.request.user.doctor)


class DoctorClinicAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DoctorClinicAvailability.objects.all()
    serializer_class = DoctorClinicAvailabilitySerializer
    permission_classes = [IsAuthenticated, IsDoctorOwner]


class AppointmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if hasattr(user, "patient"):
            return Appointment.objects.filter(patient=user.patient)
        if hasattr(user, "doctor"):
            return Appointment.objects.filter(doctor=user.doctor)
        if user.is_staff:
            return Appointment.objects.all()
        return Appointment.objects.none()

    def create(self, request, *args, **kwargs):
        # Handle patient assignment and validation
        data = request.data.copy()

        # If user is a patient, auto-assign them and prevent assigning to others
        if hasattr(request.user, "patient"):
            if "patient" in data:
                if int(data["patient"]) != request.user.patient.id:
                    return Response(
                        {"error": "You can only create appointments for yourself"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            else:
                # Auto-assign the current patient
                data["patient"] = request.user.patient.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):
        serializer.save()


class AppointmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


@api_view(["GET"])
@permission_classes([AllowAny])
def available_slots(request):
    """Get available appointment slots"""
    required = ["doctor_id", "clinic_id", "visit_type_id", "date"]
    if not all(param in request.GET for param in required):
        return Response(
            {"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        date = datetime.strptime(request.GET["date"], "%Y-%m-%d").date()
        doctor = Doctor.objects.get(id=request.GET["doctor_id"])
        clinic = Clinic.objects.get(id=request.GET["clinic_id"])
        visit_type = VisitType.objects.get(id=request.GET["visit_type_id"])
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Check doctor availability
    availability = DoctorClinicAvailability.objects.filter(
        doctor=doctor, clinic=clinic, day_of_week=date.isoweekday()
    ).first()

    if not availability:
        return Response({"available_slots": []})

    # Get booked appointments with their durations
    appointments = Appointment.objects.filter(
        doctor=doctor, scheduled_time__date=date, status="scheduled"
    ).select_related("visit_type")

    slot_duration = timedelta(minutes=visit_type.duration_minutes)
    available_slots = []

    current_time = timezone.make_aware(datetime.combine(date, availability.start_time))
    end_time = timezone.make_aware(datetime.combine(date, availability.end_time))

    # Create a set of all busy times (at 15-minute intervals)
    busy_times = set()
    for appointment in appointments:
        appt_start = appointment.scheduled_time
        appt_duration = timedelta(minutes=appointment.visit_type.duration_minutes)
        appt_end = appt_start + appt_duration

        # Mark every 15-minute interval within this appointment as busy
        time_slot = appt_start
        while time_slot < appt_end:
            busy_times.add(time_slot.time())
            time_slot += timedelta(minutes=15)

    while current_time + slot_duration <= end_time:
        # Check if any 15-minute interval within this slot is busy
        slot_available = True
        check_time = current_time
        while check_time < current_time + slot_duration:
            if check_time.time() in busy_times:
                slot_available = False
                break
            check_time += timedelta(minutes=15)

        if slot_available:
            available_slots.append(current_time.strftime("%H:%M"))

        current_time += timedelta(minutes=15)

    return Response(
        {
            "doctor": f"Dr. {doctor.user.get_full_name()}",
            "clinic": clinic.name,
            "visit_type": visit_type.name,
            "date": request.GET["date"],
            "available_slots": available_slots,
        }
    )
