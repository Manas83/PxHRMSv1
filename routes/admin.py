from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from models import User, Attendance, LeaveRequest, Holiday, Document, LeavePolicy
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
            employment_status=request.form.get('employment_status', 'probation'),
            probation_end_date=datetime.strptime(request.form.get('probation_end_date'), '%Y-%m-%d').date() if request.form.get('probation_end_date') else None,
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

@admin_bp.route('/employees/<int:emp_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_employee(emp_id):
    employee = User.query.get_or_404(emp_id)

    # Get available managers for dropdown
    managers = User.query.filter(
        User.role.in_(['admin', 'hr', 'manager']),
        User.id != emp_id,  # Don't include the employee being edited
        User.active == True
    ).all()

    if request.method == 'POST':
        # Personal Information
        employee.employee_id = request.form.get('employee_id')
        employee.first_name = request.form.get('first_name')
        employee.last_name = request.form.get('last_name')
        employee.email = request.form.get('email')
        employee.phone = request.form.get('phone')
        employee.date_of_birth = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date() if request.form.get('date_of_birth') else None
        employee.gender = request.form.get('gender')
        employee.marital_status = request.form.get('marital_status')
        employee.nationality = request.form.get('nationality')

        # Address Information
        employee.address = request.form.get('address')
        employee.city = request.form.get('city')
        employee.state = request.form.get('state')
        employee.postal_code = request.form.get('postal_code')
        employee.country = request.form.get('country')

        # Employment Information
        employee.department = request.form.get('department')
        employee.job_title = request.form.get('job_title')
        employee.hire_date = datetime.strptime(request.form.get('hire_date'), '%Y-%m-%d').date() if request.form.get('hire_date') else None
        employee.employment_type = request.form.get('employment_type')
        employee.employment_status = request.form.get('employment_status')

        # Handle probation end date
        if request.form.get('probation_end_date'):
            employee.probation_end_date = datetime.strptime(request.form.get('probation_end_date'), '%Y-%m-%d').date()
        else:
            employee.probation_end_date = None

        employee.salary = float(request.form.get('salary')) if request.form.get('salary') else None
        employee.role = request.form.get('role')

        # Manager assignment
        manager_id = request.form.get('manager_id')
        employee.manager_id = int(manager_id) if manager_id else None

        # Emergency Contact
        employee.emergency_contact_name = request.form.get('emergency_contact_name')
        employee.emergency_contact_relationship = request.form.get('emergency_contact_relationship')
        employee.emergency_contact_phone = request.form.get('emergency_contact_phone')

        # Bank Details
        employee.bank_account_number = request.form.get('bank_account_number')
        employee.bank_name = request.form.get('bank_name')
        employee.bank_ifsc = request.form.get('bank_ifsc')

        # Status
        employee.active = request.form.get('active') == 'true'

        try:
            db.session.commit()
            flash(f'Employee {employee.full_name} updated successfully!', 'success')
            return redirect(url_for('admin.employees'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating employee: {str(e)}', 'danger')

    return render_template('admin/edit_employee.html', employee=employee, managers=managers)

@admin_bp.route('/employees/<int:emp_id>/set-password', methods=['GET', 'POST'])
@login_required
@admin_required
def set_employee_password(emp_id):
    employee = User.query.get_or_404(emp_id)

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('admin/set_password.html', employee=employee)

        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('admin/set_password.html', employee=employee)

        employee.password_hash = generate_password_hash(new_password)
        employee.reset_token = None
        employee.reset_token_expires = None
        db.session.commit()

        flash(f'Password updated successfully for {employee.full_name}.', 'success')
        return redirect(url_for('admin.employees'))

    return render_template('admin/set_password.html', employee=employee)

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
    employee_ids = request.args.getlist('employee_ids')  # For selected employees

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

    # Build query for attendance data
    query = db.session.query(Attendance, User).join(User).filter(
        and_(Attendance.date >= start_date, Attendance.date <= end_date)
    )

    # Filter by selected employees if specified
    if employee_ids:
        query = query.filter(User.id.in_(employee_ids))

    attendance_data = query.order_by(User.first_name, Attendance.date).all()

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

    filename_suffix = "selected_employees" if employee_ids else "all_employees"
    response.headers['Content-Disposition'] = f'attachment; filename=timesheet_{filename_suffix}_{start_date}_to_{end_date}.csv'

    return response

@admin_bp.route('/reports/timesheet')
@login_required
@admin_required
def timesheet_export():
    """HR timesheet export page"""
    # Get all active employees for selection
    employees = User.query.filter_by(active=True, role='employee').order_by(User.first_name).all()

    # Get unique departments
    departments = db.session.query(User.department).filter_by(active=True).distinct().all()
    departments = [dept[0] for dept in departments if dept[0]]

    return render_template('admin/timesheet_export.html', 
                         employees=employees, 
                         departments=departments)

# Leave Policy Management Routes
@admin_bp.route('/leave-policies')
@login_required
@admin_required
def leave_policies():
    """View and manage leave policies"""
    policies = LeavePolicy.query.order_by(LeavePolicy.employment_status, LeavePolicy.leave_type).all()
    return render_template('admin/leave_policies.html', policies=policies)

@admin_bp.route('/leave-policy/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_leave_policy():
    """Add new leave policy"""
    if request.method == 'POST':
        try:
            policy = LeavePolicy(
                leave_type=request.form.get('leave_type'),
                leave_type_display_name=request.form.get('leave_type_display_name'),
                employment_status=request.form.get('employment_status'),
                annual_allocation=int(request.form.get('annual_allocation')),
                max_encashable=int(request.form.get('max_encashable', 0)),
                carry_forward_limit=int(request.form.get('carry_forward_limit', 0)),
                min_service_months=int(request.form.get('min_service_months', 0)),
                created_by=current_user.id
            )
            db.session.add(policy)
            db.session.commit()
            flash('Leave policy added successfully!', 'success')
            return redirect(url_for('admin.leave_policies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding leave policy: {str(e)}', 'danger')

    return render_template('admin/add_leave_policy.html')

@admin_bp.route('/leave-policy/edit/<int:policy_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_leave_policy(policy_id):
    """Edit existing leave policy"""
    policy = LeavePolicy.query.get_or_404(policy_id)

    if request.method == 'POST':
        try:
            policy.leave_type = request.form.get('leave_type')
            policy.leave_type_display_name = request.form.get('leave_type_display_name')
            policy.employment_status = request.form.get('employment_status')
            policy.annual_allocation = int(request.form.get('annual_allocation'))
            policy.max_encashable = int(request.form.get('max_encashable', 0))
            policy.carry_forward_limit = int(request.form.get('carry_forward_limit', 0))
            policy.min_service_months = int(request.form.get('min_service_months', 0))

            db.session.commit()
            flash('Leave policy updated successfully!', 'success')
            return redirect(url_for('admin.leave_policies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating leave policy: {str(e)}', 'danger')

    return render_template('admin/edit_leave_policy.html', policy=policy)

@admin_bp.route('/leave-policy/toggle/<int:policy_id>', methods=['POST'])
@login_required
@admin_required
def toggle_leave_policy(policy_id):
    """Toggle leave policy active status"""
    policy = LeavePolicy.query.get_or_404(policy_id)

    try:
        policy.is_active = not policy.is_active
        db.session.commit()

        status = 'activated' if policy.is_active else 'deactivated'
        flash(f'Leave policy {status} successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error toggling leave policy: {str(e)}', 'danger')

    return redirect(url_for('admin.leave_policies'))

@admin_bp.route('/leave-policy/delete/<int:policy_id>', methods=['POST'])
@login_required
@admin_required
def delete_leave_policy(policy_id):
    """Delete leave policy"""
    policy = LeavePolicy.query.get_or_404(policy_id)

    try:
        db.session.delete(policy)
        db.session.commit()
        flash('Leave policy deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting leave policy: {str(e)}', 'danger')

    return redirect(url_for('admin.leave_policies'))