# HRMS - Human Resource Management System

## Overview

This is a comprehensive Human Resource Management System (HRMS) built with Flask, designed to manage employee data, attendance tracking, leave management, and HR administrative tasks. The system provides role-based access control with separate interfaces for administrators and employees.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database ORM**: SQLAlchemy with Flask-SQLAlchemy extension
- **Authentication**: Flask-Login for session management
- **Email Service**: Flask-Mail for automated email notifications
- **Security**: Werkzeug for password hashing and security utilities

### Frontend Architecture
- **Template Engine**: Jinja2 (Flask's default)
- **CSS Framework**: Bootstrap 5 with dark theme
- **JavaScript**: Vanilla JavaScript with Bootstrap components
- **Icons**: Font Awesome 6.0
- **Responsive Design**: Mobile-first approach using Bootstrap grid system

### Database Schema
- **SQLAlchemy ORM** with declarative base model
- **Database Support**: Configurable (SQLite for development, PostgreSQL for production)
- **Connection Pooling**: Configured with pool recycling and pre-ping
- **Models**: User, Attendance, LeaveRequest, Holiday, Document

## Key Components

### Authentication & Authorization
- **Role-based Access Control**: Admin and Employee roles
- **Secure Password Storage**: Werkzeug password hashing
- **Session Management**: Flask-Login with remember me functionality
- **Password Reset**: Token-based password reset via email
- **First-time Login**: Mandatory password change for new employees

### User Management
- **Employee Onboarding**: Admin-controlled employee creation
- **Profile Management**: Employee self-service profile viewing
- **Account Activation**: Email-based account activation
- **Role Assignment**: Admin/Employee role differentiation

### Attendance System
- **Punch In/Out**: Single daily entry system
- **Geolocation Tracking**: GPS coordinates and IP address logging
- **Work Mode Detection**: Automatic onsite/offsite determination
- **Attendance Calendar**: Visual calendar view for employees and admins
- **Duplicate Prevention**: System prevents double punching and backdating

### Leave Management
- **Leave Types**: Sick, Casual, Earned, Optional Holiday
- **Balance Tracking**: Automatic calculation of leave balances
- **Approval Workflow**: Pending → Approved/Rejected status flow
- **Document Attachments**: Support for leave supporting documents
- **Email Notifications**: Automated status update notifications

### Administrative Features
- **Employee Management**: Add, edit, view employee records
- **Attendance Oversight**: Daily attendance monitoring and reports
- **Leave Approval**: Centralized leave request management
- **Holiday Management**: Company holiday calendar maintenance
- **Reports Generation**: CSV export for attendance and leave data

## Data Flow

### Employee Onboarding Flow
1. Admin creates employee record with basic details
2. System generates temporary password
3. Automated onboarding email sent with login credentials
4. Employee receives email and logs in for first time
5. Mandatory password reset enforced

### Attendance Flow
1. Employee accesses punch-in interface
2. System captures timestamp, IP address, and geolocation
3. Work mode automatically determined (onsite/offsite)
4. Attendance record stored in database
5. Real-time dashboard updates for admin monitoring

### Leave Request Flow
1. Employee submits leave request with details and optional documents
2. System validates leave balance availability
3. Request enters pending status
4. Admin reviews and approves/rejects request
5. Automated email notification sent to employee
6. Leave balance automatically updated if approved

## External Dependencies

### Python Packages
- **Flask**: Core web framework
- **Flask-SQLAlchemy**: Database ORM integration
- **Flask-Login**: User session management
- **Flask-Mail**: Email functionality
- **Werkzeug**: Security utilities and password hashing

### Frontend Libraries
- **Bootstrap 5**: UI framework with dark theme
- **Font Awesome 6**: Icon library
- **jQuery**: (Implied by Bootstrap components)

### Email Service
- **SMTP Configuration**: Configurable mail server (Gmail by default)
- **TLS Security**: Encrypted email transmission
- **Template-based Emails**: HTML email templates for notifications

### File Upload System
- **Upload Directory**: Configurable file storage location
- **File Size Limits**: 16MB maximum file size
- **File Type Validation**: Restricted to safe file extensions
- **Secure Filename Handling**: Prevention of directory traversal attacks

## Deployment Strategy

### Environment Configuration
- **Environment Variables**: All sensitive configuration externalized
- **Database URL**: Configurable database connection
- **Mail Server Settings**: SMTP configuration via environment variables
- **Session Security**: Configurable secret key for session encryption

### Production Considerations
- **Proxy Support**: ProxyFix middleware for reverse proxy deployments
- **Logging**: Comprehensive logging configuration
- **Database Connection Pooling**: Production-ready connection management
- **File Upload Security**: Secure file handling and validation

### Development Setup
- **SQLite Default**: Local development database
- **Debug Mode**: Enabled for development
- **Hot Reloading**: Automatic server restart on code changes
- **Host Configuration**: Bound to all interfaces (0.0.0.0) for container compatibility

## Changelog
- July 02, 2025. Successfully migrated project from Replit Agent to standard Replit environment
- July 02, 2025. Created comprehensive UI templates for employee import and leave report functionality
- July 02, 2025. Fixed SQLAlchemy compatibility warnings for Replit environment
- July 02, 2025. Added manager/reportee feature with hierarchical leave approval workflow
- July 02, 2025. Implemented advanced reporting with PDF/CSV/Excel export functionality
- July 02, 2025. Added employee import feature with manager assignment support
- July 01, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.