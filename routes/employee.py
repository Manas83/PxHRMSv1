from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Attendance, LeaveRequest, Holiday, Document, User
from extensions import db
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import os
import uuid
import csv
import io
from flask import make_response
from utils.helpers import allowed_file, get_client_ip

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    
    # Get today's attendance
    today_attendance = Attendance.query.filter_by(
        user_id=current_user.id, 
        date=today
    ).first()
    
    # Get leave balances
    leave_balances = {
        'sick': current_user.get_leave_balance('sick'),
        'casual': current_user.get_leave_balance('casual'),
        'earned': current_user.get_leave_balance('earned'),
        'optional': current_user.get_leave_balance('optional')
    }
    
    # Get recent attendance (last 7 days)
    last_week = today - timedelta(days=7)
    recent_attendance = Attendance.query.filter(
        Attendance.user_id == current_user.id,
        Attendance.date >= last_week
    ).order_by(Attendance.date.desc()).limit(7).all()
    
    # Get pending leave requests
    pending_leaves = LeaveRequest.query.filter_by(
        user_id=current_user.id,
        status='pending'
    ).count()
    
    # Get upcoming holidays
    upcoming_holidays = Holiday.query.filter(
        Holiday.date >= today
    ).order_by(Holiday.date).limit(5).all()
    
    return render_template('employee/dashboard.html',
                         today_attendance=today_attendance,
                         leave_balances=leave_balances,
                         recent_attendance=recent_attendance,
                         pending_leaves=pending_leaves,
                         upcoming_holidays=upcoming_holidays,
                         today=today)

@employee_bp.route('/punch-in', methods=['POST'])
@login_required
def punch_in():
    today = date.today()
    
    # Check if already punched in today
    existing_attendance = Attendance.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()
    
    if existing_attendance and existing_attendance.punch_in_time:
        return jsonify({'success': False, 'message': 'Already punched in today'})
    
    # Get location data (optional)
    try:
        request_data = request.get_json() or {}
        latitude = request_data.get('latitude')
        longitude = request_data.get('longitude')
        location = f"{latitude},{longitude}" if latitude and longitude else None
    except:
        latitude = None
        longitude = None
        location = None
    
    # Determine work mode - if location available, use it, otherwise allow punch in
    work_mode_detected = current_user.work_mode or 'onsite'  # Default to user's work mode
    if latitude and longitude:
        # You can implement proper geofencing logic here
        work_mode_detected = current_user.work_mode
    
    if not existing_attendance:
        attendance = Attendance(
            user_id=current_user.id,
            date=today,
            punch_in_time=datetime.now(),
            punch_in_location=location,
            punch_in_ip=get_client_ip(),
            work_mode_detected=work_mode_detected,
            status='present'
        )
        db.session.add(attendance)
    else:
        existing_attendance.punch_in_time = datetime.now()
        existing_attendance.punch_in_location = location
        existing_attendance.punch_in_ip = get_client_ip()
        existing_attendance.work_mode_detected = work_mode_detected
        existing_attendance.status = 'present'
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Punched in successfully'})

@employee_bp.route('/punch-out', methods=['POST'])
@login_required
def punch_out():
    today = date.today()
    
    attendance = Attendance.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()
    
    if not attendance or not attendance.punch_in_time:
        return jsonify({'success': False, 'message': 'Must punch in first'})
    
    if attendance.punch_out_time:
        return jsonify({'success': False, 'message': 'Already punched out today'})
    
    # Get location data (optional)
    try:
        request_data = request.get_json() or {}
        latitude = request_data.get('latitude')
        longitude = request_data.get('longitude')
        location = f"{latitude},{longitude}" if latitude and longitude else None
    except:
        location = None
    
    attendance.punch_out_time = datetime.now()
    attendance.punch_out_location = location
    attendance.punch_out_ip = get_client_ip()
    attendance.total_hours = attendance.calculate_hours()
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Punched out successfully'})

@employee_bp.route('/attendance')
@login_required
def attendance():
    # Get current month's attendance
    now = datetime.now()
    start_of_month = date(now.year, now.month, 1)
    
    attendance_records = Attendance.query.filter(
        Attendance.user_id == current_user.id,
        Attendance.date >= start_of_month
    ).order_by(Attendance.date.desc()).all()
    
    # Calculate monthly stats
    total_days = len(attendance_records)
    total_hours = sum(record.total_hours or 0 for record in attendance_records)
    
    return render_template('employee/attendance.html',
                         attendance_records=attendance_records,
                         total_days=total_days,
                         total_hours=total_hours)

@employee_bp.route('/leave/request', methods=['GET', 'POST'])
@login_required
def leave_request():
    if request.method == 'POST':
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        
        # Calculate days requested
        days_requested = (end_date - start_date).days + 1
        
        leave_req = LeaveRequest(
            user_id=current_user.id,
            leave_type=request.form.get('leave_type'),
            start_date=start_date,
            end_date=end_date,
            days_requested=days_requested,
            reason=request.form.get('reason'),
            status='pending'
        )
        
        db.session.add(leave_req)
        db.session.flush()  # Get the ID
        
        # Handle document upload
        if 'document' in request.files:
            file = request.files['document']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join('uploads', unique_filename)
                
                # Create uploads directory if it doesn't exist
                os.makedirs('uploads', exist_ok=True)
                
                file.save(file_path)
                
                document = Document(
                    user_id=current_user.id,
                    filename=unique_filename,
                    original_filename=filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    mime_type=file.content_type,
                    document_type='leave_document',
                    related_id=leave_req.id
                )
                db.session.add(document)
        
        db.session.commit()
        
        # Send notifications using the new notification system
        try:
            from utils.notifications import send_leave_request_notification
            send_leave_request_notification(leave_req)
        except Exception as e:
            # Don't fail the request if notification fails
            print(f"Failed to send notification: {e}")
        
        flash('Leave request submitted successfully. Your manager and HR have been notified.', 'success')
        return redirect(url_for('employee.leave_history'))
    
    # Get available leave types based on employment status
    available_leave_types = current_user.get_available_leave_types()
    
    return render_template('employee/leave_request.html', available_leave_types=available_leave_types)

@employee_bp.route('/leave/history')
@login_required
def leave_history():
    leave_requests = LeaveRequest.query.filter_by(
        user_id=current_user.id
    ).order_by(LeaveRequest.applied_date.desc()).all()
    
    return render_template('employee/leave_history.html', leave_requests=leave_requests)

@employee_bp.route('/profile')
@login_required
def profile():
    return render_template('employee/profile.html', user=current_user)

@employee_bp.route('/timesheet/export')
@login_required
def export_timesheet():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        flash('Please provide both start and end dates.', 'danger')
        return redirect(url_for('employee.attendance'))
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('employee.attendance'))
    
    # Get attendance data for the current user
    attendance_records = Attendance.query.filter(
        Attendance.user_id == current_user.id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).order_by(Attendance.date).all()
    
    # Generate CSV report
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Date', 'Punch In', 'Punch Out', 'Total Hours', 'Work Mode', 'Status'])
    
    total_hours = 0
    for attendance in attendance_records:
        punch_in = attendance.punch_in_time.strftime('%H:%M:%S') if attendance.punch_in_time else ''
        punch_out = attendance.punch_out_time.strftime('%H:%M:%S') if attendance.punch_out_time else ''
        hours = attendance.total_hours or 0
        total_hours += hours
        
        writer.writerow([
            attendance.date.strftime('%Y-%m-%d'),
            punch_in,
            punch_out,
            f"{hours:.2f}",
            attendance.work_mode_detected or '',
            attendance.status
        ])
    
    # Add summary row
    writer.writerow([])
    writer.writerow(['Total Hours:', '', '', f"{total_hours:.2f}", '', ''])
    
    output.seek(0)
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=timesheet_{current_user.employee_id}_{start_date}_to_{end_date}.csv'
    
    return response
