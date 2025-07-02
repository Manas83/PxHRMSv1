from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from models import db, ExitRequest, ExitInterview, User
from routes.admin import admin_required

exit_bp = Blueprint('exit_management', __name__, url_prefix='/exit')

@exit_bp.route('/')
@login_required
def dashboard():
    """Exit management dashboard"""
    if current_user.role == 'admin':
        # Admin view - all exit requests
        pending_exits = ExitRequest.query.filter_by(status='pending').count()
        approved_exits = ExitRequest.query.filter_by(status='approved').count()
        
        recent_exits = db.session.query(ExitRequest, User).join(
            User, ExitRequest.user_id == User.id
        ).order_by(ExitRequest.created_date.desc()).limit(10).all()
        
        # Upcoming last working dates
        upcoming_departures = db.session.query(ExitRequest, User).join(
            User, ExitRequest.user_id == User.id
        ).filter(
            ExitRequest.status == 'approved',
            ExitRequest.last_working_date >= date.today(),
            ExitRequest.last_working_date <= date.today() + timedelta(days=30)
        ).order_by(ExitRequest.last_working_date.asc()).all()
        
        return render_template('exit/admin_dashboard.html',
                             pending_exits=pending_exits,
                             approved_exits=approved_exits,
                             recent_exits=recent_exits,
                             upcoming_departures=upcoming_departures)
    else:
        # Employee view - their exit request
        my_exit_request = ExitRequest.query.filter_by(user_id=current_user.id).first()
        return render_template('exit/employee_dashboard.html', my_exit_request=my_exit_request)

@exit_bp.route('/request', methods=['GET', 'POST'])
@login_required
def submit_resignation():
    """Submit resignation request"""
    # Check if user already has an exit request
    existing_request = ExitRequest.query.filter_by(user_id=current_user.id).first()
    if existing_request:
        flash('You already have an exit request submitted.', 'warning')
        return redirect(url_for('exit_management.dashboard'))
    
    if request.method == 'POST':
        try:
            resignation_date = datetime.strptime(request.form['resignation_date'], '%Y-%m-%d').date()
            last_working_date = datetime.strptime(request.form['last_working_date'], '%Y-%m-%d').date()
            
            # Calculate notice period
            notice_period = (last_working_date - resignation_date).days
            
            exit_request = ExitRequest(
                user_id=current_user.id,
                resignation_date=resignation_date,
                last_working_date=last_working_date,
                reason=request.form['reason'],
                notice_period_days=notice_period
            )
            
            db.session.add(exit_request)
            db.session.commit()
            
            flash('Your resignation request has been submitted successfully!', 'success')
            return redirect(url_for('exit_management.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting resignation: {str(e)}', 'error')
    
    return render_template('exit/submit_resignation.html')

@exit_bp.route('/requests')
@login_required
@admin_required
def exit_requests():
    """List all exit requests"""
    requests = db.session.query(ExitRequest, User).join(
        User, ExitRequest.user_id == User.id
    ).order_by(ExitRequest.created_date.desc()).all()
    
    return render_template('exit/exit_requests.html', exit_requests=requests)

@exit_bp.route('/requests/<int:request_id>')
@login_required
@admin_required
def view_exit_request(request_id):
    """View exit request details"""
    exit_request = ExitRequest.query.get_or_404(request_id)
    exit_interview = ExitInterview.query.filter_by(exit_request_id=request_id).first()
    
    return render_template('exit/view_exit_request.html', 
                         exit_request=exit_request, 
                         exit_interview=exit_interview)

@exit_bp.route('/requests/<int:request_id>/review', methods=['POST'])
@login_required
@admin_required
def review_exit_request(request_id):
    """Approve or reject exit request"""
    exit_request = ExitRequest.query.get_or_404(request_id)
    
    try:
        exit_request.status = request.form['status']
        exit_request.approved_by = current_user.id
        exit_request.approved_date = datetime.now()
        exit_request.admin_comments = request.form.get('admin_comments', '')
        
        db.session.commit()
        
        status_text = 'approved' if exit_request.status == 'approved' else 'rejected'
        flash(f'Exit request has been {status_text} successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error reviewing exit request: {str(e)}', 'error')
    
    return redirect(url_for('exit_management.view_exit_request', request_id=request_id))

@exit_bp.route('/interviews/<int:request_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def conduct_exit_interview(request_id):
    """Conduct exit interview"""
    exit_request = ExitRequest.query.get_or_404(request_id)
    
    # Check if interview already exists
    existing_interview = ExitInterview.query.filter_by(exit_request_id=request_id).first()
    
    if request.method == 'POST':
        try:
            if existing_interview:
                # Update existing interview
                existing_interview.interviewer_id = current_user.id
                existing_interview.interview_date = datetime.now()
                existing_interview.feedback = request.form['feedback']
                existing_interview.suggestions = request.form.get('suggestions', '')
                existing_interview.would_recommend = request.form.get('would_recommend') == 'on'
                existing_interview.overall_rating = int(request.form['overall_rating']) if request.form.get('overall_rating') else None
            else:
                # Create new interview
                interview = ExitInterview(
                    exit_request_id=request_id,
                    interviewer_id=current_user.id,
                    interview_date=datetime.now(),
                    feedback=request.form['feedback'],
                    suggestions=request.form.get('suggestions', ''),
                    would_recommend=request.form.get('would_recommend') == 'on',
                    overall_rating=int(request.form['overall_rating']) if request.form.get('overall_rating') else None
                )
                db.session.add(interview)
            
            db.session.commit()
            
            flash('Exit interview has been recorded successfully!', 'success')
            return redirect(url_for('exit_management.view_exit_request', request_id=request_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error recording exit interview: {str(e)}', 'error')
    
    return render_template('exit/conduct_interview.html', 
                         exit_request=exit_request, 
                         existing_interview=existing_interview)

@exit_bp.route('/analytics')
@login_required
@admin_required
def exit_analytics():
    """Exit analytics and reports"""
    # Basic statistics
    total_exits = ExitRequest.query.count()
    approved_exits = ExitRequest.query.filter_by(status='approved').count()
    pending_exits = ExitRequest.query.filter_by(status='pending').count()
    
    # Department-wise exit analysis
    dept_stats = db.session.query(
        User.department,
        db.func.count(ExitRequest.id).label('exit_count')
    ).join(ExitRequest).group_by(User.department).all()
    
    # Monthly exit trends (last 12 months)
    from dateutil.relativedelta import relativedelta
    start_date = date.today() - relativedelta(months=12)
    
    monthly_exits = db.session.query(
        db.func.date_trunc('month', ExitRequest.created_date).label('month'),
        db.func.count(ExitRequest.id).label('count')
    ).filter(ExitRequest.created_date >= start_date).group_by('month').order_by('month').all()
    
    # Recent interviews with ratings
    recent_interviews = db.session.query(ExitInterview, ExitRequest, User).join(
        ExitRequest, ExitInterview.exit_request_id == ExitRequest.id
    ).join(
        User, ExitRequest.user_id == User.id
    ).order_by(ExitInterview.interview_date.desc()).limit(10).all()
    
    return render_template('exit/analytics.html',
                         total_exits=total_exits,
                         approved_exits=approved_exits,
                         pending_exits=pending_exits,
                         dept_stats=dept_stats,
                         monthly_exits=monthly_exits,
                         recent_interviews=recent_interviews)