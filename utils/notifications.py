"""
Notification utility functions for HRMS
Handles both in-app notifications and email notifications
"""
from models import Notification, User
from extensions import db
from utils.email import send_email
from datetime import datetime


def create_notification(user_id, title, message, notification_type, related_id=None):
    """Create an in-app notification for a user"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_id=related_id
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def send_leave_request_notification(leave_request):
    """Send notifications when a leave request is submitted"""
    employee = leave_request.user
    
    # Create notification for manager if exists
    if employee.manager_id:
        manager = User.query.get(employee.manager_id)
        if manager:
            # In-app notification for manager
            create_notification(
                user_id=manager.id,
                title=f"New Leave Request from {employee.full_name}",
                message=f"{employee.full_name} has requested {leave_request.leave_type} leave from {leave_request.start_date} to {leave_request.end_date} ({leave_request.days_requested} days). Reason: {leave_request.reason}",
                notification_type="leave_request_pending",
                related_id=leave_request.id
            )
            
            # Email notification to manager
            subject = f"Leave Request Approval Required - {employee.full_name}"
            email_body = f"""
Dear {manager.first_name},

{employee.full_name} has submitted a leave request that requires your approval.

Leave Details:
- Employee: {employee.full_name} ({employee.employee_id})
- Leave Type: {leave_request.leave_type.title()}
- Duration: {leave_request.start_date} to {leave_request.end_date}
- Total Days: {leave_request.days_requested}
- Reason: {leave_request.reason}

Please log in to the HRMS system to review and approve this request.

Thank you,
HRMS System
            """
            send_email(manager.email, subject, email_body)
    
    # Send copy to all HR users
    hr_users = User.query.filter_by(role='hr', active=True).all()
    for hr_user in hr_users:
        # In-app notification for HR
        create_notification(
            user_id=hr_user.id,
            title=f"New Leave Request - {employee.full_name}",
            message=f"{employee.full_name} has submitted a {leave_request.leave_type} leave request from {leave_request.start_date} to {leave_request.end_date} ({leave_request.days_requested} days).",
            notification_type="leave_request_info",
            related_id=leave_request.id
        )
        
        # Email notification to HR
        subject = f"Leave Request Submitted - {employee.full_name}"
        email_body = f"""
Dear {hr_user.first_name},

A new leave request has been submitted for your information.

Leave Details:
- Employee: {employee.full_name} ({employee.employee_id})
- Department: {employee.department}
- Leave Type: {leave_request.leave_type.title()}
- Duration: {leave_request.start_date} to {leave_request.end_date}
- Total Days: {leave_request.days_requested}
- Reason: {leave_request.reason}
- Manager: {employee.manager.full_name if employee.manager else 'No manager assigned'}

This is for your information. The request will be processed by the employee's manager.

Best regards,
HRMS System
        """
        send_email(hr_user.email, subject, email_body)


def send_leave_approval_notification(leave_request, approved_by):
    """Send notifications when a leave request is approved/rejected"""
    employee = leave_request.user
    status = leave_request.status.title()
    
    # In-app notification for employee
    title = f"Leave Request {status}"
    if leave_request.status == 'approved':
        message = f"Your {leave_request.leave_type} leave request from {leave_request.start_date} to {leave_request.end_date} has been approved by {approved_by.full_name}."
        notification_type = "leave_approved"
    else:
        message = f"Your {leave_request.leave_type} leave request from {leave_request.start_date} to {leave_request.end_date} has been rejected by {approved_by.full_name}."
        if leave_request.admin_notes:
            message += f" Reason: {leave_request.admin_notes}"
        notification_type = "leave_rejected"
    
    create_notification(
        user_id=employee.id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_id=leave_request.id
    )
    
    # Email notification to employee
    subject = f"Leave Request {status} - {leave_request.leave_type.title()} Leave"
    email_body = f"""
Dear {employee.first_name},

Your leave request has been {leave_request.status}.

Leave Details:
- Leave Type: {leave_request.leave_type.title()}
- Duration: {leave_request.start_date} to {leave_request.end_date}
- Total Days: {leave_request.days_requested}
- Status: {status}
- Reviewed by: {approved_by.full_name}
- Review Date: {leave_request.reviewed_date.strftime('%Y-%m-%d %H:%M') if leave_request.reviewed_date else 'N/A'}
"""
    
    if leave_request.admin_notes:
        email_body += f"- Notes: {leave_request.admin_notes}\n"
    
    email_body += f"""
You can view your leave history by logging into the HRMS system.

Best regards,
HRMS System
    """
    
    send_email(employee.email, subject, email_body)
    
    # Notify HR users about the decision
    hr_users = User.query.filter_by(role='hr', active=True).all()
    for hr_user in hr_users:
        create_notification(
            user_id=hr_user.id,
            title=f"Leave Request {status} - {employee.full_name}",
            message=f"{approved_by.full_name} has {leave_request.status} {employee.full_name}'s {leave_request.leave_type} leave request from {leave_request.start_date} to {leave_request.end_date}.",
            notification_type="leave_decision_info",
            related_id=leave_request.id
        )


def get_unread_notifications(user_id):
    """Get all unread notifications for a user"""
    return Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).order_by(Notification.created_date.desc()).all()


def mark_notification_read(notification_id, user_id):
    """Mark a notification as read"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=user_id
    ).first()
    if notification:
        notification.is_read = True
        db.session.commit()
        return True
    return False


def mark_all_notifications_read(user_id):
    """Mark all notifications as read for a user"""
    Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()