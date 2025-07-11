from extensions import db
from flask_login import UserMixin
from datetime import datetime, date
from sqlalchemy import func


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15))
    department = db.Column(db.String(50), nullable=False)
    designation = db.Column(db.String(50), nullable=False)
    work_mode = db.Column(db.String(20), nullable=False, default='onsite')  # onsite/offsite
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin/employee/manager
    employment_status = db.Column(db.String(20), nullable=False, default='probation')  # probation/confirmed
    probation_end_date = db.Column(db.Date)
    confirmation_date = db.Column(db.Date)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    password_hash = db.Column(db.String(256))
    active = db.Column(db.Boolean, default=True)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(100))
    reset_token_expires = db.Column(db.DateTime)
    
    @property
    def is_active(self):
        """Backward compatibility property for UserMixin"""
        return self.active
    
    # Relationships
    attendance_records = db.relationship('Attendance', backref='user', lazy=True)
    leave_requests = db.relationship('LeaveRequest', foreign_keys='LeaveRequest.user_id', backref='user', lazy=True)
    reviewed_leave_requests = db.relationship('LeaveRequest', foreign_keys='LeaveRequest.reviewed_by', backref='reviewer', lazy=True)
    documents = db.relationship('Document', backref='user', lazy=True)
    
    # Manager-Employee relationships
    reportees = db.relationship('User', backref=db.backref('manager', remote_side='User.id'), lazy=True)
    
    # Extended relationships for comprehensive HRMS
    emergency_contacts = db.relationship('EmergencyContact', backref='user', lazy=True)
    job_postings = db.relationship('JobPosting', backref='poster', lazy=True)
    interviews = db.relationship('Interview', backref='interviewer', lazy=True)
    training_programs = db.relationship('TrainingProgram', backref='creator', lazy=True)
    training_enrollments = db.relationship('TrainingEnrollment', backref='user', lazy=True)
    certifications = db.relationship('Certification', backref='user', lazy=True)
    exit_requests = db.relationship('ExitRequest', foreign_keys='ExitRequest.user_id', backref='user', lazy=True)
    approved_exits = db.relationship('ExitRequest', foreign_keys='ExitRequest.approved_by', backref='approver', lazy=True)
    exit_interviews = db.relationship('ExitInterview', backref='interviewer', lazy=True)
    announcements = db.relationship('Announcement', backref='creator', lazy=True)
    policy_documents = db.relationship('PolicyDocument', backref='creator', lazy=True)
    policy_acknowledgments = db.relationship('PolicyAcknowledgment', backref='user', lazy=True)
    employment_history = db.relationship('EmploymentHistory', backref='user', lazy=True)
    
    @property
    def is_manager(self):
        """Check if user has any reportees or has manager role"""
        return self.role == 'manager' or bool(self.reportees)
    
    @property
    def is_admin(self):
        """Check if user has admin role"""
        return self.role == 'admin'
    
    @property
    def is_hr(self):
        """Check if user has HR role"""
        return self.role == 'hr'
    
    @property
    def is_employee(self):
        """Check if user has employee role"""
        return self.role == 'employee'
    
    @property
    def can_access_all_data(self):
        """Check if user can access all employee data"""
        return self.role in ['admin', 'hr']
    
    @property
    def can_manage_employees(self):
        """Check if user can manage employees"""
        return self.role in ['admin', 'hr']
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_leave_balance(self, leave_type):
        """Calculate leave balance for a specific leave type based on employment status"""
        # Get applicable leave policy for this user's employment status
        policy = LeavePolicy.query.filter_by(
            leave_type=leave_type,
            employment_status=self.employment_status,
            is_active=True
        ).first()
        
        # If no specific policy, try to get 'all' policy
        if not policy:
            policy = LeavePolicy.query.filter_by(
                leave_type=leave_type,
                employment_status='all',
                is_active=True
            ).first()
        
        if not policy:
            return 0
        
        # Check if user meets minimum service requirement
        if policy.min_service_months > 0:
            months_service = (datetime.now() - self.date_joined).days // 30
            if months_service < policy.min_service_months:
                return 0
        
        # Calculate used leaves for current year
        used_leaves = db.session.query(func.sum(LeaveRequest.days_requested)).filter(
            LeaveRequest.user_id == self.id,
            LeaveRequest.leave_type == leave_type,
            LeaveRequest.status == 'approved',
            func.extract('year', LeaveRequest.start_date) == datetime.now().year
        ).scalar() or 0
        
        return policy.annual_allocation - used_leaves

    def get_available_leave_types(self):
        """Get all available leave types for this user based on employment status"""
        policies = LeavePolicy.query.filter(
            db.or_(
                LeavePolicy.employment_status == self.employment_status,
                LeavePolicy.employment_status == 'all'
            ),
            LeavePolicy.is_active == True
        ).all()
        
        available_types = []
        for policy in policies:
            # Check minimum service requirement
            if policy.min_service_months > 0:
                months_service = (datetime.now() - self.date_joined).days // 30
                if months_service < policy.min_service_months:
                    continue
            
            balance = self.get_leave_balance(policy.leave_type)
            available_types.append({
                'leave_type': policy.leave_type,
                'display_name': policy.leave_type_display_name,
                'balance': balance,
                'allocation': policy.annual_allocation
            })
        
        return available_types

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    punch_in_time = db.Column(db.DateTime)
    punch_out_time = db.Column(db.DateTime)
    punch_in_location = db.Column(db.String(200))  # lat,lng
    punch_out_location = db.Column(db.String(200))  # lat,lng
    punch_in_ip = db.Column(db.String(45))
    punch_out_ip = db.Column(db.String(45))
    work_mode_detected = db.Column(db.String(20))  # onsite/offsite
    total_hours = db.Column(db.Float)
    status = db.Column(db.String(20), default='present')  # present/absent/partial
    
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='unique_user_date'),)
    
    def calculate_hours(self):
        """Calculate total working hours"""
        if self.punch_in_time and self.punch_out_time:
            delta = self.punch_out_time - self.punch_in_time
            self.total_hours = delta.total_seconds() / 3600.0
            return self.total_hours
        return 0

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.String(20), nullable=False)  # sick/casual/earned/optional
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_requested = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending/approved/rejected
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_date = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    admin_comments = db.Column(db.Text)

class Holiday(db.Model):
    __tablename__ = 'holidays'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    is_optional = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    document_type = db.Column(db.String(50))  # leave_document/profile_document/other
    related_id = db.Column(db.Integer)  # Link to leave_request_id if applicable
    uploaded_date = db.Column(db.DateTime, default=datetime.utcnow)

class LeavePolicy(db.Model):
    __tablename__ = 'leave_policies'
    
    id = db.Column(db.Integer, primary_key=True)
    leave_type = db.Column(db.String(20), nullable=False)
    leave_type_display_name = db.Column(db.String(100), nullable=False)
    employment_status = db.Column(db.String(20), nullable=False)  # probation/confirmed/all
    annual_allocation = db.Column(db.Integer, nullable=False)
    max_encashable = db.Column(db.Integer, default=0)
    carry_forward_limit = db.Column(db.Integer, default=0)
    min_service_months = db.Column(db.Integer, default=0)  # Minimum months of service required
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    __table_args__ = (db.UniqueConstraint('leave_type', 'employment_status', name='unique_leave_policy'),)

# Emergency Contact Information
class EmergencyContact(db.Model):
    __tablename__ = 'emergency_contacts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    is_primary = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

# Job Postings for Recruitment
class JobPosting(db.Model):
    __tablename__ = 'job_postings'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    employment_type = db.Column(db.String(30), nullable=False)  # full-time/part-time/contract
    salary_range = db.Column(db.String(50))
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    benefits = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active/closed/draft
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)
    closing_date = db.Column(db.Date)
    
    # Relationship
    applications = db.relationship('JobApplication', backref='job_posting', lazy=True)

# Job Applications - Enhanced ATS
class JobApplication(db.Model):
    __tablename__ = 'job_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    job_posting_id = db.Column(db.Integer, db.ForeignKey('job_postings.id'), nullable=False)
    candidate_name = db.Column(db.String(100), nullable=False)
    candidate_email = db.Column(db.String(120), nullable=False)
    candidate_phone = db.Column(db.String(15), nullable=False)
    candidate_linkedin = db.Column(db.String(200))
    candidate_portfolio = db.Column(db.String(200))
    current_company = db.Column(db.String(100))
    current_designation = db.Column(db.String(100))
    experience_years = db.Column(db.Integer)
    current_salary = db.Column(db.Float)
    expected_salary = db.Column(db.Float)
    notice_period = db.Column(db.Integer)  # in days
    resume_filename = db.Column(db.String(255))
    resume_path = db.Column(db.String(500))
    cover_letter = db.Column(db.Text)
    status = db.Column(db.String(30), default='applied')  # applied/screening/interview/rejected/selected/offer_sent/hired
    stage = db.Column(db.String(50), default='application_review')  # application_review/phone_screening/technical_interview/hr_interview/final_interview/offer_negotiation
    priority = db.Column(db.String(20), default='medium')  # low/medium/high
    source = db.Column(db.String(50), default='website')  # website/linkedin/referral/job_board
    referral_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)  # Private notes for hiring team
    resume_score = db.Column(db.Float)  # AI/keyword matching score
    skills_matched = db.Column(db.Text)  # JSON array of matched skills
    overall_rating = db.Column(db.Float)  # Average of all interview ratings
    is_archived = db.Column(db.Boolean, default=False)
    rejection_reason = db.Column(db.String(200))
    
    # Relationships
    interviews = db.relationship('Interview', backref='application', lazy=True)
    evaluations = db.relationship('CandidateEvaluation', backref='application', lazy=True)
    offers = db.relationship('JobOffer', backref='application', lazy=True)
    activities = db.relationship('ApplicationActivity', backref='application', lazy=True)
    referrer = db.relationship('User', foreign_keys=[referral_by], backref='referrals')

# Candidate Evaluation/Scoring
class CandidateEvaluation(db.Model):
    __tablename__ = 'candidate_evaluations'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('job_applications.id'), nullable=False)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    evaluation_type = db.Column(db.String(50), nullable=False)  # resume_review/phone_screening/technical/hr/final
    technical_skills = db.Column(db.Float)  # 1-10 rating
    communication_skills = db.Column(db.Float)
    cultural_fit = db.Column(db.Float)
    experience_relevance = db.Column(db.Float)
    problem_solving = db.Column(db.Float)
    overall_rating = db.Column(db.Float, nullable=False)
    strengths = db.Column(db.Text)
    weaknesses = db.Column(db.Text)
    recommendation = db.Column(db.String(20))  # strongly_recommend/recommend/neutral/not_recommend/reject
    feedback = db.Column(db.Text)
    evaluation_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    evaluator = db.relationship('User', backref='evaluations')

# Job Offers
class JobOffer(db.Model):
    __tablename__ = 'job_offers'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('job_applications.id'), nullable=False)
    offered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    position_title = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    salary_offered = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    employment_type = db.Column(db.String(30), nullable=False)  # full_time/part_time/contract
    start_date = db.Column(db.Date)
    benefits = db.Column(db.Text)
    terms_conditions = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending/accepted/rejected/withdrawn/expired
    offer_sent_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)
    candidate_response_date = db.Column(db.DateTime)
    candidate_comments = db.Column(db.Text)
    offer_letter_path = db.Column(db.String(500))
    
    # Relationships
    offered_by_user = db.relationship('User', backref='job_offers')

# Application Activity Log
class ApplicationActivity(db.Model):
    __tablename__ = 'application_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('job_applications.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # status_change/note_added/interview_scheduled/email_sent
    description = db.Column(db.Text, nullable=False)
    old_value = db.Column(db.String(100))
    new_value = db.Column(db.String(100))
    activity_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='application_activities')

# Email Templates for ATS
class EmailTemplate(db.Model):
    __tablename__ = 'email_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    template_type = db.Column(db.String(50), nullable=False)  # application_received/interview_invitation/rejection/offer
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref='email_templates')

# Background Check
class BackgroundCheck(db.Model):
    __tablename__ = 'background_checks'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('job_applications.id'), nullable=False)
    check_type = db.Column(db.String(50), nullable=False)  # employment/education/criminal/reference
    status = db.Column(db.String(20), default='pending')  # pending/in_progress/completed/failed
    provider = db.Column(db.String(100))
    initiated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    initiated_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_date = db.Column(db.DateTime)
    result = db.Column(db.String(20))  # clear/flagged/failed
    details = db.Column(db.Text)
    report_file = db.Column(db.String(500))
    
    # Relationships
    initiator = db.relationship('User', backref='background_checks')

# Interview Scheduling - Enhanced
class InterviewPanel(db.Model):
    __tablename__ = 'interview_panels'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id'), nullable=False)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50))  # primary/secondary/observer
    
    # Relationships
    interviewer = db.relationship('User', backref='interview_panels')

# ATS Configuration
class ATSConfiguration(db.Model):
    __tablename__ = 'ats_configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(100), nullable=False, unique=True)
    setting_value = db.Column(db.Text)
    setting_type = db.Column(db.String(20), default='string')  # string/integer/boolean/json
    description = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow)

# Interview Scheduling - Enhanced
class Interview(db.Model):
    __tablename__ = 'interviews'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('job_applications.id'), nullable=False)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    interview_round = db.Column(db.Integer, default=1)
    interview_type = db.Column(db.String(30), nullable=False)  # phone/video/in-person/technical/hr/panel
    scheduled_date = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    location = db.Column(db.String(200))
    meeting_link = db.Column(db.String(500))
    meeting_id = db.Column(db.String(100))
    meeting_password = db.Column(db.String(50))
    status = db.Column(db.String(20), default='scheduled')  # scheduled/completed/cancelled/rescheduled/no_show
    feedback = db.Column(db.Text)
    technical_assessment = db.Column(db.Text)
    strengths = db.Column(db.Text)
    concerns = db.Column(db.Text)
    recommendation = db.Column(db.String(20))  # hire/maybe/no_hire
    overall_rating = db.Column(db.Float)  # 1-10 rating
    punctuality_rating = db.Column(db.Integer)  # 1-5
    communication_rating = db.Column(db.Integer)  # 1-5
    technical_rating = db.Column(db.Integer)  # 1-5
    culture_fit_rating = db.Column(db.Integer)  # 1-5
    reminder_sent = db.Column(db.Boolean, default=False)
    rescheduled_from = db.Column(db.Integer, db.ForeignKey('interviews.id'))
    cancelled_reason = db.Column(db.String(200))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_date = db.Column(db.DateTime)
    
    # Relationships
    panel = db.relationship('InterviewPanel', backref='interview', lazy=True)
    rescheduled_interviews = db.relationship('Interview', backref=db.backref('original_interview', remote_side='Interview.id'))

# Training Programs
class TrainingProgram(db.Model):
    __tablename__ = 'training_programs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # technical/soft-skills/compliance/leadership
    duration_hours = db.Column(db.Integer, nullable=False)
    trainer_name = db.Column(db.String(100))
    max_participants = db.Column(db.Integer)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='active')  # active/completed/cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    enrollments = db.relationship('TrainingEnrollment', backref='training_program', lazy=True)

class TrainingEnrollment(db.Model):
    __tablename__ = 'training_enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    training_program_id = db.Column(db.Integer, db.ForeignKey('training_programs.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='enrolled')  # enrolled/in_progress/completed/dropped
    completion_date = db.Column(db.DateTime)
    score = db.Column(db.Float)  # 0-100
    feedback = db.Column(db.Text)
    certificate_issued = db.Column(db.Boolean, default=False)

# Employee Certifications
class Certification(db.Model):
    __tablename__ = 'certifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    issuing_organization = db.Column(db.String(200), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date)
    certificate_number = db.Column(db.String(100))
    certificate_file = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

# Exit Management
class ExitRequest(db.Model):
    __tablename__ = 'exit_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resignation_date = db.Column(db.Date, nullable=False)
    last_working_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    notice_period_days = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending/approved/rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_date = db.Column(db.DateTime)
    admin_comments = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    exit_interview = db.relationship('ExitInterview', backref='exit_request', uselist=False, lazy=True)

# Exit Interview
class ExitInterview(db.Model):
    __tablename__ = 'exit_interviews'
    
    id = db.Column(db.Integer, primary_key=True)
    exit_request_id = db.Column(db.Integer, db.ForeignKey('exit_requests.id'), nullable=False)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    interview_date = db.Column(db.DateTime, nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    suggestions = db.Column(db.Text)
    would_recommend = db.Column(db.Boolean)
    overall_rating = db.Column(db.Integer)  # 1-10 rating
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

# Company Announcements
class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # general/policy/birthday/anniversary/event
    priority = db.Column(db.String(20), default='normal')  # low/normal/high/urgent
    target_audience = db.Column(db.String(50), default='all')  # all/department/role-specific
    target_value = db.Column(db.String(100))  # department name or role if targeted
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)

# Policy Documents
class PolicyDocument(db.Model):
    __tablename__ = 'policy_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # hr/it/finance/general/compliance
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)
    version = db.Column(db.String(10), default='1.0')
    is_active = db.Column(db.Boolean, default=True)
    requires_acknowledgment = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    acknowledgments = db.relationship('PolicyAcknowledgment', backref='policy_document', lazy=True)

# Policy Acknowledgments
class PolicyAcknowledgment(db.Model):
    __tablename__ = 'policy_acknowledgments'
    
    id = db.Column(db.Integer, primary_key=True)
    policy_document_id = db.Column(db.Integer, db.ForeignKey('policy_documents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    acknowledged_date = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    
    __table_args__ = (db.UniqueConstraint('policy_document_id', 'user_id', name='unique_policy_user_ack'),)

# Employment History
class EmploymentHistory(db.Model):
    __tablename__ = 'employment_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    position_title = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    salary = db.Column(db.Float)
    reason_for_change = db.Column(db.String(200))
    is_current = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    """Model for in-app notifications"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # leave_request, leave_approved, leave_rejected, etc.
    related_id = db.Column(db.Integer)  # ID of related object (leave request, etc.)
    is_read = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))
