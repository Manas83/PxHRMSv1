from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, make_response
from flask_login import login_required, current_user
from models import User, LeaveRequest, Attendance, Holiday
from extensions import db
from datetime import datetime, date, timedelta
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import os
from werkzeug.utils import secure_filename

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

def admin_or_manager_required(f):
    """Decorator to require admin or manager role"""
    def decorated_function(*args, **kwargs):
        if current_user.role not in ['admin', 'manager'] and not current_user.is_manager:
            flash('Access denied. Manager or Admin privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@reports_bp.route('/')
@login_required
@admin_or_manager_required
def index():
    return render_template('reports/index.html')

@reports_bp.route('/attendance-report')
@login_required
@admin_or_manager_required
def attendance_report():
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department = request.args.get('department')
    employee_id = request.args.get('employee_id')
    export_format = request.args.get('export')
    
    # Default date range (current month)
    if not start_date:
        start_date = date.today().replace(day=1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = date.today()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Build query based on user role
    if current_user.role == 'admin':
        # Admin can see all employees
        base_query = db.session.query(Attendance, User).join(User, Attendance.user_id == User.id)
    else:
        # Manager can only see their reportees
        reportee_ids = [r.id for r in current_user.reportees]
        base_query = db.session.query(Attendance, User).join(User, Attendance.user_id == User.id).filter(
            User.id.in_(reportee_ids)
        )
    
    # Apply filters
    query = base_query.filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    
    if department:
        query = query.filter(User.department == department)
    
    if employee_id:
        query = query.filter(User.employee_id == employee_id)
    
    attendance_data = query.order_by(Attendance.date.desc(), User.employee_id).all()
    
    # Get unique departments for filter dropdown
    if current_user.role == 'admin':
        departments = db.session.query(User.department).filter(User.active == True).distinct().all()
    else:
        reportee_ids = [r.id for r in current_user.reportees]
        departments = db.session.query(User.department).filter(
            User.id.in_(reportee_ids),
            User.active == True
        ).distinct().all()
    
    departments = [dept[0] for dept in departments]
    
    # Handle export
    if export_format in ['csv', 'excel', 'pdf']:
        return export_attendance_report(attendance_data, start_date, end_date, export_format)
    
    return render_template('reports/attendance_report.html',
                         attendance_data=attendance_data,
                         start_date=start_date,
                         end_date=end_date,
                         departments=departments,
                         selected_department=department,
                         selected_employee=employee_id)

@reports_bp.route('/leave-report')
@login_required
@admin_or_manager_required
def leave_report():
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department = request.args.get('department')
    leave_type = request.args.get('leave_type')
    status = request.args.get('status')
    export_format = request.args.get('export')
    
    # Default date range (current year)
    if not start_date:
        start_date = date.today().replace(month=1, day=1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = date.today()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Build query based on user role
    if current_user.role == 'admin':
        base_query = db.session.query(LeaveRequest, User).join(User, LeaveRequest.user_id == User.id)
    else:
        reportee_ids = [r.id for r in current_user.reportees]
        base_query = db.session.query(LeaveRequest, User).join(User, LeaveRequest.user_id == User.id).filter(
            User.id.in_(reportee_ids)
        )
    
    # Apply filters
    query = base_query.filter(
        LeaveRequest.start_date >= start_date,
        LeaveRequest.end_date <= end_date
    )
    
    if department:
        query = query.filter(User.department == department)
    
    if leave_type:
        query = query.filter(LeaveRequest.leave_type == leave_type)
    
    if status:
        query = query.filter(LeaveRequest.status == status)
    
    leave_data = query.order_by(LeaveRequest.applied_date.desc()).all()
    
    # Get filter options
    if current_user.role == 'admin':
        departments = db.session.query(User.department).filter(User.active == True).distinct().all()
    else:
        reportee_ids = [r.id for r in current_user.reportees]
        departments = db.session.query(User.department).filter(
            User.id.in_(reportee_ids),
            User.active == True
        ).distinct().all()
    
    departments = [dept[0] for dept in departments]
    leave_types = ['sick', 'casual', 'earned', 'optional']
    statuses = ['pending', 'approved', 'rejected']
    
    # Handle export
    if export_format in ['csv', 'excel', 'pdf']:
        return export_leave_report(leave_data, start_date, end_date, export_format)
    
    return render_template('reports/leave_report.html',
                         leave_data=leave_data,
                         start_date=start_date,
                         end_date=end_date,
                         departments=departments,
                         leave_types=leave_types,
                         statuses=statuses,
                         selected_department=department,
                         selected_leave_type=leave_type,
                         selected_status=status)

def export_attendance_report(attendance_data, start_date, end_date, format_type):
    """Export attendance report in specified format"""
    
    # Prepare data for export
    export_data = []
    for attendance, user in attendance_data:
        export_data.append({
            'Employee ID': user.employee_id,
            'Name': user.full_name,
            'Department': user.department,
            'Designation': user.designation,
            'Date': attendance.date.strftime('%Y-%m-%d'),
            'Day': attendance.date.strftime('%A'),
            'Punch In': attendance.punch_in_time.strftime('%H:%M:%S') if attendance.punch_in_time else '-',
            'Punch Out': attendance.punch_out_time.strftime('%H:%M:%S') if attendance.punch_out_time else '-',
            'Total Hours': round(attendance.total_hours, 2) if attendance.total_hours else 0,
            'Work Mode': attendance.work_mode_detected or '-',
            'Status': attendance.status.title()
        })
    
    if format_type == 'csv':
        return export_to_csv(export_data, f'attendance_report_{start_date}_{end_date}.csv')
    elif format_type == 'excel':
        return export_to_excel(export_data, f'attendance_report_{start_date}_{end_date}.xlsx')
    elif format_type == 'pdf':
        return export_attendance_to_pdf(export_data, start_date, end_date)

def export_leave_report(leave_data, start_date, end_date, format_type):
    """Export leave report in specified format"""
    
    # Prepare data for export
    export_data = []
    for leave_request, user in leave_data:
        export_data.append({
            'Employee ID': user.employee_id,
            'Name': user.full_name,
            'Department': user.department,
            'Leave Type': leave_request.leave_type.title(),
            'Start Date': leave_request.start_date.strftime('%Y-%m-%d'),
            'End Date': leave_request.end_date.strftime('%Y-%m-%d'),
            'Days': leave_request.days_requested,
            'Reason': leave_request.reason,
            'Status': leave_request.status.title(),
            'Applied Date': leave_request.applied_date.strftime('%Y-%m-%d'),
            'Reviewed Date': leave_request.reviewed_date.strftime('%Y-%m-%d') if leave_request.reviewed_date else '-',
            'Reviewer': leave_request.reviewer.full_name if leave_request.reviewer else '-'
        })
    
    if format_type == 'csv':
        return export_to_csv(export_data, f'leave_report_{start_date}_{end_date}.csv')
    elif format_type == 'excel':
        return export_to_excel(export_data, f'leave_report_{start_date}_{end_date}.xlsx')
    elif format_type == 'pdf':
        return export_leave_to_pdf(export_data, start_date, end_date)

def export_to_csv(data, filename):
    """Export data to CSV format"""
    df = pd.DataFrame(data)
    
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

def export_to_excel(data, filename):
    """Export data to Excel format"""
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
        
        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Report']
        
        # Add some formatting
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Write the column headers with formatting
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        # Auto-adjust columns width
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.set_column(i, i, min(column_len, 50))
    
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

def export_attendance_to_pdf(data, start_date, end_date):
    """Export attendance data to PDF format"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkblue,
        alignment=1  # Center alignment
    )
    
    # Build PDF content
    story = []
    
    # Title
    title = Paragraph("Attendance Report", title_style)
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Date range
    date_range = Paragraph(f"<b>Period:</b> {start_date} to {end_date}", styles['Normal'])
    story.append(date_range)
    story.append(Spacer(1, 12))
    
    # Table data
    table_data = [['Employee ID', 'Name', 'Department', 'Date', 'Punch In', 'Punch Out', 'Hours', 'Status']]
    
    for row in data:
        table_data.append([
            row['Employee ID'],
            row['Name'][:20] + '...' if len(row['Name']) > 20 else row['Name'],
            row['Department'][:10] + '...' if len(row['Department']) > 10 else row['Department'],
            row['Date'],
            row['Punch In'],
            row['Punch Out'],
            str(row['Total Hours']),
            row['Status']
        ])
    
    # Create table
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    filename = f'attendance_report_{start_date}_{end_date}.pdf'
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

def export_leave_to_pdf(data, start_date, end_date):
    """Export leave data to PDF format"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkblue,
        alignment=1
    )
    
    # Build PDF content
    story = []
    
    # Title
    title = Paragraph("Leave Report", title_style)
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Date range
    date_range = Paragraph(f"<b>Period:</b> {start_date} to {end_date}", styles['Normal'])
    story.append(date_range)
    story.append(Spacer(1, 12))
    
    # Table data
    table_data = [['Employee ID', 'Name', 'Department', 'Leave Type', 'Start Date', 'End Date', 'Days', 'Status']]
    
    for row in data:
        table_data.append([
            row['Employee ID'],
            row['Name'][:15] + '...' if len(row['Name']) > 15 else row['Name'],
            row['Department'][:10] + '...' if len(row['Department']) > 10 else row['Department'],
            row['Leave Type'],
            row['Start Date'],
            row['End Date'],
            str(row['Days']),
            row['Status']
        ])
    
    # Create table
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    filename = f'leave_report_{start_date}_{end_date}.pdf'
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@reports_bp.route('/import-employees', methods=['GET', 'POST'])
@login_required
@admin_or_manager_required
def import_employees():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Read the uploaded file
                if file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                
                # Process and import employees
                success_count, error_count, errors = process_employee_import(df)
                
                if success_count > 0:
                    flash(f'Successfully imported {success_count} employees.', 'success')
                
                if error_count > 0:
                    flash(f'{error_count} employees failed to import. Errors: {"; ".join(errors[:5])}', 'error')
                
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file format. Please upload CSV or Excel file.', 'error')
    
    return render_template('reports/import_employees.html')

def allowed_file(filename):
    """Check if file extension is allowed for import"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['csv', 'xlsx', 'xls']

def process_employee_import(df):
    """Process employee import from DataFrame"""
    success_count = 0
    error_count = 0
    errors = []
    
    required_columns = ['employee_id', 'email', 'first_name', 'last_name', 'department', 'designation']
    
    # Check required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        return success_count, len(df), errors
    
    for index, row in df.iterrows():
        try:
            # Check if employee already exists
            existing_user = User.query.filter(
                (User.email == row['email']) | (User.employee_id == row['employee_id'])
            ).first()
            
            if existing_user:
                errors.append(f"Employee {row['employee_id']} already exists")
                error_count += 1
                continue
            
            # Find manager if specified
            manager = None
            if 'manager_email' in row and pd.notna(row['manager_email']) and row['manager_email']:
                manager = User.query.filter_by(email=row['manager_email']).first()
                if not manager:
                    errors.append(f"Manager not found for {row['employee_id']}: {row['manager_email']}")
            
            # Create new employee
            employee = User(
                employee_id=row['employee_id'],
                email=row['email'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                phone=row.get('phone', ''),
                department=row['department'],
                designation=row['designation'],
                work_mode=row.get('work_mode', 'onsite'),
                role=row.get('role', 'employee'),
                employment_status=row.get('employment_status', 'probation'),
                manager_id=manager.id if manager else None,
                active=True
            )
            
            db.session.add(employee)
            success_count += 1
            
        except Exception as e:
            errors.append(f"Row {index + 1}: {str(e)}")
            error_count += 1
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        errors.append(f"Database error: {str(e)}")
        return 0, len(df), errors
    
    return success_count, error_count, errors