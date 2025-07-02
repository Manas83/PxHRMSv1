from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from models import User, Attendance, LeaveRequest, Holiday, Document
from extensions import db
from werkzeug.security import generate_password_hash
from utils.email import send_onboarding_email
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_
import secrets
import csv
import io
import os

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_manage_employees:
            flash('Access denied. Admin or HR privileges required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    today = date.today()
    
    # Get today's attendance stats
    total_employees = User.query.filter_by(role='employee', active=True).count()
    
    today_attendance = db.session.query(Attendance).filter(
        Attendance.date == today,
        Attendance.punch_in_time.isnot(None)
    ).count()
    
    # Get pending leave requests
    pending_leaves = LeaveRequest.query.filter_by(status='pending').count()
    
    # Get recent attendance records
    recent_attendance = db.session.query(Attendance, User).join(User).filter(
        Attendance.date == today
    ).order_by(Attendance.punch_in_time.desc()).limit(10).all()
    
    # Get employees who haven't punched in today
    punched_in_users = db.session.query(Attendance.user_id).filter(
        Attendance.date == today,
        Attendance.punch_in_time.isnot(None)
    )
    
    not_punched_in = User.query.filter(
        User.role == 'employee',
        User.active == True,
        ~User.id.in_(punched_in_users)
    ).all()
    
    return render_template('admin/dashboard.html',
                         total_employees=total_employees,
                         today_attendance=today_attendance,
                         pending_leaves=pending_leaves,
                         recent_attendance=recent_attendance,
                         not_punched_in=not_punched_in,
                         today=today)

@admin_bp.route('/employees')
@login_required
@admin_required
def employees():
    employees = User.query.order_by(User.first_name).all()
    return render_template('admin/employees.html', employees=employees)

@admin_bp.route('/employees/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_employee():
    if request.method == 'POST':
        # Generate temporary password
        temp_password = secrets.token_urlsafe(8)
        
        # Get manager ID from form
        manager_id = request.form.get('manager_id')
        manager_id = int(manager_id) if manager_id and manager_id != '' else None
        
        employee = User(
            email=request.form.get('email'),
            employee_id=request.form.get('employee_id'),
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            phone=request.form.get('phone'),
            department=request.form.get('department'),
            designation=request.form.get('designation'),
            work_mode=request.form.get('work_mode'),
            role=request.form.get('role', 'employee'),
            manager_id=manager_id,
            password_hash=generate_password_hash(temp_password),
            active=True
        )
        
        try:
            db.session.add(employee)
            db.session.commit()
            
            # Send onboarding email
            send_onboarding_email(employee.email, temp_password, employee.full_name)
            
            flash(f'Employee {employee.full_name} added successfully. Onboarding email sent.', 'success')
            return redirect(url_for('admin.employees'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding employee: {str(e)}', 'danger')
    
    # Get available managers for the dropdown
    managers = User.query.filter(
        User.role.in_(['admin', 'manager']),
        User.active == True
    ).all()
    
    return render_template('admin/add_employee.html', managers=managers)

@admin_bp.route('/employees/<int:emp_id>/toggle-status')
@login_required
@admin_required
def toggle_employee_status(emp_id):
    employee = User.query.get_or_404(emp_id)
    employee.active = not employee.active
    db.session.commit()
    
    status = 'activated' if employee.active else 'deactivated'
    flash(f'Employee {employee.full_name} has been {status}.', 'success')
    return redirect(url_for('admin.employees'))

@admin_bp.route('/leaves')
@login_required
@admin_required
def leaves():
    status_filter = request.args.get('status', 'pending')
    
    query = db.session.query(LeaveRequest, User).join(User, LeaveRequest.user_id == User.id)
    
    if status_filter != 'all':
        query = query.filter(LeaveRequest.status == status_filter)
    
    leave_requests = query.order_by(LeaveRequest.applied_date.desc()).all()
    
    return render_template('admin/leaves.html', 
                         leave_requests=leave_requests,
                         current_status=status_filter)

@admin_bp.route('/leaves/<int:leave_id>/review', methods=['POST'])
@login_required
@admin_required
def review_leave(leave_id):
    leave_request = LeaveRequest.query.get_or_404(leave_id)
    action = request.form.get('action')
    comments = request.form.get('comments', '')
    
    if action in ['approved', 'rejected']:
        leave_request.status = action
        leave_request.reviewed_by = current_user.id
        leave_request.reviewed_date = datetime.utcnow()
        leave_request.admin_comments = comments
        
        db.session.commit()
        
        flash(f'Leave request has been {action}.', 'success')
    
    return redirect(url_for('admin.leaves'))

@admin_bp.route('/attendance')
@login_required
@admin_required
def attendance():
    selected_date = request.args.get('date', date.today().isoformat())
    selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    
    # Get attendance records for the selected date
    attendance_records = db.session.query(Attendance, User).join(User).filter(
        Attendance.date == selected_date
    ).order_by(User.first_name).all()
    
    # Get employees who didn't punch in
    punched_in_users = [record[0].user_id for record in attendance_records]
    absent_employees = User.query.filter(
        User.role == 'employee',
        User.is_active == True,
        ~User.id.in_(punched_in_users)
    ).all()
    
    return render_template('admin/attendance.html',
                         attendance_records=attendance_records,
                         absent_employees=absent_employees,
                         selected_date=selected_date)

@admin_bp.route('/holidays')
@login_required
@admin_required
def holidays():
    current_year = datetime.now().year
    holidays = Holiday.query.filter(
        func.extract('year', Holiday.date) == current_year
    ).order_by(Holiday.date).all()
    
    return render_template('admin/holidays.html', holidays=holidays)

@admin_bp.route('/holidays/add', methods=['POST'])
@login_required
@admin_required
def add_holiday():
    holiday = Holiday(
        name=request.form.get('name'),
        date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
        is_optional=request.form.get('is_optional') == 'on'
    )
    
    db.session.add(holiday)
    db.session.commit()
    
    flash('Holiday added successfully.', 'success')
    return redirect(url_for('admin.holidays'))

@admin_bp.route('/holidays/<int:holiday_id>/delete')
@login_required
@admin_required
def delete_holiday(holiday_id):
    holiday = Holiday.query.get_or_404(holiday_id)
    db.session.delete(holiday)
    db.session.commit()
    
    flash('Holiday deleted successfully.', 'success')
    return redirect(url_for('admin.holidays'))

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    return render_template('admin/reports.html')

@admin_bp.route('/reports/attendance/download')
@login_required
@admin_required
def download_attendance_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        flash('Please provide both start and end dates.', 'danger')
        return redirect(url_for('admin.reports'))
    
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Generate CSV report
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Employee ID', 'Employee Name', 'Date', 'Punch In', 'Punch Out', 
                    'Total Hours', 'Work Mode', 'Status'])
    
    # Get attendance data
    attendance_data = db.session.query(Attendance, User).join(User).filter(
        and_(Attendance.date >= start_date, Attendance.date <= end_date)
    ).order_by(User.first_name, Attendance.date).all()
    
    for attendance, user in attendance_data:
        writer.writerow([
            user.employee_id,
            user.full_name,
            attendance.date.strftime('%Y-%m-%d'),
            attendance.punch_in_time.strftime('%H:%M:%S') if attendance.punch_in_time else '',
            attendance.punch_out_time.strftime('%H:%M:%S') if attendance.punch_out_time else '',
            f"{attendance.total_hours:.2f}" if attendance.total_hours else '0.00',
            attendance.work_mode_detected or '',
            attendance.status
        ])
    
    output.seek(0)
    
    # Create response
    from flask import make_response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=attendance_report_{start_date}_to_{end_date}.csv'
    
    return response
