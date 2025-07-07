
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import os
import json
from sqlalchemy import func, and_, or_
from models import (db, JobPosting, JobApplication, Interview, User, CandidateEvaluation, 
                   JobOffer, ApplicationActivity, EmailTemplate, BackgroundCheck, 
                   InterviewPanel, ATSConfiguration)
from routes.admin import admin_required
from utils.helpers import allowed_file
from utils.email import send_email

ats_bp = Blueprint('ats', __name__, url_prefix='/ats')

@ats_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """ATS Dashboard with comprehensive metrics"""
    # Time-based filters
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Application metrics
    total_applications = JobApplication.query.count()
    applications_this_week = JobApplication.query.filter(
        JobApplication.applied_date >= week_start
    ).count()
    applications_this_month = JobApplication.query.filter(
        JobApplication.applied_date >= month_start
    ).count()
    
    # Pipeline metrics
    pipeline_stats = db.session.query(
        JobApplication.stage,
        func.count(JobApplication.id).label('count')
    ).filter(
        JobApplication.is_archived == False
    ).group_by(JobApplication.stage).all()
    
    # Active jobs metrics
    active_jobs = JobPosting.query.filter_by(status='active').count()
    
    # Interview metrics
    upcoming_interviews = Interview.query.filter(
        Interview.scheduled_date >= datetime.now(),
        Interview.status == 'scheduled'
    ).count()
    
    interviews_today = Interview.query.filter(
        func.date(Interview.scheduled_date) == today,
        Interview.status == 'scheduled'
    ).count()
    
    # Recent activities
    recent_activities = db.session.query(ApplicationActivity, JobApplication, User).join(
        JobApplication, ApplicationActivity.application_id == JobApplication.id
    ).join(
        User, ApplicationActivity.user_id == User.id
    ).order_by(ApplicationActivity.activity_date.desc()).limit(10).all()
    
    # Conversion metrics
    hired_count = JobApplication.query.filter_by(status='hired').count()
    conversion_rate = (hired_count / total_applications * 100) if total_applications > 0 else 0
    
    # Source effectiveness
    source_stats = db.session.query(
        JobApplication.source,
        func.count(JobApplication.id).label('applications'),
        func.sum(func.case([(JobApplication.status == 'hired', 1)], else_=0)).label('hired')
    ).group_by(JobApplication.source).all()
    
    return render_template('ats/dashboard.html',
                         total_applications=total_applications,
                         applications_this_week=applications_this_week,
                         applications_this_month=applications_this_month,
                         pipeline_stats=pipeline_stats,
                         active_jobs=active_jobs,
                         upcoming_interviews=upcoming_interviews,
                         interviews_today=interviews_today,
                         recent_activities=recent_activities,
                         conversion_rate=conversion_rate,
                         source_stats=source_stats)

@ats_bp.route('/pipeline')
@login_required
@admin_required
def pipeline():
    """Candidate pipeline view"""
    # Get all active applications grouped by stage
    stages = ['application_review', 'phone_screening', 'technical_interview', 
              'hr_interview', 'final_interview', 'offer_negotiation']
    
    pipeline_data = {}
    for stage in stages:
        applications = db.session.query(JobApplication, JobPosting).join(
            JobPosting, JobApplication.job_posting_id == JobPosting.id
        ).filter(
            JobApplication.stage == stage,
            JobApplication.is_archived == False
        ).order_by(JobApplication.last_activity_date.desc()).all()
        
        pipeline_data[stage] = applications
    
    return render_template('ats/pipeline.html', pipeline_data=pipeline_data, stages=stages)

@ats_bp.route('/applications/<int:app_id>/evaluate', methods=['GET', 'POST'])
@login_required
@admin_required
def evaluate_candidate(app_id):
    """Evaluate candidate"""
    application = JobApplication.query.get_or_404(app_id)
    
    if request.method == 'POST':
        try:
            evaluation = CandidateEvaluation(
                application_id=app_id,
                evaluator_id=current_user.id,
                evaluation_type=request.form['evaluation_type'],
                technical_skills=float(request.form.get('technical_skills', 0)),
                communication_skills=float(request.form.get('communication_skills', 0)),
                cultural_fit=float(request.form.get('cultural_fit', 0)),
                experience_relevance=float(request.form.get('experience_relevance', 0)),
                problem_solving=float(request.form.get('problem_solving', 0)),
                overall_rating=float(request.form['overall_rating']),
                strengths=request.form.get('strengths', ''),
                weaknesses=request.form.get('weaknesses', ''),
                recommendation=request.form['recommendation'],
                feedback=request.form.get('feedback', '')
            )
            
            db.session.add(evaluation)
            
            # Update application rating
            avg_rating = db.session.query(func.avg(CandidateEvaluation.overall_rating)).filter_by(
                application_id=app_id
            ).scalar()
            application.overall_rating = avg_rating
            application.last_activity_date = datetime.utcnow()
            
            # Log activity
            activity = ApplicationActivity(
                application_id=app_id,
                user_id=current_user.id,
                activity_type='evaluation_added',
                description=f'Added {request.form["evaluation_type"]} evaluation with rating {request.form["overall_rating"]}'
            )
            db.session.add(activity)
            
            db.session.commit()
            flash('Evaluation saved successfully!', 'success')
            return redirect(url_for('ats.view_application', app_id=app_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving evaluation: {str(e)}', 'error')
    
    return render_template('ats/evaluate_candidate.html', application=application)

@ats_bp.route('/applications/<int:app_id>/move-stage', methods=['POST'])
@login_required
@admin_required
def move_stage(app_id):
    """Move application to different stage"""
    application = JobApplication.query.get_or_404(app_id)
    new_stage = request.form['new_stage']
    old_stage = application.stage
    
    try:
        application.stage = new_stage
        application.last_activity_date = datetime.utcnow()
        
        # Update status based on stage
        stage_status_mapping = {
            'application_review': 'applied',
            'phone_screening': 'screening',
            'technical_interview': 'interview',
            'hr_interview': 'interview',
            'final_interview': 'interview',
            'offer_negotiation': 'selected'
        }
        
        if new_stage in stage_status_mapping:
            application.status = stage_status_mapping[new_stage]
        
        # Log activity
        activity = ApplicationActivity(
            application_id=app_id,
            user_id=current_user.id,
            activity_type='stage_change',
            description=f'Moved from {old_stage} to {new_stage}',
            old_value=old_stage,
            new_value=new_stage
        )
        db.session.add(activity)
        
        db.session.commit()
        flash(f'Application moved to {new_stage.replace("_", " ").title()}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error moving application: {str(e)}', 'error')
    
    return redirect(url_for('ats.pipeline'))

@ats_bp.route('/applications/<int:app_id>/offer', methods=['GET', 'POST'])
@login_required
@admin_required
def create_offer(app_id):
    """Create job offer"""
    application = JobApplication.query.get_or_404(app_id)
    
    if request.method == 'POST':
        try:
            # Calculate expiry date (default 7 days)
            expiry_days = int(request.form.get('expiry_days', 7))
            expiry_date = datetime.utcnow() + timedelta(days=expiry_days)
            
            offer = JobOffer(
                application_id=app_id,
                offered_by=current_user.id,
                position_title=request.form['position_title'],
                department=request.form['department'],
                salary_offered=float(request.form['salary_offered']),
                currency=request.form.get('currency', 'USD'),
                employment_type=request.form['employment_type'],
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
                benefits=request.form.get('benefits', ''),
                terms_conditions=request.form.get('terms_conditions', ''),
                expiry_date=expiry_date
            )
            
            db.session.add(offer)
            
            # Update application
            application.status = 'offer_sent'
            application.stage = 'offer_negotiation'
            application.last_activity_date = datetime.utcnow()
            
            # Log activity
            activity = ApplicationActivity(
                application_id=app_id,
                user_id=current_user.id,
                activity_type='offer_created',
                description=f'Job offer created for {request.form["position_title"]} position'
            )
            db.session.add(activity)
            
            db.session.commit()
            
            # Send offer email (implement based on your email system)
            flash('Job offer created successfully!', 'success')
            return redirect(url_for('ats.view_application', app_id=app_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating offer: {str(e)}', 'error')
    
    return render_template('ats/create_offer.html', application=application)

@ats_bp.route('/applications/<int:app_id>')
@login_required
@admin_required
def view_application(app_id):
    """Enhanced application view with comprehensive details"""
    application = JobApplication.query.get_or_404(app_id)
    interviews = Interview.query.filter_by(application_id=app_id).order_by(Interview.scheduled_date.desc()).all()
    evaluations = CandidateEvaluation.query.filter_by(application_id=app_id).order_by(CandidateEvaluation.evaluation_date.desc()).all()
    offers = JobOffer.query.filter_by(application_id=app_id).order_by(JobOffer.offer_sent_date.desc()).all()
    activities = db.session.query(ApplicationActivity, User).join(
        User, ApplicationActivity.user_id == User.id
    ).filter(ApplicationActivity.application_id == app_id).order_by(
        ApplicationActivity.activity_date.desc()
    ).all()
    
    return render_template('ats/view_application.html',
                         application=application,
                         interviews=interviews,
                         evaluations=evaluations,
                         offers=offers,
                         activities=activities)

@ats_bp.route('/reports')
@login_required
@admin_required
def reports():
    """ATS Reporting dashboard"""
    # Time periods for reports
    today = date.today()
    last_30_days = today - timedelta(days=30)
    last_90_days = today - timedelta(days=90)
    
    # Hiring funnel report
    funnel_data = {}
    stages = ['applied', 'screening', 'interview', 'selected', 'hired']
    for stage in stages:
        count = JobApplication.query.filter_by(status=stage).count()
        funnel_data[stage] = count
    
    # Source effectiveness
    source_report = db.session.query(
        JobApplication.source,
        func.count(JobApplication.id).label('total'),
        func.sum(func.case([(JobApplication.status == 'hired', 1)], else_=0)).label('hired'),
        func.avg(JobApplication.overall_rating).label('avg_rating')
    ).group_by(JobApplication.source).all()
    
    # Time to hire analysis
    hired_applications = db.session.query(
        JobApplication.applied_date,
        JobApplication.last_activity_date
    ).filter_by(status='hired').all()
    
    time_to_hire_data = []
    for app in hired_applications:
        if app.applied_date and app.last_activity_date:
            days_to_hire = (app.last_activity_date.date() - app.applied_date.date()).days
            time_to_hire_data.append(days_to_hire)
    
    avg_time_to_hire = sum(time_to_hire_data) / len(time_to_hire_data) if time_to_hire_data else 0
    
    # Interview completion rate
    total_interviews = Interview.query.count()
    completed_interviews = Interview.query.filter_by(status='completed').count()
    interview_completion_rate = (completed_interviews / total_interviews * 100) if total_interviews > 0 else 0
    
    return render_template('ats/reports.html',
                         funnel_data=funnel_data,
                         source_report=source_report,
                         avg_time_to_hire=avg_time_to_hire,
                         interview_completion_rate=interview_completion_rate)

@ats_bp.route('/applications/<int:app_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_application(app_id):
    """Reject application"""
    application = JobApplication.query.get_or_404(app_id)
    
    try:
        application.status = 'rejected'
        application.rejection_reason = request.form.get('rejection_reason', '')
        application.last_activity_date = datetime.utcnow()
        application.is_archived = True
        
        # Log activity
        activity = ApplicationActivity(
            application_id=app_id,
            user_id=current_user.id,
            activity_type='application_rejected',
            description=f'Application rejected: {application.rejection_reason}'
        )
        db.session.add(activity)
        
        db.session.commit()
        flash('Application rejected successfully', 'success')
        
        # Send rejection email (implement based on your email system)
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting application: {str(e)}', 'error')
    
    return redirect(url_for('ats.pipeline'))

@ats_bp.route('/email-templates')
@login_required
@admin_required
def email_templates():
    """Manage email templates"""
    templates = EmailTemplate.query.filter_by(is_active=True).all()
    return render_template('ats/email_templates.html', templates=templates)

@ats_bp.route('/settings')
@login_required
@admin_required
def settings():
    """ATS Configuration settings"""
    configurations = ATSConfiguration.query.all()
    return render_template('ats/settings.html', configurations=configurations)
