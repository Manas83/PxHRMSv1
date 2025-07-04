from flask import current_app, url_for
from flask_mail import Message
from extensions import mail
import logging

def send_email(to, subject, template):
    """Send email using Flask-Mail"""
    try:
        # Check if mail is properly configured
        if not current_app.config.get('MAIL_USERNAME'):
            logging.warning(f"Mail not configured - skipping email to {to}")
            return False
            
        msg = Message(
            subject=subject,
            recipients=[to],
            html=template,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
        logging.info(f"Email sent successfully to {to}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {to}: {e}")
        return False

def send_onboarding_email(email, temp_password, full_name):
    """Send onboarding email with temporary password"""
    subject = "Welcome to HRMS - Your Account Details"
    
    template = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                <h2 style="color: #333;">Welcome to HRMS</h2>
                <p>Dear {full_name},</p>
                <p>Your HRMS account has been created successfully. Here are your login details:</p>
                
                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Temporary Password:</strong> {temp_password}</p>
                </div>
                
                <p>Please follow these steps to access your account:</p>
                <ol>
                    <li>Click the login link below or visit the HRMS portal</li>
                    <li>Use your email and temporary password to log in</li>
                    <li>Change your password immediately after first login</li>
                </ol>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{url_for('auth.login', _external=True)}" 
                       style="background-color: #007bff; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Login to HRMS
                    </a>
                </div>
                
                <p>If you have any questions, please contact your HR administrator.</p>
                
                <hr style="margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    This is an automated message. Please do not reply to this email.
                </p>
            </div>
        </body>
    </html>
    """
    
    send_email(email, subject, template)

def send_password_reset_email(email, token):
    """Send password reset email"""
    subject = "HRMS - Password Reset Request"
    
    reset_url = url_for('auth.reset_password_token', token=token, _external=True)
    
    template = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                <h2 style="color: #333;">Password Reset Request</h2>
                <p>You have requested a password reset for your HRMS account.</p>
                
                <p>Click the button below to reset your password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #dc3545; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p>This link will expire in 1 hour for security reasons.</p>
                
                <p>If you didn't request this password reset, please ignore this email.</p>
                
                <hr style="margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    This is an automated message. Please do not reply to this email.
                </p>
            </div>
        </body>
    </html>
    """
    
    send_email(email, subject, template)

def send_leave_notification(email, leave_request, status):
    """Send leave approval/rejection notification"""
    subject = f"Leave Request {status.title()}"
    
    template = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                <h2 style="color: #333;">Leave Request Update</h2>
                <p>Your leave request has been <strong>{status}</strong>.</p>
                
                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Leave Type:</strong> {leave_request.leave_type.title()}</p>
                    <p><strong>Duration:</strong> {leave_request.start_date} to {leave_request.end_date}</p>
                    <p><strong>Days:</strong> {leave_request.days_requested}</p>
                    <p><strong>Status:</strong> {status.title()}</p>
                </div>
                
                <p>Please log in to your HRMS account for more details.</p>
                
                <hr style="margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    This is an automated message. Please do not reply to this email.
                </p>
            </div>
        </body>
    </html>
    """
    
    send_email(email, subject, template)
