from flask import request
import os

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_client_ip():
    """Get client IP address"""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    return ip

def format_duration(hours):
    """Format duration in hours to human readable format"""
    if not hours:
        return "0h 0m"
    
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"

def get_leave_type_display(leave_type):
    """Get display name for leave type"""
    leave_types = {
        'sick': 'Sick Leave',
        'casual': 'Casual Leave',
        'earned': 'Earned Leave',
        'optional': 'Optional Holiday'
    }
    return leave_types.get(leave_type, leave_type.title())

def calculate_working_days(start_date, end_date):
    """Calculate working days between two dates (excluding weekends)"""
    from datetime import timedelta
    
    current_date = start_date
    working_days = 0
    
    while current_date <= end_date:
        # Monday = 0, Sunday = 6
        if current_date.weekday() < 5:  # Monday to Friday
            working_days += 1
        current_date += timedelta(days=1)
    
    return working_days
