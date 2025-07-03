
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import User, LeavePolicy, Designation, Department, LeaveRequest
from extensions import db
from datetime import datetime
from sqlalchemy import func

hr_admin_bp = Blueprint('hr_admin', __name__)

def hr_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'hr']:
            flash('Access denied. HR or Admin privileges required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@hr_admin_bp.route('/leave-policies')
@login_required
@hr_admin_required
def leave_policies():
    policies = LeavePolicy.query.order_by(LeavePolicy.employee_status, LeavePolicy.leave_type).all()
    return render_template('hr_admin/leave_policies.html', policies=policies)

@hr_admin_bp.route('/leave-policies/add', methods=['GET', 'POST'])
@login_required
@hr_admin_required
def add_leave_policy():
    if request.method == 'POST':
        policy = LeavePolicy(
            leave_type=request.form.get('leave_type'),
            leave_type_display=request.form.get('leave_type_display'),
            employee_status=request.form.get('employee_status'),
            annual_allocation=int(request.form.get('annual_allocation')),
            max_encashable=int(request.form.get('max_encashable', 0)),
            carry_forward_limit=int(request.form.get('carry_forward_limit', 0)),
            requires_approval=request.form.get('requires_approval') == 'on',
            min_notice_days=int(request.form.get('min_notice_days', 0)),
            max_consecutive_days=int(request.form.get('max_consecutive_days', 0)),
            created_by=current_user.id
        )
        
        try:
            db.session.add(policy)
            db.session.commit()
            flash('Leave policy added successfully.', 'success')
            return redirect(url_for('hr_admin.leave_policies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding leave policy: {str(e)}', 'danger')
    
    return render_template('hr_admin/add_leave_policy.html')

@hr_admin_bp.route('/leave-policies/<int:policy_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_admin_required
def edit_leave_policy(policy_id):
    policy = LeavePolicy.query.get_or_404(policy_id)
    
    if request.method == 'POST':
        policy.leave_type = request.form.get('leave_type')
        policy.leave_type_display = request.form.get('leave_type_display')
        policy.employee_status = request.form.get('employee_status')
        policy.annual_allocation = int(request.form.get('annual_allocation'))
        policy.max_encashable = int(request.form.get('max_encashable', 0))
        policy.carry_forward_limit = int(request.form.get('carry_forward_limit', 0))
        policy.requires_approval = request.form.get('requires_approval') == 'on'
        policy.min_notice_days = int(request.form.get('min_notice_days', 0))
        policy.max_consecutive_days = int(request.form.get('max_consecutive_days', 0))
        
        try:
            db.session.commit()
            flash('Leave policy updated successfully.', 'success')
            return redirect(url_for('hr_admin.leave_policies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating leave policy: {str(e)}', 'danger')
    
    return render_template('hr_admin/edit_leave_policy.html', policy=policy)

@hr_admin_bp.route('/leave-policies/<int:policy_id>/toggle')
@login_required
@hr_admin_required
def toggle_leave_policy(policy_id):
    policy = LeavePolicy.query.get_or_404(policy_id)
    policy.is_active = not policy.is_active
    db.session.commit()
    
    status = 'activated' if policy.is_active else 'deactivated'
    flash(f'Leave policy has been {status}.', 'success')
    return redirect(url_for('hr_admin.leave_policies'))

@hr_admin_bp.route('/designations')
@login_required
@hr_admin_required
def designations():
    designations = Designation.query.order_by(Designation.department, Designation.level).all()
    return render_template('hr_admin/designations.html', designations=designations)

@hr_admin_bp.route('/designations/add', methods=['GET', 'POST'])
@login_required
@hr_admin_required
def add_designation():
    if request.method == 'POST':
        designation = Designation(
            name=request.form.get('name'),
            level=int(request.form.get('level')),
            department=request.form.get('department'),
            description=request.form.get('description'),
            min_experience_years=int(request.form.get('min_experience_years', 0)),
            max_experience_years=int(request.form.get('max_experience_years')) if request.form.get('max_experience_years') else None,
            created_by=current_user.id
        )
        
        try:
            db.session.add(designation)
            db.session.commit()
            flash('Designation added successfully.', 'success')
            return redirect(url_for('hr_admin.designations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding designation: {str(e)}', 'danger')
    
    departments = ['IT', 'HR', 'Finance', 'Marketing', 'Sales', 'Operations', 'Admin']
    return render_template('hr_admin/add_designation.html', departments=departments)

@hr_admin_bp.route('/designations/<int:designation_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_admin_required
def edit_designation(designation_id):
    designation = Designation.query.get_or_404(designation_id)
    
    if request.method == 'POST':
        designation.name = request.form.get('name')
        designation.level = int(request.form.get('level'))
        designation.department = request.form.get('department')
        designation.description = request.form.get('description')
        designation.min_experience_years = int(request.form.get('min_experience_years', 0))
        designation.max_experience_years = int(request.form.get('max_experience_years')) if request.form.get('max_experience_years') else None
        
        try:
            db.session.commit()
            flash('Designation updated successfully.', 'success')
            return redirect(url_for('hr_admin.designations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating designation: {str(e)}', 'danger')
    
    departments = ['IT', 'HR', 'Finance', 'Marketing', 'Sales', 'Operations', 'Admin']
    return render_template('hr_admin/edit_designation.html', designation=designation, departments=departments)

@hr_admin_bp.route('/designations/<int:designation_id>/toggle')
@login_required
@hr_admin_required
def toggle_designation(designation_id):
    designation = Designation.query.get_or_404(designation_id)
    designation.is_active = not designation.is_active
    db.session.commit()
    
    status = 'activated' if designation.is_active else 'deactivated'
    flash(f'Designation has been {status}.', 'success')
    return redirect(url_for('hr_admin.designations'))

@hr_admin_bp.route('/employee-status')
@login_required
@hr_admin_required
def employee_status():
    employees = User.query.filter_by(role='employee').order_by(User.first_name).all()
    return render_template('hr_admin/employee_status.html', employees=employees)

@hr_admin_bp.route('/employee-status/<int:emp_id>/update', methods=['POST'])
@login_required
@hr_admin_required
def update_employee_status(emp_id):
    employee = User.query.get_or_404(emp_id)
    
    employee.employee_status = request.form.get('employee_status')
    
    if request.form.get('confirmation_date'):
        employee.confirmation_date = datetime.strptime(request.form.get('confirmation_date'), '%Y-%m-%d').date()
    
    if request.form.get('training_end_date'):
        employee.training_end_date = datetime.strptime(request.form.get('training_end_date'), '%Y-%m-%d').date()
    
    try:
        db.session.commit()
        flash(f'Employee status updated successfully for {employee.full_name}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating employee status: {str(e)}', 'danger')
    
    return redirect(url_for('hr_admin.employee_status'))

@hr_admin_bp.route('/leave-analytics')
@login_required
@hr_admin_required
def leave_analytics():
    # Get leave usage analytics
    current_year = datetime.now().year
    
    # Leave usage by type
    leave_usage = db.session.query(
        LeaveRequest.leave_type,
        func.sum(LeaveRequest.days_requested).label('total_days'),
        func.count(LeaveRequest.id).label('total_requests')
    ).filter(
        func.extract('year', LeaveRequest.start_date) == current_year,
        LeaveRequest.status == 'approved'
    ).group_by(LeaveRequest.leave_type).all()
    
    # Leave usage by employee status
    status_usage = db.session.query(
        User.employee_status,
        func.sum(LeaveRequest.days_requested).label('total_days'),
        func.count(LeaveRequest.id).label('total_requests')
    ).join(LeaveRequest).filter(
        func.extract('year', LeaveRequest.start_date) == current_year,
        LeaveRequest.status == 'approved'
    ).group_by(User.employee_status).all()
    
    return render_template('hr_admin/leave_analytics.html',
                         leave_usage=leave_usage,
                         status_usage=status_usage,
                         current_year=current_year)

