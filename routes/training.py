from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from models import db, TrainingProgram, TrainingEnrollment, Certification, User
from routes.admin import admin_required

training_bp = Blueprint('training', __name__, url_prefix='/training')

@training_bp.route('/')
@login_required
def dashboard():
    """Training dashboard"""
    if current_user.role == 'admin':
        # Admin view - all training programs
        active_programs = TrainingProgram.query.filter_by(status='active').count()
        total_enrollments = TrainingEnrollment.query.count()
        completed_trainings = TrainingEnrollment.query.filter_by(status='completed').count()
        
        recent_programs = TrainingProgram.query.order_by(TrainingProgram.created_date.desc()).limit(5).all()
        
        return render_template('training/admin_dashboard.html',
                             active_programs=active_programs,
                             total_enrollments=total_enrollments,
                             completed_trainings=completed_trainings,
                             recent_programs=recent_programs)
    else:
        # Employee view - their training
        my_enrollments = TrainingEnrollment.query.filter_by(user_id=current_user.id).all()
        available_programs = TrainingProgram.query.filter_by(status='active').filter(
            TrainingProgram.start_date >= date.today()
        ).all()
        my_certifications = Certification.query.filter_by(user_id=current_user.id, is_active=True).all()
        
        return render_template('training/employee_dashboard.html',
                             my_enrollments=my_enrollments,
                             available_programs=available_programs,
                             my_certifications=my_certifications)

@training_bp.route('/programs')
@login_required
@admin_required
def programs():
    """List all training programs"""
    programs = TrainingProgram.query.order_by(TrainingProgram.created_date.desc()).all()
    return render_template('training/programs.html', programs=programs)

@training_bp.route('/programs/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_program():
    """Add new training program"""
    if request.method == 'POST':
        try:
            program = TrainingProgram(
                name=request.form['name'],
                description=request.form['description'],
                category=request.form['category'],
                duration_hours=int(request.form['duration_hours']),
                trainer_name=request.form.get('trainer_name', ''),
                max_participants=int(request.form['max_participants']) if request.form.get('max_participants') else None,
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
                end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date(),
                created_by=current_user.id
            )
            
            db.session.add(program)
            db.session.commit()
            
            flash('Training program created successfully!', 'success')
            return redirect(url_for('training.programs'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating training program: {str(e)}', 'error')
    
    return render_template('training/add_program.html')

@training_bp.route('/programs/<int:program_id>')
@login_required
@admin_required
def program_details(program_id):
    """View training program details"""
    program = TrainingProgram.query.get_or_404(program_id)
    enrollments = db.session.query(TrainingEnrollment, User).join(
        User, TrainingEnrollment.user_id == User.id
    ).filter(TrainingEnrollment.training_program_id == program_id).all()
    
    return render_template('training/program_details.html', program=program, enrollments=enrollments)

@training_bp.route('/enroll/<int:program_id>', methods=['POST'])
@login_required
def enroll_program(program_id):
    """Enroll in training program"""
    program = TrainingProgram.query.get_or_404(program_id)
    
    # Check if already enrolled
    existing_enrollment = TrainingEnrollment.query.filter_by(
        training_program_id=program_id,
        user_id=current_user.id
    ).first()
    
    if existing_enrollment:
        flash('You are already enrolled in this program.', 'warning')
        return redirect(url_for('training.dashboard'))
    
    # Check capacity
    if program.max_participants:
        current_enrollments = TrainingEnrollment.query.filter_by(training_program_id=program_id).count()
        if current_enrollments >= program.max_participants:
            flash('This program is full. Cannot enroll.', 'error')
            return redirect(url_for('training.dashboard'))
    
    try:
        enrollment = TrainingEnrollment(
            training_program_id=program_id,
            user_id=current_user.id
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        flash('Successfully enrolled in the training program!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error enrolling in program: {str(e)}', 'error')
    
    return redirect(url_for('training.dashboard'))

@training_bp.route('/enrollments/<int:enrollment_id>/complete', methods=['POST'])
@login_required
@admin_required
def complete_enrollment(enrollment_id):
    """Mark enrollment as completed"""
    enrollment = TrainingEnrollment.query.get_or_404(enrollment_id)
    
    try:
        enrollment.status = 'completed'
        enrollment.completion_date = datetime.now()
        enrollment.score = float(request.form['score']) if request.form.get('score') else None
        enrollment.feedback = request.form.get('feedback', '')
        enrollment.certificate_issued = request.form.get('certificate_issued') == 'on'
        
        db.session.commit()
        
        flash('Training completion recorded successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating enrollment: {str(e)}', 'error')
    
    return redirect(url_for('training.program_details', program_id=enrollment.training_program_id))

@training_bp.route('/certifications')
@login_required
def my_certifications():
    """View employee's certifications"""
    certifications = Certification.query.filter_by(user_id=current_user.id, is_active=True).order_by(Certification.issue_date.desc()).all()
    return render_template('training/my_certifications.html', certifications=certifications)

@training_bp.route('/certifications/add', methods=['GET', 'POST'])
@login_required
def add_certification():
    """Add employee certification"""
    if request.method == 'POST':
        try:
            certification = Certification(
                user_id=current_user.id,
                name=request.form['name'],
                issuing_organization=request.form['issuing_organization'],
                issue_date=datetime.strptime(request.form['issue_date'], '%Y-%m-%d').date(),
                expiry_date=datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date() if request.form.get('expiry_date') else None,
                certificate_number=request.form.get('certificate_number', '')
            )
            
            db.session.add(certification)
            db.session.commit()
            
            flash('Certification added successfully!', 'success')
            return redirect(url_for('training.my_certifications'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding certification: {str(e)}', 'error')
    
    return render_template('training/add_certification.html')

@training_bp.route('/reports')
@login_required
@admin_required
def training_reports():
    """Training analytics and reports"""
    # Training completion statistics
    total_programs = TrainingProgram.query.count()
    active_programs = TrainingProgram.query.filter_by(status='active').count()
    total_enrollments = TrainingEnrollment.query.count()
    completed_enrollments = TrainingEnrollment.query.filter_by(status='completed').count()
    
    # Category-wise training data
    category_stats = db.session.query(
        TrainingProgram.category,
        db.func.count(TrainingProgram.id).label('program_count'),
        db.func.count(TrainingEnrollment.id).label('enrollment_count')
    ).outerjoin(TrainingEnrollment).group_by(TrainingProgram.category).all()
    
    # Recent completions
    recent_completions = db.session.query(TrainingEnrollment, TrainingProgram, User).join(
        TrainingProgram, TrainingEnrollment.training_program_id == TrainingProgram.id
    ).join(
        User, TrainingEnrollment.user_id == User.id
    ).filter(
        TrainingEnrollment.status == 'completed'
    ).order_by(TrainingEnrollment.completion_date.desc()).limit(10).all()
    
    return render_template('training/reports.html',
                         total_programs=total_programs,
                         active_programs=active_programs,
                         total_enrollments=total_enrollments,
                         completed_enrollments=completed_enrollments,
                         category_stats=category_stats,
                         recent_completions=recent_completions)