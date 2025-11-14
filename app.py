from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from functools import wraps
import os
from werkzeug.utils import secure_filename
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


app = Flask(__name__)
app.config['SENDGRID_API_KEY'] = os.environ.get('SENDGRID_API_KEY')
app.config['SECRET_KEY'] = 'evuraqwertysecretkey'
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///evura.db')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'dcm', 'doc', 'docx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.String(20))
    address = db.Column(db.String(200))
    blood_type = db.Column(db.String(5))
    allergies = db.Column(db.Text)
    chronic_conditions = db.Column(db.Text)  
    emergency_contact = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointments = db.relationship('Appointment', backref='patient', lazy=True, foreign_keys='Appointment.patient_id')
    records = db.relationship('MedicalRecord', backref='patient', lazy=True)

    def has_chronic_conditions(self):
        return bool(self.chronic_conditions and self.chronic_conditions.strip())

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    specialization = db.Column(db.String(100))
    license_number = db.Column(db.String(50))
    hospital = db.Column(db.String(200))
    years_experience = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointments = db.relationship('Appointment', backref='doctor', lazy=True, foreign_keys='Appointment.doctor_id')
    records = db.relationship('MedicalRecord', backref='doctor', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending') 
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Medical Records Models for later usage in patient history
class MedicalFile(db.Model):
    """Store uploaded medical files (X-rays, MRI, lab reports, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    
    # File details
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # X-ray, MRI, Lab Report, Prescription
    file_category = db.Column(db.String(50), nullable=False)  # Imaging, Lab, Prescription, Report
    
    # Medical context
    description = db.Column(db.Text, nullable=True)
    diagnosis = db.Column(db.String(200), nullable=True)
    hospital_name = db.Column(db.String(200), nullable=True)
    
    # Chronic disease tracking
    is_chronic_related = db.Column(db.Boolean, default=False)
    chronic_condition = db.Column(db.String(200), nullable=True)
    
    # Timestamps
    test_date = db.Column(db.DateTime, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='medical_files')
    doctor = db.relationship('Doctor', backref='uploaded_files')

class TestResult(db.Model):
    """Store structured test results (blood work, imaging interpretations)"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    
    # Test details
    test_name = db.Column(db.String(200), nullable=False)  # CBC, MRI, X-ray, etc.
    test_type = db.Column(db.String(100), nullable=False)  # Blood, Imaging, Biopsy
    
    # Results
    result_value = db.Column(db.Text, nullable=False)
    normal_range = db.Column(db.String(100), nullable=True)
    interpretation = db.Column(db.Text, nullable=True)
    
    # Medical context
    hospital_name = db.Column(db.String(200), nullable=True)
    is_chronic_related = db.Column(db.Boolean, default=False)
    chronic_condition = db.Column(db.String(200), nullable=True)
    
    # Linked file
    medical_file_id = db.Column(db.Integer, db.ForeignKey('medical_file.id'), nullable=True)
    
    # Timestamps
    test_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='test_results')
    doctor = db.relationship('Doctor', backref='ordered_tests')
    medical_file = db.relationship('MedicalFile', backref='test_results')

class Procedure(db.Model):
    """Store surgical procedures and treatments"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    
    # Procedure details
    procedure_name = db.Column(db.String(200), nullable=False)
    procedure_type = db.Column(db.String(100), nullable=False)  # Surgery, Treatment, Intervention
    
    # Medical context
    description = db.Column(db.Text, nullable=False)
    outcome = db.Column(db.Text, nullable=True)
    complications = db.Column(db.Text, nullable=True)
    
    hospital_name = db.Column(db.String(200), nullable=True)
    is_chronic_related = db.Column(db.Boolean, default=False)
    chronic_condition = db.Column(db.String(200), nullable=True)
    
    # Timestamps
    procedure_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='procedures')
    doctor = db.relationship('Doctor', backref='performed_procedures')

class Prescription(db.Model):
    """Store medication prescriptions"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    
    # Medication details
    medication_name = db.Column(db.String(200), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(100), nullable=False)
    
    # Medical context
    reason = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    
    is_chronic_related = db.Column(db.Boolean, default=False)
    chronic_condition = db.Column(db.String(200), nullable=True)
    
    # Effectiveness tracking
    effectiveness = db.Column(db.String(50), nullable=True)  # Effective, Partial, Ineffective
    side_effects = db.Column(db.Text, nullable=True)
    
    # Timestamps
    prescribed_date = db.Column(db.DateTime, default=datetime.utcnow)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    patient = db.relationship('Patient', backref='prescriptions')
    doctor = db.relationship('Doctor', backref='prescriptions')

class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
    diagnosis = db.Column(db.Text, nullable=False)
    treatment = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    visit_date = db.Column(db.String(20), nullable=False)
    follow_up_required = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# EMAIL FUNCTIONS

def send_email(to, subject, template_name, **kwargs):
    try:
        # Create email content
        html_content = render_email_template(template_name, **kwargs)
        
        # Create SendGrid message
        message = Mail(
            from_email='s.kayitare@alustudent.com',
            to_emails=to,
            subject=f"E-Vura Healthcare: {subject}",
            html_content=html_content
        )
        
        # Send via SendGrid
        sg = SendGridAPIClient(api_key=app.config['SENDGRID_API_KEY'])
        response = sg.send(message)
        print(f"✅ Email sent to {to}: {subject} (Status: {response.status_code})")
        return True
        
    except Exception as e:
        print(f"❌ Email failed to {to}: {e}")
        return False
    
def render_email_template(template_name, **kwargs):
    """Email templates with alerts"""
    base_style = """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e5e7eb; border-radius: 15px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #0d9488, #14b8a6); color: white; padding: 25px; text-align: center;">
            <h2 style="margin: 0; font-size: 28px; font-weight: bold;">E-Vura Healthcare</h2>
            <p style="margin: 8px 0 0; opacity: 0.9; font-size: 16px;">Your Smart Healthcare Connection</p>
        </div>
        <div style="padding: 30px;">
            {content}
        </div>
        <div style="background: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb; color: #6b7280;">
            <p style="margin: 0; font-size: 14px;">© 2025 E-Vura Healthcare Platform</p>
            <p style="margin: 5px 0 0; font-size: 14px;">Bumbogo, Kigali Innovation City, Rwanda</p>
            <p style="margin: 5px 0 0; font-size: 14px;">+250 784 650 21/2 | info@e-vura.com</p>
        </div>
    </div>
    """
    
    templates = {
        'appointment_request': f"""
            <div style="text-align: center; margin-bottom: 25px;">
                <h3 style="color: #0d9488; font-size: 24px; margin-bottom: 10px;">🩺 New Appointment Request</h3>
            </div>
            
            <p style="font-size: 16px; line-height: 1.6;">Dear <strong>Dr. {kwargs.get('doctor_name')}</strong>,</p>
            <p style="font-size: 16px; line-height: 1.6;">You have received a new appointment request from a patient:</p>
            
            <div style="background: #f0f9ff; border-left: 4px solid #0ea5e9; padding: 20px; margin: 25px 0; border-radius: 8px;">
                <p style="margin: 8px 0; font-size: 15px;"><strong>** Patient:</strong> {kwargs.get('patient_name')}</p>
                <p style="margin: 8px 0; font-size: 15px;"><strong>** Date:</strong> {kwargs.get('date')}</p>
                <p style="margin: 8px 0; font-size: 15px;"><strong>** Time:</strong> {kwargs.get('time')}</p>
                <p style="margin: 8px 0; font-size: 15px;"><strong>** Reason:</strong> {kwargs.get('reason', 'General consultation')}</p>
                {f"<div style='background: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 8px; margin-top: 15px;'><p style='margin: 0; color: #dc2626; font-weight: bold; font-size: 15px;'>⚠️ CHRONIC CONDITION: {kwargs.get('chronic_conditions')}</p></div>" if kwargs.get('chronic_conditions') else ""}
            </div>
            
            <div style="background: #ecfdf5; border-left: 4px solid #10b981; padding: 15px; margin: 25px 0; border-radius: 8px;">
                <p style="margin: 0; color: #065f46; font-size: 14px;">
                    <strong>** Next Steps:</strong> Please log in to your E-Vura dashboard to review and respond to this appointment request.
                </p>
            </div>
            
            <p style="margin-top: 30px; font-size: 16px;">Best regards,<br><strong>The E-Vura Healthcare Team</strong></p>
        """,
        
        'appointment_confirmed': f"""
            <div style="text-align: center; margin-bottom: 25px;">
                <h3 style="color: #10b981; font-size: 24px; margin-bottom: 10px;"> Appointment Confirmed!</h3>
            </div>
            
            <p style="font-size: 16px; line-height: 1.6;">Dear <strong>{kwargs.get('patient_name')}</strong>,</p>
            <p style="font-size: 16px; line-height: 1.6;">Great news! Your appointment has been <strong style="color: #10b981;">confirmed</strong>:</p>
            
            <div style="background: #ecfdf5; border-left: 4px solid #10b981; padding: 20px; margin: 25px 0; border-radius: 8px;">
                <p style="margin: 8px 0; font-size: 15px;"><strong>** Doctor:</strong> Dr. {kwargs.get('doctor_name')}</p>
                <p style="margin: 8px 0; font-size: 15px;"><strong>** Date:</strong> {kwargs.get('date')}</p>
                <p style="margin: 8px 0; font-size: 15px;"><strong>** Time:</strong> {kwargs.get('time')}</p>
                <p style="margin: 8px 0; font-size: 15px;"><strong>** Location:</strong> {kwargs.get('hospital', 'Please contact doctor for location details')}</p>
            </div>
            
            <div style="background: #fef7f0; border-left: 4px solid #f59e0b; padding: 20px; margin: 25px 0; border-radius: 8px;">
                <p style="margin: 0 0 10px; color: #92400e; font-weight: bold; font-size: 15px;">** Important Reminders:</p>
                <ul style="margin: 0; color: #78350f; line-height: 1.8;">
                    <li>Please arrive 15 minutes early for check-in</li>
                    <li>Bring a valid ID and any relevant medical documents</li>
                    <li>Your complete medical history is already accessible to the doctor via E-Vura</li>
                </ul>
            </div>
            
            <p style="font-size: 16px; line-height: 1.6;">If you need to reschedule or have any questions, please contact us.</p>
            <p style="margin-top: 30px; font-size: 16px;">Best regards,<br><strong>The E-Vura Healthcare Team</strong></p>
        """,
        
        'appointment_rejected': f"""
            <div style="text-align: center; margin-bottom: 25px;">
                <h3 style="color: #ef4444; font-size: 24px; margin-bottom: 10px;">** Appointment Update</h3>
            </div>
            
            <p style="font-size: 16px; line-height: 1.6;">Dear <strong>{kwargs.get('patient_name')}</strong>,</p>
            <p style="font-size: 16px; line-height: 1.6;">We regret to inform you that <strong>Dr. {kwargs.get('doctor_name')}</strong> is not available for your requested appointment on <strong>{kwargs.get('date')}</strong> at <strong>{kwargs.get('time')}</strong>.</p>
            
            <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 20px; margin: 25px 0; border-radius: 8px;">
                <p style="margin: 0 0 10px; color: #dc2626; font-weight: bold; font-size: 15px;">** What's Next?</p>
                <ul style="margin: 0; color: #991b1b; line-height: 1.8;">
                    <li>Log in to your E-Vura dashboard</li>
                    <li>Select a different available time slot</li>
                    <li>Or choose another qualified doctor</li>
                </ul>
            </div>
            
            <p style="font-size: 16px; line-height: 1.6;">We apologize for any inconvenience and appreciate your understanding.</p>
            <p style="margin-top: 30px; font-size: 16px;">Best regards,<br><strong>The E-Vura Healthcare Team</strong></p>
        """,
        
        'appointment_completed': f"""
            <div style="text-align: center; margin-bottom: 25px;">
                <h3 style="color: #0d9488; font-size: 24px; margin-bottom: 10px;">** Consultation Complete</h3>
            </div>
            
            <p style="font-size: 16px; line-height: 1.6;">Dear <strong>{kwargs.get('patient_name')}</strong>,</p>
            <p style="font-size: 16px; line-height: 1.6;">Your consultation with <strong>Dr. {kwargs.get('doctor_name')}</strong> on <strong>{kwargs.get('date')}</strong> has been completed successfully.</p>
            
            <div style="background: #f0fdfa; border-left: 4px solid #0d9488; padding: 20px; margin: 25px 0; border-radius: 8px;">
                <p style="margin: 0 0 10px; color: #065f46; font-weight: bold; font-size: 15px;">** What's Been Updated:</p>
                <ul style="margin: 0; color: #047857; line-height: 1.8;">
                    <li>Your medical records have been updated with new information</li>
                    <li>New diagnosis and treatment details added to your history</li>
                    <li>All records are accessible for your next doctor visit</li>
                    <li>Chronic condition status updated if applicable</li>
                </ul>
            </div>
            
            <p style="font-size: 16px; line-height: 1.6;">You can view your updated medical history anytime in your E-Vura dashboard.</p>
            <p style="font-size: 16px; line-height: 1.6;">Take care and thank you for trusting E-Vura with your healthcare journey!</p>
            <p style="margin-top: 30px; font-size: 16px;">Best regards,<br><strong>The E-Vura Healthcare Team</strong></p>
        """
    }
    
    content = templates.get(template_name, f"<p>E-Vura Healthcare Platform notification</p>")
    return base_style.format(content=content)

# HELPER FUNCTIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'user_type' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_type') != 'patient':
            flash('Access denied. Patients only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_type') != 'doctor':
            flash('Access denied. Doctors only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        if session['user_type'] == 'patient':
            return redirect(url_for('patient_dashboard'))
        else:
            return redirect(url_for('doctor_dashboard'))
    return render_template('index.html')

@app.route('/register/patient', methods=['GET', 'POST'])
def register_patient():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        
        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'warning')
            return redirect(url_for('register_patient'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'warning')
            return redirect(url_for('register_patient'))
        
        if Patient.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'warning')
            return redirect(url_for('register_patient'))
        
        if Patient.query.filter_by(username=username).first():
            flash('Username already taken. Please choose another.', 'warning')
            return redirect(url_for('register_patient'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_patient = Patient(username=username, email=email, password=hashed_password)
        
        try:
            db.session.add(new_patient)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register_patient.html')

@app.route('/register/doctor', methods=['GET', 'POST'])
def register_doctor():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        specialization = request.form.get('specialization', '').strip()
        license_number = request.form.get('license_number', '').strip()
        hospital = request.form.get('hospital', '').strip()
        
        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'warning')
            return redirect(url_for('register_doctor'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'warning')
            return redirect(url_for('register_doctor'))
        
        if Doctor.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'warning')
            return redirect(url_for('register_doctor'))
        
        if Doctor.query.filter_by(username=username).first():
            flash('Username already taken. Please choose another.', 'warning')
            return redirect(url_for('register_doctor'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_doctor = Doctor(
            username=username, email=email, password=hashed_password,
            specialization=specialization, license_number=license_number, hospital=hospital
        )
        
        try:
            db.session.add(new_doctor)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register_doctor.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user_type = request.form['user_type']
        
        if user_type == 'patient':
            user = Patient.query.filter_by(email=email).first()
        else:
            user = Doctor.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_type'] = user_type
            session['username'] = user.username
            
            flash(f'Welcome back, {user.username}!', 'success')
            
            if user_type == 'patient':
                return redirect(url_for('patient_dashboard'))
            else:
                return redirect(url_for('doctor_dashboard'))
        else:
            flash('Invalid email, password, or user type.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('index'))

@app.route('/patient/dashboard')
@login_required
@patient_required
def patient_dashboard():
    patient = Patient.query.get(session['user_id'])
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.created_at.desc()).all()
    records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.created_at.desc()).limit(5).all()
    doctors = Doctor.query.all()
    
    return render_template('patient_dashboard.html', 
                         patient=patient, appointments=appointments,
                         records=records, doctors=doctors)

@app.route('/doctor/dashboard')
@login_required
@doctor_required
def doctor_dashboard():
    doctor = Doctor.query.get(session['user_id'])
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.created_at.desc()).all()
    patients = Patient.query.join(Appointment).filter(Appointment.doctor_id == doctor.id).distinct().all()
    
    return render_template('doctor_dashboard.html', doctor=doctor, appointments=appointments, patients=patients)

@app.route('/patient/profile', methods=['GET', 'POST'])
@login_required
@patient_required
def patient_profile():
    patient = Patient.query.get(session['user_id'])
    
    if request.method == 'POST':
        patient.phone = request.form.get('phone', '').strip()
        patient.date_of_birth = request.form.get('date_of_birth', '').strip()
        patient.address = request.form.get('address', '').strip()
        patient.blood_type = request.form.get('blood_type', '').strip()
        patient.allergies = request.form.get('allergies', '').strip()
        patient.chronic_conditions = request.form.get('chronic_conditions', '').strip()
        patient.emergency_contact = request.form.get('emergency_contact', '').strip()
        
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash('Error updating profile.', 'danger')
        
        return redirect(url_for('patient_profile'))
    
    records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.created_at.desc()).all()
    return render_template('patient_profile.html', patient=patient, records=records)

@app.route('/doctor/profile', methods=['GET', 'POST'])
@login_required
@doctor_required
def doctor_profile():
    doctor = Doctor.query.get(session['user_id'])
    
    if request.method == 'POST':
        doctor.phone = request.form.get('phone', '').strip()
        doctor.specialization = request.form.get('specialization', '').strip()
        doctor.hospital = request.form.get('hospital', '').strip()
        years_exp = request.form.get('years_experience', '').strip()
        
        if years_exp.isdigit():
            doctor.years_experience = int(years_exp)
        
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash('Error updating profile.', 'danger')
    
    return render_template('doctor_profile.html', doctor=doctor)

@app.route('/patient/find-doctors')
@login_required
@patient_required
def find_doctors():
    doctors = Doctor.query.all()
    return render_template('find_doctors.html', doctors=doctors)

@app.route('/doctor/<int:doctor_id>/profile')
@login_required
def view_doctor_profile(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    total_patients = Patient.query.join(Appointment).filter(Appointment.doctor_id == doctor_id).distinct().count()
    total_appointments = Appointment.query.filter_by(doctor_id=doctor_id).count()
    completed_appointments = Appointment.query.filter_by(doctor_id=doctor_id, status='completed').count()
    
    return render_template('view_doctor_profile.html', doctor=doctor, 
                         total_patients=total_patients, total_appointments=total_appointments,
                         completed_appointments=completed_appointments)

@app.route('/appointment/book', methods=['POST'])
@login_required
@patient_required
def book_appointment():
    try:
        doctor_id = request.form['doctor_id']
        date = request.form['date']
        time = request.form['time']
        reason = request.form.get('reason', '').strip()
        
        doctor = Doctor.query.get(doctor_id)
        patient = Patient.query.get(session['user_id'])
        
        if not doctor:
            flash('Doctor not found.', 'danger')
            return redirect(url_for('find_doctors'))
        
        existing = Appointment.query.filter_by(doctor_id=doctor_id, date=date, time=time).filter(
            Appointment.status.in_(['pending', 'confirmed'])).first()
        
        if existing:
            flash('This time slot is already booked.', 'warning')
            return redirect(request.referrer or url_for('find_doctors'))
        
        appointment = Appointment(
            patient_id=session['user_id'], doctor_id=doctor_id,
            date=date, time=time, reason=reason, status='pending'
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        # Send email alert
        send_email(
            to=doctor.email, subject="New Appointment Request", template_name='appointment_request',
            doctor_name=doctor.username, patient_name=patient.username, date=date, time=time,
            reason=reason or 'General consultation',
            chronic_conditions=patient.chronic_conditions if patient.has_chronic_conditions() else None
        )
        
        flash('Appointment booked! Doctor will be notified.', 'success')
        
    except Exception as e:
        flash('Error booking appointment.', 'danger')
    
    return redirect(url_for('patient_dashboard'))

@app.route('/doctor/consultations')
@login_required
@doctor_required
def consultations():
    doctor = Doctor.query.get(session['user_id'])
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.created_at.desc()).all()
    return render_template('consultations.html', doctor=doctor, appointments=appointments)

@app.route('/patient/medical-records')
@login_required
@patient_required
def medical_records():
    patient = Patient.query.get(session['user_id'])
    
    # Get all medical records sorted by date
    medical_files = MedicalFile.query.filter_by(patient_id=patient.id).order_by(MedicalFile.test_date.desc()).all()
    test_results = TestResult.query.filter_by(patient_id=patient.id).order_by(TestResult.test_date.desc()).all()
    procedures = Procedure.query.filter_by(patient_id=patient.id).order_by(Procedure.procedure_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(Prescription.prescribed_date.desc()).all()
    
    # Create timeline combining all records
    timeline = []
    
    for file in medical_files:
        timeline.append({
            'type': 'file',
            'date': file.test_date,
            'data': file
        })
    
    for test in test_results:
        timeline.append({
            'type': 'test',
            'date': test.test_date,
            'data': test
        })
    
    for proc in procedures:
        timeline.append({
            'type': 'procedure',
            'date': proc.procedure_date,
            'data': proc
        })
    
    for presc in prescriptions:
        timeline.append({
            'type': 'prescription',
            'date': presc.prescribed_date,
            'data': presc
        })
    
    timeline.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('medical_records.html', 
                         patient=patient,
                         timeline=timeline,
                         medical_files=medical_files,
                         test_results=test_results,
                         procedures=procedures,
                         prescriptions=prescriptions)

@app.route('/patient/upload-records', methods=['GET', 'POST'])
@login_required
@patient_required
def upload_records():
    """Upload medical files and records"""
    if request.method == 'POST':
        try:
            patient = Patient.query.get(session['user_id'])
            
            # files upload handling
            if 'medical_file' in request.files:
                file = request.files['medical_file']
                if file and file.filename:
                    # Generate unique filename
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    # Create medical file record
                    medical_file = MedicalFile(
                        patient_id=patient.id,
                        filename=unique_filename,
                        original_filename=filename,
                        file_type=request.form.get('file_type'),
                        file_category=request.form.get('file_category'),
                        description=request.form.get('description'),
                        diagnosis=request.form.get('diagnosis'),
                        hospital_name=request.form.get('hospital_name'),
                        is_chronic_related=bool(request.form.get('is_chronic_related')),
                        chronic_condition=request.form.get('chronic_condition') if request.form.get('is_chronic_related') else None,
                        test_date=datetime.strptime(request.form.get('test_date'), '%Y-%m-%d')
                    )
                    db.session.add(medical_file)
            
            # Handle test result entry (without file)
            if request.form.get('add_test_result'):
                test_result = TestResult(
                    patient_id=patient.id,
                    test_name=request.form.get('test_name'),
                    test_type=request.form.get('test_type'),
                    result_value=request.form.get('result_value'),
                    normal_range=request.form.get('normal_range'),
                    interpretation=request.form.get('interpretation'),
                    hospital_name=request.form.get('hospital_name'),
                    is_chronic_related=bool(request.form.get('is_chronic_related')),
                    chronic_condition=request.form.get('chronic_condition') if request.form.get('is_chronic_related') else None,
                    test_date=datetime.strptime(request.form.get('test_date'), '%Y-%m-%d')
                )
                db.session.add(test_result)
            
            db.session.commit()
            flash('Medical record uploaded successfully!', 'success')
            return redirect(url_for('medical_records'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading record: {str(e)}', 'error')
    
    patient = Patient.query.get(session['user_id'])
    return render_template('upload_records.html', patient=patient)

@app.route('/doctor/patient-history/<int:patient_id>')
@login_required
@doctor_required
def view_patient_history(patient_id):
    """Doctor views complete patient medical history"""
    patient = Patient.query.get_or_404(patient_id)
    doctor = Doctor.query.get(session['user_id'])
    
    # Check if doctor has permission (has treated or is treating this patient)
    has_permission = Appointment.query.filter_by(
        patient_id=patient_id,
        doctor_id=doctor.id
    ).first() is not None
    
    if not has_permission:
        flash('You do not have permission to view this patient\'s records', 'error')
        return redirect(url_for('doctor_dashboard'))
    
    # Get all medical records
    medical_files = MedicalFile.query.filter_by(patient_id=patient.id).order_by(MedicalFile.test_date.desc()).all()
    test_results = TestResult.query.filter_by(patient_id=patient.id).order_by(TestResult.test_date.desc()).all()
    procedures = Procedure.query.filter_by(patient_id=patient.id).order_by(Procedure.procedure_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(Prescription.prescribed_date.desc()).all()
    
    # Create timeline
    timeline = []
    
    for file in medical_files:
        timeline.append({'type': 'file', 'date': file.test_date, 'data': file})
    for test in test_results:
        timeline.append({'type': 'test', 'date': test.test_date, 'data': test})
    for proc in procedures:
        timeline.append({'type': 'procedure', 'date': proc.procedure_date, 'data': proc})
    for presc in prescriptions:
        timeline.append({'type': 'prescription', 'date': presc.prescribed_date, 'data': presc})
    
    timeline.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('view_patient_history.html',
                         patient=patient,
                         doctor=doctor,
                         timeline=timeline,
                         medical_files=medical_files,
                         test_results=test_results,
                         procedures=procedures,
                         prescriptions=prescriptions,
                         now=datetime.now())

@app.route('/doctor/add-medical-note/<int:patient_id>', methods=['POST'])
@login_required
@doctor_required
def add_medical_note(patient_id):
    """Doctor adds test results or prescriptions for patient"""
    try:
        doctor = Doctor.query.get(session['user_id'])
        patient = Patient.query.get_or_404(patient_id)
        
        record_type = request.form.get('record_type')
        
        if record_type == 'test_result':
            test_result = TestResult(
                patient_id=patient_id,
                doctor_id=doctor.id,
                test_name=request.form.get('test_name'),
                test_type=request.form.get('test_type'),
                result_value=request.form.get('result_value'),
                normal_range=request.form.get('normal_range'),
                interpretation=request.form.get('interpretation'),
                hospital_name=doctor.hospital,
                is_chronic_related=bool(request.form.get('is_chronic_related')),
                chronic_condition=request.form.get('chronic_condition'),
                test_date=datetime.now()
            )
            db.session.add(test_result)
            
        elif record_type == 'prescription':
            prescription = Prescription(
                patient_id=patient_id,
                doctor_id=doctor.id,
                medication_name=request.form.get('medication_name'),
                dosage=request.form.get('dosage'),
                frequency=request.form.get('frequency'),
                duration=request.form.get('duration'),
                reason=request.form.get('reason'),
                instructions=request.form.get('instructions'),
                is_chronic_related=bool(request.form.get('is_chronic_related')),
                chronic_condition=request.form.get('chronic_condition'),
                start_date=datetime.now()
            )
            db.session.add(prescription)
            
        elif record_type == 'procedure':
            procedure = Procedure(
                patient_id=patient_id,
                doctor_id=doctor.id,
                procedure_name=request.form.get('procedure_name'),
                procedure_type=request.form.get('procedure_type'),
                description=request.form.get('description'),
                outcome=request.form.get('outcome'),
                hospital_name=doctor.hospital,
                is_chronic_related=bool(request.form.get('is_chronic_related')),
                chronic_condition=request.form.get('chronic_condition'),
                procedure_date=datetime.now()
            )
            db.session.add(procedure)
        
        db.session.commit()
        flash('Medical record added successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding medical record: {str(e)}', 'error')
    
    return redirect(url_for('view_patient_history', patient_id=patient_id))

@app.route('/download-medical-file/<int:file_id>')
@login_required
def download_medical_file(file_id):
    """Download a medical file"""
    medical_file = MedicalFile.query.get_or_404(file_id)
    
    # Check permission (patient or authorized doctor)
    if session.get('user_type') == 'patient':
        if medical_file.patient_id != session['user_id']:
            flash('Unauthorized access', 'error')
            return redirect(url_for('index'))
    elif session.get('user_type') == 'doctor':
        # Check if doctor has treated this patient
        has_permission = Appointment.query.filter_by(
            patient_id=medical_file.patient_id,
            doctor_id=session['user_id']
        ).first() is not None
        if not has_permission:
            flash('Unauthorized access', 'error')
            return redirect(url_for('doctor_dashboard'))
    
    try:
        return send_file(
            os.path.join(app.config['UPLOAD_FOLDER'], medical_file.filename),
            as_attachment=True,
            download_name=medical_file.original_filename
        )
    except Exception as e:
        flash('File not found', 'error')
        return redirect(url_for('medical_records'))
    


@app.route('/appointment/<int:appointment_id>/status', methods=['POST'])
@login_required
@doctor_required
def update_appointment_status(appointment_id):
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        
        if appointment.doctor_id != session['user_id']:
            flash('Access denied.', 'danger')
            return redirect(url_for('doctor_dashboard'))
        
        new_status = request.form['status']
        appointment.status = new_status
        
        doctor = Doctor.query.get(appointment.doctor_id)
        patient = Patient.query.get(appointment.patient_id)
        
        db.session.commit()
        
        if new_status == 'confirmed':
            send_email(
                to=patient.email, subject="Appointment Confirmed", template_name='appointment_confirmed',
                patient_name=patient.username, doctor_name=doctor.username,
                date=appointment.date, time=appointment.time, hospital=doctor.hospital or 'TBD'
            )
            flash('Appointment confirmed and patient notified.', 'success')
        elif new_status == 'cancelled':
            send_email(
                to=patient.email, subject="Appointment Update", template_name='appointment_rejected',
                patient_name=patient.username, doctor_name=doctor.username,
                date=appointment.date, time=appointment.time
            )
            flash('Appointment cancelled and patient notified.', 'info')
        elif new_status == 'completed':
            send_email(
                to=patient.email, subject="Consultation Complete", template_name='appointment_completed',
                patient_name=patient.username, doctor_name=doctor.username,
                date=appointment.date, time=appointment.time
            )
            flash('Consultation completed and patient notified.', 'success')
    
    except Exception as e:
        flash('Error updating status.', 'danger')
    
    return redirect(url_for('consultations'))

@app.route('/appointment/<int:appointment_id>/add-record', methods=['POST'])
@login_required
@doctor_required
def add_medical_record(appointment_id):
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        
        if appointment.doctor_id != session['user_id']:
            flash('Access denied.', 'danger')
            return redirect(url_for('doctor_dashboard'))
        
        record = MedicalRecord(
            patient_id=appointment.patient_id, doctor_id=appointment.doctor_id,
            appointment_id=appointment.id, diagnosis=request.form['diagnosis'],
            treatment=request.form.get('treatment', ''), prescription=request.form.get('prescription', ''),
            notes=request.form.get('notes', ''), visit_date=appointment.date,
            follow_up_required=bool(request.form.get('follow_up_required'))
        )
        
        db.session.add(record)
        appointment.notes = request.form.get('notes', '')
        db.session.commit()
        
        flash('Medical record added successfully!', 'success')
        
    except Exception as e:
        flash('Error adding medical record.', 'danger')
    
    return redirect(url_for('consultations'))

print(f"🔍 DATABASE_URL exists: {bool(os.environ.get('DATABASE_URL'))}")

print(f"🔍 Final DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

# Create database tables on startup

with app.app_context():

    try:

        print("🔄 Attempting to connect to database...")

        db.create_all()

        print('✅ E-Vura Database tables created successfully!')

    except Exception as e:

        print(f' Error creating database: {e}')

        print(f'❌ Error details: {str(e)}')

        print(f'❌ Error type: {type(e).__name__}')

        import traceback

        print(f'❌ Full traceback: {traceback.format_exc()}')
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
