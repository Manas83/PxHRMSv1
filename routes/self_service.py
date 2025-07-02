from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from models import db, EmergencyContact, PolicyDocument, PolicyAcknowledgment, Announcement, EmploymentHistory
from utils.helpers import get_client_ip

self_service_bp = Blueprint('self_service', __name__, url_prefix='/self-service')

@self_service_bp.route('/')
@login_required
def dashboard():
    """Employee self-service dashboard"""
    # Get recent announcements
    recent_announcements = Announcement.query.filter(
        Announcement.is_active == True,
        (Announcement.target_audience == 'all') | 
        (Announcement.target_audience == 'department' and Announcement.target_value == current_user.department) |
        (Announcement.target_audience == 'role' and Announcement.target_value == current_user.role)
    ).order_by(Announcement.created_date.desc()).limit(5).all()
    
    # Get pending policy acknowledgments
    pending_policies = db.session.query(PolicyDocument).filter(
        PolicyDocument.is_active == True,
        PolicyDocument.requires_acknowledgment == True,
        ~PolicyDocument.id.in_(
            db.session.query(PolicyAcknowledgment.policy_document_id).filter_by(user_id=current_user.id)
        )
    ).all()
    
    return render_template('self_service/dashboard.html',
                         recent_announcements=recent_announcements,
                         pending_policies=pending_policies)

@self_service_bp.route('/profile')
@login_required
def profile():
    """View employee profile"""
    emergency_contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    employment_history = EmploymentHistory.query.filter_by(user_id=current_user.id).order_by(EmploymentHistory.start_date.desc()).all()
    
    return render_template('self_service/profile.html',
                         emergency_contacts=emergency_contacts,
                         employment_history=employment_history)

@self_service_bp.route('/emergency-contacts', methods=['GET', 'POST'])
@login_required
def emergency_contacts():
    """Manage emergency contacts"""
    if request.method == 'POST':
        try:
            # If setting as primary, remove primary flag from others
            is_primary = request.form.get('is_primary') == 'on'
            if is_primary:
                EmergencyContact.query.filter_by(user_id=current_user.id, is_primary=True).update({'is_primary': False})
            
            contact = EmergencyContact(
                user_id=current_user.id,
                name=request.form['name'],
                relationship=request.form['relationship'],
                phone=request.form['phone'],
                email=request.form.get('email', ''),
                address=request.form.get('address', ''),
                is_primary=is_primary
            )
            
            db.session.add(contact)
            db.session.commit()
            
            flash('Emergency contact added successfully!', 'success')
            return redirect(url_for('self_service.emergency_contacts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding emergency contact: {str(e)}', 'error')
    
    contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    return render_template('self_service/emergency_contacts.html', contacts=contacts)

@self_service_bp.route('/emergency-contacts/<int:contact_id>/delete', methods=['POST'])
@login_required
def delete_emergency_contact(contact_id):
    """Delete emergency contact"""
    contact = EmergencyContact.query.filter_by(id=contact_id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(contact)
        db.session.commit()
        flash('Emergency contact deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting emergency contact: {str(e)}', 'error')
    
    return redirect(url_for('self_service.emergency_contacts'))

@self_service_bp.route('/policies')
@login_required
def policies():
    """View company policies"""
    all_policies = PolicyDocument.query.filter_by(is_active=True).order_by(PolicyDocument.category, PolicyDocument.title).all()
    
    # Get user's acknowledgments
    user_acknowledgments = {ack.policy_document_id: ack for ack in 
                          PolicyAcknowledgment.query.filter_by(user_id=current_user.id).all()}
    
    return render_template('self_service/policies.html',
                         policies=all_policies,
                         user_acknowledgments=user_acknowledgments)

@self_service_bp.route('/policies/<int:policy_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_policy(policy_id):
    """Acknowledge a policy document"""
    policy = PolicyDocument.query.get_or_404(policy_id)
    
    # Check if already acknowledged
    existing_ack = PolicyAcknowledgment.query.filter_by(
        policy_document_id=policy_id,
        user_id=current_user.id
    ).first()
    
    if existing_ack:
        flash('You have already acknowledged this policy.', 'warning')
        return redirect(url_for('self_service.policies'))
    
    try:
        acknowledgment = PolicyAcknowledgment(
            policy_document_id=policy_id,
            user_id=current_user.id,
            ip_address=get_client_ip()
        )
        
        db.session.add(acknowledgment)
        db.session.commit()
        
        flash('Policy acknowledged successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error acknowledging policy: {str(e)}', 'error')
    
    return redirect(url_for('self_service.policies'))

@self_service_bp.route('/announcements')
@login_required
def announcements():
    """View all announcements"""
    all_announcements = Announcement.query.filter(
        Announcement.is_active == True,
        (Announcement.target_audience == 'all') | 
        (Announcement.target_audience == 'department' and Announcement.target_value == current_user.department) |
        (Announcement.target_audience == 'role' and Announcement.target_value == current_user.role)
    ).order_by(Announcement.created_date.desc()).all()
    
    return render_template('self_service/announcements.html', announcements=all_announcements)

@self_service_bp.route('/payslips')
@login_required
def payslips():
    """View payslips (placeholder for future implementation)"""
    # This would integrate with payroll system
    return render_template('self_service/payslips.html')

@self_service_bp.route('/documents')
@login_required
def my_documents():
    """View employee documents"""
    from models import Document
    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_date.desc()).all()
    return render_template('self_service/my_documents.html', documents=documents)

@self_service_bp.route('/leave-balance')
@login_required
def leave_balance():
    """View detailed leave balance"""
    leave_types = ['sick', 'casual', 'earned', 'optional']
    leave_balances = {}
    
    for leave_type in leave_types:
        balance = current_user.get_leave_balance(leave_type)
        leave_balances[leave_type] = balance
    
    # Get recent leave history
    recent_leaves = current_user.leave_requests.order_by(
        current_user.leave_requests.property.mapper.class_.applied_date.desc()
    ).limit(10).all()
    
    return render_template('self_service/leave_balance.html',
                         leave_balances=leave_balances,
                         recent_leaves=recent_leaves)

@self_service_bp.route('/update-profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    """Update basic profile information"""
    if request.method == 'POST':
        try:
            # Only allow updating certain fields
            current_user.phone = request.form.get('phone', current_user.phone)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('self_service.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
    
    return render_template('self_service/update_profile.html')