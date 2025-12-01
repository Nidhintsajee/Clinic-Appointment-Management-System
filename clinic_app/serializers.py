from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import (
    Clinic,
    VisitType,
    Doctor,
    Patient,
    DoctorClinicAvailability,
    Appointment,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_staff"]
        read_only_fields = ["is_staff"]


class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = "__all__"


class VisitTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitType
        fields = "__all__"


class DoctorSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Doctor
        fields = "__all__"


class PatientSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Patient
        fields = "__all__"


class DoctorClinicAvailabilitySerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(
        source="doctor.user.get_full_name", read_only=True
    )
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)

    class Meta:
        model = DoctorClinicAvailability
        fields = "__all__"


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source="patient.user.get_full_name", read_only=True
    )
    doctor_name = serializers.CharField(
        source="doctor.user.get_full_name", read_only=True
    )
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    visit_type_name = serializers.CharField(source="visit_type.name", read_only=True)

    class Meta:
        model = Appointment
        fields = "__all__"
        read_only_fields = ["created_at", "end_time"]

    def validate(self, data):
        """Custom validation to prevent double booking"""
        # Call model's clean method for validation
        instance = Appointment(**data)
        try:
            instance.clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)

        return data

    def create(self, validated_data):
        # Calculate end time based on visit type
        visit_type = validated_data.get("visit_type")
        scheduled_time = validated_data.get("scheduled_time")

        if visit_type and scheduled_time:
            from datetime import timedelta

            validated_data["end_time"] = scheduled_time + timedelta(
                minutes=visit_type.duration_minutes
            )

        return super().create(validated_data)


class PatientRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True, min_length=4, max_length=150)
    password = serializers.CharField(
        write_only=True, min_length=8, validators=[validate_password]
    )
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True, max_length=30)
    last_name = serializers.CharField(write_only=True, max_length=30)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = Patient
        fields = [
            "username",
            "password",
            "confirm_password",
            "email",
            "first_name",
            "last_name",
            "date_of_birth",
            "phone",
            "emergency_contact",
        ]

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")

        if User.objects.filter(username=data["username"]).exists():
            raise serializers.ValidationError("Username already exists")

        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError("Email already exists")

        return data

    def create(self, validated_data):
        user_data = {
            "username": validated_data["username"],
            "password": validated_data["password"],
            "email": validated_data["email"],
            "first_name": validated_data["first_name"],
            "last_name": validated_data["last_name"],
        }

        user = User.objects.create_user(
            username=user_data["username"],
            password=user_data["password"],
            email=user_data["email"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
        )

        patient = Patient.objects.create(
            user=user,
            date_of_birth=validated_data["date_of_birth"],
            phone=validated_data["phone"],
            emergency_contact=validated_data.get("emergency_contact", ""),
        )

        return patient


class DoctorRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True, min_length=4, max_length=150)
    password = serializers.CharField(
        write_only=True, min_length=8, validators=[validate_password]
    )
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True, max_length=30)
    last_name = serializers.CharField(write_only=True, max_length=30)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = Doctor
        fields = [
            "username",
            "password",
            "confirm_password",
            "email",
            "first_name",
            "last_name",
            "specialization",
            "license_number",
        ]

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")

        if User.objects.filter(username=data["username"]).exists():
            raise serializers.ValidationError("Username already exists")

        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError("Email already exists")

        if Doctor.objects.filter(license_number=data["license_number"]).exists():
            raise serializers.ValidationError("License number already exists")

        return data

    def create(self, validated_data):
        user_data = {
            "username": validated_data["username"],
            "password": validated_data["password"],
            "email": validated_data["email"],
            "first_name": validated_data["first_name"],
            "last_name": validated_data["last_name"],
        }

        user = User.objects.create_user(
            username=user_data["username"],
            password=user_data["password"],
            email=user_data["email"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
        )

        doctor = Doctor.objects.create(
            user=user,
            specialization=validated_data["specialization"],
            license_number=validated_data["license_number"],
        )

        return doctor


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("New passwords do not match")
        return data
