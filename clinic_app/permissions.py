from rest_framework import permissions


class IsPatient(permissions.BasePermission):
    """Check if user is a patient"""

    def has_permission(self, request, view):
        return hasattr(request.user, "patient")


class IsDoctor(permissions.BasePermission):
    """Check if user is a doctor"""

    def has_permission(self, request, view):
        return hasattr(request.user, "doctor")


class IsClinicStaff(permissions.BasePermission):
    """Check if user is clinic staff (can be extended later)"""

    def has_permission(self, request, view):
        return request.user.is_staff or hasattr(request.user, "doctor")


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level permission to only allow owners of an object to edit it."""

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check if user is patient and owns the appointment
        if hasattr(request.user, "patient") and hasattr(obj, "patient"):
            return obj.patient == request.user.patient

        # Check if user is doctor and owns the appointment/availability
        if hasattr(request.user, "doctor") and hasattr(obj, "doctor"):
            return obj.doctor == request.user.doctor

        return False


class IsPatientOwner(permissions.BasePermission):
    """Patient can only access their own data"""

    def has_object_permission(self, request, view, obj):
        if hasattr(request.user, "patient"):
            return obj.patient == request.user.patient
        return False


class IsDoctorOwner(permissions.BasePermission):
    """Doctor can only access their own data"""

    def has_object_permission(self, request, view, obj):
        if hasattr(request.user, "doctor"):
            return obj.doctor == request.user.doctor
        return False
