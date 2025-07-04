# HRMS - Human Resource Management System

## Overview

This is a comprehensive, enterprise-grade Human Resource Management System (HRMS) built with Flask, designed to handle all aspects of HR operations including employee lifecycle management, recruitment, training, attendance tracking, leave management, exit processes, and employee self-service. The system provides role-based access control with interfaces for administrators, managers, and employees, covering the complete spectrum of HR functionality.

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
- **Role-based Access Control**: Admin, Manager, and Employee roles with hierarchical permissions
- **Secure Password Storage**: Werkzeug password hashing
- **Session Management**: Flask-Login with remember me functionality
- **Password Reset**: Token-based password reset via email
- **First-time Login**: Mandatory password change for new employees

### Employee Information Management
- **Personal & Job Details**: Comprehensive employee profiles with employment history
- **Emergency Contacts**: Multiple contact management with priority designation
- **Document Storage**: Secure file upload and management for employee documents
- **Manager-Employee Relationships**: Hierarchical reporting structure with automatic workflow routing
- **Employment History Tracking**: Complete job progression and role change history

### Attendance & Time Tracking
- **Daily Punch-in/Punch-out**: Single daily entry system with onsite/offsite detection
- **Geolocation Tracking**: GPS coordinates and IP address logging for location verification
- **Work Mode Detection**: Automatic onsite/offsite determination based on location
- **Work Hours Calculation**: Automatic calculation of total working hours and overtime
- **Attendance Calendar**: Visual calendar view for employees and admins
- **Duplicate Prevention**: System prevents double punching and backdating
- **Comprehensive Reporting**: Detailed attendance reports with export functionality

### Leave Management
- **Multiple Leave Types**: Sick, Casual, Earned, Optional Holiday with configurable policies
- **Advanced Balance Tracking**: Automatic calculation with carry-forward and encashment rules
- **Hierarchical Approval Workflow**: Manager and admin approval routing
- **Document Attachments**: Support for leave supporting documents
- **Email Notifications**: Automated status update notifications
- **Holiday Calendar Management**: Company-wide holiday planning and optional holiday selection

### Recruitment & Onboarding
- **Job Posting Management**: Create, publish, and manage job openings
- **Application Tracking**: Complete applicant lifecycle management
- **Interview Scheduling**: Multi-round interview coordination with feedback collection
- **Resume Management**: Secure resume storage and retrieval
- **Public Job Portal**: Candidate-facing job application interface
- **Onboarding Workflows**: New hire process management with checklist tracking

### Training & Development
- **Training Program Management**: Create and manage comprehensive training programs
- **Enrollment System**: Employee self-enrollment with capacity management
- **Progress Tracking**: Monitor training completion and scores
- **Certification Management**: Employee certification tracking with expiry monitoring
- **Training Reports**: Analytics on training effectiveness and completion rates
- **Category-based Organization**: Technical, soft-skills, compliance, and leadership training

### Employee Self-Service Portal
- **Profile Management**: Employee self-service profile updates
- **Leave Applications**: Online leave request submission with balance viewing
- **Document Access**: Personal document viewing and download
- **Policy Acknowledgment**: Digital policy reading and acknowledgment tracking
- **Announcements**: Company-wide and targeted communication
- **Emergency Contact Management**: Self-service contact information updates

### Exit & Offboarding
- **Resignation Management**: Digital resignation submission and approval workflow
- **Exit Interview System**: Structured exit interview process with feedback collection
- **Notice Period Tracking**: Automatic calculation and monitoring
- **Final Settlement Process**: Comprehensive offboarding workflow
- **Analytics**: Exit trends and feedback analysis for retention insights

### HR Analytics & Reports
- **Comprehensive Dashboards**: Headcount, attendance, leave, and attrition analytics
- **Multi-format Export**: Excel, PDF, and CSV export capabilities
- **Custom Report Generation**: Flexible reporting with date range and filter options
- **Trend Analysis**: Historical data visualization and trend identification
- **Department-wise Analytics**: Segmented reporting for organizational insights

### Compliance & Policy Management
- **Policy Document Management**: Centralized policy storage and version control
- **Digital Acknowledgment Tracking**: Employee policy reading confirmation
- **Compliance Monitoring**: Automated tracking of policy acknowledgments
- **Audit Trail**: Complete activity logging for compliance requirements

### Notifications & Alerts
- **Email Notifications**: Automated alerts for approvals, reminders, and status updates
- **Targeted Announcements**: Role-based and department-specific communications
- **Birthday & Anniversary Tracking**: Automated celebration reminders
- **Policy Update Alerts**: Notification system for new policy requirements

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
- July 04, 2025. Implemented comprehensive notification system with email alerts and in-app notifications
- July 04, 2025. Added leave request workflow with automatic notifications to managers and HR
- July 04, 2025. Created manager approval system with email notifications to employees
- July 04, 2025. Built notifications dropdown in navigation with real-time unread count
- July 04, 2025. Enhanced manager dashboard with prominent pending leave alerts
- July 04, 2025. Added comprehensive employee edit functionality for Admin and HR users
- July 04, 2025. Created full-featured edit employee interface with all personal, employment, and contact details
- July 04, 2025. Added Edit button to employee list with proper access control
- July 04, 2025. Implemented default leave policies creation script for system initialization
- July 04, 2025. Created test users for different roles with proper role-based access
- July 03, 2025. Implemented advanced leave management system with employment status-based policies
- July 03, 2025. Added HR configurable leave types and allocation management
- July 03, 2025. Enhanced employee models with probation/confirmed status tracking
- July 03, 2025. Created dynamic leave balance calculation based on employment status
- July 03, 2025. Built leave policy management interface for HR users
- July 03, 2025. Updated employee forms and import to handle employment status
- July 03, 2025. Successfully migrated project to Replit environment with full functionality
- July 02, 2025. Implemented comprehensive role-based access control with profile-based menu display
- July 02, 2025. Added role assignment functionality in employee import and add employee features
- July 02, 2025. Updated navigation to show appropriate menus based on user roles (Employee, Manager, HR, Admin)
- July 02, 2025. Enhanced employee management with role display and proper access restrictions
- July 02, 2025. Successfully completed comprehensive HRMS expansion with enterprise-grade features
- July 02, 2025. Implemented complete recruitment module with job posting, application tracking, and interview management
- July 02, 2025. Added comprehensive training and development system with certification tracking
- July 02, 2025. Built complete exit management system with resignation workflow and exit interviews
- July 02, 2025. Created extensive employee self-service portal with policy management and announcements
- July 02, 2025. Enhanced navigation structure with organized dropdown menus for all modules
- July 02, 2025. Extended database schema with 13 new models covering all HR processes
- July 02, 2025. Successfully migrated project from Replit Agent to standard Replit environment
- July 02, 2025. Created comprehensive UI templates for employee import and leave report functionality
- July 02, 2025. Fixed SQLAlchemy compatibility warnings for Replit environment
- July 02, 2025. Added manager/reportee feature with hierarchical leave approval workflow
- July 02, 2025. Implemented advanced reporting with PDF/CSV/Excel export functionality
- July 02, 2025. Added employee import feature with manager assignment support
- July 01, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.