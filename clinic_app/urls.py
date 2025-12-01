from django.urls import path, include
from . import views

urlpatterns = [
    # Authentication
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/profile/', views.user_profile, name='user-profile'),
    path('auth/change-password/', views.change_password, name='change-password'),
    
    # Registration
    path('auth/patient/register/', views.patient_register, name='patient-register'),
    path('auth/doctor/register/', views.doctor_register, name='doctor-register'),
    
    # Public endpoints
    path('clinics/', views.ClinicListCreateView.as_view(), name='clinic-list'),
    path('available-slots/', views.available_slots, name='available-slots'),
    
    # Protected endpoints
    path('clinics/<int:pk>/', views.ClinicDetailView.as_view(), name='clinic-detail'),
    path('visit-types/', views.VisitTypeListCreateView.as_view(), name='visit-type-list'),
    path('visit-types/<int:pk>/', views.VisitTypeDetailView.as_view(), name='visit-type-detail'),
    path('doctors/', views.DoctorListCreateView.as_view(), name='doctor-list'),
    path('doctors/<int:pk>/', views.DoctorDetailView.as_view(), name='doctor-detail'),
    path('patients/', views.PatientListCreateView.as_view(), name='patient-list'),
    path('patients/<int:pk>/', views.PatientDetailView.as_view(), name='patient-detail'),
    path('availability/', views.DoctorClinicAvailabilityListCreateView.as_view(), name='availability-list'),
    path('availability/<int:pk>/', views.DoctorClinicAvailabilityDetailView.as_view(), name='availability-detail'),
    path('appointments/', views.AppointmentListCreateView.as_view(), name='appointment-list'),
    path('appointments/<int:pk>/', views.AppointmentDetailView.as_view(), name='appointment-detail'),
]