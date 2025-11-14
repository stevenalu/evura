# 🏥 E-Vura Healthcare Platform

**Your Smart Healthcare Connection**

E-Vura is a healthcare platform that ensures complete patient medical history is always accessible to doctors, preventing repeated diagnoses and ensuring continuity of care.

---

## 🎯 Purpose

E-Vura addresses the critical problem of fragmented patient medical records by allowing:
- **Patients** to store and manage their complete health history
- **Doctors** to access patient records seamlessly across hospitals
- **Seamless continuity of care** when patients change doctors or hospitals

This platform was inspired by a personal health journey where lack of accessible medical history led to repeated diagnoses and treatment delays.

---

## ✨ Features

### For Patients:
- ✅ Secure account creation and login
- ✅ Complete profile management with medical information
- ✅ Book appointments with available doctors
- ✅ View appointment history and status
- ✅ Access complete medical records
- ✅ Track blood type, allergies, and chronic conditions

### For Doctors:
- ✅ Professional profile management
- ✅ View all consultation requests
- ✅ Accept, reject, or complete appointments
- ✅ Manage patient records
- ✅ Track total patients and consultations

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone or Download the Project
```bash
cd evura
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the Application
```bash
python app.py
```

The application will:
1. Automatically create the database (`evura.db`)
2. Start the Flask development server
3. Be accessible at `http://127.0.0.1:5000`

---

## 📁 Project Structure

```
evura/
├── app.py                      # Main Flask application with all routes and models
├── requirements.txt            # Python dependencies
├── instance/
│   └── evura.db               # SQLite database (auto-generated)
└── templates/
    ├── base.html              # Base template with common elements
    ├── index.html             # Landing page with role selection
    ├── login.html             # Login page for all users
    ├── register_patient.html  # Patient registration form
    ├── register_doctor.html   # Doctor registration form
    ├── patient_dashboard.html # Patient dashboard with appointments
    ├── doctor_dashboard.html  # Doctor dashboard with consultations
    ├── patient_profile.html   # Patient profile management
    ├── doctor_profile.html    # Doctor profile management
    └── consultations.html     # Doctor consultation management page
```

---

## 🔐 User Flow

### Patient Journey:
1. **Landing Page** → Choose "I'm a Patient"
2. **Registration** → Create account with username, email, password
3. **Login** → Sign in as Patient
4. **Dashboard** → View appointments, medical records, available doctors
5. **Book Appointment** → Select doctor, date, time, and reason
6. **Profile** → Update personal info and medical history

### Doctor Journey:
1. **Landing Page** → Choose "I'm a Doctor"
2. **Registration** → Create account with professional details
3. **Login** → Sign in as Doctor
4. **Dashboard** → View consultation requests and patient statistics
5. **Manage Requests** → Accept, reject, or complete appointments
6. **Profile** → Update professional information

---

## 🗄️ Database Models

### Patient
- Username, Email, Password (hashed)
- Phone, Date of Birth, Address
- Blood Type, Allergies, Chronic Conditions
- Emergency Contact

### Doctor
- Username, Email, Password (hashed)
- Phone, Specialization
- License Number, Hospital
- Years of Experience

### Appointment
- Patient ID, Doctor ID
- Date, Time, Reason
- Status (pending, confirmed, completed, cancelled)

### MedicalRecord
- Patient ID, Doctor ID
- Diagnosis, Treatment, Prescription
- Notes, Visit Date

---

## 🎨 Design Philosophy

E-Vura follows a **clean, minimal, and professional** design approach:

- **Healthcare Colors**: Teal/cyan gradients (#0891b2, #06b6d4) for trust and professionalism
- **Green Accents**: (#10b981) for doctor-related features
- **Consistent Layout**: All pages follow the same structure
- **Embedded CSS**: Simple inline styles for easy maintenance
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Clean Typography**: Segoe UI for clarity and readability

---

## 🔒 Security Features

- **Password Hashing**: Uses bcrypt for secure password storage
- **Session Management**: Flask sessions for authentication
- **Role-Based Access**: Separate routes for patients and doctors
- **Protected Routes**: Login required decorators prevent unauthorized access

---

## 💡 Future Enhancements (Optional)

- Medical record uploads (PDFs, images)
- Doctor availability calendar
- Real-time notifications
- Video consultations
- Prescription management
- Lab test results integration

---

## 🐛 Troubleshooting

### Database Issues
If you encounter database errors:
```bash
# Delete the database and restart
rm instance/evura.db
python app.py
```

### Port Already in Use
If port 5000 is occupied:
```python
# In app.py, change the last line:
app.run(debug=True, port=5001)  # Use different port
```

### Module Not Found
Make sure you've installed dependencies:
```bash
pip install -r requirements.txt
```

---

## 📧 Contact & Support

**E-Vura Healthcare Platform**  
Bumbogo, Kigali Innovation City  
Next to Azam, Kigali, Rwanda  

📞 Phone: +250 784 650 21/2  
📧 Email: info@e-vura.com

---

## 📜 License

© 2025 E-Vura | Empowering Health Through Technology

---

## 🙏 Acknowledgments

This platform was inspired by a personal health journey with chronic bone infection, highlighting the critical need for accessible, continuous medical records. E-Vura is built to ensure no patient experiences fragmented care due to inaccessible medical history.

---

**Built with care for better healthcare** ❤️🏥# evura
