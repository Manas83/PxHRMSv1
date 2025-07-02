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
    
    @property
    def is_manager(self):
        """Check if user has any reportees"""
        return bool(self.reportees)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_leave_balance(self, leave_type):
        """Calculate leave balance for a specific leave type"""
        # Default annual leave allocation
        annual_allocation = {
            'sick': 12,
            'casual': 12,
            'earned': 21,
            'optional': 2
        }
        
        used_leaves = db.session.query(func.sum(LeaveRequest.days_requested)).filter(
            LeaveRequest.user_id == self.id,
            LeaveRequest.leave_type == leave_type,
            LeaveRequest.status == 'approved',
            func.extract('year', LeaveRequest.start_date) == datetime.now().year
        ).scalar() or 0
        
        return annual_allocation.get(leave_type, 0) - used_leaves

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
    annual_allocation = db.Column(db.Integer, nullable=False)
    max_encashable = db.Column(db.Integer, default=0)
    carry_forward_limit = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
