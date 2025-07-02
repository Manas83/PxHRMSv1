from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import os
from models import db, JobPosting, JobApplication, Interview, User
from routes.admin import admin_required
from utils.helpers import allowed_file

recruitment_bp = Blueprint('recruitment', __name__, url_prefix='/recruitment')

@recruitment_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Recruitment dashboard"""
    # Get active job postings
    active_jobs = JobPosting.query.filter_by(status='active').count()
    
    # Get recent applications
    recent_applications = db.session.query(JobApplication, JobPosting).join(
        JobPosting, JobApplication.job_posting_id == JobPosting.id
    ).order_by(JobApplication.applied_date.desc()).limit(10).all()
    
    # Get upcoming interviews
    upcoming_interviews = db.session.query(Interview, JobApplication, JobPosting).join(
        JobApplication, Interview.application_id == JobApplication.id
    ).join(
        JobPosting, JobApplication.job_posting_id == JobPosting.id
    ).filter(
        Interview.scheduled_date >= datetime.now(),
        Interview.status == 'scheduled'
    ).order_by(Interview.scheduled_date.asc()).limit(5).all()
    
    # Get statistics
    total_applications = JobApplication.query.count()
    pending_interviews = Interview.query.filter_by(status='scheduled').count()
    
    return render_template('recruitment/dashboard.html',
                         active_jobs=active_jobs,
                         recent_applications=recent_applications,
                         upcoming_interviews=upcoming_interviews,
                         total_applications=total_applications,
                         pending_interviews=pending_interviews)

@recruitment_bp.route('/jobs')
@login_required
@admin_required
def jobs():
    """List all job postings"""
    job_postings = JobPosting.query.order_by(JobPosting.posted_date.desc()).all()
    return render_template('recruitment/jobs.html', job_postings=job_postings)

@recruitment_bp.route('/jobs/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_job():
    """Add new job posting"""
    if request.method == 'POST':
        try:
            job = JobPosting(
                title=request.form['title'],
                department=request.form['department'],
                location=request.form['location'],
                employment_type=request.form['employment_type'],
                salary_range=request.form.get('salary_range', ''),
                description=request.form['description'],
                requirements=request.form['requirements'],
                benefits=request.form.get('benefits', ''),
                closing_date=datetime.strptime(request.form['closing_date'], '%Y-%m-%d').date() if request.form.get('closing_date') else None,
                posted_by=current_user.id
            )
            
            db.session.add(job)
            db.session.commit()
            
            flash('Job posting created successfully!', 'success')
            return redirect(url_for('recruitment.jobs'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating job posting: {str(e)}', 'error')
    
    return render_template('recruitment/add_job.html')

@recruitment_bp.route('/jobs/<int:job_id>/applications')
@login_required
@admin_required
def job_applications(job_id):
    """View applications for a specific job"""
    job = JobPosting.query.get_or_404(job_id)
    applications = JobApplication.query.filter_by(job_posting_id=job_id).order_by(JobApplication.applied_date.desc()).all()
    
    return render_template('recruitment/job_applications.html', job=job, applications=applications)

@recruitment_bp.route('/applications/<int:app_id>')
@login_required
@admin_required
def view_application(app_id):
    """View application details"""
    application = JobApplication.query.get_or_404(app_id)
    interviews = Interview.query.filter_by(application_id=app_id).order_by(Interview.scheduled_date.desc()).all()
    
    return render_template('recruitment/view_application.html', application=application, interviews=interviews)

@recruitment_bp.route('/applications/<int:app_id>/schedule-interview', methods=['GET', 'POST'])
@login_required
@admin_required
def schedule_interview(app_id):
    """Schedule interview for application"""
    application = JobApplication.query.get_or_404(app_id)
    
    if request.method == 'POST':
        try:
            interview = Interview(
                application_id=app_id,
                interviewer_id=current_user.id,
                scheduled_date=datetime.strptime(request.form['scheduled_date'], '%Y-%m-%dT%H:%M'),
                interview_type=request.form['interview_type'],
                location=request.form.get('location', ''),
                meeting_link=request.form.get('meeting_link', '')
            )
            
            db.session.add(interview)
            db.session.commit()
            
            flash('Interview scheduled successfully!', 'success')
            return redirect(url_for('recruitment.view_application', app_id=app_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error scheduling interview: {str(e)}', 'error')
    
    return render_template('recruitment/schedule_interview.html', application=application)

@recruitment_bp.route('/interviews/<int:interview_id>/feedback', methods=['GET', 'POST'])
@login_required
@admin_required
def interview_feedback(interview_id):
    """Add interview feedback"""
    interview = Interview.query.get_or_404(interview_id)
    
    if request.method == 'POST':
        try:
            interview.status = 'completed'
            interview.feedback = request.form['feedback']
            interview.rating = int(request.form['rating']) if request.form.get('rating') else None
            
            # Update application status if provided
            if request.form.get('application_status'):
                interview.application.status = request.form['application_status']
            
            db.session.commit()
            
            flash('Interview feedback saved successfully!', 'success')
            return redirect(url_for('recruitment.view_application', app_id=interview.application_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving feedback: {str(e)}', 'error')
    
    return render_template('recruitment/interview_feedback.html', interview=interview)

# Public routes for job applications (no login required)
@recruitment_bp.route('/public/jobs')
def public_jobs():
    """Public job listing page"""
    active_jobs = JobPosting.query.filter_by(status='active').filter(
        JobPosting.closing_date >= date.today()
    ).order_by(JobPosting.posted_date.desc()).all()
    
    return render_template('recruitment/public_jobs.html', jobs=active_jobs)

@recruitment_bp.route('/public/jobs/<int:job_id>')
def public_job_detail(job_id):
    """Public job detail page"""
    job = JobPosting.query.filter_by(id=job_id, status='active').first_or_404()
    return render_template('recruitment/public_job_detail.html', job=job)

@recruitment_bp.route('/public/jobs/<int:job_id>/apply', methods=['GET', 'POST'])
def apply_job(job_id):
    """Public job application form"""
    job = JobPosting.query.filter_by(id=job_id, status='active').first_or_404()
    
    if request.method == 'POST':
        try:
            # Handle file upload
            resume_filename = ''
            resume_path = ''
            
            if 'resume' in request.files:
                file = request.files['resume']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    resume_filename = timestamp + filename
                    
                    # Create uploads directory if it doesn't exist
                    upload_dir = os.path.join(current_app.root_path, 'uploads', 'resumes')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    resume_path = os.path.join(upload_dir, resume_filename)
                    file.save(resume_path)
            
            application = JobApplication(
                job_posting_id=job_id,
                candidate_name=request.form['candidate_name'],
                candidate_email=request.form['candidate_email'],
                candidate_phone=request.form['candidate_phone'],
                cover_letter=request.form.get('cover_letter', ''),
                resume_filename=resume_filename,
                resume_path=resume_path
            )
            
            db.session.add(application)
            db.session.commit()
            
            flash('Your application has been submitted successfully! We will contact you soon.', 'success')
            return redirect(url_for('recruitment.public_jobs'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting application: {str(e)}', 'error')
    
    return render_template('recruitment/apply_job.html', job=job)