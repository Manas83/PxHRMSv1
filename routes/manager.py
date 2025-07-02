from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import User, LeaveRequest, Attendance
from extensions import db
from datetime import datetime, date, timedelta
from utils.email import send_leave_notification

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')

def manager_required(f):
    """Decorator to require manager role or has reportees"""
    def decorated_function(*args, **kwargs):
        if current_user.role not in ['admin', 'manager'] and not current_user.is_manager:
            flash('Access denied. Manager privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@manager_bp.route('/dashboard')
@login_required
@manager_required
def dashboard():
    today = date.today()
    
    # Get reportees
    reportees = current_user.reportees if current_user.role != 'admin' else User.query.filter_by(active=True).all()
    
    # Get pending leave requests from reportees
    if current_user.role == 'admin':
        pending_leaves = LeaveRequest.query.filter_by(status='pending').count()
    else:
        reportee_ids = [r.id for r in reportees]
        pending_leaves = LeaveRequest.query.filter(
            LeaveRequest.user_id.in_(reportee_ids),
            LeaveRequest.status == 'pending'
        ).count()
    
    # Get today's attendance for reportees
    if current_user.role == 'admin':
        today_attendance = Attendance.query.filter_by(date=today).count()
        total_reportees = User.query.filter_by(role='employee', active=True).count()
    else:
        reportee_ids = [r.id for r in reportees]
        today_attendance = Attendance.query.filter(
            Attendance.user_id.in_(reportee_ids),
            Attendance.date == today
        ).count()
        total_reportees = len(reportees)
    
    return render_template('manager/dashboard.html',
                         reportees=reportees,
                         pending_leaves=pending_leaves,
                         today_attendance=today_attendance,
                         total_reportees=total_reportees,
                         today=today)

@manager_bp.route('/team-leaves')
@login_required
@manager_required
def team_leaves():
    status_filter = request.args.get('status', 'pending')
    
    # Get reportees
    if current_user.role == 'admin':
        # Admin can see all leave requests
        query = db.session.query(LeaveRequest, User).join(User, LeaveRequest.user_id == User.id)
    else:
        # Manager can only see reportees' leave requests
        reportee_ids = [r.id for r in current_user.reportees]
        query = db.session.query(LeaveRequest, User).join(User, LeaveRequest.user_id == User.id).filter(
            LeaveRequest.user_id.in_(reportee_ids)
        )
    
    if status_filter != 'all':
        query = query.filter(LeaveRequest.status == status_filter)
    
    leave_requests = query.order_by(LeaveRequest.applied_date.desc()).all()
    
    return render_template('manager/team_leaves.html',
                         leave_requests=leave_requests,
                         current_status=status_filter)

@manager_bp.route('/review-leave/<int:leave_id>', methods=['POST'])
@login_required
@manager_required
def review_leave(leave_id):
    leave_request = LeaveRequest.query.get_or_404(leave_id)
    
    # Check if user has permission to review this leave
    if current_user.role not in ['admin'] and leave_request.user not in current_user.reportees:
        flash('You do not have permission to review this leave request.', 'error')
        return redirect(url_for('manager.team_leaves'))
    
    action = request.form.get('action')
    comments = request.form.get('comments', '')
    
    if action in ['approve', 'reject']:
        leave_request.status = 'approved' if action == 'approve' else 'rejected'
        leave_request.reviewed_by = current_user.id
        leave_request.reviewed_date = datetime.utcnow()
        leave_request.admin_comments = comments
        
        db.session.commit()
        
        # Send notification email
        try:
            send_leave_notification(leave_request.user.email, leave_request, leave_request.status)
        except Exception as e:
            print(f"Failed to send email notification: {e}")
        
        flash(f'Leave request has been {leave_request.status}.', 'success')
    else:
        flash('Invalid action specified.', 'error')
    
    return redirect(url_for('manager.team_leaves'))

@manager_bp.route('/team-attendance')
@login_required
@manager_required
def team_attendance():
    selected_date = request.args.get('date')
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()
    
    # Get reportees
    if current_user.role == 'admin':
        reportees = User.query.filter_by(role='employee', active=True).all()
    else:
        reportees = current_user.reportees
    
    # Get attendance records for the selected date
    reportee_ids = [r.id for r in reportees]
    attendance_records = []
    
    if reportee_ids:
        attendance_data = db.session.query(Attendance, User).join(
            User, Attendance.user_id == User.id
        ).filter(
            Attendance.date == selected_date,
            User.id.in_(reportee_ids)
        ).all()
        
        attendance_records = attendance_data
    
    # Get employees who didn't punch in
    present_user_ids = [att.user_id for att, _ in attendance_records]
    absent_employees = [emp for emp in reportees if emp.id not in present_user_ids]
    
    return render_template('manager/team_attendance.html',
                         attendance_records=attendance_records,
                         absent_employees=absent_employees,
                         selected_date=selected_date,
                         reportees=reportees)