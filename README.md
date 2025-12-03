# Clinic Appointment Management System API

A Django REST API for a platform that allows multiple independent clinics to manage their appointments. Each clinic operates independently with their own doctors and patients. Doctors may work at multiple clinics with different availability at each. Patients can register and book appointments at any clinic.

## 🚀 Features

- **Multi-clinic support**: Each clinic operates independently
- **Doctor management**: Doctors can work at multiple clinics with different availability
- **Patient registration**: Patients can register and book appointments at any clinic
- **Appointment scheduling**: Smart scheduling with duration-based time slots
- **Overlap prevention**: No double-booking of doctors
- **Availability checking**: Get available time slots based on doctor's schedule
- **Role-based access control**: Different permissions for patients, doctors, and staff
- **Comprehensive API**: RESTful endpoints for all operations

## 🛠️ Technology Stack

- **Backend**: Django 5.2 + Django REST Framework
- **Database**: PostgreSQL
- **Authentication**: Token-based authentication
- **Testing**: Django Test Framework with coverage reporting

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

## ⚙️ Installation & Setup

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd clinic_management

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE clinic_db;
CREATE USER clinic_user WITH PASSWORD 'clinic_password';
GRANT ALL PRIVILEGES ON DATABASE clinic_db TO clinic_user;
\q
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```ini
DEBUG=True
SECRET_KEY=your-secret-key-here
DB_NAME=clinic_db
DB_USER=clinic_user
DB_PASSWORD=clinic_password
DB_HOST=localhost
DB_PORT=5432
```

### 4. Initialize Database

```bash
# Apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`

## 🧪 Running Tests

```bash
# Run all tests
python manage.py test

# Run specific test classes
python manage.py test clinic_app.tests_scheduling
python manage.py test clinic_app.tests.AppointmentSchedulingTests

# Run with coverage
coverage run --source='clinic_app' manage.py test
coverage report -m
```

## 📚 API Documentation

### Authentication

All endpoints (except public ones) require authentication via Bearer token.

#### Login
```http
POST /api/auth/login/
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

Response:
```json
{
    "token": "your-auth-token",
    "user_id": 1,
    "username": "your_username",
    "is_doctor": false,
    "is_patient": true
}
```

#### Logout
```http
POST /api/auth/logout/
Authorization: Token your-auth-token
```

### Public Endpoints

#### 1. Patient Registration
```http
POST /api/auth/patient/register/
Content-Type: application/json

{
    "username": "john_doe",
    "password": "securepassword123",
    "confirm_password": "securepassword123",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-01-01",
    "phone": "555-1234"
}
```

#### 2. Get Available Slots
```http
GET /api/available-slots/?doctor_id=1&clinic_id=1&visit_type_id=1&date=2024-01-01
```

Response:
```json
{
    "doctor": "Dr. John Smith",
    "clinic": "Main Clinic",
    "visit_type": "Consultation",
    "date": "2024-01-01",
    "available_slots": ["09:00", "09:15", "10:00", "11:30"]
}
```

### Protected Endpoints (Require Authentication)

#### 1. Clinics
```http
GET    /api/clinics/                 # List all clinics
POST   /api/clinics/                 # Create clinic (admin only)
GET    /api/clinics/{id}/            # Get clinic details
PUT    /api/clinics/{id}/            # Update clinic (admin only)
DELETE /api/clinics/{id}/            # Delete clinic (admin only)
```

#### 2. Doctors
```http
GET    /api/doctors/                 # List all doctors
POST   /api/doctors/                 # Create doctor (admin only)
GET    /api/doctors/{id}/            # Get doctor details
PUT    /api/doctors/{id}/            # Update doctor (admin only)
DELETE /api/doctors/{id}/            # Delete doctor (admin only)
```

#### 3. Patients
```http
GET    /api/patients/                # List all patients (admin only)
GET    /api/patients/{id}/           # Get patient details (admin only)
```

#### 4. Appointments
```http
GET    /api/appointments/            # List appointments (user-specific)
POST   /api/appointments/            # Create appointment
GET    /api/appointments/{id}/       # Get appointment details
PUT    /api/appointments/{id}/       # Update appointment
DELETE /api/appointments/{id}/       # Cancel appointment
```

**Create Appointment Example:**
```http
POST /api/appointments/
Authorization: Token your-auth-token
Content-Type: application/json

{
    "doctor": 1,
    "clinic": 1,
    "visit_type": 1,
    "scheduled_time": "2024-01-01T10:00:00Z",
    "notes": "Regular checkup"
}
```

#### 5. Patient Profile
```http
GET    /api/auth/profile/         # Get current patient profile
POST   /api/auth/change-password/ # Change password
```

#### 6. Doctor Availability
```http
GET    /api/availability/            # List doctor availability
POST   /api/availability/            # Set availability (doctor only)
GET    /api/availability/{id}/       # Get availability details
PUT    /api/availability/{id}/       # Update availability (doctor only)
DELETE /api/availability/{id}/       # Delete availability (doctor only)
```

#### 7. Visit Types
```http
GET    /api/visit-types/             # List visit types
POST   /api/visit-types/             # Create visit type (staff only)
GET    /api/visit-types/{id}/        # Get visit type details
PUT    /api/visit-types/{id}/        # Update visit type (staff only)
DELETE /api/visit-types/{id}/        # Delete visit type (staff only)
```

## 🔐 Permission Model

- **Patients**: Can view/manage their own appointments and profile
- **Doctors**: Can manage their availability and view their appointments
- **Staff/Admins**: Full access to all resources
- **Public**: Can view clinics and check available slots

## 📊 Data Models

### Clinic
- `name`, `address`, `phone`, `email`
- `operating_hours_start`, `operating_hours_end`

### Doctor
- Linked to User model
- `specialization`, `license_number`
- Many-to-many with Clinic through DoctorClinicAvailability

### Patient
- Linked to User model
- `date_of_birth`, `phone`, `emergency_contact`

### VisitType
- `name`, `duration_minutes`
- Linked to Clinic

### Appointment
- Links: Patient, Doctor, Clinic, VisitType
- `scheduled_time`, `end_time`, `status`, `notes`
- Automatic end_time calculation based on visit type duration
- Overlap prevention validation

### DoctorClinicAvailability
- Links: Doctor, Clinic
- `day_of_week`, `start_time`, `end_time`

## 🎯 Core Scheduling Logic

### Available Slots Calculation
The system calculates available time slots by:
1. Checking doctor's availability for the specific clinic and day
2. Considering existing appointments
3. Accounting for visit type duration
4. Preventing overlaps (with optional buffer time)

### Overlap Prevention
- No two appointments can overlap for the same doctor
- Only `scheduled` appointments block time slots
- `cancelled` and `completed` appointments don't block scheduling

## 🐛 Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify credentials in `.env` file
   - Ensure database exists: `sudo -u postgres psql -c "\l"`

2. **401 Unauthorized errors**
   - Use `Authorization: Token your-token-here` (not Bearer)
   - Ensure token is valid (login again if needed)

3. **Migration errors**
   - Delete `db.sqlite3` and migration files
   - Run: `python manage.py makemigrations` then `python manage.py migrate`

4. **Test failures**
   - Ensure test database permissions: `ALTER USER clinic_user CREATEDB;`
   - Or use SQLite for testing by modifying `settings.py`

### Logs
Check Django server logs for detailed error messages.

## 📈 Testing Coverage

The project includes comprehensive tests for:
- Appointment scheduling logic
- Overlap prevention
- Available slots calculation
- API endpoints
- Authentication and permissions

Run test coverage:
```bash
 coverage run --source='clinic_app' manage.py test
 coverage report -m
 ```

## 🔧 Development

### Project Structure
```
clinic_management/
├── clinic_project/          # Django project settings
├── clinic_app/             # Main application
│   ├── models.py           # Data models
│   ├── serializers.py      # API serializers
│   ├── views.py            # API views
│   ├── tests.py           # Unit tests
│   └── tests_scheduling.py # Scheduling logic tests
├── manage.py              # Django management script
└── requirements.txt       # Python dependencies
```

## 🔗 Quick Links

- [Postman Collection](https://postman.co/workspace/My-Workspace~9a97bb13-dd4a-4b31-801b-239f89e63e7e/collection/7902837-6b77a2ae-84e3-4245-bcfb-e7ded075e84b?action=share&creator=7902837&active-environment=7902837-133cfe58-c210-4b09-a211-38ce9e9e1ef5)